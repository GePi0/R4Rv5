R4Rv5 — Conversational Builder (Flask + Ollama + LangChain)

R4Rv5 es un **entorno de chat persistente** que combina una interfaz modular
en JavaScript con un backend en Flask y un modelo local servido por Ollama
o cualquier LLM compatible a través de LangChain.

Permite crear y gestionar proyectos de conversación,
cada uno con múltiples fases (`main`, `fase 1`, `fase 2`, …),
guardando automáticamente todos los mensajes, metadatos y contextos.


Características principales

- **Frontend simple y modular**:  
  HTML + JavaScript sin frameworks, con módulos organizados (`core` / `ui`).

- **Backend Flask**:  
  API REST limpia (`/api/message`, `/api/projects`, `/api/save_context`, `/api/history`).

- **Persistencia automática**:  
  Cada conversación se guarda en `projects/<nombre>/fase/contextmemory_*.pkl`
  con backups rotativos (`/backups/*.bak`).

- **Contextos exportables**:  
  Cada fase puede generar su propio `context.md` con metadatos YAML y resumen.

- **HUD de métricas real**:  
  Muestra tokens, tiempo‑to‑first, velocidad (tok/s) y modelo utilizado,
  incluso tras reiniciar o cambiar de proyecto.

- **Diseño inspirado en ChatGPT**:  
  Loader de puntos `···`, rehidratación, sidebar y UI limpia.


Estructura de carpetas

R4Rv5/

├── r4r_core/

│   ├── context_builder.py          ← Genera context.md

│   ├── context_loader.py           ← Carga jerárquica de contextos

│   ├── conversation_persistence.py ← Persistencia con backups

│   ├── rag_chain.py                ← Lógica LangChain + Ollama

│   ├── summarizer_chain.py         ← Resumen semántico automático

│   └── vector_store.py             ← Embeddings y búsqueda semántica

│

├── r4r_ui/

│   ├── app.py                      ← Backend Flask principal

│   ├── templates/index.html        ← UI base

│   └── static/

│        ├── style.css              ← Estilos finales R4R v5

│        └── js/

│             ├── core/             ← Módulos de render, API y estado

│             └── ui/               ← Componentes de UX (sidebar, header, feedback)

│

├── projects/                       ← Repositorio de proyectos generados

├── requirements.txt

└── .env                            ← Configuración global


Instalación

1. Clonar y entrar al proyecto
   ```bash
   git clone https://github.com/<tu_usuario>/R4Rv5.git
   cd R4Rv5


2. Crear entorno virtual
	python -m venv .venv
	source .venv/bin/activate


3. Instalar dependencias
	pip install -r requirements.txt

 
4. Configurar .env
(El proyecto lee todo desde aquí — sin necesidad de tocar código)

	# .env
	MODEL_PROVIDER=ollama_local
	MODEL_NAME=mistral:7b-instruct-q4_K_M
	OLLAMA_API_HOST=http://localhost:11434
	PROJECTS_DIR=projects
	DEFAULT_LANG=es
	FLASK_PORT=5000


6. Ejecutar el servidor
	python -m r4r_ui.app

 
7. Abre tu navegador en
http://127.0.0.1:5000   


Uso básico
1. Escribe un prompt inicial → se crea automáticamente un nuevo proyecto con su carpeta, título y contexto.

2. Envía mensajes y observa el HUD con métricas en tiempo real.

3. Usa el botón Guardar para generar un nuevo contexto y pasar a la siguiente fase.

4. Cambia de proyecto o fase directamente desde el sidebar sin reiniciar el servidor.


Configuración adicional
- Modelos compatibles:
	- Ollama (local o remoto)

	- OpenAI / Anthropic (configurar las API keys en .env)


- Backups:

Cada guardado crea un .bak en backups/ dentro del proyecto.

- HUD:

Persiste en .pkl con "meta": {"metrics": {...}, "model": "..." }.


Arquitectura resumida
	Frontend JS → Flask API → LangChain → Ollama Serve → LLM
	        ↑                     ↓
	   Persistencia (.pkl)   Contexto (.md)


Endpoints Flask principales
Método		Ruta	        	Descripción
POST		/api/message		Envía un mensaje al modelo activo
GET	    	/api/projects		Lista proyectos y fases existentes
POST		/api/history		Recupera conversación previa
POST		/api/save_context	Genera context.md y crea nueva fase
PATCH/DELETE/api/project/<slug>	Renombra o elimina proyecto


Estructura de un proyecto generado
projects/
└── Multiplicación_234x5_r4r_20251117T...
    ├── main/
    │    ├── context.md
    │    ├── contextmemory_main.pkl
    │    └── backups/
    │         └── contextmemory_main_20251117_....
    └── fase 1/
         └── contextmemory_fase 1.pkl


Recomendaciones

- No edites los .pkl manualmente.

- Realiza las pruebas en entorno virtual Python ≥ 3.11.

- Si usas Ollama, asegúrate de que el modelo (MODEL_NAME) está cargado localmente.


Estado actual (2025‑11)
Área			Estado
Persistencia	✅ Estable
Interfaz UI		✅ Finalizada (v5.0)
HUD y métricas	✅ Persistentes
Sidebar y fases	✅ Completo
Estilo R4R		✅ Minimalista y funcional


Autores
Gerard Piella Olmedo — Arquitectura + Integración + UI/UX
Ayudado por GPT‑5 (modo colaborativo)


----------------------------------------------------------------------


Licencia

MIT License © 2025

Puedes usar, modificar y redistribuir este código libremente,

siempre que cites la fuente y mantengas la referencia a este proyecto.


----------------------------------------------------------------------


Créditos
Inspirado por LangChain, Ollama y la arquitectura de chat persistente Flask‑JS.
Diseñado desde cero para transparencia total, sin dependencias web complejas.
