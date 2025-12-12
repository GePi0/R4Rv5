# r4r_core/summarizer_chain.py
# -----------------------------------------------------------
# Genera un resumen semántico usando el modelo elegido (.env)
# -----------------------------------------------------------

import os
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


def get_llm():
    """Selecciona proveedor y modelo según .env"""
    load_dotenv()
    provider = os.getenv("MODEL_PROVIDER", "ollama_local").lower()
    model_name = os.getenv("MODEL_NAME", "mistral:7b")

    if "ollama" in provider:
        # Ollama local o cloud: usa el endpoint local por defecto
        base_url = os.getenv("OLLAMA_API_HOST", "http://localhost:11434")
        return ChatOllama(model=model_name, base_url=base_url, temperature=0.3)
    elif "openai" in provider:
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model_name=model_name, api_key=api_key, temperature=0.3)
    else:
        raise ValueError(f"Proveedor no soportado: {provider}")


def summarize_conversation(messages: list[dict]) -> str:
    """Crea un resumen semántico real vía LLM."""
    llm = get_llm()

    # Unimos mensajes de usuario en un solo texto
    conversation_text = "\n\n".join(
        [f"{m['role']}: {m['content']}" for m in messages]
    )

    prompt = PromptTemplate(
        input_variables=["conversation"],
        template=(
            "Analiza la siguiente conversación y genera un resumen conciso:\n\n"
            "{conversation}\n\n"
            "Resumen breve (máx. 5 líneas) y en español:"
        ),
    )

    chain = RunnablePassthrough() | prompt | llm | StrOutputParser()
    return chain.invoke({"conversation": conversation_text})
