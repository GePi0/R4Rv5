// r4r_ui/static/js/core/stateManager.js
// ---------------------------------------------------------
// R4R v5 — State Manager (sin watcher)
// Gestión del proyecto/fase actual con refresco manual
// ---------------------------------------------------------

import { apiClient } from "./apiClient.js";
import { chatRenderer } from "./chatRenderer.js";

export const stateManager = {
  // Estado global de la UI
  current: { project: null, phase: null, title: null },

  // Marca temporal del último guardado o carga
  lastMemoryTime: 0,

  /**
   * Actualiza el contexto actual (proyecto/fase/título visible)
   * Usado al crear un proyecto nuevo o al cambiar de fase en la sidebar.
   */
  set(project, phase, title) {
    this.current = { project, phase, title };
    console.log("📦 Contexto activo cambiado →", this.current);
  },

  /**
   * Refresca el historial de la conversación desde backend
   * (solo se invoca desde sidebar o tras guardar).
   * No re-renderiza automáticamente durante conversaciones.
   */
  async refreshHistory(project, phase) {
    if (!project || !phase) return;

    try {
      console.log(`♻️ Cargando historial para ${project} / ${phase}`);
      const data = await apiClient.getHistory(project, phase);

      // Actualizamos memoria temporal interna
      this.lastMemoryTime = data.memory_time || Date.now();

      // Renderizamos mensajes previos en el chatbox
      if (Array.isArray(data.history)) {
        chatRenderer.renderAll(data.history);
        chatRenderer.scrollToBottom(false);
        console.log("✅ Historial renderizado manualmente.");
      } else {
        console.warn("⚠️ No hay historial disponible en backend.");
      }

      // Devuelve los datos por si otros módulos los necesitan
      return data;
    } catch (err) {
      console.error("❌ Error al refrescar historial:", err);
    }
  },
};
