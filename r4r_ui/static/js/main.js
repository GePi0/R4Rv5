// r4r_ui/static/js/main.js
// --------------------------------------------------
// R4R v5 — Flujo principal con Ollama + HUD estable
// Sin watcher, persistencia backend-only
// --------------------------------------------------

import { chatRenderer } from "./core/chatRenderer.js";
import { stateManager } from "./core/stateManager.js";
import { apiClient } from "./core/apiClient.js";
import { initSidebar, setActive } from "./ui/sidebar.js";
import { initHeader } from "./ui/header.js";
import { showToast } from "./ui/feedback.js";

window.addEventListener("DOMContentLoaded", async () => {
  console.log("🌐 UI cargando...");

  // Inicialización básica
  initHeader();
  await initSidebar();

  const chatInput = document.createElement("textarea");
  const sendBtn = document.createElement("button");
  sendBtn.textContent = "↵";
  const inputArea = document.getElementById("inputArea");
  inputArea.append(chatInput, sendBtn);
  
  // --- Teclado: Enter = enviar / Shift+Enter = salto ---
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // --- Auto‑resize del textarea ---
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 220) + "px";
  });

  // --- Envío de mensaje ---
  sendBtn.addEventListener("click", async () => {
    const text = chatInput.value.trim();
    if (!text) return;

    // Si no hay proyecto activo, se creará nuevo automáticamente
    const project = stateManager.current.project;
    const phase = stateManager.current.phase;

    // agrega el mensaje del usuario al chat
    chatRenderer.append("user", text);
    chatInput.value = "";

    // loader inline del asistente
    const loader = chatRenderer.append("assistant", "", true);

    try {
      console.log("🚀 Enviando prompt al modelo...");
      const res = await apiClient.sendMessage(text, project, phase);

      if (!res || !res.reply) {
        throw new Error("Respuesta vacía del modelo.");
      }

      // elimina loader temporal
      if (loader) loader.remove();

      // crea un único bloque para la respuesta
      const botDiv = document.createElement("div");
      botDiv.className = "bot fade";
      chatRenderer.chatbox.appendChild(botDiv);
      setTimeout(() => botDiv.classList.add("show"), 20);

      // almacena métricas recibidas para el HUD
      window.lastMetrics = res.metrics || {};

      // almacena nombre real del modelo para mostrar en el HUD
      window.lastModel = res.model || "Modelo";

      // animar tipeo del contenido
      await chatRenderer.typeResponseIn(botDiv, res.reply, 12);

      // actualizar estado global / sidebar / HUD
      const friendlyTitle = res.project_display || res.project;
      stateManager.set(res.project, res.phase, friendlyTitle);
      await initSidebar(stateManager.current.title);
      setActive(res.project, res.phase);

      const titleSpan = document.getElementById("sessionTitle");
      if (titleSpan)
        titleSpan.innerText = `${friendlyTitle} / ${res.phase}`;

      // ✅ Guardado backend automático, sin rehidratar UI
      showToast("Mensaje enviado correctamente", "success");

      // re-habilitar el botón Guardar (ya que hay nuevo contenido)
      const saveBtn = document.querySelector("#header button");
      if (saveBtn) saveBtn.disabled = false;
    } catch (err) {
      console.error("❌ Error al enviar mensaje:", err);
      showToast("Error al enviar mensaje", "error");
      if (loader) loader.remove();
    }
  });
});
