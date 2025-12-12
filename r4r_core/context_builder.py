# r4r_core/context_builder.py
# --------------------------------------------------------------
# Genera un archivo context.md con metadatos YAML + resumen
# a partir de la memoria persistente (.pkl) de una fase,
# manteniendo el título original del proyecto.
# --------------------------------------------------------------

from pathlib import Path
import pickle
import yaml
from datetime import datetime
from dotenv import load_dotenv
import os
from r4r_core.summarizer_chain import summarize_conversation

def load_existing_conversation(memory_path: Path) -> list[dict]:
    """Carga un pickle existente de forma segura, con recuperación automática."""
    if not memory_path.exists():
        raise FileNotFoundError(f"No existe: {memory_path}")

    try:
        with open(memory_path, "rb") as f:
            data = pickle.load(f)
            # Verificación básica de integridad
            if not isinstance(data, list):
                raise ValueError("Contenido inesperado en pickle")
            return data
    except Exception as e:
        print(f"[⚠️] Error al leer {memory_path.name}: {e}")

        # Buscar copia de seguridad
        backup_dir = memory_path.parent / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob(f"{memory_path.stem}_*.bak"))
            if backups:
                last_backup = backups[-1]
                print(f"[♻️] Restaurando desde backup: {last_backup.name}")
                try:
                    with open(last_backup, "rb") as bf:
                        data = pickle.load(bf)
                        # reescribir copia estable
                        with open(memory_path, "wb") as nf:
                            pickle.dump(data, nf)
                        return data
                except Exception as ee:
                    print(f"[❌] No se pudo restaurar backup: {ee}")

        # fallback → crear lista vacía sin borrar .pkl previo
        print("[🆕] Fallback: creando lista vacía temporal sin sobrescribir.")
        return []

def auto_summary(messages: list[dict]) -> str:
    """Genera resumen real mediante el modelo definido en .env."""
    try:
        summary = summarize_conversation(messages)
        return summary.strip()
    except Exception as e:
        print(f"[Aviso] Falló el resumen automático: {e}")
        # Fallback de seguridad
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        return " | ".join(user_msgs[:3])[:250]


def get_base_title(project_dir: Path) -> str:
    """Obtiene el título original desde main/context.md."""
    main_md = project_dir / "main/context.md"
    if not main_md.exists():
        return "Proyecto R4R"
    try:
        with open(main_md, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"')
    except Exception as e:
        print(f"[Aviso] No se pudo leer título de main/context.md: {e}")
    return "Proyecto R4R"


def build_metadata(phase_name: str, messages: list[dict], base_title: str) -> dict:
    """Crea los metadatos preservando el título original del proyecto."""
    tags = [phase_name.lower()]
    if any("error" in m["content"].lower() for m in messages):
        tags.append("debug")
    return {
        "title": base_title,  # conservar nombre original
        "tags": tags,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": auto_summary(messages),
    }


def convert_to_markdown(metadata: dict, body_text: str) -> str:
    """Empaqueta YAML + cuerpo en markdown."""
    yaml_block = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{yaml_block}\n---\n\n{body_text.strip()}\n"


def save_context_md(project_dir: Path, phase_name: str, markdown_text: str):
    """Guarda context.md dentro de la carpeta de la fase."""
    phase_dir = project_dir / phase_name
    phase_dir.mkdir(parents=True, exist_ok=True)
    target = phase_dir / "context.md"
    with open(target, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    print(f"✅ context.md guardado en {target}")


def generate_context_md(project_name: str, phase_name: str):
    """Pipeline completo para construir context.md."""
    load_dotenv()
    base = Path(os.getenv("PROJECTS_DIR", "projects"))
    project_dir = base / project_name
    memory_path = project_dir / phase_name / f"contextmemory_{phase_name}.pkl"

    messages = load_existing_conversation(memory_path)
    base_title = get_base_title(project_dir)              # ← mantiene el título real

    metadata = build_metadata(phase_name, messages, base_title)
    body_lines = [f"{m['role'].upper()}: {m['content']}" for m in messages]
    markdown_body = "\n\n".join(body_lines)

    md_text = convert_to_markdown(metadata, markdown_body)
    save_context_md(project_dir, phase_name, md_text)
