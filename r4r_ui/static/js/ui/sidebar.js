// r4r_ui/static/js/ui/sidebar.js
// --------------------------------------------------
// Sidebar UI — proyectos y fases (R4R v5 actualizado)
// Integración botón "Nuevo Proyecto" ✎ + UX óptimo
// --------------------------------------------------

import { apiClient } from "../core/apiClient.js";
import { chatRenderer } from "../core/chatRenderer.js";
import { stateManager } from "../core/stateManager.js";
import { showToast } from "../ui/feedback.js";

// ==== FUNCIÓN PRINCIPAL ====

export async function initSidebar(expandTitle = null) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  // 🔹 Header de la barra lateral con botón "Nuevo Proyecto"
  sidebar.innerHTML = `
    <div class="sidebarHeader">
      <div class="sidebarTitle">R4R</div>
      <div class="projectHeader">
        <span>Proyectos</span>
        <span id="newProjectBtn" title="Nuevo proyecto">✎</span>
      </div>
    </div>
  `;
  
  const list = document.createElement("div");
  list.className = "projectList";
  sidebar.appendChild(list);

  // 🟦 Acción del botón "Nuevo proyecto"
  const newBtn = document.getElementById("newProjectBtn");
  newBtn.addEventListener("click", () => {
    console.log("🆕 Nuevo proyecto iniciado");
    const chatbox = document.getElementById("chatbox");
    chatbox.innerHTML = "";
    const titleSpan = document.getElementById("sessionTitle");
    if (titleSpan)
      titleSpan.innerText = "Nuevo proyecto — pendiente";
    stateManager.set(null, null, "Nuevo proyecto");
    showToast("Crea un nuevo proyecto escribiendo tu primer prompt", "success");
  });

  // ==== Cargar proyectos existentes ====
  let projects = [];
  try {
    const res = await fetch("/api/projects");
    projects = await res.json();
  } catch (err) {
    sidebar.innerHTML += `<div>Error al cargar proyectos</div>`;
    return;
  }

  if (!Array.isArray(projects) || projects.length === 0) {
    list.innerHTML = `<div style='color:#888;padding:8px'>Sin proyectos</div>`;
    return;
  }

  // Render principal
  projects.forEach((p) => {
    const det = document.createElement("details");
    det.dataset.slug = p.project;
    if (expandTitle && expandTitle === p.title) det.open = true;

    // ----- Cabecera del proyecto -----
    const sum = document.createElement("summary");
    sum.style.display = "flex";
    sum.style.justifyContent = "space-between";
    sum.style.alignItems = "center";
    sum.style.padding = "2px 0";
    sum.style.cursor = "default";

    // nombre visible
    const nameSpan = document.createElement("span");
    nameSpan.textContent = p.title;
    nameSpan.style.flex = "1";
    nameSpan.style.color = "#fff";

    // icono ⋮ menú contextual
    const menu = document.createElement("span");
    menu.textContent = "⋮";
    menu.className = "projMenu";
    menu.title = "Opciones de proyecto";

    // evitar toggle del <details> al clicar en ⋮
    menu.addEventListener("mousedown", (ev) => ev.preventDefault());
    menu.addEventListener("click", (ev) => {
      ev.stopPropagation();
      ev.preventDefault();

      const existing = document.querySelector(".contextMenu");
      if (existing && existing.dataset.slug === p.project) {
        existing.remove();
        return;
      }
      if (existing) existing.remove();
      showContextMenu(ev.pageX, ev.pageY, p.project, p.title);
    });

    sum.append(nameSpan, menu);
    det.appendChild(sum);

    // ----- Fases -----
    (p.phases || [])
      .sort((a, b) => {
        if (a === "main") return -1;
        if (b === "main") return 1;
        const numA = parseInt(a.replace(/[^0-9]/g, "")) || 0;
        const numB = parseInt(b.replace(/[^0-9]/g, "")) || 0;
        return numA - numB;
      })
      .forEach((ph) => {
        const item = document.createElement("div");
        item.textContent = "· " + ph;
        item.className = "phaseNode";
        item.onclick = async () => {
          console.log(`📂 Cargando fase: ${ph} del proyecto ${p.project}`);

          // título visible actual
          const currentDetails = document.querySelector(
            `details[data-slug="${p.project}"]`
          );
          let currentTitle = p.title;
          if (currentDetails) {
            const visibleSpan = currentDetails.querySelector("summary span");
            if (visibleSpan) currentTitle = visibleSpan.textContent.trim();
          }

          // actualizar estado global
          stateManager.set(p.project, ph, currentTitle);

          // loader + fetch + render
          chatRenderer.showLoader();
          const data = await apiClient.getHistory(p.project, ph);
          chatRenderer.renderAll(data.history);
          chatRenderer.hideLoader();

          // actualizar header
          const titleSpan = document.getElementById("sessionTitle");
          if (titleSpan) {
            titleSpan.innerText = `${currentTitle} / ${ph}`;
          }

          const saveBtn = document.querySelector("#header button");
          if (saveBtn) saveBtn.disabled = false;

          // marcar fase activa
          setActive(p.project, ph);
        };

        det.appendChild(item);
      });

    list.appendChild(det);
  });

  console.log("✅ Sidebar render completado");
}

