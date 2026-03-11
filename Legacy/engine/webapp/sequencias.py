"""Gerenciador de sequências PyAutoGUI para o protótipo web.

Este módulo mantém um singleton simples responsável por disparar rotinas
assíncronas do PyAutoGUI sem bloquear o backend FastAPI. A ideia é
servir como ponto central onde iremos evoluir as sequências reais de
cadastro (telas 1, 2 etc.).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyautogui
except ImportError:  # pragma: no cover - ambiente sem pyautogui
    pyautogui = None  # type: ignore

from .database import product_db
from modules.automation.byte_empresa import (
    ativar_janela_byte_empresa,
    executar_tela1_mecanico,
    executar_tela2_mecanico,
    recarregar_config_automacao,
)
from modules.core.file_manager import load_targets


logger = logging.getLogger(__name__)


class SequenciaManager:
    """Gerencia execuções assíncronas das sequências PyAutoGUI."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_result: Optional[Dict[str, str]] = None
        self._cancel_event = threading.Event()

    def _run_basico(self) -> None:
        inicio = time.time()
        logger.info("Iniciando sequência básica de automação")
        try:
            registros_obj = product_db.list()
            if not registros_obj:
                raise RuntimeError("Nenhum produto disponível para cadastrar.")

            cancel_event = self._cancel_event
            ordering_map = {product_db.make_key(record): record for record in registros_obj}
            if pyautogui is None:
                logger.warning(
                    "pyautogui não está disponível neste ambiente. Executando em modo dry-run."
                )
                time.sleep(1.0)
                sucesso = 0
                falhas: List[Dict[str, str]] = []
                concluido_keys: List[str] = []
            else:
                registros = [montar_dados_produto(record) for record in registros_obj]
                recarregar_config_automacao()
                coordenadas = load_targets()
                if not coordenadas:
                    raise RuntimeError("Coordenadas de calibração não encontradas (data/targets.json).")

                sucesso, falhas, concluido_keys = _executar_fluxo_byte_empresa(
                    registros, coordenadas, cancel_event
                )

            duracao = time.time() - inicio
            resultado = {
                "status": "success",
                "message": "Fluxo Byte Empresa concluído",
                "duration": f"{duracao:.2f}s",
                "sucesso": str(sucesso),
            }
            if falhas:
                resultado["falhas"] = str(len(falhas))

            concluidokeys = [key for key in concluido_keys if key]
            if sucesso and concluidokeys:
                registros_sucesso = [ordering_map[key] for key in concluidokeys if key in ordering_map]
                if registros_sucesso:
                    metrics = product_db.record_automation_success(registros_sucesso)
                    resultado.update(
                        {
                            "tempo_economizado": str(metrics.get("tempo_economizado", 0)),
                            "caracteres_digitados": str(metrics.get("caracteres_digitados", 0)),
                        }
                    )
            logger.info(resultado["message"])
        except KeyboardInterrupt as exc:  # cancelamento solicitado
            duracao = time.time() - inicio
            resultado = {
                "status": "cancelled",
                "message": str(exc) or "Automação cancelada",
                "duration": f"{duracao:.2f}s",
            }
            logger.info("Automação cancelada pelo usuário")
        except Exception as exc:  # pragma: no cover - erros runtime
            resultado = {
                "status": "error",
                "message": str(exc),
            }
            logger.exception("Falha na sequência básica: %s", exc)
        finally:
            with self._lock:
                self._running = False
                self._thread = None
                self._last_result = resultado
                self._cancel_event.clear()

    def iniciar_sequencia_basica(self) -> Dict[str, str]:
        with self._lock:
            if self._running:
                raise RuntimeError("Já existe uma sequência em execução")
            self._cancel_event.clear()
            self._running = True
            self._thread = threading.Thread(target=self._run_basico, name="seq-basica", daemon=True)
            self._thread.start()
            self._last_result = None
            logger.debug("Thread da sequência básica iniciada")
            return {"status": "started", "message": "Sequência básica disparada"}

    def cancelar(self) -> Dict[str, str]:
        with self._lock:
            if not self._running:
                return {"status": "idle", "message": "Nenhuma automação em execução"}
            self._cancel_event.set()
            return {"status": "stopping", "message": "Cancelamento solicitado"}

    def status(self) -> Dict[str, Optional[str]]:
        with self._lock:
            estado = "running" if self._running else "idle"
            info: Dict[str, Optional[str]] = {
                "estado": estado,
                "cancel_requested": str(self._cancel_event.is_set()) if self._running else "False",
            }
            if self._last_result:
                info.update(self._last_result)
            return info


