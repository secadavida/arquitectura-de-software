"use strict";

const SUITS = { O: "oros", C: "copas", E: "espadas", B: "bastos" };
const SUIT_ORDER = { O: 0, C: 1, E: 2, B: 3 };
const RANK_LABEL = { 1: "A", 10: "S", 11: "C", 12: "R" };

const params = new URLSearchParams(location.search);
const gameId = params.get("game");
let playerId = params.get("player");

const ui = {
  state: null,
  order: [],          // orden de la mano elegido por el jugador
  selected: null,     // código de la carta seleccionada
  lastDrawn: null,
  latencies: [],
  lastRoundShown: null,
  deadline: null,     // instante local en que vence el turno
};

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ red
async function api(path, options = {}) {
  const started = performance.now();
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  trackLatency(performance.now() - started);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || `Error ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function trackLatency(ms) {
  ui.latencies.push(ms);
  if (ui.latencies.length > 20) ui.latencies.shift();
  const avg = ui.latencies.reduce((a, b) => a + b, 0) / ui.latencies.length;
  $("latency").textContent = `Latencia: ${Math.round(ms)} ms (prom. ${Math.round(avg)} ms)`;
}

function say(text, kind = "info") {
  const box = $("message");
  box.textContent = text;
  box.className = `message ${kind}`;
}

// ------------------------------------------------------------------ lobby
async function initLobby() {
  $("lobby").classList.remove("hidden");
  const modes = await api("/api/modes");
  $("modes").innerHTML = modes.map((m, i) => `
    <label class="mode-option">
      <input type="radio" name="mode" value="${m.id}" ${i === 0 ? "checked" : ""}>
      <b>${m.name}</b> — <span class="muted">${m.description}</span>
    </label>`).join("");

  $("join-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const pin = new FormData(event.target).get("pin").trim();
    try {
      const game = await api(`/api/rooms/${encodeURIComponent(pin)}`);
      $("join-links").innerHTML = `<li class="muted">Elige tu nombre:</li>` + playerLinks(game);
    } catch (err) {
      $("join-links").innerHTML = `<li>${escapeHtml(err.message)}</li>`;
    }
  });

  $("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const players = form.getAll("player").map((p) => p.trim()).filter(Boolean);
    try {
      const created = await api("/api/games", {
        method: "POST",
        body: JSON.stringify({ mode: form.get("mode"), players, turn_seconds: Number(form.get("turn_seconds") || 0) }),
      });
      showLinks(created);
    } catch (err) {
      alert(err.message);
    }
  });
}

function playerLinks(game) {
  const base = `${location.origin}${location.pathname}`;
  return game.players.map((p) => {
    const url = `${base}?game=${game.game_id}&player=${p.id}`;
    return `<li><b>${escapeHtml(p.name)}</b>: <a href="${url}" target="_blank">${url}</a></li>`;
  }).join("");
}

function showLinks(created) {
  $("created-pin").textContent = created.room_pin;
  $("player-links").innerHTML = playerLinks(created);
  $("created").classList.remove("hidden");
}

// ------------------------------------------------------------------ partida
async function initGame() {
  $("game").classList.remove("hidden");
  $("deck").addEventListener("click", () => draw("mazo"));
  $("pile").addEventListener("click", () => draw("pozo"));
  $("discard").addEventListener("click", discard);
  $("close").addEventListener("click", closeRound);
  $("hint-toggle").addEventListener("change", renderHand);
  $("sort-rank").addEventListener("click", () => sortHand(byRank));
  $("sort-suit").addEventListener("click", () => sortHand(bySuit));
  $("player-switch").addEventListener("change", (e) => {
    params.set("player", e.target.value);
    location.search = params.toString();
  });
  await refresh();
  connectSocket();
  setInterval(() => ui.state && renderTimer(), 500);
}

function connectSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${location.host}/ws/games/${gameId}`);
  socket.onmessage = () => refresh();
  socket.onclose = () => setTimeout(connectSocket, 1500);
}

async function refresh() {
  try {
    const query = playerId ? `?player=${encodeURIComponent(playerId)}` : "";
    const state = await api(`/api/games/${gameId}${query}`);
    applyState(state);
    loadEvents();
  } catch (err) {
    say(err.message, "err");
  }
}

function applyState(state) {
  ui.state = state;
  ui.deadline = state.turn_remaining == null ? null : Date.now() + state.turn_remaining * 1000;
  const hand = state.me ? state.me.hand.map((c) => c.code) : [];
  ui.order = ui.order.filter((code) => hand.includes(code));
  hand.forEach((code) => { if (!ui.order.includes(code)) ui.order.push(code); });
  if (!hand.includes(ui.selected)) ui.selected = null;
  render();
}

