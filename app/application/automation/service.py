from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
from math import hypot
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
COMPLETE_TRANSITION_TARGETS = (
    "cadastro_completo_passo_1",
    "cadastro_completo_passo_2",
    "cadastro_completo_passo_3",
    "cadastro_completo_passo_4",
)

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - depends on local OS
    pyautogui = None  # type: ignore

try:
    import ctypes
except Exception:  # pragma: no cover - platform dependent
    ctypes = None  # type: ignore

EMERGENCY_DRAG_DISTANCE_PX = 260
EMERGENCY_DRAG_MAX_SECONDS = 0.45
EMERGENCY_EDGE_MARGIN_PX = 18
EMERGENCY_MONITOR_INTERVAL = 0.03
EMERGENCY_STOP_MESSAGE = "Parada de emergencia acionada pelo arrasto do mouse ate a borda da tela"


class AutomationService:
    def __init__(self, product_service: ProductService, data_dir: Path) -> None:
        self._products = product_service
        self._data_dir = data_dir
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_result: dict[str, str] | None = None
        self._cancel_event = threading.Event()
        self._cancel_reason: str | None = None
        self._active_job_kind: str | None = None
        self._active_job_phase: str | None = None
        self._active_job_message: str | None = None
        self._active_product_ordering_key: str | None = None
        self._active_product_name: str | None = None
        self._active_product_code: str | None = None
        self._active_product_description: str | None = None
        self._active_product_index: int | None = None
        self._active_product_total: int | None = None
        self._gradebot_module: Any | None = None
        self._failsafe_stop_event: threading.Event | None = None
        self._failsafe_thread: threading.Thread | None = None

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
            started_phase="catalog",
            worker=self._run_catalog_worker,
        )

    def execute_complete(self) -> dict[str, str]:
        self._ensure_complete_ready()
        return self._start_background_operation(
            kind="complete",
            thread_name="lojasync-complete-automation",
            started_message="Cadastro completo iniciado",
            started_phase="catalog",
            worker=self._run_complete_worker,
        )

    def cancel(self) -> dict[str, str]:
        with self._lock:
            if not self._running:
                return {"status": "idle", "message": "Nenhuma automacao em execucao"}
            self._cancel_reason = "Automacao cancelada pelo usuario"
            self._cancel_event.set()
            grade_stage_active = self._active_job_kind == "grades" or self._active_job_phase == "grades"
            if grade_stage_active:
                try:
                    self._load_gradebot().request_stop()
                except Exception:
                    logger.exception("Falha ao solicitar parada do GradeBot")
            message = "Cancelamento solicitado"
            if grade_stage_active:
                message = "Parada do GradeBot solicitada"
            return {"status": "stopping", "message": message}

    def status(self) -> dict[str, Any]:
        with self._lock:
            state = "running" if self._running else "idle"
            payload: dict[str, Any] = {
                "estado": state,
                "cancel_requested": "True" if self._cancel_event.is_set() and self._running else "False",
            }
            if self._running:
                if self._active_job_kind:
                    payload["job_kind"] = self._active_job_kind
                if self._active_job_phase:
                    payload["phase"] = self._active_job_phase
                if self._active_job_message:
                    payload["message"] = self._active_job_message
                if self._active_product_ordering_key:
                    payload["ordering_key_atual"] = self._active_product_ordering_key
                if self._active_product_name:
                    payload["produto_atual"] = self._active_product_name
                if self._active_product_code:
                    payload["codigo_atual"] = self._active_product_code
                if self._active_product_description:
                    payload["descricao_digitada"] = self._active_product_description
                if self._active_product_index is not None:
                    payload["item_atual"] = self._active_product_index
                if self._active_product_total is not None:
                    payload["total_itens"] = self._active_product_total
            elif self._last_result:
                payload.update(self._last_result)
            return payload

    def agents(self) -> dict[str, list[dict[str, Any]]]:
        status = self.status()
        capabilities = ["pyautogui"]
        if self._native_byte_empresa_supported():
            capabilities.append("pywinauto")
        return {
            "agents": [
                {
                    "agent_id": "Executor Local",
                    "status": status.get("estado", "idle"),
                    "capabilities": capabilities,
                    "last_seen": 0,
                    "last_event": {"message": status.get("message", "Executor interno")},
                    "kind": "local",
                    "is_local": True,
                    "synchronized": status.get("estado") in {"idle", "running"},
                    "native_byte_empresa_enabled": self._native_byte_empresa_enabled(),
                    "native_byte_empresa_supported": self._native_byte_empresa_supported(),
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

    def byte_empresa_context(self) -> dict[str, Any]:
        driver = self._create_native_byte_empresa_driver()
        return driver.inspect_context()

    def byte_empresa_prepare(self) -> dict[str, Any]:
        driver = self._create_native_byte_empresa_driver()
        return driver.prepare_catalog_window()

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
            started_phase="grades",
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
            started_phase="grades",
            worker=lambda: self._run_gradebot_worker(tasks=prepared_tasks, pause=pause, speed=speed),
        )

    def execute_grades_from_products(self) -> dict[str, Any]:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI nao esta disponivel neste ambiente.")
        self._sync_legacy_automation_files()
        self._ensure_gradebot_ready()
        tasks = self._prepare_grade_tasks(self._products.list_products())
        if not tasks:
            raise RuntimeError("Nenhum produto com grades validas foi encontrado na lista atual.")
        return self._start_background_operation(
            kind="grades",
            thread_name="lojasync-gradebot-products",
            started_message=f"Insercao de grades iniciada para {len(tasks)} produto(s)",
            started_phase="grades",
            worker=lambda: self._run_gradebot_worker(tasks=tasks, pause=None, speed=None),
        )

    def stop_gradebot(self) -> dict[str, str]:
        with self._lock:
            grade_stage_active = self._active_job_kind == "grades" or self._active_job_phase == "grades"
            if not self._running or not grade_stage_active:
                return {"status": "idle", "message": "Nenhuma automacao de grades em execucao"}
        return self.cancel()

    def _run_catalog_worker(self) -> dict[str, str]:
        started_at = time.time()
        try:
            products = self._products.list_products()
            if not products:
                raise RuntimeError("Nenhum produto disponivel para cadastrar.")
            completed_keys, failures, metrics = self._run_catalog_sequence(products)

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

    def _run_complete_worker(self) -> dict[str, str]:
        started_at = time.time()
        try:
            products = self._products.list_products()
            if not products:
                raise RuntimeError("Nenhum produto disponivel para cadastrar.")

            incomplete_grades = self._find_incomplete_grade_products(products)
            if incomplete_grades:
                raise RuntimeError(self._build_incomplete_grades_message(incomplete_grades))

            completed_keys, failures, metrics = self._run_catalog_sequence(products)
            successful_products = self._products.get_by_ordering_keys(completed_keys)
            grade_tasks = self._prepare_grade_tasks(successful_products)

            result: dict[str, str] = {
                "status": "success",
                "message": "Cadastro completo concluido",
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "complete",
                "sucesso": str(len(completed_keys)),
                "sucesso_catalogo": str(len(completed_keys)),
            }
            if failures:
                result["falhas"] = str(failures)
            if metrics:
                result["tempo_economizado"] = str(metrics.get("tempo_economizado", 0))
                result["caracteres_digitados"] = str(metrics.get("caracteres_digitados", 0))

            if not grade_tasks:
                result["message"] = "Cadastro em massa concluido; nenhum item com grade para inserir"
                return result

            self._set_active_product(None)
            self._set_active_state(
                "Executando transicao entre cadastro e grades...",
                phase="transition",
            )
            self._run_complete_transition_sequence(self.load_targets())

            grade_result = self._run_gradebot_worker(
                tasks=grade_tasks,
                pause=None,
                speed=None,
                job_kind="complete",
                phase="grades",
            )
            result.update(grade_result)
            result["job_kind"] = "complete"
            result["duration"] = f"{time.time() - started_at:.2f}s"
            result["sucesso"] = str(len(completed_keys))
            result["sucesso_catalogo"] = str(len(completed_keys))
            result["sucesso_grades"] = str(len(grade_tasks))
            if failures:
                result["falhas"] = str(failures)
            if metrics:
                result["tempo_economizado"] = str(metrics.get("tempo_economizado", 0))
                result["caracteres_digitados"] = str(metrics.get("caracteres_digitados", 0))
            if grade_result.get("status") == "success":
                result["message"] = "Cadastro completo concluido"
            return result
        except KeyboardInterrupt as exc:
            return {
                "status": "cancelled",
                "message": str(exc) or "Cadastro completo cancelado",
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "complete",
            }
        except Exception as exc:
            logger.exception("Falha no cadastro completo")
            return {
                "status": "error",
                "message": str(exc),
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": "complete",
            }

    def _run_gradebot_worker(
        self,
        *,
        tasks: list[dict[str, Any]],
        pause: float | None,
        speed: float | None,
        job_kind: str = "grades",
        phase: str = "grades",
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
            self._set_active_state(
                "Executando GradeBot..." if total <= 1 else f"Executando GradeBot em lote ({total} produtos)",
                phase=phase,
            )

            for index, task in enumerate(tasks, start=1):
                if self._cancel_event.is_set() or gradebot.is_cancel_requested():
                    raise KeyboardInterrupt(self._cancel_reason or "Automacao de grades cancelada pelo usuario")
                grades_map = task.get("grades") if isinstance(task.get("grades"), dict) else {}
                if not grades_map:
                    continue
                self._set_active_state(
                    f"Executando GradeBot no produto {index}/{total}" if total > 1 else "Executando GradeBot...",
                    phase=phase,
                )
                gradebot.run(grades_map, model_index=task.get("model_index"), activation_step=activation_step)
                activation_step = False
                executed += 1

            return {
                "status": "success",
                "message": "Fluxo de grades concluido",
                "duration": f"{time.time() - started_at:.2f}s",
                "sucesso": str(executed),
                "job_kind": job_kind,
            }
        except KeyboardInterrupt as exc:
            return {
                "status": "cancelled",
                "message": str(exc) or "Automacao de grades cancelada",
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": job_kind,
            }
        except Exception as exc:
            logger.exception("Falha ao executar GradeBot")
            return {
                "status": "error",
                "message": str(exc),
                "duration": f"{time.time() - started_at:.2f}s",
                "job_kind": job_kind,
            }

    def _run_catalog_sequence(self, products: list[Product]) -> tuple[list[str], int, dict[str, int]]:
        if self._should_use_native_byte_empresa():
            try:
                driver = self._create_native_byte_empresa_driver()
                driver.prepare_catalog_window()
            except Exception:
                logger.exception("Falha ao preparar automacao nativa do ByteEmpresa; voltando ao fluxo legado")
                self._set_active_state(
                    "Automacao nativa experimental indisponivel; usando fluxo legado.",
                    phase="catalog",
                )
            else:
                completed_keys: list[str] = []
                failures = 0
                total = len(products)
                for index, product in enumerate(products, start=1):
                    self._check_cancel()
                    payload = self._product_to_payload(product)
                    self._set_active_product(product, payload=payload, index=index, total=total)
                    self._set_active_state(f"Cadastrando produto {index}/{total}", phase="catalog")
                    try:
                        ok = driver.submit_product(payload, self._cancel_event)
                    except KeyboardInterrupt:
                        raise
                    except Exception as exc:
                        logger.exception("Falha na automacao nativa do ByteEmpresa")
                        self._set_active_state(str(exc), phase="catalog")
                        ok = False
                    if ok:
                        completed_keys.append(product.ordering_key())
                    else:
                        failures += 1
                metrics: dict[str, int] = {}
                if completed_keys:
                    records = self._products.get_by_ordering_keys(completed_keys)
                    metrics = self._products.record_automation_success(records)
                return completed_keys, failures, metrics

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
        total = len(products)
        for index, product in enumerate(products, start=1):
            self._check_cancel()
            payload = self._product_to_payload(product)
            self._set_active_product(product, payload=payload, index=index, total=total)
            self._set_active_state(f"Cadastrando produto {index}/{total}", phase="catalog")
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
        return completed_keys, failures, metrics

    def _prepare_grade_tasks(self, products: list[Product]) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for product in products:
            if not product.grades:
                continue
            grades_map = {
                str(item.tamanho).strip(): int(item.quantidade)
                for item in product.grades
                if str(item.tamanho).strip() and int(item.quantidade or 0) > 0
            }
            if grades_map:
                tasks.append({"grades": grades_map})
        return tasks

    def _run_complete_transition_sequence(self, targets: dict[str, Any]) -> None:
        for index, key in enumerate(COMPLETE_TRANSITION_TARGETS, start=1):
            point = targets.get(key)
            if not isinstance(point, dict):
                raise RuntimeError(f"Coordenada ausente para a transicao do cadastro completo: {key}")
            self._check_cancel()
            self._set_active_state(
                f"Preparando tela de grades ({index}/{len(COMPLETE_TRANSITION_TARGETS)})",
                phase="transition",
            )
            pyautogui.click(int(point["x"]), int(point["y"]))
            self._wait_cancelable(0.35)

    def _check_cancel(self) -> None:
        if self._cancel_event.is_set():
            raise KeyboardInterrupt(self._cancel_reason or "Automacao cancelada pelo usuario")

    def _wait_cancelable(self, seconds: float) -> None:
        end_time = time.time() + max(0.0, float(seconds))
        while time.time() < end_time:
            self._check_cancel()
            time.sleep(min(0.05, max(0.0, end_time - time.time())))

    def _ensure_bulk_ready(self) -> None:
        if self._should_use_native_byte_empresa():
            try:
                self._create_native_byte_empresa_driver().prepare_catalog_window()
                return
            except Exception:
                logger.exception("Falha ao preparar automacao nativa do ByteEmpresa; validando fluxo legado")
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

    def _ensure_complete_ready(self) -> None:
        if self._should_use_native_byte_empresa():
            try:
                self._create_native_byte_empresa_driver().prepare_catalog_window()
            except Exception:
                logger.exception("Falha ao preparar automacao nativa do ByteEmpresa; voltando ao fluxo legado")
                self._ensure_bulk_ready()
        else:
            self._ensure_bulk_ready()
        products = self._products.list_products()
        if not products:
            raise RuntimeError("Nenhum produto disponivel para cadastrar.")
        incomplete_grades = self._find_incomplete_grade_products(products)
        if incomplete_grades:
            raise RuntimeError(self._build_incomplete_grades_message(incomplete_grades))
        if not self._prepare_grade_tasks(products):
            return
        self._ensure_gradebot_ready()
        targets = self.load_targets()
        missing = [key for key in COMPLETE_TRANSITION_TARGETS if not targets.get(key)]
        if missing:
            raise RuntimeError(
                "Calibracao do Cadastro completo incompleta. Ajuste os cliques de transicao: " + ", ".join(missing)
            )

    def _start_background_operation(
        self,
        *,
        kind: str,
        thread_name: str,
        started_message: str,
        started_phase: str | None,
        worker: Any,
    ) -> dict[str, Any]:
        with self._lock:
            if self._running:
                running_label = "automacao"
                if self._active_job_kind == "catalog":
                    running_label = "cadastro em massa"
                elif self._active_job_kind == "grades":
                    running_label = "insercao de grades"
                elif self._active_job_kind == "complete":
                    running_label = "cadastro completo"
                raise RuntimeError(f"Ja existe uma {running_label} em execucao")

            self._cancel_event.clear()
            self._cancel_reason = None
            self._running = True
            self._last_result = None
            self._active_job_kind = kind
            self._active_job_phase = started_phase
            self._active_job_message = started_message
            self._active_product_ordering_key = None
            self._active_product_name = None
            self._active_product_code = None
            self._active_product_description = None
            self._active_product_index = None
            self._active_product_total = None
            self._start_mouse_failsafe_monitor_locked()

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
                        self._stop_mouse_failsafe_monitor_locked()
                        self._running = False
                        self._thread = None
                        self._last_result = result
                        self._active_job_kind = None
                        self._active_job_phase = None
                        self._active_job_message = None
                        self._active_product_ordering_key = None
                        self._active_product_name = None
                        self._active_product_code = None
                        self._active_product_description = None
                        self._active_product_index = None
                        self._active_product_total = None
                        self._cancel_event.clear()
                        self._cancel_reason = None

            self._thread = threading.Thread(target=_runner, name=thread_name, daemon=True)
            self._thread.start()
            return {"status": "started", "message": started_message, "job_kind": kind}

    def _set_active_state(self, message: str, *, phase: str | None = None) -> None:
        with self._lock:
            if self._running:
                self._active_job_message = message
                if phase is not None:
                    self._active_job_phase = phase

    def _set_active_product(
        self,
        product: Product | None,
        *,
        payload: dict[str, Any] | None = None,
        index: int | None = None,
        total: int | None = None,
    ) -> None:
        with self._lock:
            if not self._running or product is None:
                self._active_product_ordering_key = None
                self._active_product_name = None
                self._active_product_code = None
                self._active_product_description = None
                self._active_product_index = None
                self._active_product_total = None
                return
            self._active_product_ordering_key = product.ordering_key()
            self._active_product_name = str(product.nome or "").strip() or None
            self._active_product_code = str(product.codigo or "").strip() or None
            self._active_product_description = str(
                (payload or {}).get("descricao_completa") or product.descricao_completa or product.nome or ""
            ).strip() or None
            self._active_product_index = index
            self._active_product_total = total

    @staticmethod
    def _find_incomplete_grade_products(products: list[Product]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for product in products:
            if not product.grades:
                continue
            total_grades = sum(max(int(item.quantidade or 0), 0) for item in product.grades)
            expected = max(int(product.quantidade or 0), 0)
            if total_grades == expected:
                continue
            pending.append(
                {
                    "nome": str(product.nome or "").strip() or str(product.codigo or "").strip() or "Item sem nome",
                    "total_grades": total_grades,
                    "quantidade": expected,
                }
            )
        return pending

    @staticmethod
    def _build_incomplete_grades_message(pending: list[dict[str, Any]]) -> str:
        if not pending:
            return "Existem grades pendentes."
        sample = ", ".join(
            f"{item['nome']} ({item['total_grades']}/{item['quantidade']})" for item in pending[:3]
        )
        remaining = len(pending) - min(len(pending), 3)
        suffix = f" e mais {remaining} item(ns)" if remaining > 0 else ""
        return (
            "Nao e possivel executar o Cadastro Completo porque existem grades pendentes: "
            f"{sample}{suffix}. Abra 'Inserir Grade' e finalize esses itens antes de continuar."
        )

    def _request_emergency_stop_locked(self, message: str = EMERGENCY_STOP_MESSAGE) -> None:
        if not self._running or self._cancel_event.is_set():
            return
        self._cancel_reason = message
        self._cancel_event.set()
        self._active_job_message = message
        grade_stage_active = self._active_job_kind == "grades" or self._active_job_phase == "grades"
        if grade_stage_active:
            try:
                self._load_gradebot().request_stop()
            except Exception:
                logger.exception("Falha ao solicitar parada emergencial do GradeBot")
        logger.warning(message)

    def _start_mouse_failsafe_monitor_locked(self) -> None:
        if pyautogui is None:
            return
        if self._failsafe_thread and self._failsafe_thread.is_alive():
            return
        stop_event = threading.Event()
        self._failsafe_stop_event = stop_event
        self._failsafe_thread = threading.Thread(
            target=self._monitor_mouse_emergency_stop,
            args=(stop_event,),
            name="lojasync-mouse-failsafe",
            daemon=True,
        )
        self._failsafe_thread.start()

    def _stop_mouse_failsafe_monitor_locked(self) -> None:
        if self._failsafe_stop_event is not None:
            self._failsafe_stop_event.set()
        self._failsafe_stop_event = None
        self._failsafe_thread = None

    def _monitor_mouse_emergency_stop(self, stop_event: threading.Event) -> None:
        if pyautogui is None:
            return
        try:
            screen_width, screen_height = pyautogui.size()
        except Exception:
            return

        drag_started_at: float | None = None
        drag_distance = 0.0
        last_pos: tuple[int, int] | None = None

        while not stop_event.wait(EMERGENCY_MONITOR_INTERVAL):
            try:
                x, y = pyautogui.position()
            except Exception:
                continue
            current_pos = (int(x), int(y))
            button_pressed = self._is_any_mouse_button_pressed()
            now = time.monotonic()

            if button_pressed:
                if drag_started_at is None or last_pos is None:
                    drag_started_at = now
                    drag_distance = 0.0
                    last_pos = current_pos
                    continue

                drag_distance += hypot(current_pos[0] - last_pos[0], current_pos[1] - last_pos[1])
                elapsed = now - drag_started_at
                last_pos = current_pos

                if (
                    elapsed <= EMERGENCY_DRAG_MAX_SECONDS
                    and drag_distance >= EMERGENCY_DRAG_DISTANCE_PX
                    and self._is_near_screen_edge(current_pos, screen_width, screen_height)
                ):
                    with self._lock:
                        self._request_emergency_stop_locked()
                    return

                if elapsed > EMERGENCY_DRAG_MAX_SECONDS:
                    drag_started_at = now
                    drag_distance = 0.0
                    last_pos = current_pos
            else:
                drag_started_at = None
                drag_distance = 0.0
                last_pos = current_pos

    @staticmethod
    def _is_near_screen_edge(position: tuple[int, int], width: int, height: int) -> bool:
        x, y = position
        return (
            x <= EMERGENCY_EDGE_MARGIN_PX
            or y <= EMERGENCY_EDGE_MARGIN_PX
            or x >= max(0, width - EMERGENCY_EDGE_MARGIN_PX)
            or y >= max(0, height - EMERGENCY_EDGE_MARGIN_PX)
        )

    @staticmethod
    def _is_any_mouse_button_pressed() -> bool:
        if os.name != "nt" or ctypes is None:
            return False
        try:
            user32 = ctypes.windll.user32
            left_pressed = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
            right_pressed = bool(user32.GetAsyncKeyState(0x02) & 0x8000)
            return left_pressed or right_pressed
        except Exception:
            return False

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return default
        raw = str(value).strip().lower()
        if raw in {"1", "true", "yes", "y", "on"}:
            return True
        if raw in {"0", "false", "no", "n", "off"}:
            return False
        return default

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
        descricao = self._build_catalog_description(product)
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

    @staticmethod
    def _build_catalog_description(product: Product) -> str:
        parts: list[str] = []

        base_description = str(product.descricao_completa or product.nome or "").strip()
        if base_description:
            parts.append(base_description)

        brand = str(product.marca or "").strip()
        code = str(product.codigo or "").strip()

        normalized_description = f" {base_description.casefold()} " if base_description else ""
        if brand and f" {brand.casefold()} " not in normalized_description:
            parts.append(brand)
        if code and f" {code.casefold()} " not in normalized_description:
            parts.append(code)

        description = " ".join(part for part in parts if part).strip()
        if description:
            return description
        return f"{product.nome} {brand} {code}".strip()

    @staticmethod
    def _native_byte_empresa_supported() -> bool:
        try:
            from app.application.automation.byteempresa.catalog import native_byteempresa_available

            return bool(native_byteempresa_available())
        except Exception:
            return False

    def _native_byte_empresa_enabled(self) -> bool:
        env_value = os.getenv("LOJASYNC_ENABLE_NATIVE_BYTEEMPRESA")
        if env_value not in (None, ""):
            return self._coerce_bool(env_value, False)

        profile = self._load_desktop_profile()
        native_settings = profile.get("native_byte_empresa")
        if isinstance(native_settings, dict) and native_settings.get("enabled") not in (None, ""):
            return self._coerce_bool(native_settings.get("enabled"), False)

        profile_value = profile.get("native_byte_empresa_enabled")
        if profile_value not in (None, ""):
            return self._coerce_bool(profile_value, False)
        return False

    def _should_use_native_byte_empresa(self) -> bool:
        return self._native_byte_empresa_enabled() and self._native_byte_empresa_supported()

    @staticmethod
    def _create_native_byte_empresa_driver():
        try:
            from app.application.automation.byteempresa.catalog import ByteEmpresaCatalogDriver

            return ByteEmpresaCatalogDriver()
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

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
        fallback = Path(__file__).resolve().parents[3]
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