_manager = SequenciaManager()


def iniciar_sequencia_basica() -> Dict[str, str]:
    """API pública para disparar a sequência básica."""
    return _manager.iniciar_sequencia_basica()


def obter_status() -> Dict[str, Optional[str]]:
    """Retorna o status atual da automação básica."""
    return _manager.status()


def cancelar_sequencia_basica() -> Dict[str, str]:
    """Solicita o cancelamento da sequência em execução."""
    return _manager.cancelar()


def _executar_fluxo_byte_empresa(
    registros: List[Dict[str, Any]], coordenadas: dict, cancel_event: threading.Event
) -> Tuple[int, List[Dict[str, str]], List[str]]:
    logger.debug("Iniciando fluxo Byte Empresa para %s produtos", len(registros))
    _check_cancel(cancel_event)
    ativado, mensagem = ativar_janela_byte_empresa(coordenadas)
    if not ativado:
        raise RuntimeError(f"Falha ao ativar Byte Empresa: {mensagem}")

    sucesso = 0
    falhas: List[Dict[str, str]] = []
    concluidos: List[str] = []

    for dados in registros:
        _check_cancel(cancel_event)
        logger.debug("Processando produto %s (%s)", dados["nome"], dados["codigo"])

        try:
            etapa1 = executar_tela1_mecanico(dados, coordenadas, cancel_event)
            if not etapa1:
                falhas.append({"codigo": dados["codigo"], "etapa": "tela1"})
                continue

            etapa2 = executar_tela2_mecanico(dados, coordenadas, cancel_event)
            if not etapa2:
                falhas.append({"codigo": dados["codigo"], "etapa": "tela2"})
                continue

            sucesso += 1
            chave = dados.get("ordering_key")
            if isinstance(chave, str) and chave:
                concluidos.append(chave)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Erro durante cadastro do produto %s: %s", dados["codigo"], exc)
            falhas.append({"codigo": dados["codigo"], "erro": str(exc)})

    return sucesso, falhas, concluidos


def _check_cancel(cancel_event: threading.Event) -> None:
    if cancel_event.is_set():
        raise KeyboardInterrupt("Automação cancelada pelo usuário")


def montar_dados_produto(record: object) -> Dict[str, str]:
    try:
        preco_final = record.preco_final or product_db._calculate_sale_price(record.preco)  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - fallback se acesso privado falhar
        preco_final = getattr(record, "preco_final", None)

    descricao = getattr(record, "descricao_completa", None)
    if not descricao:
        descricao = f"{record.nome} {record.marca} {record.codigo}".strip()

    grades = (
        [
            {"tamanho": getattr(g, "tamanho", str(getattr(g, "tamanho", ""))), "quantidade": int(getattr(g, "quantidade", 0))}
            for g in (getattr(record, "grades", None) or [])
        ]
        if getattr(record, "grades", None)
        else None
    )
    cores = (
        [
            {"cor": getattr(c, "cor", str(getattr(c, "cor", ""))), "quantidade": int(getattr(c, "quantidade", 0))}
            for c in (getattr(record, "cores", None) or [])
        ]
        if getattr(record, "cores", None)
        else None
    )
    return {
        "nome": record.nome,
        "codigo": record.codigo,
        "quantidade": str(record.quantidade),
        "preco": record.preco,
        "preco_final": preco_final or record.preco,
        "categoria": record.categoria,
        "marca": record.marca,
        "descricao_completa": descricao,
        "grades": grades,
        "cores": cores,
        "ordering_key": product_db.make_key(record),
    }


def preparar_produtos_para_automacao() -> List[Dict[str, Any]]:
    registros = product_db.list()
    return [montar_dados_produto(record) for record in registros]