function isMyTurn() {
  const s = ui.state;
  return s && s.status === "IN_PROGRESS" && s.me && s.current_player_id === s.me.id;
}

function render() {
  const s = ui.state;
  $("mode-name").textContent = s.mode.name;
  $("mode-desc").textContent = s.mode.description;
  $("round-label").textContent = s.status === "FINISHED" ? "Partida finalizada" : `Ronda ${s.round}`;
  $("score-head").textContent = s.mode.accumulates_points ? `Puntos (pierde con ${s.mode.loss_threshold})` : "Puntos";
  $("pin-label").textContent = `PIN ${s.room_pin}`;
  renderTimer();
  $("deck-count").textContent = s.deck_count;
  $("pile-count").textContent = s.pile_count;
  $("pile-top").outerHTML = s.pile_top ? cardHtml(s.pile_top, "", "pile-top") : `<span id="pile-top" class="card empty"></span>`;
  renderSwitch();
  renderScores();
  renderHand();
  renderTurnMessage();
  renderRoundResult();
}

function renderTimer() {
  const label = $("timer-label");
  if (!ui.deadline || ui.state.status !== "IN_PROGRESS") { label.classList.add("hidden"); return; }
  const secs = Math.max(0, Math.ceil((ui.deadline - Date.now()) / 1000));
  label.textContent = `⏱ ${secs} s`;
  label.classList.toggle("low", secs <= 10);
  label.classList.remove("hidden");
}

function renderSwitch() {
  const s = ui.state;
  const options = [`<option value="">(espectador)</option>`].concat(
    s.players.map((p) => `<option value="${p.id}" ${p.id === playerId ? "selected" : ""}>${escapeHtml(p.name)}</option>`));
  $("player-switch").innerHTML = options.join("");
}

function renderScores() {
  const s = ui.state;
  $("scores").innerHTML = s.players.map((p) => `
    <tr class="${p.id === s.current_player_id ? "turn" : ""}">
      <td>${escapeHtml(p.name)}${s.me && p.id === s.me.id ? " (tú)" : ""}</td>
      <td>${p.cards}</td>
      <td>${p.score}</td>
    </tr>`).join("");
}

function meldClassMap() {
  const map = {};
  const s = ui.state;
  if (!s.me || !$("hint-toggle").checked) return map;
  s.me.suggestion.melds.forEach((meld, i) => meld.cards.forEach((code) => { map[code] = `m${i + 1}`; }));
  return map;
}

function renderHand() {
  const s = ui.state;
  if (!s || !s.me) {
    $("hand").innerHTML = `<p class="muted">Modo espectador: elige un jugador en “Ver como”.</p>`;
    $("hand-count").textContent = "";
    updateButtons();
    return;
  }
  const byCode = Object.fromEntries(s.me.hand.map((c) => [c.code, c]));
  const melds = meldClassMap();
  $("hand").innerHTML = ui.order.map((code) => {
    const extra = [melds[code] || "", code === ui.selected ? "selected" : "", code === ui.lastDrawn ? "new" : ""].join(" ");
    return cardHtml(byCode[code], extra);
  }).join("");
  $("hand").querySelectorAll(".card").forEach((el) => el.addEventListener("click", () => {
    ui.selected = ui.selected === el.dataset.code ? null : el.dataset.code;
    renderHand();
  }));
  $("hand-count").textContent = `(${s.me.hand.length} cartas)`;
  const sug = s.me.suggestion;
  $("hint-text").textContent = $("hint-toggle").checked
    ? `Mejor organización: ${sug.melds.length} combinación(es); sobrantes = ${sug.leftover_points} pts.`
    : "";
  updateButtons();
}

function updateButtons() {
  const s = ui.state;
  const canDraw = isMyTurn() && s.phase === "robar";
  const canDiscard = isMyTurn() && s.phase === "descartar" && ui.selected;
  $("deck").disabled = !canDraw;
  $("pile").disabled = !canDraw || !s.pile_top;
  $("discard").disabled = !canDiscard;
  $("close").disabled = !canDiscard;
}

