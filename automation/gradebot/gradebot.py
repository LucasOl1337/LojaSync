import json
import time
import argparse
from pathlib import Path
from typing import Callable, Dict, List, Tuple

try:
    import pyautogui as pag
except Exception as e:
    raise SystemExit(f"pyautogui não está instalado ou falhou ao carregar: {e}")

pag.FAILSAFE = True
pag.PAUSE = 0.08

SPEED = 1.0  # multiplicador de tempo para esperas internas

ConfigPath = Path(__file__).with_name("config.json")


def _load_config(path: Path = ConfigPath) -> dict:
    if not path.exists():
        raise SystemExit(f"Config não encontrado em {path}. Rode: python gradebot.py calibrate")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg: dict, path: Path = ConfigPath):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _get_mouse_pos(prompt: str) -> Tuple[int, int]:
    input(f"{prompt} | Posicione o mouse no local pedido e pressione ENTER...")
    x, y = pag.position()
    print(f"  -> capturado: ({x}, {y})")
    return int(x), int(y)


def calibrate():
    print("=== GradeBot - Calibração ===")
    print("Esta calibração grava coordenadas da sua tela para automação.")
    print("Dica: deixe o ERP aberto na tela alvo, em 100% de escala do Windows.")

    cfg = {
        "buttons": {},
        "grid": {},
        "model": {"strategy": "index", "index": 0, "hotkey": ""},
        "erp_size_order": []
    }

    def _capture(key: str, prompt: str, optional: bool = False):
        if optional:
            answer = input(f"Deseja calibrar '{key}' agora? (s/N): ").strip().lower()
            if answer not in {"s", "sim", "y", "yes"}:
                return
        cfg["buttons"][key] = _get_mouse_pos(prompt)

    # Focar aplicativo e abrir alteração de grade
    _capture("focus_app", "Barra de tarefas ou Desktop: posicione no ícone do Byte Empresa para focar a janela")
    _capture("alterar_grade", "Janela do ERP: posicione no botão 'Alterar Grade' (ou 'Definir Grade')")
    # Botões/menu
    _capture("modelos", "Na janela de grade, posicione no botão 'Modelos'")
    _capture("model_select", "Janela 'Consulta Grades Modelo': clique na linha/posição do modelo padrão")
    _capture("model_ok", "Janela 'Consulta Grades Modelo': posicione no botão OK")
    _capture("confirm_sim", "Caixa 'Importar Grade Modelo': posicione no botão 'Sim'")
    _capture("close_after_import", "Se houver, posicione no botão 'Fechar' que aparece antes da grade final", optional=True)
    _capture("save_grade", "Na janela de grade, posicione no botão 'Ok/Gravar' final", optional=True)
    _capture("close_grade", "Ainda na janela de grade, posicione no botão 'Fechar' final", optional=True)

    # Grid
    print("Agora vamos calibrar a grade de tamanhos (coluna Quantidade)")
    first = _get_mouse_pos("Posicione no campo QUANTIDADE da 1ª linha (primeiro tamanho)")
    cfg["grid"]["first_quant_cell"] = first
    try:
        row_height = int(input("Altura (em pixels) entre cada linha da grade (ex.: 17): ") or "17")
    except ValueError:
        row_height = 17
    cfg["grid"]["row_height"] = max(1, row_height)

    # Ordem dos tamanhos conforme o ERP
    print("Informe a ordem dos tamanhos exatamente como aparecem no ERP (separados por vírgula).\nExemplo: PP,P,M,G,GG ou 32,34,36,38,40,42")
    order = input("Tamanhos (ordem): ").strip()
    cfg["erp_size_order"] = [s.strip() for s in order.split(",") if s.strip()]

    # Estratégia de fallback por índice
    try:
        idx = int(input("Índice (0-based) do modelo padrão na lista (ENTER para 0): ") or "0")
    except ValueError:
        idx = 0
    cfg["model"]["index"] = idx

    # Compatibilidade com versões antigas
    if "open_grade" not in cfg["buttons"]:
        cfg["buttons"]["open_grade"] = cfg["buttons"].get("alterar_grade")

    _save_config(cfg)
    print(f"Calibração salva em {ConfigPath}")


def _move_click(x: int, y: int, delay: float = 0.15):
    pag.moveTo(x, y, duration=delay)
    pag.click()


def _type_value(v: int):
    pag.typewrite(str(int(v)))


def _sleep(t: float):
    time.sleep(max(0.0, t) * SPEED)


def _normalize_key(k: str) -> str:
    return str(k).strip().lower()


def _build_row_values(erp_order: List[str], grades: Dict[str, int]) -> List[int]:
    # normaliza para comparação tolerante (P,p etc.)
    norm_map = {_normalize_key(k): int(v) for k, v in grades.items()}
    values = []
    for label in erp_order:
        values.append(norm_map.get(_normalize_key(label), 0))
    return values


