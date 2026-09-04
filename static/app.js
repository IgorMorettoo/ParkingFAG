const byId = (id) => document.getElementById(id);

function render(reading) {
  if (!reading) return;
  byId("free").textContent = reading.free_spaces;
  byId("occupied").textContent = reading.occupied_spaces;
  byId("total").textContent = reading.total_spaces;
  byId("updated").textContent = `Atualizado em ${new Date(reading.captured_at).toLocaleString("pt-BR")}`;
  const spaces = reading.spaces || [];
  byId("spaces").innerHTML = spaces.map((space) => `
    <article class="space ${space.is_free ? "free" : "occupied"}">
      <strong>Vaga ${space.index}</strong>
      <span>${space.is_free ? "Livre" : "Ocupada"}</span>
    </article>`).join("");
  byId("empty").hidden = spaces.length > 0;
}

async function refresh() {
  try {
    const response = await fetch("/api/readings/latest", { cache: "no-store" });
    if (!response.ok) throw new Error("offline");
    const data = await response.json();
    render(data.reading);
    byId("connection").textContent = "Sistema online";
    byId("connection").className = "status online";
  } catch {
    byId("connection").textContent = "Sem conexao";
    byId("connection").className = "status";
  }
}

refresh();
setInterval(refresh, 5000);

