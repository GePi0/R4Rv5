// r4r_ui/static/js/ui/header.js
// --------------------------------------------------
// Header UI (título + botón Guardar)
// Incluye feedback toast visual y sincronización con sidebar
// --------------------------------------------------

import { apiClient } from "../core/apiClient.js";
import { stateManager } from "../core/stateManager.js";
import { showToast } from "../ui/feedback.js";

/**
 * Inicializa el header principal de la interfaz.
 * Contiene el título de la sesión y el botón Guardar.
 */
export function initHeader() {
  const header = document.getElementById("header");
  header.innerHTML = ""; // limpiar

  // --- Texto del título dinámico ---
  const titleSpan = document.createElement("span");
  titleSpan.id = "sessionTitle";
  titleSpan.innerText = "Nuevo proyecto — pendiente";

  // --- Botón de guardado ---
  const saveBtn = document.createElement("button");
  saveBtn.innerText = "Guardar";
  saveBtn.disabled = true;

  // --- Insertar en DOM ---
  header.append(titleSpan, saveBtn);

  // --- Acción botón Guardar ---
  saveBtn.onclick = async () => {
    const { project, phase, title } = stateManager.current;
    if (!project || !phase) {
      showToast("Ningún proyecto activo para guardar", "error");
      return;
    }

    saveBtn.disabled = true;
    titleSpan.innerText = `${title} / ${phase} — guardando...`;

    try {
      const res = await apiClient.saveContext(project, phase);

      // Guardado exitoso
      if (res?.saved) {
        titleSpan.innerText = `${title} / ${phase} — guardado ✅`;
        showToast(`Contexto guardado correctamente`, "success");

        // Si hay nueva fase creada
        if (res.next_phase) {
          await import("./sidebar.js").then(async ({ initSidebar }) => {
            await initSidebar(title);
          });
          showToast(`Nueva fase creada: ${res.next_phase}`, "success");
        }

        saveBtn.disabled = true;
      }
      // Error leve reportado por backend
      else {
        titleSpan.innerText = "⚠️ Error al guardar";
        saveBtn.disabled = false;
        showToast("Error durante el guardado", "error");
      }
    } catch (err) {
      console.error("❌ Error al guardar contexto:", err);
      titleSpan.innerText = "❌ Fallo de conexión al guardar";
      saveBtn.disabled = false;
      showToast("Fallo de conexión al guardar", "error");
    } finally {
      // Restaurar estado visual tras unos segundos
      setTimeout(() => {
        const stateText = stateManager.pending
          ? "pendiente de guardar"
          : "guardado";
        titleSpan.innerText = `${stateManager.current.title} / ${stateManager.current.phase} — ${stateText}`;
      }, 2500);
    }
  };

  return { header, titleSpan, saveBtn };
}