def _as_xy(p) -> Tuple[int, int]:
    if p is None:
        raise SystemExit("Coordenada ausente na configuração. Refaça a calibração.")
    if isinstance(p, dict):
        x = p.get("x")
        y = p.get("y")
        if x is None or y is None:
            raise SystemExit("Coordenada inválida (dict sem x/y). Refaça a calibração.")
        return int(x), int(y)
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return int(p[0]), int(p[1])
    raise SystemExit("Coordenada inválida. Refaça a calibração.")


RUN_SEQUENCE: List[str] = [
    "activation",
    "open_model_button",
    "select_model_entry",
    "confirm_model_ok",
    "confirm_import",
    "close_aux_modal",
    "fill_grid",
    "save_and_close",
]
"""Sequência padrão de passos PyAutoGUI.

Reordene ou edite esta lista para controlar a ordem das ações. Cada item
corresponde a uma função registrada em STEP_HANDLERS; basta comentar/remover
um passo ou inserir novos desde que tenham um handler cadastrado.
"""


STEP_HANDLERS: Dict[str, Callable[[dict], None]] = {}


def _register_step(name: str):
    def decorator(func: Callable[[dict], None]):
        STEP_HANDLERS[name] = func
        return func

    return decorator


CANCEL_REQUESTED = False


def reset_stop_flag():
    global CANCEL_REQUESTED
    CANCEL_REQUESTED = False


def request_stop():
    global CANCEL_REQUESTED
    CANCEL_REQUESTED = True


def is_cancel_requested() -> bool:
    return bool(CANCEL_REQUESTED)


@_register_step("activation")
def _step_activation(ctx: dict):
    if ctx.get("activation_step") and ctx.get("focus_btn"):
        _move_click(*ctx["focus_btn"])
        _sleep(0.4)
    if ctx.get("alterar_btn"):
        _move_click(*ctx["alterar_btn"])
        _sleep(0.35)


@_register_step("open_model_button")
def _step_open_model(ctx: dict):
    _move_click(*ctx["modelos_btn"])
    _sleep(0.4)


@_register_step("select_model_entry")
def _step_select_model_entry(ctx: dict):
    btn = ctx.get("model_select_btn")
    if not btn:
        print("[gradebot] coordenada 'model_select' ausente; pule este passo ou recalcule.")
        return
    _move_click(*btn)
    _sleep(0.2)


@_register_step("confirm_model_ok")
def _step_confirm_model_ok(ctx: dict):
    btn = ctx.get("model_ok_btn")
    if not btn:
        print("[gradebot] coordenada 'model_ok' ausente; recalcule.")
        return
    _move_click(*btn)
    _sleep(0.35)


@_register_step("confirm_import")
def _step_confirm_import(ctx: dict):
    _move_click(*ctx["confirm_btn"])
    _sleep(0.4)


@_register_step("close_aux_modal")
def _step_close_aux(ctx: dict):
    btn = ctx.get("close_import_btn")
    if not btn:
        return
    _move_click(*btn)
    _sleep(0.25)


@_register_step("fill_grid")
def _step_fill_grid(ctx: dict):
    row_values = ctx["row_values"]
    last_fill_idx = ctx["last_fill_idx"]
    first_cell = ctx["first_cell"]
    _move_click(*first_cell)
    _sleep(0.03)
    if last_fill_idx == -1:
        return

    for i, val in enumerate(row_values):
        if CANCEL_REQUESTED:
            print("[gradebot] cancelamento solicitado — interrompendo preenchimento")
            ctx["cancelled"] = True
            return
        if i > last_fill_idx:
            break
        should_fill = int(val or 0) > 0
        if should_fill:
            _type_value(val)
            pag.press('enter')
            pag.press('down')
            _sleep(0.02)
        elif i < last_fill_idx:
            pag.press('down')


@_register_step("save_and_close")
def _step_save_close(ctx: dict):
    if ctx.get("cancelled"):
        return
    if ctx.get("save_btn"):
        _move_click(*ctx["save_btn"])
        _sleep(0.35)
    if ctx.get("close_btn"):
        _move_click(*ctx["close_btn"])
        _sleep(0.25)


