export const apiClient = {
  async sendMessage(message, project, phase) {
    console.log("🧩 apiClient.sendMessage() → backend", { message, project, phase });

    const r = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, project, phase }),
    });

    if (!r.ok) {
      const text = await r.text();
      console.error("❌ Error HTTP de backend:", r.status, text);
      throw new Error("Error al conectar con backend");
    }

    const json = await r.json();
    console.log("📨 Respuesta backend:", json);
    return json;
  },

  async getHistory(project, phase) {
    const r = await fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, phase }),
    });
    return await r.json();
  },

  async saveContext(project, phase) {
    const r = await fetch("/api/save_context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, phase }),
    });
    return r.json();
  },
};
