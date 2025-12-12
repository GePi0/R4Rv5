# r4r_core/conversation_persistence.py
# -------------------------------------------------------------
# Módulo de persistencia local de conversaciones R4R
# Cada mensaje se guarda en disco (.pkl)
# Autoguardado inmediato con backup seguro
# -------------------------------------------------------------

import pickle
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List


def ensure_dir(path: Path) -> None:
    """Crea el directorio padre si no existe."""
    path.parent.mkdir(parents=True, exist_ok=True)

def append_message(memory_path: Path, role: str, content: str, extra: dict | None = None) -> None:
    """Añade un mensaje (user o assistant) y guarda inmediatamente."""
    ensure_dir(memory_path)
    messages: list[dict[str, Any]] = []
    if memory_path.exists():
        try:
            with open(memory_path, "rb") as f:
                messages = pickle.load(f)
        except Exception:
            messages = []

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "content": content,
    }

    # 🟢 incluir métricas u otros datos auxiliares
    if extra and isinstance(extra, dict):
        entry["meta"] = extra

    messages.append(entry)

    tmp_path = memory_path.with_suffix(".pkl.tmp")
    with open(tmp_path, "wb") as f:
        pickle.dump(messages, f)
    tmp_path.replace(memory_path)
    auto_backup(memory_path)


    # 🟢 Guardamos atómicamente para evitar corrupción por cierres abruptos
    tmp_path = memory_path.with_suffix(".pkl.tmp")
    with open(tmp_path, "wb") as f:
        pickle.dump(messages, f)

    tmp_path.replace(memory_path)

    # 🟢 Backup en cada guardado (copias versionadas)
    auto_backup(memory_path)


def load_memory(memory_path: Path) -> List[dict[str, Any]]:
    """Carga la conversación previa si existe."""
    if not memory_path.exists():
        return []
    try:
        with open(memory_path, "rb") as f:
            data = pickle.load(f)
            if not isinstance(data, list):
                return []
            return data
    except Exception:
        return []


def auto_backup(memory_path: Path) -> None:
    """Genera copia .bak con timestamp (rotativo)."""
    backup_dir = memory_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{memory_path.stem}_{timestamp}.bak"

    # Evita copia de 0 bytes o interrumpida
    if memory_path.exists() and memory_path.stat().st_size > 0:
        shutil.copy(memory_path, backup_path)


def rollback_last(memory_path: Path) -> None:
    """Elimina el último mensaje en caso de fallo."""
    if not memory_path.exists():
        return
    try:
        with open(memory_path, "rb") as f:
            messages = pickle.load(f)
        if messages:
            messages.pop()
            with open(memory_path, "wb") as f:
                pickle.dump(messages, f)
    except Exception:
        # no hacemos rollback si el archivo está corrupto
        pass


class SessionLogger:
    """Encapsula acceso a memoria persistente de una fase."""

    def __init__(self, project_dir: Path, phase: str):
        self.project_dir = project_dir
        self.phase = phase
        self.memory_path = self._build_path()
        ensure_dir(self.memory_path)

    def _build_path(self) -> Path:
        folder = "main" if self.phase.lower() == "main" else self.phase
        return self.project_dir / folder / f"contextmemory_{folder}.pkl"

    def save(self, role: str, content: str, extra: dict | None = None) -> None:
        append_message(self.memory_path, role, content, extra)

    def load(self) -> List[dict[str, Any]]:
        return load_memory(self.memory_path)

    def backup(self) -> None:
        auto_backup(self.memory_path)

    def rollback(self) -> None:
        rollback_last(self.memory_path)
