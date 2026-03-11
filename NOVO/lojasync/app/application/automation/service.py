from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from app.application.products.service import ProductService
from app.domain.products.entities import Product

logger = logging.getLogger(__name__)

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - depends on local OS
    pyautogui = None  # type: ignore


class AutomationService:
    def __init__(self, product_service: ProductService, data_dir: Path) -> None:
        self._products = product_service
        self._data_dir = data_dir
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_result: dict[str, str] | None = None
        self._cancel_event = threading.Event()

    def targets_path(self) -> Path:
        return self._data_dir / "targets.json"

    def _legacy_targets_path(self) -> Path:
        return self._workspace_root() / "engine" / "data" / "targets.json"

    def load_targets(self) -> dict[str, Any]:
        for path in (self.targets_path(), self._legacy_targets_path()):
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                return payload
        return {}

    def save_targets(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_targets()
        current.update(payload)
        path = self.targets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return current

    def capture_target(self, target: str) -> dict[str, Any]:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI nao disponivel para captura de coordenadas")
        name = (target or "").strip()
        if not name:
            raise RuntimeError("Target invalido")
        try:
            x, y = pyautogui.position()
        except Exception as exc:  # pragma: no cover - OS integration
            raise RuntimeError(f"Falha ao capturar coordenadas: {exc}") from exc
        return {"target": name, "point": {"x": int(x), "y": int(y)}}

    def execute(self) -> dict[str, str]:
        with self._lock:
            if self._running:
                raise RuntimeError("Ja existe uma automacao em execucao")
            self._cancel_event.clear()
            self._running = True
            self._last_result = None
            self._thread = threading.Thread(target=self._run_local, name="lojasync-local-automation", daemon=True)
            self._thread.start()
            return {"status": "started", "message": "Sequencia basica disparada"}

    def cancel(self) -> dict[str, str]:
        with self._lock:
            if not self._running:
                return {"status": "idle", "message": "Nenhuma automacao em execucao"}
            self._cancel_event.set()
            return {"status": "stopping", "message": "Cancelamento solicitado"}

    def status(self) -> dict[str, str | None]:
        with self._lock:
            state = "running" if self._running else "idle"
            payload: dict[str, str | None] = {
                "estado": state,
                "cancel_requested": "True" if self._cancel_event.is_set() and self._running else "False",
            }
            if self._last_result:
                payload.update(self._last_result)
            return payload

    def agents(self) -> dict[str, list[dict[str, Any]]]:
        status = self.status()
        return {
            "agents": [
                {
                    "agent_id": "Executor Local",
                    "status": status.get("estado", "idle"),
                    "capabilities": ["pyautogui"],
                    "last_seen": 0,
                    "last_event": {"message": status.get("message", "Executor interno")},
                    "kind": "local",
                    "is_local": True,
                    "synchronized": status.get("estado") in {"idle", "running"},
                }
            ]
        }

    def get_gradebot_config(self) -> dict[str, Any]:
        path = self._gradebot_config_path()
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def set_gradebot_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = self.get_gradebot_config()
        config.setdefault("buttons", {})
        config.setdefault("grid", {})
        config.setdefault("model", {"strategy": "index", "index": 0})

        buttons = payload.get("buttons")
        if isinstance(buttons, dict):
            for key, point in buttons.items():
                if isinstance(point, dict) and "x" in point and "y" in point:
                    config["buttons"][key] = {"x": int(point["x"]), "y": int(point["y"])}

        first_quant = payload.get("first_quant_cell")
        second_quant = payload.get("second_quant_cell")
        row_height = payload.get("row_height")
        if isinstance(first_quant, dict) and "x" in first_quant and "y" in first_quant:
            config["grid"]["first_quant_cell"] = (int(first_quant["x"]), int(first_quant["y"]))
        if row_height is None and isinstance(first_quant, dict) and isinstance(second_quant, dict):
            row_height = max(1, int(second_quant["y"]) - int(first_quant["y"]))
        if row_height is not None:
            config["grid"]["row_height"] = int(row_height)

        if payload.get("model_index") is not None:
            config["model"]["index"] = int(payload["model_index"])
            config["model"]["strategy"] = "index"
        if payload.get("model_hotkey") is not None:
            hotkey = str(payload["model_hotkey"]).strip()
            config["model"]["hotkey"] = hotkey
            config["model"]["strategy"] = "hotkey" if hotkey else "index"

        if isinstance(payload.get("erp_size_order"), list):
            config["erp_size_order"] = [
                str(item).strip() for item in payload["erp_size_order"] if str(item).strip()
            ]

        path = self._gradebot_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return config

    def run_gradebot(
        self,
        *,
        grades: dict[str, int] | None,
        grades_json: str | None,
        model_index: int | None,
        pause: float | None,
        speed: float | None,
    ) -> dict[str, str]:
        gradebot = self._load_gradebot()
        if grades_json:
            grades_map = gradebot.parse_grades_json(grades_json)
        elif grades:
            grades_map = {str(key): int(value) for key, value in grades.items()}
        else:
            raise RuntimeError("Informe 'grades' ou 'grades_json'.")

        def _run() -> None:
            try:
                if pause is not None:
                    gradebot.pag.PAUSE = max(0.0, float(pause))
                if speed is not None:
                    gradebot.SPEED = max(0.05, float(speed))
                gradebot.reset_stop_flag()
                gradebot.run(grades_map, model_index=model_index, activation_step=True)
            except Exception:
                logger.exception("Falha ao executar GradeBot")

        threading.Thread(target=_run, name="lojasync-gradebot", daemon=True).start()
        return {"status": "started"}

    def run_gradebot_batch(
        self,
        *,
        tasks: list[dict[str, Any]],
        pause: float | None,
        speed: float | None,
    ) -> dict[str, Any]:
        gradebot = self._load_gradebot()
        if pause is not None:
            gradebot.pag.PAUSE = max(0.0, float(pause))
        if speed is not None:
            gradebot.SPEED = max(0.05, float(speed))
        gradebot.reset_stop_flag()
        total = 0
        activation_step = True
        for task in tasks or []:
            if gradebot.is_cancel_requested():
                break
            if isinstance(task.get("grades_json"), str) and task["grades_json"].strip():
                grades_map = gradebot.parse_grades_json(task["grades_json"])
            elif isinstance(task.get("grades"), dict):
                grades_map = {str(key): int(value) for key, value in task["grades"].items()}
            else:
                continue
            gradebot.run(grades_map, model_index=task.get("model_index"), activation_step=activation_step)
            activation_step = False
            total += 1
        return {"status": "ok", "executados": total}

    def stop_gradebot(self) -> dict[str, str]:
        gradebot = self._load_gradebot()
        gradebot.request_stop()
        return {"status": "stopping"}

    def _run_local(self) -> None:
        started_at = time.time()
        result: dict[str, str]
        try:
            products = self._products.list_products()
            if not products:
                raise RuntimeError("Nenhum produto disponivel para cadastrar.")
            if pyautogui is None:
                raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")

            targets = self.load_targets()
            if not targets:
                raise RuntimeError("Coordenadas de calibracao nao encontradas.")

            byte_empresa = self._load_byte_empresa_module()
            byte_empresa.recarregar_config_automacao()
            success, message = byte_empresa.ativar_janela_byte_empresa(targets)
            if not success:
                raise RuntimeError(f"Falha ao ativar Byte Empresa: {message}")

            completed_keys: list[str] = []
            failures = 0
            for product in products:
                self._check_cancel()
                payload = self._product_to_payload(product)
                ok1 = byte_empresa.executar_tela1_mecanico(payload, targets, self._cancel_event)
                if not ok1:
                    failures += 1
                    continue
                ok2 = byte_empresa.executar_tela2_mecanico(payload, targets, self._cancel_event)
                if not ok2:
                    failures += 1
                    continue
                completed_keys.append(product.ordering_key())

            metrics: dict[str, int] = {}
            if completed_keys:
                records = self._products.get_by_ordering_keys(completed_keys)
                metrics = self._products.record_automation_success(records)

            duration = f"{time.time() - started_at:.2f}s"
            result = {
                "status": "success",
                "message": "Fluxo Byte Empresa concluido",
                "duration": duration,
                "sucesso": str(len(completed_keys)),
            }
            if failures:
                result["falhas"] = str(failures)
            if metrics:
                result["tempo_economizado"] = str(metrics.get("tempo_economizado", 0))
                result["caracteres_digitados"] = str(metrics.get("caracteres_digitados", 0))
        except KeyboardInterrupt as exc:
            result = {
                "status": "cancelled",
                "message": str(exc) or "Automacao cancelada",
                "duration": f"{time.time() - started_at:.2f}s",
            }
        except Exception as exc:
            logger.exception("Falha na automacao local")
            result = {
                "status": "error",
                "message": str(exc),
                "duration": f"{time.time() - started_at:.2f}s",
            }
        finally:
            with self._lock:
                self._running = False
                self._thread = None
                self._last_result = result
                self._cancel_event.clear()

    def _check_cancel(self) -> None:
        if self._cancel_event.is_set():
            raise KeyboardInterrupt("Automacao cancelada pelo usuario")

    def _product_to_payload(self, product: Product) -> dict[str, Any]:
        descricao = product.descricao_completa or f"{product.nome} {product.marca} {product.codigo}".strip()
        return {
            "nome": product.nome,
            "codigo": product.codigo,
            "quantidade": str(product.quantidade),
            "preco": product.preco,
            "preco_final": product.preco_final or product.preco,
            "categoria": product.categoria,
            "marca": product.marca,
            "descricao_completa": descricao,
            "grades": [
                {"tamanho": item.tamanho, "quantidade": int(item.quantidade)}
                for item in (product.grades or [])
            ]
            if product.grades
            else None,
            "cores": [
                {"cor": item.cor, "quantidade": int(item.quantidade)}
                for item in (product.cores or [])
            ]
            if product.cores
            else None,
            "ordering_key": product.ordering_key(),
        }

    def _candidate_project_roots(self) -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def _add(path: Path | None) -> None:
            if path is None:
                return
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            key = str(resolved).lower()
            if key in seen:
                return
            seen.add(key)
            candidates.append(resolved)

        for env_name in ("LOJASYNC_WORKSPACE_ROOT", "LOJASYNC_LEGACY_ROOT", "LOJASYNC_ENGINE_ROOT"):
            raw = (os.getenv(env_name) or "").strip()
            if not raw:
                continue
            env_path = Path(raw)
            _add(env_path.parent if env_name == "LOJASYNC_ENGINE_ROOT" and env_path.name.lower() == "engine" else env_path)

        service_path = Path(__file__).resolve()
        for parent in service_path.parents:
            _add(parent)
            for child_name in ("LojaSync", "NOVO", "LojaSync120226"):
                _add(parent / child_name)

        desktop = next((parent for parent in service_path.parents if parent.name.lower() == "desktop"), None)
        if desktop and desktop.exists():
            for child in desktop.iterdir():
                if child.is_dir():
                    _add(child)

        return candidates

    def _find_project_root(self, relative_path: str) -> Path | None:
        target = Path(relative_path)
        for root in self._candidate_project_roots():
            if (root / target).exists():
                return root
            legacy_root = root / "Legacy"
            if (legacy_root / target).exists():
                return legacy_root
        return None

    def _workspace_root(self) -> Path:
        fallback = Path(__file__).resolve().parents[5]
        return (
            self._find_project_root("engine/modules/automation/byte_empresa.py")
            or self._find_project_root("automation/gradebot/gradebot.py")
            or fallback
        )

    def _gradebot_config_path(self) -> Path:
        project_root = self._find_project_root("automation/gradebot/gradebot.py") or self._workspace_root()
        return project_root / "automation" / "gradebot" / "config.json"

    def _load_byte_empresa_module(self) -> Any:
        project_root = self._find_project_root("engine/modules/automation/byte_empresa.py") or self._workspace_root()
        engine_root = project_root / "engine"
        module_file = engine_root / "modules" / "automation" / "byte_empresa.py"
        if not module_file.exists():
            raise RuntimeError(
                f"Modulo legado do Byte Empresa nao encontrado em '{module_file}'. "
                "Defina LOJASYNC_WORKSPACE_ROOT apontando para a raiz que contem a pasta engine."
            )
        if str(engine_root) not in sys.path:
            sys.path.insert(0, str(engine_root))
        return importlib.import_module("modules.automation.byte_empresa")

    def _load_gradebot(self) -> Any:
        project_root = self._find_project_root("automation/gradebot/gradebot.py") or self._workspace_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            return importlib.import_module("automation.gradebot.gradebot")
        except ModuleNotFoundError:
            module_path = project_root / "automation" / "gradebot" / "gradebot.py"
            if not module_path.exists():
                raise RuntimeError(
                    f"Arquivo gradebot.py nao encontrado em '{module_path}'. "
                    "Defina LOJASYNC_WORKSPACE_ROOT apontando para a raiz correta."
                )
            spec = importlib.util.spec_from_file_location("lojasync_gradebot", str(module_path))
            if spec is None or spec.loader is None:
                raise RuntimeError("Falha ao preparar import do GradeBot.")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module
