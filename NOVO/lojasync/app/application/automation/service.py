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

from app.application.automation.profiles import (
    has_gradebot_configuration,
    load_json_object,
    merge_gradebot_config,
    normalize_gradebot_config,
    normalize_targets,
    save_json_object,
)
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
        self._active_job_kind: str | None = None
        self._active_job_message: str | None = None
        self._gradebot_module: Any | None = None

    def targets_path(self) -> Path:
        return self._data_dir / "targets.json"

    def desktop_profile_path(self) -> Path:
        return self._data_dir / "desktop_automation.json"

    def _legacy_targets_path(self) -> Path:
        return self._workspace_root() / "engine" / "data" / "targets.json"

    def _legacy_byte_empresa_config_path(self) -> Path:
        return self._workspace_root() / "engine" / "data" / "automacao.json"

    def _load_desktop_profile(self) -> dict[str, Any]:
        profile = load_json_object(self.desktop_profile_path(), repair=True)
        return profile if isinstance(profile, dict) else {}

    def _save_desktop_profile(self, profile: dict[str, Any]) -> None:
        save_json_object(self.desktop_profile_path(), profile)

    def _sync_legacy_targets(self, targets: dict[str, Any]) -> None:
        normalized = normalize_targets(targets)
        if not normalized:
            return
        save_json_object(self.targets_path(), normalized)
        save_json_object(self._legacy_targets_path(), normalized)

    def _sync_legacy_gradebot_config(self, config: dict[str, Any]) -> None:
        normalized = normalize_gradebot_config(config)
        if not normalized:
            return
        save_json_object(self._gradebot_config_path(), normalized)

    def _sync_legacy_byte_empresa_config(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict) or not config:
            return
        save_json_object(self._legacy_byte_empresa_config_path(), config)

    def _sync_legacy_automation_files(self) -> None:
        targets = self.load_targets()
        if targets:
            self._sync_legacy_targets(targets)
        gradebot_config = self.get_gradebot_config()
        if gradebot_config:
            self._sync_legacy_gradebot_config(gradebot_config)
        profile = self._load_desktop_profile()
        byte_empresa_config = profile.get("byte_empresa")
        if not isinstance(byte_empresa_config, dict) or not byte_empresa_config:
            byte_empresa_config = load_json_object(self._legacy_byte_empresa_config_path(), repair=True)
            if isinstance(byte_empresa_config, dict) and byte_empresa_config:
                profile["byte_empresa"] = byte_empresa_config
                self._save_desktop_profile(profile)
        if isinstance(byte_empresa_config, dict) and byte_empresa_config:
            self._sync_legacy_byte_empresa_config(byte_empresa_config)

    def load_targets(self) -> dict[str, Any]:
        profile = self._load_desktop_profile()
        profile_targets = normalize_targets(profile.get("targets"))
        if profile_targets:
            self._sync_legacy_targets(profile_targets)
            return profile_targets

        for path in (self.targets_path(), self._legacy_targets_path()):
            payload = load_json_object(path, repair=True)
            normalized = normalize_targets(payload)
            if normalized:
                profile["targets"] = normalized
                self._save_desktop_profile(profile)
                self._sync_legacy_targets(normalized)
                return normalized
        return {}

    def save_targets(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_targets()
        current.update(normalize_targets(payload))
        normalized = normalize_targets(current)
        profile = self._load_desktop_profile()
        profile["targets"] = normalized
        self._save_desktop_profile(profile)
        self._sync_legacy_targets(normalized)
        return normalized

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
        self._ensure_bulk_ready()
        return self._start_background_operation(
            kind="catalog",
            thread_name="lojasync-local-automation",
            started_message="Cadastro em massa iniciado",
            worker=self._run_catalog_worker,
        )

    def cancel(self) -> dict[str, str]:
        with self._lock:
            if not self._running:
                return {"status": "idle", "message": "Nenhuma automacao em execucao"}
            self._cancel_event.set()
            if self._active_job_kind == "grades":
                try:
                    self._load_gradebot().request_stop()
                except Exception:
                    logger.exception("Falha ao solicitar parada do GradeBot")
            message = "Cancelamento solicitado"
            if self._active_job_kind == "grades":
                message = "Parada do GradeBot solicitada"
            return {"status": "stopping", "message": message}

    def status(self) -> dict[str, str | None]:
        with self._lock:
            state = "running" if self._running else "idle"
            payload: dict[str, str | None] = {
                "estado": state,
                "cancel_requested": "True" if self._cancel_event.is_set() and self._running else "False",
            }
            if self._running:
                if self._active_job_kind:
                    payload["job_kind"] = self._active_job_kind
                if self._active_job_message:
                    payload["message"] = self._active_job_message
            elif self._last_result:
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
        profile = self._load_desktop_profile()
        current = normalize_gradebot_config(profile.get("gradebot"))
        if has_gradebot_configuration(current):
            self._sync_legacy_gradebot_config(current)
            return current

        payload = load_json_object(self._gradebot_config_path(), repair=True)
        current = normalize_gradebot_config(payload)
        if has_gradebot_configuration(current):
            profile["gradebot"] = current
            self._save_desktop_profile(profile)
            self._sync_legacy_gradebot_config(current)
        return current

    def set_gradebot_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = merge_gradebot_config(self.get_gradebot_config(), payload)
        profile = self._load_desktop_profile()
        profile["gradebot"] = config
        self._save_desktop_profile(profile)
        self._sync_legacy_gradebot_config(config)
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
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")
        self._sync_legacy_automation_files()
        self._ensure_gradebot_ready()
        if grades_json:
            grades_map = self._load_gradebot().parse_grades_json(grades_json)
        elif grades:
            grades_map = {str(key): int(value) for key, value in grades.items()}
        else:
            raise RuntimeError("Informe 'grades' ou 'grades_json'.")
        return self._start_background_operation(
            kind="grades",
            thread_name="lojasync-gradebot",
            started_message="Insercao de grades iniciada",
            worker=lambda: self._run_gradebot_worker(
                tasks=[{"grades": grades_map, "model_index": model_index}],
                pause=pause,
                speed=speed,
            ),
        )

    def run_gradebot_batch(
        self,
        *,
        tasks: list[dict[str, Any]],
        pause: float | None,
        speed: float | None,
    ) -> dict[str, Any]:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")
        self._sync_legacy_automation_files()
        self._ensure_gradebot_ready()
        prepared_tasks: list[dict[str, Any]] = []
        gradebot = self._load_gradebot()
        for task in tasks or []:
            if isinstance(task.get("grades_json"), str) and task["grades_json"].strip():
                grades_map = gradebot.parse_grades_json(task["grades_json"])
            elif isinstance(task.get("grades"), dict):
                grades_map = {str(key): int(value) for key, value in task["grades"].items()}
            else:
                continue
            if grades_map:
                prepared_tasks.append({"grades": grades_map, "model_index": task.get("model_index")})
        if not prepared_tasks:
            raise RuntimeError("Nenhuma grade valida foi informada para execucao.")
        return self._start_background_operation(
            kind="grades",
            thread_name="lojasync-gradebot-batch",
            started_message=f"Insercao de grades iniciada para {len(prepared_tasks)} produto(s)",
            worker=lambda: self._run_gradebot_worker(tasks=prepared_tasks, pause=pause, speed=speed),
        )

    def stop_gradebot(self) -> dict[str, str]:
        with self._lock:
            if not self._running or self._active_job_kind != "grades":
                return {"status": "idle", "message": "Nenhuma automacao de grades em execucao"}
        return self.cancel()

    def _run_catalog_worker(self) -> dict[str, str]:
        started_at = time.time()
        try:
            products = self._products.list_products()
            if not products:
                raise RuntimeError("Nenhum produto disponivel para cadastrar.")
            if pyautogui is None:
                raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")

            targets = self.load_targets()
            if not targets:
                raise RuntimeError("Coordenadas de calibracao nao encontradas.")
            self._sync_legacy_automation_files()

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
                "job_kind": "catalog",
            }
            if failures:
                result["falhas"] = str(failures)
            if metrics:
                result["tempo_economizado"] = str(metrics.get("tempo_economizado", 0))
                result["caracteres_digitados"] = str(metrics.get("caracteres_digitados", 0))
            return result
        except KeyboardInterrupt as exc:
            return {
                "status": "cancelled",
                "message": str(exc) or "Automacao cancelada",
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "catalog",
            }
        except Exception as exc:
            logger.exception("Falha na automacao local")
            return {
                "status": "error",
                "message": str(exc),
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "catalog",
            }

    def _run_gradebot_worker(
        self,
        *,
        tasks: list[dict[str, Any]],
        pause: float | None,
        speed: float | None,
    ) -> dict[str, str]:
        started_at = time.time()
        try:
            gradebot = self._load_gradebot()
            if pause is not None:
                gradebot.pag.PAUSE = max(0.0, float(pause))
            if speed is not None:
                gradebot.SPEED = max(0.05, float(speed))
            gradebot.reset_stop_flag()

            total = len(tasks)
            executed = 0
            activation_step = True
            self._set_active_message(
                "Executando GradeBot..." if total <= 1 else f"Executando GradeBot em lote ({total} produtos)"
            )

            for index, task in enumerate(tasks, start=1):
                if self._cancel_event.is_set() or gradebot.is_cancel_requested():
                    raise KeyboardInterrupt("Automacao de grades cancelada pelo usuario")
                grades_map = task.get("grades") if isinstance(task.get("grades"), dict) else {}
                if not grades_map:
                    continue
                self._set_active_message(
                    f"Executando GradeBot no produto {index}/{total}" if total > 1 else "Executando GradeBot..."
                )
                gradebot.run(grades_map, model_index=task.get("model_index"), activation_step=activation_step)
                activation_step = False
                executed += 1

            return {
                "status": "success",
                "message": "Fluxo de grades concluido",
                "duration": f"{time.time() - started_at:.2f}s",
                "sucesso": str(executed),
                "job_kind": "grades",
            }
        except KeyboardInterrupt as exc:
            return {
                "status": "cancelled",
                "message": str(exc) or "Automacao de grades cancelada",
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "grades",
            }
        except Exception as exc:
            logger.exception("Falha ao executar GradeBot")
            return {
                "status": "error",
                "message": str(exc),
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "grades",
            }

    def _check_cancel(self) -> None:
        if self._cancel_event.is_set():
            raise KeyboardInterrupt("Automacao cancelada pelo usuario")

    def _ensure_bulk_ready(self) -> None:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")
        targets = self.load_targets()
        missing: list[str] = []
        for key in ("byte_empresa_posicao", "campo_descricao", "tres_pontinhos"):
            if not targets.get(key):
                missing.append(key)
        if missing:
            raise RuntimeError(
                "Calibracao do cadastro em massa incompleta. Ajuste antes de executar: " + ", ".join(missing)
            )

    def _start_background_operation(
        self,
        *,
        kind: str,
        thread_name: str,
        started_message: str,
        worker: Any,
    ) -> dict[str, Any]:
        with self._lock:
            if self._running:
                running_label = "automacao"
                if self._active_job_kind == "catalog":
                    running_label = "cadastro em massa"
                elif self._active_job_kind == "grades":
                    running_label = "insercao de grades"
                raise RuntimeError(f"Ja existe uma {running_label} em execucao")

            self._cancel_event.clear()
            self._running = True
            self._last_result = None
            self._active_job_kind = kind
            self._active_job_message = started_message

            def _runner() -> None:
                result: dict[str, str]
                try:
                    result = worker()
                except Exception as exc:  # pragma: no cover - defensive fallback
                    logger.exception("Falha inesperada na automacao em background")
                    result = {
                        "status": "error",
                        "message": str(exc),
                        "job_kind": kind,
                    }
                finally:
                    with self._lock:
                        self._running = False
                        self._thread = None
                        self._last_result = result
                        self._active_job_kind = None
                        self._active_job_message = None
                        self._cancel_event.clear()

            self._thread = threading.Thread(target=_runner, name=thread_name, daemon=True)
            self._thread.start()
            return {"status": "started", "message": started_message, "job_kind": kind}

    def _set_active_message(self, message: str) -> None:
        with self._lock:
            if self._running:
                self._active_job_message = message

    def _ensure_gradebot_ready(self) -> None:
        config = self.get_gradebot_config()
        missing: list[str] = []

        buttons = config.get("buttons") if isinstance(config.get("buttons"), dict) else {}
        for key in ("focus_app", "alterar_grade", "modelos", "model_select", "model_ok", "confirm_sim"):
            if not buttons.get(key):
                missing.append(f"buttons.{key}")

        grid = config.get("grid") if isinstance(config.get("grid"), dict) else {}
        if not grid.get("first_quant_cell"):
            missing.append("grid.first_quant_cell")

        order = config.get("erp_size_order")
        if not isinstance(order, list) or not order:
            missing.append("erp_size_order")

        if missing:
            raise RuntimeError(
                "Calibracao de grades incompleta. Ajuste antes de executar: " + ", ".join(missing)
            )

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
        if self._gradebot_module is not None:
            return self._gradebot_module
        project_root = self._find_project_root("automation/gradebot/gradebot.py") or self._workspace_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            self._gradebot_module = importlib.import_module("automation.gradebot.gradebot")
            return self._gradebot_module
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
            self._gradebot_module = module
            return module
