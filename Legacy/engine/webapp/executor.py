
import asyncio
import contextlib
import json
import platform
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Dict, List

import httpx
import websockets

try:
    import pyautogui  # type: ignore
except ImportError:  # pragma: no cover
    pyautogui = None  # type: ignore

import sys

ROOT_DIR = Path(__file__).resolve().parent
PARENT_DIR = ROOT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from modules.automation.byte_empresa import (  # type: ignore
    ativar_janela_byte_empresa,
    executar_tela1_mecanico,
    executar_tela2_mecanico,
    recarregar_config_automacao,
)
from modules.core.file_manager import load_targets  # type: ignore

WS_PATH = "/automation/remote/ws"
DEFAULT_HOST = "100.85.212.33"
DEFAULT_PORT = 8800
DEFAULT_CAPABILITIES = "pyautogui"
DEFAULT_STATUS_READY = "Pronto"                                         
DEFAULT_STATUS_CONNECTING = "Conectando"
DEFAULT_STATUS_DISCONNECTED = "Desconectado"


def _format_capabilities(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


class AgentWorker:
    def __init__(self, host: str, port: int, agent_id: str, token: str | None, capabilities: list[str], status_cb, log_cb):
        self.host = host
        self.port = port
        self.agent_id = agent_id
        self.token = token or None
        self.capabilities = capabilities
        self.status_cb = status_cb
        self.log_cb = log_cb
        self.stop_event = threading.Event()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.current_status = "idle"
        self._lock = threading.RLock()
        self.stop_event = threading.Event()
        self.status_cb(DEFAULT_STATUS_DISCONNECTED)
        self._awaiting_command = False
        self.last_command_received = 0.0
        if pyautogui is None:
            self.log_cb("PyAutoGUI não encontrado: executando em modo simulado")
        else:
            self.log_cb("PyAutoGUI disponível: executor pronto para automações")

    @property
    def uri(self) -> str:
        return f"ws://{self.host}:{self.port}{WS_PATH}"

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        finally:
            self.loop.run_until_complete(self._shutdown())
            self.loop.close()
            self.loop = None

    def stop(self) -> None:
        self.stop_event.set()
        if self.loop is not None:
            self.loop.call_soon_threadsafe(lambda: None)

    def trigger_basic_sequence(self) -> None:
        self.log_cb("Solicitando execução de cadastro ao backend")

        def _invoke() -> None:
            url = f"http://{self.host}:{self.port}/automation/execute"
            headers: Dict[str, str] = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            try:
                response = httpx.post(url, json={}, headers=headers, timeout=20.0)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detalhe = ""
                    with contextlib.suppress(Exception):
                        payload = exc.response.json()
                        detalhe = payload.get("detail") or payload
                    if not detalhe:
                        detalhe = exc.response.text
                    self.log_cb(f"Backend retornou erro {exc.response.status_code}: {detalhe}")
                    return

                data = response.json()
                status = str(data.get("status", "unknown"))
                message = data.get("message", "sem mensagem")
                self.log_cb(f"Backend respondeu: status={status} msg={message}")
                if status.lower() not in {"accepted", "success", "running"}:
                    self.log_cb("Aviso: backend não confirmou delegação ao executor remoto")
                    return
                self._schedule_command_wait()
            except Exception as exc:
                self.log_cb(f"Falha ao acionar backend: {exc}")

        threading.Thread(target=_invoke, daemon=True).start()

    def _schedule_command_wait(self) -> None:
        trigger_time = time.time()
        with self._lock:
            self._awaiting_command = True

        def _monitor() -> None:
            time.sleep(5)
            with self._lock:
                if self._awaiting_command and self.last_command_received < trigger_time:
                    self.log_cb("Nenhum comando recebido do servidor após 5 segundos.")
                    self._awaiting_command = False

        threading.Thread(target=_monitor, daemon=True).start()

    def cancel_sequence(self) -> None:
        self.log_cb("Solicitando cancelamento ao backend")

        def _invoke() -> None:
            url = f"http://{self.host}:{self.port}/automation/cancel"
            headers: Dict[str, str] = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            try:
                response = httpx.post(url, json={}, headers=headers, timeout=10.0)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detalhe = ""
                    with contextlib.suppress(Exception):
                        payload = exc.response.json()
                        detalhe = payload.get("detail") or payload
                    if not detalhe:
                        detalhe = exc.response.text
                    self.log_cb(f"Erro ao cancelar ({exc.response.status_code}): {detalhe}")
                    return
                data = response.json()
                status = str(data.get("status", "unknown"))
                message = data.get("message", "sem mensagem")
                self.log_cb(f"Cancelamento respondido: status={status} msg={message}")
            except Exception as exc:
                self.log_cb(f"Falha ao cancelar: {exc}")
            finally:
                with self._lock:
                    self._awaiting_command = False

        threading.Thread(target=_invoke, daemon=True).start()

    async def _shutdown(self) -> None:
        if self.websocket is not None:
            with contextlib.suppress(Exception):
                await self.websocket.close(code=1000, reason="shutdown")
        self.websocket = None

    async def _main(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.status_cb(DEFAULT_STATUS_CONNECTING)
                async with websockets.connect(self.uri, ping_interval=None, ping_timeout=None) as ws:
                    self.websocket = ws
                    await self._register(ws)
                    self.current_status = "ready"
                    self.status_cb(DEFAULT_STATUS_READY)
                    self.log_cb("Conexão ativa. Aguardando comandos do servidor...")
                    await self._serve(ws)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.websocket = None
                if self.stop_event.is_set():
                    break
                self.status_cb(DEFAULT_STATUS_DISCONNECTED)
                self.log_cb(f"Falha de conexão: {exc}")
                await asyncio.sleep(3)
        self.status_cb(DEFAULT_STATUS_DISCONNECTED)

    async def _register(self, ws: websockets.WebSocketClientProtocol) -> None:
        payload: dict[str, object] = {
            "type": "register",
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
        }
        if self.token:
            payload["token"] = self.token
        await ws.send(json.dumps(payload))
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("type") != "registered":
            raise RuntimeError("Registro rejeitado")
        self.log_cb("Registrado com sucesso")

    async def _serve(self, ws: websockets.WebSocketClientProtocol) -> None:
        heartbeat = asyncio.create_task(self._heartbeat(ws))
        receiver = asyncio.create_task(self._receiver(ws))
        done, pending = await asyncio.wait({heartbeat, receiver}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc:
                raise exc

    async def _heartbeat(self, ws: websockets.WebSocketClientProtocol) -> None:
        while not self.stop_event.is_set():
            payload = {
                "type": "heartbeat",
                "status": self.current_status,
                "timestamp": time.time(),
            }
            try:
                await ws.send(json.dumps(payload))
            except Exception as exc:
                self.log_cb(f"Erro ao enviar heartbeat: {exc}")
                break
            await asyncio.sleep(5)

    async def _receiver(self, ws: websockets.WebSocketClientProtocol) -> None:
        async for raw in ws:
            if self.stop_event.is_set():
                break
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                self.log_cb(f"Mensagem inválida recebida: {raw!r}")
                continue
            self.log_cb(f"Mensagem recebida do servidor: {message}")
            await self._handle_message(ws, message)

    async def _handle_message(self, ws: websockets.WebSocketClientProtocol, message: dict[str, object]) -> None:
        msg_type = message.get("type")
        if msg_type == "command":
            await self._handle_command(ws, message)
        else:
            self.log_cb(f"Mensagem recebida: {message}")

    async def _handle_command(self, ws: websockets.WebSocketClientProtocol, message: dict[str, object]) -> None:
        command = str(message.get("command") or "")
        command_id = message.get("id")
        payload = message.get("payload") or {}
        if not command_id:
            return
        self.log_cb(f"Recebido comando {command} ({len(payload or {})} campos)")
        if payload:
            try:
                preview = json.dumps(payload, ensure_ascii=False)[:600]
            except Exception:
                preview = str(payload)[:600]
            self.log_cb(f"Payload: {preview}")
        with self._lock:
            self._awaiting_command = False
            self.last_command_received = time.time()

        ack = {
            "type": "ack",
            "id": command_id,
            "status": "accepted",
            "timestamp": time.time(),
        }
        await ws.send(json.dumps(ack))
        self.current_status = "busy"
        self.status_cb(f"Executando {command}")
        self.log_cb(f"Executando comando {command}")
        try:
            result_payload = await self._execute_command(command, payload)
            status = result_payload.get("status", "done")
            message_text = result_payload.get("message", "")
        except Exception as exc:
            status = "error"
            message_text = str(exc)
            self.log_cb(f"Erro: {exc}")
        else:
            self.log_cb(f"Comando {command} finalizado: {message_text or status}")
        self.current_status = "ready"
        self.status_cb(DEFAULT_STATUS_READY)
        result = {
            "type": "result",
            "id": command_id,
            "status": status,
            "message": message_text,
            "timestamp": time.time(),
        }
        await ws.send(json.dumps(result))

    async def _send_command(self, command: str, payload: dict[str, object]) -> None:
        ws = self.websocket
        if ws is None:
            raise RuntimeError("Conexão encerrada")
        message_id = f"local-{int(time.time()*1000)}"
        envelope = {
            "type": "command",
            "id": message_id,
            "command": command,
            "payload": payload,
        }
        try:
            await ws.send(json.dumps(envelope))
        except Exception as exc:
            raise RuntimeError(f"Falha ao enviar comando: {exc}") from exc
        self.log_cb(f"Comando manual {command} enviado")

    async def _execute_command(self, command: str, payload: object) -> dict[str, object]:
        if command in {"automation.basic", "automation_basic", "run_automation"}:
            produtos = []
            ordering_keys: list[str] = []
            if isinstance(payload, dict):
                produtos_raw = payload.get("products")
                if isinstance(produtos_raw, list):
                    produtos = [self._normalizar_produto(item) for item in produtos_raw]
                    for item in produtos_raw:
                        if isinstance(item, dict):
                            chave = item.get("ordering_key")
                            if isinstance(chave, str) and chave:
                                ordering_keys.append(chave)
            if not produtos:
                return {"status": "skipped", "message": "Payload sem produtos"}
            if pyautogui is None:
                self.log_cb("PyAutoGUI indisponível: não é possível executar automação")
                return {"status": "error", "message": "PyAutoGUI indisponível no executor"}
            self.log_cb(f"Iniciando automação para {len(produtos)} produtos")
            resultado = await asyncio.to_thread(self._executar_fluxo_byte_empresa, produtos)
            if ordering_keys:
                resultado.setdefault("ordering_keys", ordering_keys)
            return resultado

        await asyncio.sleep(0.5)
        return {"status": "done", "message": f"Comando {command} finalizado"}

    def _normalizar_produto(self, item: object) -> Dict[str, Any]:
        if isinstance(item, dict):
            return {
                "nome": str(item.get("nome", "")),
                "codigo": str(item.get("codigo", "")),
                "quantidade": str(item.get("quantidade", "1")),
                "preco": str(item.get("preco", "")),
                "preco_final": str(item.get("preco_final", item.get("preco", ""))),
                "categoria": str(item.get("categoria", "")),
                "marca": str(item.get("marca", "")),
                "descricao_completa": str(item.get("descricao_completa", "")),
                "ordering_key": str(item.get("ordering_key", "")),
            }
        return {
            "nome": str(getattr(item, "nome", "")),
            "codigo": str(getattr(item, "codigo", "")),
            "quantidade": str(getattr(item, "quantidade", "1")),
            "preco": str(getattr(item, "preco", "")),
            "preco_final": str(getattr(item, "preco_final", getattr(item, "preco", ""))),
            "categoria": str(getattr(item, "categoria", "")),
            "marca": str(getattr(item, "marca", "")),
            "descricao_completa": str(getattr(item, "descricao_completa", "")),
            "ordering_key": str(getattr(item, "ordering_key", "")),
        }

    def _executar_fluxo_byte_empresa(self, produtos: List[Dict[str, Any]]) -> Dict[str, object]:
        inicio = time.time()
        try:
            self.log_cb(f"Preparando execução para {len(produtos)} produtos")
            recarregar_config_automacao()
            self.log_cb("Configurações de automação recarregadas")
            coordenadas = load_targets()
            if not coordenadas:
                raise RuntimeError("Coordenadas de calibração não encontradas")
            self.log_cb("Coordenadas carregadas com sucesso")

            ativado, mensagem = ativar_janela_byte_empresa(coordenadas)
            if not ativado:
                raise RuntimeError(f"Falha ao ativar Byte Empresa: {mensagem}")
            self.log_cb("Janela Byte Empresa ativada")

            sucesso = 0
            falhas: List[str] = []
            concluidos: List[str] = []

            for produto in produtos:
                if self.stop_event.is_set():
                    raise RuntimeError("Execução interrompida")
                nome = produto.get("nome") or produto.get("descricao_completa")
                codigo = produto.get("codigo")
                self.log_cb(f"Processando {nome} ({codigo})")
                try:
                    etapa1 = executar_tela1_mecanico(produto, coordenadas, threading.Event())
                    if not etapa1:
                        falhas.append(f"{codigo} (tela1)")
                        self.log_cb(f"Falha na tela 1 para {codigo}")
                        continue
                    etapa2 = executar_tela2_mecanico(produto, coordenadas, threading.Event())
                    if not etapa2:
                        falhas.append(f"{codigo} (tela2)")
                        self.log_cb(f"Falha na tela 2 para {codigo}")
                        continue
                    sucesso += 1
                    chave = produto.get("ordering_key")
                    if isinstance(chave, str) and chave:
                        concluidos.append(chave)
                    self.log_cb(f"Produto {codigo} concluído")
                except Exception as exc:  # pragma: no cover - interação real
                    falhas.append(f"{codigo}: {exc}")
                    self.log_cb(f"Erro no produto {codigo}: {exc}")

            duracao = time.time() - inicio
            mensagem = f"{sucesso} produtos concluídos"
            if falhas:
                mensagem += f", {len(falhas)} falhas"
                self.log_cb(f"Falhas registradas: {falhas}")
            return {
                "status": "done" if not falhas else "partial",
                "message": mensagem,
                "sucesso": sucesso,
                "falhas": falhas,
                "concluidos": concluidos,
            }
        except Exception as exc:
            self.log_cb(f"Falha na automação: {exc}")
            return {"status": "error", "message": str(exc)}


class ExecutorGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("LojaSync Executor")
        self.agent_var = tk.StringVar(value=f"Agent-{platform.node() or 'local'}")
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.token_var = tk.StringVar()
        self.capabilities_var = tk.StringVar(value=DEFAULT_CAPABILITIES)
        self.status_var = tk.StringVar(value=DEFAULT_STATUS_DISCONNECTED)
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: AgentWorker | None = None
        self.worker_thread: threading.Thread | None = None
        self._build_ui()
        self.root.after(200, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Agente").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(frame, textvariable=self.agent_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Host").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(frame, textvariable=self.host_var).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Porta").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(frame, textvariable=self.port_var).grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Token").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(frame, textvariable=self.token_var).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Capacidades").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(frame, textvariable=self.capabilities_var).grid(row=4, column=1, sticky="ew", pady=(0, 8))

        controls = ttk.Frame(frame)
        controls.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        self.connect_button = ttk.Button(controls, text="Conectar", command=self._toggle_connection)
        self.connect_button.grid(row=0, column=0, sticky="ew")
        self.trigger_button = ttk.Button(controls, text="Executar Cadastro", command=self._trigger_sequence, state="disabled")
        self.trigger_button.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.cancel_button = ttk.Button(controls, text="Parar", command=self._cancel_sequence, state="disabled")
        self.cancel_button.grid(row=0, column=2, sticky="ew")

        status_frame = ttk.Frame(frame)
        status_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1, sticky="w", padx=(8, 0))

        log_frame = ttk.LabelFrame(frame, text="Eventos")
        log_frame.grid(row=7, column=0, columnspan=2, sticky="nsew")
        frame.rowconfigure(7, weight=1)
        self.log_text = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _toggle_connection(self) -> None:
        if self.worker is not None:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        try:
            port = int(self.port_var.get().strip() or DEFAULT_PORT)
        except ValueError:
            messagebox.showerror("Erro", "Porta inválida")
            return
        host = self.host_var.get().strip() or DEFAULT_HOST
        agent_id = self.agent_var.get().strip()
        if not agent_id:
            messagebox.showerror("Erro", "Informe o nome do agente")
            return
        capabilities = _format_capabilities(self.capabilities_var.get() or DEFAULT_CAPABILITIES)
        self.worker = AgentWorker(host, port, agent_id, self.token_var.get().strip() or None, capabilities, self._enqueue_status, self._enqueue_log)
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()
        self.connect_button.config(text="Desconectar")
        self.trigger_button.config(state="normal")
        self.cancel_button.config(state="normal")
        self._enqueue_log("Iniciando conexão")

    def _disconnect(self) -> None:
        if self.worker is not None:
            self.worker.stop()
        if self.worker_thread is not None:
            self.worker_thread.join(timeout=2)
        self.worker = None
        self.worker_thread = None
        self.connect_button.config(text="Conectar")
        self.trigger_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self._enqueue_status(DEFAULT_STATUS_DISCONNECTED)
        self._enqueue_log("Conexão encerrada")

    def _trigger_sequence(self) -> None:
        if self.worker is None:
            messagebox.showinfo("Executor", "Conecte o agente antes de executar.")
            return
        try:
            self.worker.trigger_basic_sequence()
            self._enqueue_log("Comando de cadastro enviado")
        except Exception as exc:
            messagebox.showerror("Executor", f"Falha ao enviar comando: {exc}")

    def _cancel_sequence(self) -> None:
        if self.worker is None:
            messagebox.showinfo("Executor", "Conecte o agente antes de cancelar.")
            return
        self.worker.cancel_sequence()

    def _enqueue_status(self, text: str) -> None:
        self.queue.put(("status", text))

    def _enqueue_log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.queue.put(("log", f"[{timestamp}] {text}"))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, text = self.queue.get_nowait()
                if kind == "status":
                    self.status_var.set(text)
                    color = "green" if "Pronto" in text or "Conectado" in text else "red"
                    self.status_label.configure(foreground=color)
                elif kind == "log":
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", text + "\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self._drain_queue)

    def _on_close(self) -> None:
        self._disconnect()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = ExecutorGUI()
    app.run()


if __name__ == "__main__":
    main()