// ==== MENÚ CONTEXTUAL ====

function showContextMenu(x, y, slug, title) {
  const old = document.querySelector(".contextMenu");
  if (old) old.remove();

  const menu = document.createElement("div");
  menu.className = "contextMenu";
  menu.dataset.slug = slug;
  menu.style.left = x + "px";
  menu.style.top = y + "px";
  menu.innerHTML = `
    <div class="ctxItem" id="renameOpt">✏️ Renombrar</div>
    <div class="ctxItem" id="deleteOpt">🗑 Eliminar</div>
  `;
  document.body.appendChild(menu);

  // --- Opción Renombrar ---
  document.getElementById("renameOpt").onclick = async () => {
    menu.remove();

    const details = document.querySelector(`details[data-slug="${slug}"]`);
    if (!details) return;
    const summary = details.querySelector("summary");
    const nameSpan = summary.querySelector("span");

    const input = document.createElement("input");
    input.type = "text";
    input.value = nameSpan.textContent;
    Object.assign(input.style, {
      flex: "1",
      border: "1px solid #555",
      borderRadius: "4px",
      background: "#222",
      color: "#fff",
      padding: "2px 4px",
      fontFamily: "inherit",
      fontSize: "0.9em",
      outline: "none",
    });

    summary.replaceChild(input, nameSpan);
    input.focus();
    input.select();

    const restore = () => summary.replaceChild(nameSpan, input);

    input.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        const newTitle = input.value.trim();
        if (!newTitle || newTitle === nameSpan.textContent) {
          restore();
          return;
        }
        try {
          await fetch(`/api/project/${slug}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_title: newTitle }),
          });

          nameSpan.textContent = newTitle;
          restore();
          showToast(`Proyecto renombrado a "${newTitle}"`, "success");
          console.log("✅ Proyecto renombrado:", newTitle);

          if (stateManager.current.project === slug) {
            stateManager.current.title = newTitle;
            const t = document.getElementById("sessionTitle");
            if (t)
              t.innerText = `${newTitle} / ${stateManager.current.phase}`;
          }

          const detProj = document.querySelector(
            `details[data-slug="${slug}"]`
          );
          if (detProj) detProj.dataset.title = newTitle;
        } catch (err) {
          console.error("❌ Error al renombrar:", err);
          showToast("Error al renombrar proyecto", "error");
          restore();
        }
      }
      if (e.key === "Escape") restore();
    });

    input.addEventListener("blur", restore);
  };

  // --- Opción Eliminar ---
  document.getElementById("deleteOpt").onclick = async () => {
    menu.remove();

    const confirmed = await confirmModal(
      "Eliminar proyecto",
      `¿Eliminar el proyecto <strong>${title}</strong> y todas sus fases?`
    );
    if (!confirmed) return;

    try {
      await fetch(`/api/project/${slug}`, { method: "DELETE" });
      const chatbox = document.getElementById("chatbox");
      chatbox.innerHTML = "";
      await initSidebar();
      const titleSpan = document.getElementById("sessionTitle");
      if (titleSpan)
        titleSpan.innerText = "Proyecto eliminado — selecciona otro";
      showToast(`Proyecto "${title}" eliminado`, "success");
    } catch (err) {
      console.error("❌ Error eliminando:", err);
      showToast("Error al eliminar proyecto", "error");
    }
  };

  document.addEventListener("click", () => menu.remove(), { once: true });
}

// ==== MODAL BLUR ====

function confirmModal(title, message, confirmText = "Eliminar") {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.id = "modalOverlay";
    overlay.innerHTML = `
      <div class="modalBox">
        <h4>${title}</h4>
        <p>${message}</p>
        <div class="modalBtns">
          <button class="modalCancel">Cancelar</button>
          <button class="modalDelete">${confirmText}</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const cancelBtn = overlay.querySelector(".modalCancel");
    const deleteBtn = overlay.querySelector(".modalDelete");

    cancelBtn.onclick = () => {
      overlay.remove();
      resolve(false);
    };
    deleteBtn.onclick = () => {
      overlay.remove();
      resolve(true);
    };

    document.addEventListener(
      "keydown",
      (e) => {
        if (e.key === "Escape") {
          overlay.remove();
          resolve(false);
        }
      },
      { once: true }
    );
  });
}

// ==== SELECCIÓN ACTIVA ====

export function setActive(projectSlug, phaseName) {
  document.querySelectorAll("details.active").forEach((el) =>
    el.classList.remove("active")
  );
  document.querySelectorAll(".phaseNode.active").forEach((el) =>
    el.classList.remove("active")
  );

  const det = document.querySelector(`details[data-slug="${projectSlug}"]`);
  if (det) det.classList.add("active");

  const nodes = det?.querySelectorAll(".phaseNode") || [];
  for (const n of nodes) {
    if (n.textContent.trim().endsWith(phaseName)) {
      n.classList.add("active");
      break;
    }
  }
}