function renderTurnMessage() {
  const s = ui.state;
  if (s.status === "FINISHED") {
    const losers = s.losers.length ? ` Pierde: ${s.losers.join(", ")}.` : "";
    say(`Partida finalizada. Gana: ${s.winners.join(", ")}.${losers}`, "ok");
    return;
  }
  if (!s.me) return;
  const current = s.players.find((p) => p.id === s.current_player_id);
  if (!isMyTurn()) {
    say(`Turno de ${current.name}. Espera tu turno.`, "info");
  } else if (s.phase === "robar") {
    say("Tu turno: roba una carta del mazo o del pozo.", "info");
  } else {
    say("Selecciona una carta para descartar, o cierra la ronda descartándola.", "info");
  }
}

function renderRoundResult() {
  const r = ui.state.last_round;
  const box = $("round-result");
  if (!r) { box.classList.add("hidden"); return; }
  const rows = Object.keys(r.totals).map((name) => `
    <tr><td>${escapeHtml(name)}</td><td>${r.penalties[name]}</td><td>${r.totals[name]}</td>
    <td class="muted">${r.hands[name].length} cartas</td></tr>`).join("");
  box.innerHTML = `
    <h2>Resultado de la ronda ${r.number}: cerró ${escapeHtml(r.closer)}</h2>
    <table class="scores"><thead><tr><th>Jugador</th><th>Sobrantes de la ronda</th><th>Acumulado</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
  box.classList.remove("hidden");
  if (ui.lastRoundShown !== null && ui.lastRoundShown !== r.number && ui.state.status === "IN_PROGRESS") {
    say(`Ronda ${r.number} liquidada (cerró ${r.closer}). Comienza la ronda ${ui.state.round}.`, "ok");
  }
  ui.lastRoundShown = r.number;
}

async function loadEvents() {
  try {
    const events = await api(`/api/games/${gameId}/events`);
    const names = Object.fromEntries(ui.state.players.map((p) => [p.id, p.name]));
    $("events").innerHTML = events.slice(-40).reverse().map((e) =>
      `<li>${e.ts.slice(11, 19)} · ${e.event}${e.player_id ? " · " + escapeHtml(names[e.player_id] || e.player_id) : ""} · ${escapeHtml(JSON.stringify(e.payload))}</li>`).join("");
  } catch (err) {
    $("events").innerHTML = `<li>${escapeHtml(err.message)}</li>`;
  }
}

// ------------------------------------------------------------------ acciones
async function draw(source) {
  try {
    const before = new Set(ui.state.me.hand.map((c) => c.code));
    const state = await api(`/api/games/${gameId}/draw`, {
      method: "POST", body: JSON.stringify({ player: playerId, source, version: ui.state.version }),
    });
    ui.lastDrawn = state.me.hand.map((c) => c.code).find((c) => !before.has(c)) || null;
    applyState(state);
  } catch (err) { handleError(err); }
}

async function discard() {
  try {
    const state = await api(`/api/games/${gameId}/discard`, {
      method: "POST", body: JSON.stringify({ player: playerId, card: ui.selected, version: ui.state.version }),
    });
    ui.selected = null;
    ui.lastDrawn = null;
    applyState(state);
  } catch (err) { handleError(err); }
}

async function closeRound() {
  try {
    const result = await api(`/api/games/${gameId}/close`, {
      method: "POST", body: JSON.stringify({ player: playerId, card: ui.selected, version: ui.state.version }),
    });
    applyState(result.state);
    if (!result.valid) {
      say(`${result.cause} Sigue tu turno: descarta una carta.`, "err");
    }
  } catch (err) { handleError(err); }
}

function handleError(err) {
  // 409 por versión desactualizada (R2) o 423 por cerrojo (ADR-05): se recarga el estado vigente.
  say(err.message, "err");
  if (err.status === 409 || err.status === 423) refresh().then(() => say(err.message, "err"));
}

// ------------------------------------------------------------------ utilidades
const byRank = (a, b) => a.rank - b.rank || SUIT_ORDER[a.suit] - SUIT_ORDER[b.suit];
const bySuit = (a, b) => SUIT_ORDER[a.suit] - SUIT_ORDER[b.suit] || a.rank - b.rank;

function sortHand(compare) {
  if (!ui.state || !ui.state.me) return;
  ui.order = [...ui.state.me.hand].sort(compare).map((c) => c.code);
  renderHand();
}

function cardHtml(card, extra = "", id = "") {
  const rank = RANK_LABEL[card.rank] || card.rank;
  return `<span ${id ? `id="${id}"` : ""} class="card ${card.suit} ${extra}" data-code="${card.code}" title="${card.label} (${card.points} pts)">
    <span class="pts">${card.points}</span><span class="rank">${rank}</span><span class="suit">${SUITS[card.suit]}</span></span>`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

(gameId ? initGame() : initLobby()).catch((err) => say(err.message, "err"));