def run(grades: Dict[str, int], model_index: int | None = None, activation_step: bool = True):
    cfg = _load_config()

    def _get_btn(name: str):
        btns = cfg.get("buttons", {})
        value = btns.get(name)
        if not value:
            return ()
        try:
            return _as_xy(value)
        except SystemExit:
            return ()

    focus_btn = _get_btn("focus_app")
    alterar_btn = _get_btn("alterar_grade") or _get_btn("open_grade")
    modelos_btn = _as_xy(cfg["buttons"]["modelos"])
    model_select_btn = _as_xy(cfg["buttons"]["model_select"])
    model_ok_btn = _as_xy(cfg["buttons"]["model_ok"])
    confirm_btn = _as_xy(cfg["buttons"]["confirm_sim"])
    close_import_btn = _get_btn("close_after_import")
    save_btn = _get_btn("save_grade")
    close_btn = _get_btn("close_grade")
    first_cell = _as_xy(cfg["grid"]["first_quant_cell"])
    row_height = int(cfg["grid"].get("row_height", 20) or 20)
    erp_order = cfg.get("erp_size_order", [])

    if not erp_order:
        raise SystemExit("Config erp_size_order vazio. Rode 'calibrate' e preencha a ordem dos tamanhos.")

    row_values = _build_row_values(erp_order, grades)
    print("[gradebot] valores alinhados:", row_values)
    last_fill_idx = max((idx for idx, value in enumerate(row_values) if int(value or 0) > 0), default=-1)

    ctx = {
        "cfg": cfg,
        "activation_step": bool(activation_step),
        "focus_btn": focus_btn,
        "alterar_btn": alterar_btn,
        "modelos_btn": modelos_btn,
        "model_select_btn": model_select_btn,
        "model_ok_btn": model_ok_btn,
        "confirm_btn": confirm_btn,
        "close_import_btn": close_import_btn,
        "save_btn": save_btn,
        "close_btn": close_btn,
        "first_cell": first_cell,
        "row_height": row_height,
        "row_values": row_values,
        "last_fill_idx": last_fill_idx,
        "cancelled": False,
    }

    for step_name in RUN_SEQUENCE:
        if ctx.get("cancelled") or CANCEL_REQUESTED:
            break
        handler = STEP_HANDLERS.get(step_name)
        if handler is None:
            print(f"[gradebot] passo '{step_name}' não possui handler registrado — pulando")
            continue
        handler(ctx)

    if CANCEL_REQUESTED or ctx.get("cancelled"):
        print("[gradebot] cancelado antes de finalizar a janela de grade")
        return

    print("Preenchimento concluído.")


def parse_grades_json(path: str) -> Dict[str, int]:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Arquivo não encontrado: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # {"P": 1, "M": 2}
        return {str(k): int(v) for k, v in data.items()}
    if isinstance(data, list):
        # [{"tamanho":"P","quantidade":1}, ...]
        out = {}
        for item in data:
            k = str(item.get("tamanho"))
            v = int(item.get("quantidade", 0))
            out[k] = v
        return out
    raise SystemExit("JSON inválido: use objeto {tamanho: quantidade} ou lista de itens.")


def parse_tasks_json(path: str) -> List[dict]:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Arquivo não encontrado: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("Tasks JSON inválido: deve ser uma lista de tarefas.")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="GradeBot - automação de preenchimento de grades (PyAutoGUI). Use um JSON no formato {tamanho: quantidade} ou lista de itens.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_cal = sub.add_parser("calibrate", help="calibrar coordenadas e ordem dos tamanhos")

    sp_run = sub.add_parser("run", help="executar preenchimento")
    sp_run.add_argument("grades_json", help="arquivo JSON com as quantidades por tamanho")
    sp_run.add_argument("--model-index", type=int, default=None, help="índice do modelo na lista (0=primeiro)")
    sp_run.add_argument("--pause", type=float, default=0.08, help="pausa do pyautogui entre ações (default=0.08)")
    sp_run.add_argument("--speed", type=float, default=1.0, help="fator de velocidade para esperas internas (1.0 padrão)")

    sp_batch = sub.add_parser("batch", help="executar preenchimento em lote a partir de um arquivo de tarefas")
    sp_batch.add_argument("tasks_json", help="arquivo JSON (lista) com tarefas: cada item pode ter 'grades' {tam:qtd} ou 'grades_json', e opcional 'model_index'")
    sp_batch.add_argument("--pause", type=float, default=0.08, help="pausa do pyautogui entre ações (default=0.08)")
    sp_batch.add_argument("--speed", type=float, default=1.0, help="fator de velocidade para esperas internas (1.0 padrão)")

    args = ap.parse_args()

    if args.cmd == "calibrate":
        calibrate()
    elif args.cmd == "run":
        grades_map = parse_grades_json(args.grades_json)
        pag.PAUSE = max(0.0, float(args.pause))
        SPEED = max(0.05, float(args.speed))
        run(grades_map, model_index=args.model_index)
    elif args.cmd == "batch":
        tasks = parse_tasks_json(args.tasks_json)
        pag.PAUSE = max(0.0, float(args.pause))
        SPEED = max(0.05, float(args.speed))
        for i, job in enumerate(tasks, start=1):
            print(f"=== Tarefa {i}/{len(tasks)} ===")
            if isinstance(job, dict) and "grades" in job and isinstance(job["grades"], dict):
                grades_map = {str(k): int(v) for k, v in job["grades"].items()}
            elif isinstance(job, dict) and "grades_json" in job:
                grades_map = parse_grades_json(str(job["grades_json"]))
            else:
                print("Tarefa ignorada: faltou 'grades' ou 'grades_json'.")
                continue
            m_idx = job.get("model_index", None)
            run(grades_map, model_index=m_idx)
            _sleep(0.4)
