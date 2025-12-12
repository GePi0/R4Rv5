# r4r_core/context_loader.py
# -------------------------------------------------------------
# Carga jerárquica de contextos (main + fases previas)
# y devuelve un "paquete de conocimiento" listo para usar.
# -------------------------------------------------------------

from pathlib import Path
import pickle
import yaml


class R4RContextLoader:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def _load_markdown(self, path: Path) -> str:
        if not path.exists():
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_memory(self, memory_path: Path):
        if not memory_path.exists():
            return []
        with open(memory_path, "rb") as f:
            return pickle.load(f)

    def _discover_phases(self) -> list[str]:
        """Devuelve lista ordenada de fases detectadas en el proyecto."""
        phases = []
        for p in self.project_dir.iterdir():
            if p.is_dir() and p.name.startswith("fase"):
                phases.append(p.name)
        return sorted(phases)

    def load_hierarchy(self, current_phase: str) -> dict:
        """Carga context.md jerárquicamente hasta current_phase."""
        main_md = self._load_markdown(self.project_dir / "main" / "context.md")
        phases = self._discover_phases()

        static_contexts = [{"phase": "main", "content": main_md}]
        merged_text = main_md

        for ph in phases:
            content = self._load_markdown(self.project_dir / ph / "context.md")
            static_contexts.append({"phase": ph, "content": content})
            merged_text += f"\n\n# --- {ph.upper()} ---\n\n{content}"
            if ph == current_phase:
                break

        # añadir memory de la fase actual
        mem_path = self.project_dir / current_phase / f"contextmemory_{current_phase}.pkl"
        dynamic_memory = self._load_memory(mem_path)

        return {
            "static_contexts": static_contexts,
            "dynamic_memory": dynamic_memory,
            "merged_text": merged_text,
        }
