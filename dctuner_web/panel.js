(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = { history: [], peak: { rpm: 0, afr: 0, temperature: 0, pressure: 0, load: 0, advance: 0 }, min: { rpm: Infinity }, recording: false, lastStatus: "offline", started: Date.now() };
  const number = (value, digits = 0) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "0";
  const setText = (id, value) => { const node = $(id); if (node) node.textContent = value; };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, Number(value) || 0));
  let toastTimer;
  function showToast(message) { const toast = $("toast"); if (!toast) return; toast.textContent = message; toast.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove("show"), 3200); }

  function activateView(id) {
    document.querySelectorAll(".workspace-view").forEach((view) => view.classList.toggle("active-view", view.id === id));
    document.querySelectorAll(".workspace-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.target === id));
    if (id === "dashboardView") setTimeout(drawChart, 0);
    if (id === "tuneView") setTimeout(mapDraw3D, 0);
  }
  document.querySelectorAll(".workspace-tab").forEach((tab) => tab.addEventListener("click", () => activateView(tab.dataset.target)));
  document.querySelectorAll(".menu-item").forEach((item) => item.addEventListener("click", () => showToast(`${item.textContent}: usa las pestañas de trabajo para abrir esta sección.`)));
  document.querySelectorAll("[data-not-ready]").forEach((button) => button.addEventListener("click", () => showToast(button.dataset.notReady)));
  document.querySelectorAll(".subtab").forEach((tab) => tab.addEventListener("click", () => { document.querySelectorAll(".subtab").forEach((other) => other.classList.remove("active")); tab.classList.add("active"); showToast(`${tab.textContent}: tabla lista para cargar un archivo de mapa.`); }));
  document.querySelectorAll("[data-target='terminalCard']").forEach((button) => button.addEventListener("click", () => { activateView("logsView"); setTimeout(() => $("terminalCard").scrollIntoView({ behavior: "smooth", block: "center" }), 0); }));

  const splash = $("splashScreen");
  if (splash) window.setTimeout(() => splash.classList.add("hidden"), 2600);

  function updateClock() { setText("clock", new Date().toLocaleTimeString("es-MX", { hour12: false })); }
  setInterval(updateClock, 1000); updateClock();

  function updateConnection(status) {
    const telemetry = status.telemetry || {};
    const dot = $("connectionDot");
    dot.className = "status-dot " + (telemetry.status === "connected" ? "online" : telemetry.status === "simulated" ? "simulated" : "offline");
    setText("connectionText", telemetry.status === "connected" ? "ECU CONECTADA" : telemetry.status === "simulated" ? "SIMULACIÓN" : "SIN CONEXIÓN");
    const profileName = status.profile === "speeduino" ? "Speeduino" : "MegaSquirt";
    setText("sourceStatus", `${profileName} · ${telemetry.source || status.mode || "—"}`);
    setText("portStatus", status.port || "—");
    setText("healthBadge", telemetry.status === "connected" || telemetry.status === "simulated" ? (telemetry.status === "simulated" ? "SIMULACIÓN" : "EN LÍNEA") : "REVISAR");
    $("healthBadge").className = "badge " + (telemetry.status === "connected" || telemetry.status === "simulated" ? "good" : "warn");
    setText("recordStatus", state.recording ? "ACTIVO" : "INACTIVO");
    setText("recordStatus", state.recording ? "ACTIVO" : "INACTIVO");
    if (telemetry.status === "error" && status.last_error) setText("sourceStatus", status.last_error);
  }

  function updateGauge(id, value, digits, barId, max) {
    setText(id, number(value, digits));
    const bar = $(barId); if (bar) bar.style.width = `${clamp((Number(value) / max) * 100, 0, 100)}%`;
  }

  function updateTelemetry(item) {
    if (!item) return;
    state.history.push(item);
    if (state.history.length > 300) state.history.shift();
    ["rpm", "afr", "temperature", "pressure", "load", "advance"].forEach((key) => {
      const value = Number(item[key]) || 0;
      state.peak[key] = Math.max(state.peak[key] || 0, value);
    });
    state.min.rpm = Math.min(state.min.rpm, Number(item.rpm) || 0);
    updateGauge("rpm", item.rpm, 0, "rpmBar", 8000);
    updateGauge("afr", item.afr, 1, "afrBar", 22);
    updateGauge("temperature", item.temperature, 0, "temperatureBar", 120);
    updateGauge("pressure", item.pressure, 0, "pressureBar", 250);
    updateGauge("load", item.load, 0, "loadBar", 100);
    updateGauge("advance", item.advance, 1, "advanceBar", 45);
    setText("voltage", `${number(item.voltage, 1)} V`);
    setText("throttle", `${number(item.throttle, 0)} %`);
    setText("rpmPeak", number(state.peak.rpm, 0));
    setText("rpmMin", state.min.rpm === Infinity ? "0" : number(state.min.rpm, 0));
    setText("frameStatus", item.iso_time ? new Date(item.iso_time).toLocaleTimeString("es-MX", { hour12: false }) : "—");
    drawChart();
  }

  function drawChart() {
    const canvas = $("telemetryChart");
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(300, Math.floor(rect.width));
    const height = 280;
    if (canvas.width !== width * ratio || canvas.height !== height * ratio) { canvas.width = width * ratio; canvas.height = height * ratio; }
    const ctx = canvas.getContext("2d"); ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = "#0b0d0f"; ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#1e282e"; ctx.lineWidth = 1;
    for (let i = 1; i < 5; i++) { const y = Math.round((height / 5) * i) + .5; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
    for (let i = 1; i < 8; i++) { const x = Math.round((width / 8) * i) + .5; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
    const points = state.history; if (points.length < 2) return;
    const line = (key, max, color, multiplier = 1) => {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
      points.forEach((item, index) => { const x = (index / (points.length - 1)) * width; const y = height - (clamp(Number(item[key]) * multiplier, 0, max) / max) * (height - 18) - 8; if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
      ctx.stroke();
    };
    line("rpm", 8000, "#00a8ff"); line("afr", 2200, "#ff2020", 100);
  }
  window.addEventListener("resize", drawChart);

  async function getJSON(url, options) { const response = await fetch(url, options); if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); }
  async function refresh() {
    try {
      const [telemetry, status] = await Promise.all([getJSON("/api/telemetry?limit=1"), getJSON("/api/status")]);
      updateConnection(status); updateTelemetry(telemetry.latest);
      state.lastStatus = status.telemetry.status;
    } catch (error) { setText("connectionText", "SERVIDOR NO DISPONIBLE"); $("connectionDot").className = "status-dot offline"; }
  }

  $("connectButton").addEventListener("click", async () => {
    const button = $("connectButton"); button.disabled = true; button.textContent = "CONECTANDO...";
    try {
      const status = await getJSON("/api/connection", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ simulation: $("modeSelect").value === "true", profile: $("profileSelect").value, port: $("portSelect").value, baud: Number($("baudSelect").value) }) });
      updateConnection(status.status);
      $("safetyNotice").innerHTML = status.status.mode === "simulación" ? "<strong>MODO SEGURO:</strong> el simulador está activo. Ningún comando sale por USB." : "<strong>ECU EN SERIE:</strong> verifica RPM, temperatura y voltaje antes de modificar un mapa.";
    } catch (error) { setText("connectionText", "ERROR DE CONEXIÓN"); }
    button.disabled = false; button.textContent = "CONECTAR";
  });

  $("recordButton").addEventListener("click", async () => {
    const next = !state.recording;
    try {
      const result = await getJSON("/api/recording", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active: next }) });
      state.recording = result.active; $("recordButton").textContent = state.recording ? "■ DETENER" : "● GRABAR"; updateConnection({ telemetry: { status: state.lastStatus }, mode: "", port: "" }); loadLogs();
    } catch (error) { appendTerminal(`Error de registro: ${error.message}`); }
  });

  $("clearPeaksButton").addEventListener("click", () => { state.peak = { rpm: 0, afr: 0, temperature: 0, pressure: 0, load: 0, advance: 0 }; state.min.rpm = Infinity; setText("rpmPeak", "0"); setText("rpmMin", "0"); });
  $("refreshButton").addEventListener("click", refresh);
  $("reloadLogsButton").addEventListener("click", loadLogs);

  async function loadLogs() {
    try {
      const result = await getJSON("/api/logs");
      $("logsList").innerHTML = result.files.length ? result.files.map((file) => `<div class="log-row"><span class="log-name">${escapeHTML(file.name)}</span><a class="button small" href="/api/logs/${encodeURIComponent(file.name)}">DESCARGAR</a></div>`).join("") : '<span class="muted">No hay registros todavía.</span>';
    } catch (error) { $("logsList").innerHTML = '<span class="muted">No se pudo cargar la lista.</span>'; }
  }
  function escapeHTML(value) { return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }
  function appendTerminal(message) { const output = $("terminalOutput"); output.textContent += `\n${new Date().toLocaleTimeString("es-MX", { hour12: false })} ${message}`; output.scrollTop = output.scrollHeight; }
  $("commandForm").addEventListener("submit", async (event) => { event.preventDefault(); const input = $("commandInput"); const command = input.value.trim(); if (!command) return; appendTerminal(`> ${command}`); input.value = ""; try { const result = await getJSON("/api/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ command }) }); appendTerminal(result.message); } catch (error) { appendTerminal("Comando bloqueado o ECU desconectada"); } });

  const mapState = { values: Array.from({ length: 256 }, (_, index) => 30 + ((index * 7) % 80)), compare: null, undo: [], redo: [], fileName: "mapa.msq", extension: "msq" };
  function mapSnapshot() { return mapState.values.slice(); }
  function mapPushUndo() { mapState.undo.push(mapSnapshot()); if (mapState.undo.length > 30) mapState.undo.shift(); mapState.redo = []; }
  function mapRender() {
    const grid = $("mapGrid"); if (!grid) return;
    let html = '<div class="map-cell axis">RPM/MAP</div>';
    for (let col = 0; col < 16; col += 1) html += `<div class="map-cell axis">${500 + col * 500}</div>`;
    for (let row = 0; row < 16; row += 1) {
      html += `<div class="map-cell axis">${20 + row * 5}%</div>`;
      for (let col = 0; col < 16; col += 1) { const index = row * 16 + col; const diff = mapState.compare && Number(mapState.compare[index]) !== Number(mapState.values[index]) ? " diff" : ""; html += `<div class="map-cell value${diff}" contenteditable="true" spellcheck="false" data-index="${index}">${number(mapState.values[index], 1)}</div>`; }
    }
    grid.innerHTML = html;
    grid.querySelectorAll(".map-cell.value").forEach((cell) => cell.addEventListener("blur", () => { const index = Number(cell.dataset.index); const value = Number(cell.textContent.replace(",", ".")); if (Number.isFinite(value)) { mapPushUndo(); mapState.values[index] = value; mapRender(); } }));
    setText("mapDiffStatus", mapState.compare ? `${mapState.compare.filter((value, index) => Number(value) !== Number(mapState.values[index])).length} celdas diferentes` : "Edición en el navegador; no se escribe en la ECU.");
    setText("mapFileStatus", mapState.fileName.toUpperCase()); $("mapFileStatus").className = "badge good";
    mapDraw3D();
  }
  function mapDraw3D() {
    const canvas = $("map3d"); if (!canvas) return; const ctx = canvas.getContext("2d"); const width = canvas.width; const height = canvas.height;
    ctx.fillStyle = "#090b0d"; ctx.fillRect(0, 0, width, height); ctx.strokeStyle = "#1b2b34"; ctx.lineWidth = 1;
    for (let row = 0; row < 16; row += 1) { ctx.beginPath(); for (let col = 0; col < 16; col += 1) { const x = 28 + col * 26 + row * 10; const y = 218 - row * 8 - Number(mapState.values[row * 16 + col]) * 1.1; if (col === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); }
    for (let col = 0; col < 16; col += 1) { ctx.beginPath(); for (let row = 0; row < 16; row += 1) { const x = 28 + col * 26 + row * 10; const y = 218 - row * 8 - Number(mapState.values[row * 16 + col]) * 1.1; if (row === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); }
    ctx.strokeStyle = "#00a8ff"; ctx.lineWidth = 2;
    for (let row = 0; row < 16; row += 1) { ctx.beginPath(); for (let col = 0; col < 16; col += 1) { const x = 28 + col * 26 + row * 10; const y = 218 - row * 8 - Number(mapState.values[row * 16 + col]) * 1.1; if (col === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); }
  }
  function readFile(file, callback) { const reader = new FileReader(); reader.onload = () => callback(reader.result, file.name); reader.onerror = () => appendTerminal(`No se pudo leer ${file.name}`); reader.readAsArrayBuffer(file); }
  function valuesFromBuffer(buffer, name) {
    const lower = name.toLowerCase(); const bytes = new Uint8Array(buffer); let values = [];
    if (lower.endsWith(".bin")) values = Array.from(bytes.slice(0, 256));
    else { const text = new TextDecoder("utf-8").decode(bytes).replace(/^\uFEFF/, ""); try { const data = JSON.parse(text); const source = Array.isArray(data) ? data.flat(Infinity) : (data.values || data.table || data.map || []); values = source.map(Number).filter(Number.isFinite); } catch (error) { values = text.split(/[\s,;]+/).map(Number).filter(Number.isFinite); } }
    values = values.slice(0, 256); while (values.length < 256) values.push(0); return values;
  }
  function chooseMap(file, isCompare) { if (!file) return; readFile(file, (buffer, name) => { const values = valuesFromBuffer(buffer, name); if (isCompare) { mapState.compare = values; } else { mapPushUndo(); mapState.values = values; mapState.compare = null; mapState.fileName = name; mapState.extension = name.toLowerCase().endsWith(".bin") ? "bin" : "msq"; } mapRender(); }); }
  function downloadMap() { const values = mapState.values.slice(); let blob; let filename = mapState.fileName || "mapa.msq"; if (mapState.extension === "bin") { blob = new Blob([new Uint8Array(values.map((value) => Math.max(0, Math.min(255, Math.round(Number(value) || 0)))) )], { type: "application/octet-stream" }); if (!filename.toLowerCase().endsWith(".bin")) filename += ".bin"; } else { blob = new Blob([JSON.stringify({ format: "DC TUNER STUDIO MAP", rows: 16, columns: 16, values }, null, 2)], { type: "application/json" }); if (!filename.toLowerCase().endsWith(".msq")) filename += ".msq"; } const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = filename; link.click(); URL.revokeObjectURL(link.href); }
  $("mapFileInput").addEventListener("change", (event) => chooseMap(event.target.files[0], false));
  $("mapCompareFile").addEventListener("change", (event) => chooseMap(event.target.files[0], true));
  $("mapSaveButton").addEventListener("click", downloadMap);
  $("mapUndoButton").addEventListener("click", () => { if (!mapState.undo.length) return; mapState.redo.push(mapSnapshot()); mapState.values = mapState.undo.pop(); mapRender(); });
  $("mapRedoButton").addEventListener("click", () => { if (!mapState.redo.length) return; mapState.undo.push(mapSnapshot()); mapState.values = mapState.redo.pop(); mapRender(); });
  mapRender();

  loadLogs(); refresh(); setInterval(refresh, 100);
})();
