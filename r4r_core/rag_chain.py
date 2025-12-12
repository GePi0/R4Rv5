# r4r_core/rag_chain.py
# -------------------------------------------------------------
# Conversational RAG pipeline con memoria RAM (contextMemory)
# combinada con memoria persistente (.pkl) y búsqueda semántica
# -------------------------------------------------------------

from pathlib import Path
from r4r_core.vector_store import R4RVectorStore
from r4r_core.conversation_persistence import SessionLogger
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import os

class R4RConversationalRAG:
    """
    Pipeline conversacional RAG con tres capas de memoria:
      1. contextMemory (RAM / LangChain)
      2. contextmemory_faseX.pkl  (persistente)
      3. context.md (vector search)
    """

    def __init__(self, project_dir: Path, phase: str):
        load_dotenv()
        self.project_dir = project_dir
        self.phase = phase

        # Modelo LLM desde .env
        self.llm = ChatOllama(
            model=os.getenv("MODEL_NAME", "mistral:7b"),
            temperature=0.3,
            base_url=os.getenv("OLLAMA_API_HOST", "http://localhost:11434"),
        )

        # Core components
        self.memory = ConversationBufferMemory(return_messages=True)
        self.vector_store = R4RVectorStore()
        self.logger = SessionLogger(project_dir, phase)

    # ────────────────────────────────────────────
    #   INIT / HYDRATION
    # ────────────────────────────────────────────
    def initialize(self):
        """Indexa contextos (main + fases) en memoria
        y reconstruye el buffer RAM desde el .pkl existente.
        """
        print(f"🧩 Indexando contextos de {self.project_dir.name} ...")
        self.vector_store.index_contexts(self.project_dir)

        # Rehidratar .pkl → contextMemory (RAM)
        previous_msgs = self.logger.load()
        if previous_msgs:
            for m in previous_msgs:
                role = m["role"].lower()
                content = m["content"]
                if role == "user":
                    self.memory.chat_memory.add_user_message(content)
                else:
                    self.memory.chat_memory.add_ai_message(content)
            print(f"🔁 Rehidratada memoria con {len(previous_msgs)} mensajes previos.\n")
        else:
            print("🆕 Nueva sesión — memoria vacía.\n")

    # ────────────────────────────────────────────
    #   MAIN QUERY PIPELINE
    # ────────────────────────────────────────────
    def query(self, user_input: str, k: int = 3) -> str:
        # Registrar mensaje
        self.logger.save("user", user_input)
        self.memory.chat_memory.add_user_message(user_input)

        # Paso 1: búsqueda semántica top‑k en context.md
        relevant_docs = self.vector_store.query(user_input, k=k)
        snippets = "\n\n".join(
            [doc.page_content[:800] for doc in relevant_docs]
        )

        # Paso 2: preparar prompt base
        template = PromptTemplate(
            input_variables=["context", "conversation", "question"],
            template=(
                "Eres un asistente dentro del proyecto R4R. "
                "Responde basándote en el contexto del proyecto y la conversación actual.\n\n"
                "Contexto relevante:\n{context}\n\n"
                "Conversación previa:\n{conversation}\n\n"
                "Pregunta: {question}\n\n"
                "Responde de manera clara y en español:"
            ),
        )

        # Dump temporal del buffer como string
        conversation_text = "\n".join(
            f"{m.type}: {m.content}" for m in self.memory.chat_memory.messages[-8:]
        )

        chain = RunnablePassthrough() | template | self.llm | StrOutputParser()

        response = chain.invoke(
            {
                "context": snippets,
                "conversation": conversation_text,
                "question": user_input,
            }
        )

        # Guardar mensaje en buffer y persistente con metadatos
        self.memory.chat_memory.add_ai_message(response)
        try:
            from os import getenv
            self.logger.save(
                "assistant",
                response,
                {
                    "metrics": {
                        "length": len(response.split())
                    },
                    "model": getenv("MODEL_NAME", "undefined"),
                }
            )
        except Exception as e:
            print(f"[⚠️] Error guardando metadatos: {e}")

        return response

    # ────────────────────────────────────────────
    #   FINALIZACIÓN / GUARDADO
    # ────────────────────────────────────────────
    def finalize(self):
        """Resincroniza buffer RAM → .pkl manteniendo los metadatos previos."""
        from pathlib import Path
        import pickle
    
        # 1️⃣ Cargar versión actual (si existe)
        existing = []
        if self.logger.memory_path.exists():
            try:
                with open(self.logger.memory_path, "rb") as f:
                    existing = pickle.load(f)
            except Exception:
                existing = []
    
        # 2️⃣ Reconstruir mensajes del buffer actual
        updated = []
        for m in self.memory.chat_memory.messages:
            role = "user" if m.type == "human" else "assistant"
            content = m.content
            updated.append({"role": role, "content": content})
    
        # 3️⃣ Si los existentes tenían meta (metrics, model),
        #     los transferimos al matching assistant original.
        merged = []
        for idx, msg in enumerate(updated):
            if msg["role"] == "assistant":
                # Recuperar meta del existente si coincide por orden
                meta = None
                if idx < len(existing) and isinstance(existing[idx], dict):
                    meta = existing[idx].get("meta")
                if meta:
                    msg["meta"] = meta
            merged.append(msg)
    
        # 4️⃣ Guardar sin perder meta
        tmp_path = self.logger.memory_path.with_suffix(".pkl.tmp")
        with open(tmp_path, "wb") as f:
            pickle.dump(merged, f)
        tmp_path.replace(self.logger.memory_path)
    
        print(f"💾 Memoria sincronizada preservando metadatos → {self.logger.memory_path}")
