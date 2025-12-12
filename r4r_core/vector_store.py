# r4r_core/vector_store.py
# -------------------------------------------------------------
# Vector store en memoria (RAM) con Chroma y OllamaEmbeddings.
# Sin persist_dir -> evita errores de escritura en SQLite.
# Los contextos se indexan al vuelo cuando se abre fase/proyecto.
# -------------------------------------------------------------

from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

class R4RVectorStore:
    def __init__(self):
        # modelo de embeddings
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        # colección en memoria
        self.vectorstore = Chroma(
            collection_name="r4r_temp",
            embedding_function=self.embeddings
        )

    def index_contexts(self, project_dir: Path):
        """Leer todos los context.md del proyecto y generar embeddings en RAM."""
        contexts = []
        for md in project_dir.rglob("context.md"):
            phase_name = md.parent.name
            with open(md, "r", encoding="utf-8") as f:
                contexts.append(Document(page_content=f.read(), metadata={"phase": phase_name}))
        if not contexts:
            print("⚠️ No se encontraron context.md para indexar.")
            return
        self.vectorstore.add_documents(contexts)
        print(f"✅ Indexados {len(contexts)} contextos en memoria.")

    def query(self, question: str, k: int = 3):
        """Búsqueda semántica en el vectorstore temporal."""
        return self.vectorstore.similarity_search(question, k=k)
