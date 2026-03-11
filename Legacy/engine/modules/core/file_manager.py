"""
📁 GERENCIADOR DE ARQUIVOS
==========================

Responsável por todas as operações de arquivo:
- Detecção do diretório da aplicação
- Salvamento e carregamento de configurações
- Gerenciamento de dados (marcas, margem, targets)
- Histórico de produtos
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Union
from ..config.constants import MARCAS_PADRAO, MARGEM_PADRAO, MARCAS_POR_TIPAGEM


def get_app_base_dir() -> Path:
    """
    🗂️ GERENCIAMENTO DE DIRETÓRIOS
    
    Retorna a pasta base da aplicação, funcionando tanto para:
    - Script Python (.py): Usa a pasta onde está o arquivo
    - Executável (.exe): Usa a pasta onde está o executável
    
    LÓGICA:
    1. Verifica se está rodando como executável (PyInstaller)
    2. Se SIM: pega a pasta do .exe (cuidado com _internal)
    3. Se NÃO: pega a pasta do script .py
    
    RETORNO:
    Path object da pasta base onde ficam os dados
    """
    # Detecta se está rodando como executável compilado
    if getattr(sys, "frozen", False):
        try:
            # Pega o caminho do executável
            base = Path(sys.executable).resolve().parent
            
            # PyInstaller às vezes cria pasta _internal, usar a pasta pai
            if base.name.lower() == "_internal":
                return base.parent
            return base
        except Exception:
            # Em caso de erro, usa pasta atual
            return Path.cwd()
    
    # Se rodando como script Python, usa pasta do arquivo
    # Como estamos em modules/core/, precisa subir 2 níveis
    return Path(__file__).parent.parent.parent


def ensure_data_dir() -> Path:
    """Garante que o diretório data/ existe e retorna o caminho."""
    data_dir = get_app_base_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ===================================================================
# FUNÇÕES DE COORDENADAS DE CALIBRAÇÃO
# ===================================================================

def save_targets(config: dict) -> Path:
    """Salva as coordenadas de calibração em data/targets.json."""
    data_dir = ensure_data_dir()
    path = data_dir / "targets.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_targets() -> dict:
    """Carrega as coordenadas de calibração de data/targets.json."""
    path = get_app_base_dir() / "data" / "targets.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# ===================================================================
# FUNÇÕES DE HISTÓRICO DE PRODUTOS
# ===================================================================

def save_entry(payload: dict) -> Path:
    """Salva um item no arquivo data/enviados.jsonl."""
    data_dir = ensure_data_dir()
    enviados = data_dir / "enviados.jsonl"

    payload_out = {
        **{k: str(v).strip() for k, v in payload.items()},
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": "ok",
    }
    
    with enviados.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload_out, ensure_ascii=False) + "\n")
    # Snapshot após a alteração (estado atual), para que Ctrl+Z volte para o estado anterior
    try:
        create_enviados_snapshot(tag="append")  # type: ignore
    except Exception:
        pass
    return enviados


# ===================================================================
# BACKUP / UNDO de enviados.jsonl
# ===================================================================

def get_enviados_path() -> Path:
    """Retorna o caminho absoluto do arquivo data/enviados.jsonl, garantindo data/."""
    return ensure_data_dir() / "enviados.jsonl"


def _get_enviados_backups_dir() -> Path:
    """Diretório de backups do enviados.jsonl: data/backups/enviados/"""
    d = ensure_data_dir() / "backups" / "enviados"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_enviados(tag: str = "") -> Path:
    """Cria um backup do data/enviados.jsonl em data/backups/enviados/.

    Nome: enviados-YYYYMMDD-HHMMSS[-tag].jsonl
    Se o arquivo não existir ainda, cria um backup vazio para manter histórico.
    Retorna o caminho do backup gerado.
    """
    enviados = get_enviados_path()
    backups_dir = _get_enviados_backups_dir()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag_norm = ("-" + tag.strip()) if tag and tag.strip() else ""
    backup_path = backups_dir / f"enviados-{ts}{tag_norm}.jsonl"
    try:
        if enviados.exists():
            backup_path.write_text(enviados.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            backup_path.write_text("", encoding="utf-8")
    except Exception as e:
        print(f"Erro ao criar backup de enviados: {e}")
    return backup_path


def list_enviados_backups(limit: int = 50) -> List[Path]:
    """Lista backups de enviados.jsonl ordenados por data (mais recentes primeiro)."""
    d = _get_enviados_backups_dir()
    items = sorted(d.glob("enviados-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return items[: max(1, int(limit))]


def restore_enviados_from_backup(backup_path: Union[str, Path]) -> Path:
    """Restaura enviados.jsonl a partir de um backup específico.

    Antes de restaurar, cria um backup do estado atual (tag pre-restore).
    Retorna o caminho do arquivo restaurado (enviados.jsonl).
    """
    try:
        bp = Path(backup_path).resolve()
        if not bp.exists():
            raise FileNotFoundError(f"Backup não encontrado: {bp}")
        # Backup do estado atual
        backup_enviados(tag="pre-restore")
        # Restaurar
        enviados = get_enviados_path()
        enviados.write_text(bp.read_text(encoding="utf-8"), encoding="utf-8")
        return enviados
    except Exception as e:
        print(f"Erro ao restaurar enviados: {e}")
        return get_enviados_path()


def restore_enviados_last_backup() -> Path:
    """Restaura o backup mais recente disponível de enviados.jsonl.

    Cria um backup do estado atual (tag pre-restore) antes de restaurar.
    """
    backups = list_enviados_backups(limit=1)
    if not backups:
        print("Nenhum backup de enviados encontrado.")
        return get_enviados_path()
    return restore_enviados_from_backup(backups[0])


# ===================================================================
# UNDO/REDO multi-nível com ponteiro persistente
# ===================================================================

def _undo_state_path() -> Path:
    """Caminho do arquivo de estado do undo/redo."""
    return _get_enviados_backups_dir() / "state.json"


def _load_undo_state() -> dict:
    p = _undo_state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8") or "{}")
        except Exception:
            return {}
    return {}


def _save_undo_state(state: dict) -> None:
    p = _undo_state_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def create_enviados_snapshot(tag: str = "ui", max_snapshots: int = 30) -> Path:
    """Cria um snapshot com controle de pilha undo/redo.

    - Salva o estado atual de enviados.jsonl em backups.
    - Atualiza a lista ordenada de snapshots e o ponteiro 'index'.
    - Remove qualquer snapshot à frente do ponteiro (reset de REDO).
    - Faz pruning para manter no máximo 'max_snapshots'.
    """
    # Criar backup físico atual
    snap_path = backup_enviados(tag=tag)

    state = _load_undo_state()
    lista = state.get("list", []) or []
    idx = state.get("index")
    if not isinstance(idx, int):
        idx = len(lista) - 1
    # Descartar redos à frente do ponteiro atual
    if 0 <= idx < len(lista) - 1:
        lista = lista[: idx + 1]
    # Adicionar novo snapshot
    try:
        lista.append(str(snap_path))
    except Exception:
        pass
    # Pruning se exceder
    while len(lista) > max(1, int(max_snapshots)):
        try:
            # Remover o mais antigo [0]
            old = Path(lista.pop(0))
            if old.exists():
                old.unlink(missing_ok=True)  # type: ignore
        except Exception:
            pass
    # Atualizar ponteiro para o último
    idx = len(lista) - 1
    state = {"list": lista, "index": idx}
    _save_undo_state(state)
    return snap_path


def undo_enviados_step() -> bool:
    """Restaura o snapshot anterior (Ctrl+Z). Retorna True se aplicou, False caso contrário."""
    state = _load_undo_state()
    lista = state.get("list", []) or []
    idx = state.get("index")
    if not isinstance(idx, int):
        return False
    if idx <= 0 or idx >= len(lista):
        return False
    # Mover ponteiro para trás e restaurar
    idx -= 1
    target = Path(lista[idx])
    restore_enviados_from_backup(target)
    state["index"] = idx
    _save_undo_state(state)
    return True


def has_undo_history() -> bool:
    """Retorna True se já existir histórico de snapshots (state.json com lista)."""
    st = _load_undo_state()
    lst = st.get("list", []) or []
    return len(lst) > 0


def seed_undo_if_empty(tag: str = "init") -> None:
    """Garante um snapshot inicial se o histórico estiver vazio."""
    try:
        if not has_undo_history():
            create_enviados_snapshot(tag=tag)
    except Exception:
        pass


def redo_enviados_step() -> bool:
    """Restaura o próximo snapshot (Ctrl+Y). Retorna True se aplicou, False caso contrário."""
    state = _load_undo_state()
    lista = state.get("list", []) or []
    idx = state.get("index")
    if not isinstance(idx, int):
        return False
    if idx < -1 or idx >= len(lista) - 1:
        return False
    # Mover ponteiro para frente e restaurar
    idx += 1
    target = Path(lista[idx])
    restore_enviados_from_backup(target)
    state["index"] = idx
    _save_undo_state(state)
    return True


# ===================================================================
# FUNÇÕES DE GERENCIAMENTO DE MARCAS
# ===================================================================

def carregar_marcas_salvas() -> List[str]:
    """Carrega a lista de marcas salvas do arquivo data/marcas.json."""
    try:
        arquivo_marcas = get_app_base_dir() / "data" / "marcas.json"
        if arquivo_marcas.exists():
            with open(arquivo_marcas, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Cria arquivo com marcas padrão se não existir
            salvar_marcas(MARCAS_PADRAO)
            return MARCAS_PADRAO
    except Exception:
        return MARCAS_PADRAO


def salvar_marcas(marcas: List[str]) -> None:
    """Salva a lista de marcas no arquivo data/marcas.json."""
    try:
        data_dir = ensure_data_dir()
        arquivo_marcas = data_dir / "marcas.json"
        with open(arquivo_marcas, "w", encoding="utf-8") as f:
            json.dump(marcas, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar marcas: {e}")


def adicionar_nova_marca(nova_marca: str) -> bool:
    """Adiciona uma nova marca à lista e salva no arquivo."""
    try:
        marcas = carregar_marcas_salvas()
        if nova_marca.strip() and nova_marca not in marcas:
            marcas.append(nova_marca.strip())
            salvar_marcas(marcas)
            return True
        return False
    except Exception:
        return False


# ===================================================================
# FUNÇÕES DE GERENCIAMENTO DE MARCAS POR TIPAGEM
# ===================================================================

def carregar_marcas_por_tipagem() -> Dict[str, List[str]]:
    """Carrega as marcas específicas por tipagem do arquivo data/marcas_tipagem.json."""
    try:
        arquivo_marcas_tipagem = get_app_base_dir() / "data" / "marcas_tipagem.json"
        if arquivo_marcas_tipagem.exists():
            with open(arquivo_marcas_tipagem, "r", encoding="utf-8") as f:
                marcas_tipagem = json.load(f)
                # Garantir que todas as tipagens existem
                for tipagem in MARCAS_POR_TIPAGEM:
                    if tipagem not in marcas_tipagem:
                        marcas_tipagem[tipagem] = MARCAS_POR_TIPAGEM[tipagem].copy()
                return marcas_tipagem
        else:
            # Cria arquivo com marcas padrão por tipagem se não existir
            marcas_iniciais = {}
            for tipagem, marcas in MARCAS_POR_TIPAGEM.items():
                marcas_iniciais[tipagem] = marcas.copy()
            salvar_marcas_por_tipagem(marcas_iniciais)
            return marcas_iniciais
    except Exception as e:
        print(f"Erro ao carregar marcas por tipagem: {e}")
        return MARCAS_POR_TIPAGEM.copy()


def salvar_marcas_por_tipagem(marcas_tipagem: Dict[str, List[str]]) -> None:
    """Salva as marcas por tipagem no arquivo data/marcas_tipagem.json."""
    try:
        data_dir = ensure_data_dir()
        arquivo_marcas_tipagem = data_dir / "marcas_tipagem.json"
        with open(arquivo_marcas_tipagem, "w", encoding="utf-8") as f:
            json.dump(marcas_tipagem, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar marcas por tipagem: {e}")


def obter_marcas_para_tipagem(tipagem: str) -> List[str]:
    """Retorna as marcas disponíveis para uma tipagem específica."""
    try:
        marcas_tipagem = carregar_marcas_por_tipagem()
        
        if tipagem == "padrao":
            # Para tipagem padrão, retorna todas as marcas salvas
            return carregar_marcas_salvas()
        elif tipagem in marcas_tipagem:
            # Para outras tipagens, retorna as marcas específicas
            return marcas_tipagem[tipagem]
        else:
            # Fallback para marcas padrão
            return MARCAS_PADRAO
    except Exception as e:
        print(f"Erro ao obter marcas para tipagem {tipagem}: {e}")
        return MARCAS_PADRAO


def adicionar_marca_para_tipagem(tipagem: str, nova_marca: str) -> bool:
    """Adiciona uma nova marca para uma tipagem específica."""
    try:
        nova_marca = nova_marca.strip()
        if not nova_marca:
            return False
            
        marcas_tipagem = carregar_marcas_por_tipagem()
        
        # Garantir que a tipagem existe
        if tipagem not in marcas_tipagem:
            marcas_tipagem[tipagem] = []
        
        # Adicionar marca se não existir
        if nova_marca not in marcas_tipagem[tipagem]:
            marcas_tipagem[tipagem].append(nova_marca)
            salvar_marcas_por_tipagem(marcas_tipagem)
            
            # Se for tipagem padrão, também adiciona na lista geral
            if tipagem == "padrao":
                adicionar_nova_marca(nova_marca)
            
            return True
        return False
    except Exception as e:
        print(f"Erro ao adicionar marca {nova_marca} para tipagem {tipagem}: {e}")
        return False


# ===================================================================
# FUNÇÕES DE GERENCIAMENTO DE MARGEM
# ===================================================================

def carregar_margem_padrao() -> float:
    """Carrega a margem padrão do arquivo data/margem.json."""
    try:
        arquivo_margem = get_app_base_dir() / "data" / "margem.json"
        if arquivo_margem.exists():
            with open(arquivo_margem, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return dados.get("margem", MARGEM_PADRAO)
        else:
            # Cria arquivo com margem padrão se não existir
            salvar_margem_padrao(MARGEM_PADRAO)
            return MARGEM_PADRAO
    except Exception:
        return MARGEM_PADRAO


def salvar_margem_padrao(margem: float) -> None:
    """Salva a margem padrão no arquivo data/margem.json."""
    try:
        data_dir = ensure_data_dir()
        arquivo_margem = data_dir / "margem.json"
        with open(arquivo_margem, "w", encoding="utf-8") as f:
            json.dump({"margem": margem}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar margem: {e}")


# ===================================================================
# FUNÇÕES DE PERSISTÊNCIA DE GRADES
# ===================================================================

def carregar_grades() -> Dict[str, dict]:
    """Carrega o dicionário de grades salvas de data/grades.json.

    Estrutura esperada:
    {
      "0": {"sizes": {"GG": 1, "G": 2, ...}, "total": 3, "timestamp": "..."},
      "1": {...}
    }
    """
    try:
        arquivo = get_app_base_dir() / "data" / "grades.json"
        if arquivo.exists():
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception:
        return {}


def salvar_grade(index: int, grade: Dict[str, int]) -> Path:
    """Salva a grade de um produto (por índice da lista exibida) em data/grades.json.

    Parâmetros:
    - index: índice do produto na lista exibida (0-based)
    - grade: dict tamanho->quantidade, ex: {"GG":2, "G":1}
    """
    data_dir = ensure_data_dir()
    arquivo = data_dir / "grades.json"

    # Carregar grades existentes
    try:
        grades = {}
        if arquivo.exists():
            with open(arquivo, "r", encoding="utf-8") as f:
                grades = json.load(f)
    except Exception:
        grades = {}

    # Normalizar chaves e calcular total
    index_key = str(index)
    total = sum(int(v) for v in grade.values()) if grade else 0
    grades[index_key] = {
        "sizes": {str(k): int(v) for k, v in grade.items()},
        "total": int(total),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    # Salvar arquivo
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(grades, f, ensure_ascii=False, indent=2)

    return arquivo


def salvar_grades(grades_dict: Dict[str, dict]) -> Path:
    """Sobrescreve o arquivo data/grades.json com o dicionário informado.

    Estrutura esperada das entradas: { "<index>": {"sizes": {...}, "total": int, "timestamp": str} }
    """
    data_dir = ensure_data_dir()
    arquivo = data_dir / "grades.json"
    # Normalizar chaves como str
    grades_out = {}
    for k, v in (grades_dict or {}).items():
        try:
            sizes = v.get("sizes", {}) if isinstance(v, dict) else {}
            total = int(v.get("total", sum(int(x) for x in sizes.values()))) if isinstance(v, dict) else 0
            ts = v.get("timestamp") if isinstance(v, dict) else None
        except Exception:
            sizes, total, ts = {}, 0, None
        grades_out[str(k)] = {
            "sizes": {str(kk): int(vv) for kk, vv in (sizes or {}).items()},
            "total": int(total),
            "timestamp": ts or datetime.now().isoformat(timespec="seconds"),
        }
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(grades_out, f, ensure_ascii=False, indent=2)
    return arquivo


def limpar_grades() -> None:
    """Apaga todas as grades (remove o arquivo data/grades.json ou o zera)."""
    arquivo = get_app_base_dir() / "data" / "grades.json"
    try:
        if arquivo.exists():
            arquivo.unlink()
        # Alternativamente, poderíamos escrever um JSON vazio
        # arquivo.write_text("{}", encoding="utf-8")
    except Exception as e:
        print(f"Erro ao limpar grades: {e}")
