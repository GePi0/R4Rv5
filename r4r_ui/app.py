# r4r_ui/app.py
# ==========================================================
# FASE 6.8 — Persistencia completa con HUD rehidratable
# ==========================================================

import os, re, uuid, json, shutil, pickle, time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv

from r4r_core.rag_chain import R4RConversationalRAG
from r4r_core.conversation_persistence import load_memory
from r4r_core.context_builder import generate_context_md
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ----------------------------------------------------------
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "projects"))
sessions: dict[tuple[str, str], R4RConversationalRAG] = {}
saving_state: set[str] = set()

# ======================================================
# HELPERS
# ======================================================

def make_uuid() -> str:
    return f"{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"

def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip())
    return slug.strip("_")

# ======================================================
# ROUTES HTTP
# ======================================================

@app.route("/")
def index():
    return render_template("index.html")

# ---------- LISTAR PROYECTOS ----------
@app.route("/api/projects", methods=["GET"])
def list_projects():
    data = []
    for prj in PROJECTS_DIR.iterdir():
        if not prj.is_dir():
            continue
        title = prj.name
        meta = prj / "main/context.md"
        if meta.exists():
            with open(meta, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"')
                        break
        phases = [p.name for p in prj.iterdir() if p.is_dir()]
        data.append({"project": prj.name, "title": title, "phases": phases})
    # ordenar por fecha de creación (últimos arriba)
    data.sort(key=lambda x: os.path.getmtime(PROJECTS_DIR / x["project"]), reverse=True)
    return jsonify(data)

# ---------- HISTORIAL ----------
@app.route("/api/history", methods=["POST"])
def load_history():
    from r4r_core.context_builder import load_existing_conversation

    data = request.get_json()
    project = data.get("project")
    phase = data.get("phase", "main")

    pkl_path = PROJECTS_DIR / project / phase / f"contextmemory_{phase}.pkl"
    ctx_path = PROJECTS_DIR / project / phase / "context.md"

    messages = []
    if pkl_path.exists():
        try:
            messages = load_existing_conversation(pkl_path)
        except FileNotFoundError:
            messages = []

    ctx_exists = ctx_path.exists()
    ctx_time = ctx_path.stat().st_mtime if ctx_exists else 0
    memory_time = pkl_path.stat().st_mtime if pkl_path.exists() else 0
    pending = memory_time > ctx_time

    return jsonify({
        "history": messages,
        "context_exists": ctx_exists,
        "pending": pending,
        "memory_time": memory_time,
    })

# ---------- GUARDAR CONTEXTO Y CREAR NUEVA FASE ----------
@app.route("/api/save_context", methods=["POST"])
def save_context():
    data = request.get_json() or {}
    project = data.get("project")
    phase = data.get("phase", "main")

    project_dir = PROJECTS_DIR / str(project)
    if not project or not project_dir.exists():
        print(f"[❌] Proyecto inexistente: {project_dir}")
        return jsonify({"error": "project_not_found"}), 404

    key = f"{project}:{phase}"
    if key in saving_state:
        return jsonify({"status": "pending"}), 202
    saving_state.add(key)

    try:
        print(f"🔄 Generando context.md para {project}/{phase} ...")
        generate_context_md(project, phase)
    except Exception as e:
        print(f"[❌] Error al generar context.md: {e}")
        return jsonify({"error": "context_build_failed"}), 500
    finally:
        saving_state.discard(key)

    # Crear siguiente fase vacía
    existing = [
        p.name for p in project_dir.iterdir()
        if p.is_dir() and p.name.lower().startswith("fase")
    ]
    next_index = len(existing) + 1
    next_phase = f"fase {next_index}"
    next_phase_dir = project_dir / next_phase
    try:
        next_phase_dir.mkdir(exist_ok=True)
        (next_phase_dir / f"contextmemory_{next_phase}.pkl").touch()
    except Exception as e:
        print(f"[⚠️] Error creando nueva fase: {e}")

    return jsonify({"saved": True, "next_phase": next_phase})

# ---------- MENSAJE / CREACIÓN ----------
@app.route("/api/message", methods=["POST"])
def message_pipeline():
    """Procesa un mensaje del usuario y mantiene persistencia con HUD."""
    data = request.get_json()
    msg = data.get("message", "").strip()
    project = data.get("project")
    phase = data.get("phase", "main")

    llm = ChatOllama(
        model=os.getenv("MODEL_NAME", "mistral:7b"),
        temperature=0.3,
        base_url=os.getenv("OLLAMA_API_HOST", "http://localhost:11434"),
    )

    # === NUEVO PROYECTO ===
    if not project:
        uid = make_uuid()
        tmp_dir = PROJECTS_DIR / f"tmp_{uid}" / "main"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        multitask = PromptTemplate(
            input_variables=["input"],
            template=(
                "Analiza el mensaje inicial del usuario:\n\n{input}\n\n"
                "Devuelve JSON exacto con dos claves:\n"
                "title → título corto\n"
                "reply → respuesta útil y natural en español\n"
                '{{\"title\":\"...\", \"reply\":\"...\"}}'
            ),
        )
        chain = RunnablePassthrough() | multitask | llm | StrOutputParser()
        raw = chain.invoke({"input": msg})
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"title": "Nuevo proyecto", "reply": raw}

        title = payload["title"].strip()
        reply = payload["reply"].strip()

        slug = f"{slugify(title)}_r4r_{uid}"
        project_dir = PROJECTS_DIR / slug
        tmp_dir.parent.rename(project_dir)

        meta = (
            f"---\n"
            f"id: r4r_{uid}\n"
            f'title: "{title}"\n'
            f"created: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"summary: Proyecto creado automáticamente.\n"
            f"---\n"
        )
        with open(project_dir / "main/context.md", "w", encoding="utf-8") as f:
            f.write(meta)

        rag = R4RConversationalRAG(project_dir, "main")
        rag.initialize()
        sessions[(slug, "main")] = rag

        # Guardar primer mensaje + respuesta
        rag.logger.save("user", msg)
        rag.logger.save("assistant", reply, {
            "metrics": {"ttf": 0, "tokens": len(reply.split()), "tok_per_s": 0},
            "model": os.getenv("MODEL_NAME", "undefined")
        })

        # 🔁 Rehidratar memoria RAM
        try:
            history = rag.logger.load()
            for m in history:
                if m["role"] == "user":
                    rag.memory.chat_memory.add_user_message(m["content"])
                else:
                    rag.memory.chat_memory.add_ai_message(m["content"])
            print(f"🔁 Memoria inicial rehidratada ({len(history)} msgs)")
        except Exception as e:
            print(f"[⚠️] No se pudo rehidratar memoria inicial: {e}")

        rag.finalize()
        return jsonify({
            "reply": reply,
            "project": slug,
            "project_display": title,
            "phase": "main",
            "metrics": {"ttf": 0, "tokens": len(reply.split()), "tok_per_s": 0},
            "model": os.getenv("MODEL_NAME", "undefined")
        })

    # === PROYECTO EXISTENTE ===
    key = (project, phase)
    rag = sessions.get(key)
    if not rag:
        project_dir = PROJECTS_DIR / project
        rag = R4RConversationalRAG(project_dir, phase)
        rag.initialize()
        sessions[key] = rag

    start = time.perf_counter()
    response = rag.query(msg)
    ttf = round(time.perf_counter() - start, 2)
    tokens = len(response.split())
    tok_per_s = round(tokens / max(ttf, 0.001), 2)
    metrics = {"ttf": ttf, "tokens": tokens, "tok_per_s": tok_per_s}
    model_name = os.getenv("MODEL_NAME", "undefined")

    # 🔹 Guardar con métricas y modelo persistente
    rag.logger.save("assistant", response, {"metrics": metrics, "model": model_name})
    try:
        rag.finalize()
        print(f"💾 Contexto sincronizado para {project}/{phase}")
    except Exception as e:
        print(f"[⚠️] Error persistiendo conversación: {e}")

    # Leer título legible
    title_display = project
    context_file = PROJECTS_DIR / project / "main" / "context.md"
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("title:"):
                    title_display = line.split(":", 1)[1].strip().strip('"')
                    break

    return jsonify({
        "reply": response,
        "project": project,
        "phase": phase,
        "project_display": title_display,
        "metrics": metrics,
        "model": model_name
    })

