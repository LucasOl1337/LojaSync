from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import WebSocket


logger = logging.getLogger(__name__)


@dataclass
class RemoteAgent:
    agent_id: str
    websocket: WebSocket
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    status: str = "idle"
    last_event: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=lambda: time.monotonic())
    pending: Dict[str, asyncio.Future] = field(default_factory=dict)

    def touch(self) -> None:
        self.last_seen = time.monotonic()


class RemoteAgentManager:
    """Administra agentes remotos conectados via WebSocket."""

    def __init__(self, auth_token: Optional[str] = None) -> None:
        self._auth_token = auth_token
        self._agents: Dict[str, RemoteAgent] = {}
        self._lock = asyncio.Lock()

    @property
    def auth_required(self) -> bool:
        return bool(self._auth_token)

    def _check_token(self, token: Optional[str]) -> bool:
        if not self._auth_token:
            return True
        return token == self._auth_token

    async def register(self, websocket: WebSocket, payload: Dict[str, Any]) -> Optional[RemoteAgent]:
        """Registra um agente a partir da mensagem inicial."""

        if payload.get("type") != "register":
            logger.warning("Registro rejeitado: payload inválido %s", payload)
            return None

        agent_id = str(payload.get("agent_id") or "").strip()
        token = payload.get("token")
        if not agent_id:
            logger.warning("Registro rejeitado: agent_id ausente")
            return None
        if not self._check_token(token):
            logger.warning("Registro rejeitado: token inválido para agente %s", agent_id)
            return None

        capabilities_raw = payload.get("capabilities") or []
        capabilities = tuple(str(item) for item in capabilities_raw if isinstance(item, str))

        async with self._lock:
            # desconecta agente anterior com mesmo ID
            existing = self._agents.get(agent_id)
            if existing is not None:
                logger.info("Agente %s já conectado. Encerrando instância anterior.", agent_id)
                await self._safe_close(existing.websocket, code=4002, reason="agent reconnected")
            agent = RemoteAgent(agent_id=agent_id, websocket=websocket, capabilities=capabilities)
            self._agents[agent_id] = agent
            logger.info("Agente %s registrado com capacidades %s", agent_id, capabilities)
            return agent

    async def _safe_close(self, websocket: WebSocket, code: int = 1000, reason: str | None = None) -> None:
        with contextlib.suppress(Exception):
            await websocket.close(code=code, reason=reason)

    async def handle_message(self, agent_id: str, message: Dict[str, Any]) -> None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                logger.warning("Mensagem recebida para agente desconhecido: %s", agent_id)
                return

            agent.touch()
            msg_type = message.get("type")

            if msg_type == "heartbeat":
                agent.status = message.get("status", agent.status)
                logger.debug("Heartbeat recebido de %s com status %s", agent_id, agent.status)
                return

            if msg_type == "event":
                agent.status = message.get("status") or agent.status
                agent.last_event = message
                logger.debug("Evento recebido de %s: %s", agent_id, message)
                return

            if msg_type in {"ack", "result"}:
                message_id = message.get("id")
                if not message_id:
                    logger.warning("Mensagem %s sem id de %s", msg_type, agent_id)
                    return
                future = agent.pending.get(message_id)
                if future is not None and not future.done():
                    future.set_result(message)
                if msg_type == "result":
                    agent.status = message.get("status", agent.status)
                    agent.last_event = message
                    agent.pending.pop(message_id, None)
                logger.info("%s recebido de %s para comando %s", msg_type.upper(), agent_id, message_id)
                return

            agent.last_event = message
            logger.debug("Mensagem genérica de %s: %s", agent_id, message)

    async def disconnect(self, agent_id: str) -> None:
        async with self._lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return
            logger.info("Agente %s desconectado", agent_id)
            for future in agent.pending.values():
                if not future.done():
                    future.set_exception(ConnectionError("Agente desconectado"))

    async def send_command(
        self,
        command: str,
        payload: Dict[str, Any] | None = None,
        wait_for: str = "ack",
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        agent = await self._pick_available_agent()
        if agent is None:
            raise RuntimeError("Nenhum agente remoto disponível")

        message_id = uuid4().hex
        envelope = {
            "type": "command",
            "id": message_id,
            "command": command,
            "payload": payload or {},
        }

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        async with self._lock:
            if agent.status not in {"idle", "ready"}:
                raise RuntimeError(f"Agente {agent.agent_id} ocupado")
            agent.pending[message_id] = future
            agent.status = "busy"
            agent.last_event = {
                "type": "event",
                "status": "busy",
                "message": f"Enviando comando {command}",
                "timestamp": time.time(),
            }
            await agent.websocket.send_json(envelope)
            logger.info(
                "Comando %s (%s) enviado para agente %s", command, message_id, agent.agent_id
            )

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.info(
                "Resposta inicial (%s) recebida do agente %s para comando %s",
                result.get("type"),
                agent.agent_id,
                message_id,
            )
        except asyncio.TimeoutError as exc:
            async with self._lock:
                agent.pending.pop(message_id, None)
                agent.status = "idle"
            logger.error("Timeout aguardando resposta do agente %s para %s", agent.agent_id, command)
            raise TimeoutError(f"Tempo limite aguardando resposta do agente {agent.agent_id}") from exc

        msg_type = result.get("type")
        if wait_for == "ack" and msg_type == "ack":
            agent.status = result.get("status", agent.status)
            return result
        if wait_for == "result" and msg_type == "result":
            agent.status = result.get("status", agent.status)
            return result
        # Caso aguarde resultado completo, continue escutando
        if wait_for == "result" and msg_type == "ack":
            # aguarda resultado definitivo reutilizando future
            new_future: asyncio.Future = loop.create_future()
            async with self._lock:
                agent.pending[message_id] = new_future
                logger.debug(
                    "Aguardando resultado final do agente %s para comando %s", agent.agent_id, command
                )
            result = await asyncio.wait_for(new_future, timeout=timeout)
            agent.status = result.get("status", agent.status)
            return result

        return result

    async def _pick_available_agent(self) -> Optional[RemoteAgent]:
        async with self._lock:
            for agent in self._agents.values():
                if agent.status in {"idle", "ready"}:
                    return agent
            return None

    def has_connected_agents(self) -> bool:
        return bool(self._agents)

    def snapshot(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "agents": [],
        }
        now = time.monotonic()
        for agent in self._agents.values():
            data["agents"].append(
                {
                    "agent_id": agent.agent_id,
                    "status": agent.status,
                    "capabilities": agent.capabilities,
                    "last_seen": now - agent.last_seen,
                    "last_event": agent.last_event,
                    "kind": "remote",
                    "is_local": False,
                    "synchronized": agent.status in {"idle", "ready", "busy"},
                }
            )
        return data


# Utilitário para dependência baseada em ambiente

def build_manager_from_env() -> RemoteAgentManager:
    token = os.getenv("REMOTE_AGENT_TOKEN") or None
    return RemoteAgentManager(auth_token=token)
