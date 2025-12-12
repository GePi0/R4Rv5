// r4r_ui/static/js/core/chatRenderer.js
// --------------------------------------------------
// Render Chat + Scroll inteligente + Tipeo inline real
// R4R v5 — versión estable con loader fijo y HUD dinámico
// --------------------------------------------------

import { renderMarkdown } from "./markdown.js";

class ChatRenderer {
  constructor() {
    this.chatbox = document.getElementById("chatbox");

    this.loader = document.createElement("div");
    this.loader.id = "chatLoader";
    this.loader.style.display = "none";
    this.chatbox.style.position = "relative";
    this.chatbox.appendChild(this.loader);
  }

  // --- Scroll ---
  isAtBottom() {
    const { scrollTop, scrollHeight, clientHeight } = this.chatbox;
    return scrollHeight - clientHeight - scrollTop < 20;
  }

  scrollToBottom(smooth = true) {
    const behavior = smooth ? "smooth" : "auto";
    this.chatbox.scrollTo({ top: this.chatbox.scrollHeight, behavior });
  }

  // --- Loader estado general ---
  showLoader() {
    this.loader.style.display = "block";
  }

  hideLoader() {
    this.loader.style.display = "none";
  }

  // --- Limpieza de chat completo ---
  clear() {
    this.chatbox.innerHTML = "";
    this.chatbox.appendChild(this.loader);
  }

  // --- Render completo de mensajes históricos ---
  renderAll(messages) {
      this.clear();
      if (!messages || messages.length === 0) return;
  
      messages.forEach((m) => {
        const div = document.createElement("div");
        div.className = m.role;
  
        if (m.role === "assistant" || m.role === "bot") {
          div.classList.add("bot");
          div.innerHTML = renderMarkdown(m.content);
          this.chatbox.appendChild(div);
  
          // 🔹 reconstruir HUD si hay meta guardada
          if (m.meta && m.meta.metrics) {
            const hub = document.createElement("div");
            hub.className = "response-meta";
            const meta = m.meta.metrics;
            const model = (m.meta.model || "Modelo").toString();
            const tok_s = meta.tok_per_s ? `${meta.tok_per_s.toFixed(2)} tok/s` : "—";
            const toks = meta.tokens ?? "—";
            const ttff = meta.ttf ? `${meta.ttf.toFixed(2)}s` : "—";
            hub.innerHTML = `
              <span>⚡ ${model}</span>
              <span>🕓 ${tok_s}</span>
              <span>🔢 ${toks} tokens</span>
              <span>⏳ TTF ${ttff}</span>`;
            div.insertAdjacentElement("afterend", hub);
          }
        } else {
          div.classList.add("user");
          div.innerText = m.content;
          this.chatbox.appendChild(div);
        }
      });
  
      this.scrollToBottom(false);
    }

  // --- Añadir mensajes dinámicos ---
  append(role, content, isLoader = false) {
    // Loader fijo al estilo ChatGPT
    if (isLoader) {
      // --- Preparar contenedor fijo para loader y futura respuesta ---
      let replyContainer = this.chatbox.querySelector("#current-reply");
      if (!replyContainer) {
        replyContainer = document.createElement("div");
        replyContainer.id = "current-reply";
        replyContainer.className = "reply-placeholder";
        this.chatbox.appendChild(replyContainer);
      } else {
        replyContainer.innerHTML = ""; // limpia si ya existe
      }

      const loaderEl = document.createElement("div");
      loaderEl.className = "inline-loader";
      loaderEl.innerHTML = `
        <span class="typing-loader">
          <span></span><span></span><span></span>
        </span>`;
      replyContainer.appendChild(loaderEl);
      this.scrollToBottom();
      return loaderEl;
    }

    // --- Mensajes normales ---
    const div = document.createElement("div");
    div.className = role + " fade";

    if (role === "assistant" || role === "bot") {
      div.classList.add("bot");
      div.innerHTML = renderMarkdown(content);
    } else {
      div.classList.add("user");
      div.innerText = content;
    }

    this.chatbox.appendChild(div);
    setTimeout(() => div.classList.add("show"), 20);
    this.scrollToBottom();
    return div;
  }

  // --- Escribir tipo "máquina de escribir" + HUD fijo ---
  async typeResponseIn(div, text, delay = 12) {
    if (!div) return;
    div.innerHTML = "";
    const shouldStick = this.isAtBottom();
    let output = "";

    for (let i = 0; i < text.length; i++) {
      output += text[i];
      div.innerHTML = renderMarkdown(output);
      if (shouldStick) this.scrollToBottom(false);
      await new Promise((r) => setTimeout(r, delay));
    }

    div.innerHTML = renderMarkdown(text);
    if (shouldStick) this.scrollToBottom();

    // eliminar placeholder del loader fijo si existe
    const replyContainer = this.chatbox.querySelector("#current-reply");
    if (replyContainer) replyContainer.remove();

    // HUD fijo (modelo dinámico y métricas reales)
    const hub = document.createElement("div");
    hub.className = "response-meta";

    const m = window.lastMetrics || {};
    const modelName = window.lastModel || "Modelo";
    const tok_s = m.tok_per_s
      ? `${m.tok_per_s.toFixed(2)} tok/s`
      : "0 tok/s";
    const toks = m.tokens || 0;
    const ttff = m.ttf ? `${m.ttf.toFixed(2)}s` : "0s";

    hub.innerHTML = `
      <span>⚡ ${modelName}</span>
      <span>🕓 ${tok_s}</span>
      <span>🔢 ${toks} tokens</span>
      <span>⏳ TTF ${ttff}</span>`;

    div.insertAdjacentElement("afterend", hub);
  }
}

export const chatRenderer = new ChatRenderer();