# ---------- PATCH / DELETE ----------
@app.route("/api/project/<path:slug>", methods=["PATCH", "DELETE"])
def project_manage(slug):
    project_dir = PROJECTS_DIR / slug
    if not project_dir.exists():
        return jsonify({"error": "not found"}), 404

    if request.method == "DELETE":
        shutil.rmtree(project_dir)
        return jsonify({"deleted": True})

    if request.method == "PATCH":
        data = request.get_json()
        new_title = data.get("new_title", "").strip()
        if not new_title:
            return jsonify({"error": "empty"}), 400
        meta = project_dir / "main/context.md"
        if meta.exists():
            lines = open(meta, encoding="utf-8").read().splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("title:"):
                    lines[i] = f'title: "{new_title}"'
                    break
            with open(meta, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        return jsonify({"renamed": True, "title": new_title})

# ---------- SOCKET.IO ----------
@socketio.on("disconnect")
def on_disconnect():
    sid = getattr(request, "sid", "unknown")
    to_remove = [
        key for key, rag in sessions.items()
        if getattr(rag, "sid", None) == sid
    ]
    for key in to_remove:
        sessions[key].finalize()
        del sessions[key]
    print(f"🔒 Sesión {sid} guardada y eliminada.")

# ----------------------------------------------------------
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5000))
    socketio.run(app, host=host, port=port, debug=True)
