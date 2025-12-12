	# 🧩 R4Rv5 — Technical Overview
	**Conversational Builder + Persistent RAG System**
	
	---
	
	## 📘 Índice
	1. [Arquitectura general](#-arquitectura-general)
	2. [Backend: Flask + LangChain](#-backend-flask--langchain)
	3. [Frontend: estructura JS modular](#-frontend-estructura-js-modular)
	4. [Pipeline interno de chat](#-pipeline-interno-de-chat)
	5. [Persistencia y backups](#-persistencia-y-backups)
	6. [Contextos & generación de `context.md`](#-contextos--generación-de-contextmd)
	7. [HUD y metadatos de métrica](#-hud-y-metadatos-de-métrica)
	8. [Extensión del modelo (OpenAI, HuggingFace, etc.)](#-extensión-del-modelo)
	9. [Control de versiones y buenas prácticas](#-control-de-versiones--buenas-prácticas)
	
	---
	
	## 🧠 Arquitectura general
	
	R4Rv5 implementa un sistema de **RAG (Retrieval‑Augmented Generation)** con persistencia local:
	
	```text
	Frontend JS → Flask API → LangChain/Ollama → Modelo LLM
	        ↑                     ↓
	   Pickle + Context.md   Generación de respuesta + métricas
	```

-----------------------------------------------------
	
Cada proyecto genera su propio ecosistema de contexto:

projects/<slug>/

├── main/contextmemory_main.pkl

├── main/backups/contextmemory_main_YYYYMMDD_HHMMSS.bak

└── fase N/contextmemory_fase N.pkl

-----------------------------------------------------
	
	## ⚙️ Backend Flask + LangChain
	
	Archivo: **`r4r_ui/app.py`**
	
	### Funciones principales
	| Endpoint | Descripción |
	|-----------|--------------|
	| `POST /api/message` | Canaliza prompts hacia el modelo activo |
	| `GET /api/projects` | Enumera proyectos y fases |
	| `POST /api/save_context` | Crea `context.md` y la siguiente fase |
	| `POST /api/history` | Devuelve historial persistente de mensajes |
	| `PATCH/DELETE /api/project/<slug>` | Renombra o elimina proyectos |
	
	### Core components
	- **`R4RConversationalRAG`** (en `rag_chain.py`):  
	  - Contiene el `ChatOllama` de LangChain.  
	  - Gestiona la memoria RAM (`ConversationBufferMemory`).  
	  - Indexa contextos mediante `R4RVectorStore`.  
	  - Garantiza persistencia por sesión (`.pkl`).
	
	- **`SessionLogger` (conversation_persistence.py)**  
	  - Escribe/lee los `.pkl`.  
	  - Crea backups automáticos en cada mensaje.  
	  - Controla corrupción o recupera `.bak` automáticamente.
	
	---
	
	## 💻 Frontend: estructura JS modular

---------------------------------------------------

r4r_ui/static/js/

├── core/

│    ├── apiClient.js       ← comunicación REST

│    ├── chatRenderer.js    ← render + loader + HUD

│    ├── stateManager.js    ← proyecto/fase actual

│    └── markdown.js        ← renderer Markdown + HLJS

└── ui/

├── sidebar.js         ← navegación de proyectos/fases

├── header.js          ← header + guardado

└── feedback.js        ← sistema de toasts

----------------------------------------------------

	### Comunicación
	Todo el frontend usa `fetch` a `/api/*`  
	y responses en formato JSON:
	```json
	{
	  "reply": "...",
	  "project": "slug_proyecto",
	  "phase": "main",
	  "metrics": {"ttf": 1.23, "tokens": 312, "tok_per_s": 205.4},
	  "model": "mistral:7b-instruct-q4_K_M"
	}


---

🔄 Pipeline interno de chat

Flujo resumido

	prompt usuario
	   ↓
	apiClient.sendMessage()
	   ↓
	@app.route("/api/message")
	   ↓
	R4RConversationalRAG.query()
	   ↓
	LangChain → ChatOllama.generate()
	   ↓
	respuesta JSON + métricas
	   ↓
	chatRenderer.typeResponseIn()
	   ↓
	HUD + persistencia en .pkl


---

💾 Persistencia y backups


Archivo: r4r_core/conversation_persistence.py


- Guardado atómico: se escribe primero .pkl.tmp, luego se reemplaza.

- Backup rotativo:

cada guardado genera backups/contextmemory_main_YYYYMMDD_HHMMSS.bak.

- Recuperación segura:

si .pkl está vacío o corrupto → se rehidrata desde el último .bak.

Formato del .pkl:


	[
	  {"role": "user", "content": "¿Cuánto es 2+2?"},
	  {
	    "role": "assistant",
	    "content": "La suma de 2 y 2 es 4.",
	    "meta": {
	      "metrics": {"ttf": 0.8, "tokens": 8, "tok_per_s": 120.5},
	      "model": "mistral:7b-instruct-q4_K_M"
	    }
	  }
	]


---

🌐 Contextos & generación de context.md


Archivo: context_builder.py

Procesa la conversación de cada fase para crear un

archivo context.md con:


- encabezado YAML (title, tags, created, summary)

- cuerpo concatenado de conversación

- detección automática de palabras clave

- resumen semántico (summarizer_chain.py)

Ejemplo:


	---
	title: "Multiplicación Básica"
	tags: [main]
	created: 2025-11-17 11:30
	summary: "El usuario solicita operaciones aritméticas simples."
	---
	USER: ¿Cuánto es 3×4?
	ASSISTANT: El resultado es 12.


---

⚡ HUD y metadatos de métrica


HUD = “Heads‑Up Display” mostrado bajo cada respuesta.

Incluye:


- modelo (meta.model)

- tokens

- velocidad (tok/s)

- time‑to‑first (TTF)

Es reconstruido automáticamente desde m.meta.metrics en chatRenderer.renderAll()

tras un F5 o cambio de proyecto.


---

🧩 Extensión del modelo


Para cambiar de modelo no se modifica código, solo el .env:


	MODEL_PROVIDER=ollama_local
	MODEL_NAME=mistral:7b-instruct-q4_K_M

Otros proveedores

- OpenAI

	MODEL_PROVIDER=openai
	MODEL_NAME=gpt-4o
	OPENAI_API_KEY=<tu_key>



- Anthropic

	MODEL_PROVIDER=anthropic
	MODEL_NAME=claude-3-opus
	ANTHROPIC_API_KEY=<tu_key>



La clase get_llm() de summarizer_chain.py detecta automáticamente el proveedor.


---

🧱 Control de versiones & buenas prácticas

- Usa Python 3.11+ y LangChain ≥ 0.2.x.

- No edites los .pkl manualmente.

- Cada PR debe pasar por los checks de persistencia .pkl y context.md.

- Mantén el .env fuera de commits (.gitignore).


---

🧑💻 Autoría


Gerard Piella Olmedo — Arquitectura, desarrollo, UI/UX

Asistencia técnica y refactorización colaborativa mediante GPT‑5.


---

⚖️ Licencia


MIT License © 2025

Puedes reutilizar, modificar y redistribuir libremente,

manteniendo referencia a la autoría original.
