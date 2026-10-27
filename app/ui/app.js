const PAGE = 120;
const POLL_MS = 3000;

const state = {
  lang: load("lang", "it") === "en" ? "en" : "it",
  saves: [],
  characters: {},
  path: "",
  mtime: 0,
  relics: [],
  byUid: new Map(),
  shown: PAGE,
  tab: "relics",
  sync: { key: "searching", cls: "" },
  filters: { text: "", color: "all", kind: "all", character: "" },
  junk: { kind: "all", threshold: Number(load("threshold", 5)), solo: load("solo", "1") === "1" },
};

const $ = (sel) => document.querySelector(sel);
const T = () => STRINGS[state.lang];

// Preferenze del singolo utente: se lo storage non è disponibile si usano i valori predefiniti.
function load(key, fallback) {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem(key, value); } catch { /* ignorato */ }
}

// Nome di reliquia, effetto o malus nella lingua scelta.
const nm = (obj) => (state.lang === "en" ? obj.name_en : obj.name);
const charName = (key) => (state.lang === "en" ? key : state.characters[key] || key);

async function api(url) {
  const res = await fetch(url, { cache: "no-store" });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || res.statusText);
  return body;
}

// key è una chiave di STRINGS (eventualmente con argomenti) oppure un messaggio d'errore già pronto.
function setSync(key, cls = "", ...args) {
  state.sync = { key, cls, args };
  const text = T()[key];
  $("#sync").textContent = typeof text === "function" ? text(...args) : text ?? key;
  $("#sync").className = "sync " + cls;
}

function timeOf(mtime) {
  return new Date(mtime * 1000).toLocaleString(T().locale, { dateStyle: "short", timeStyle: "short" });
}

function applyLanguage() {
  const t = T();
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t[el.dataset.i18n]; });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => { el.innerHTML = t[el.dataset.i18nHtml]; });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t[el.dataset.i18nTitle]; });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t[el.dataset.i18nPlaceholder]; });
  document.querySelectorAll("#lang button").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));

  const charSel = $("#character");
  for (const opt of charSel.options) if (opt.value) opt.textContent = charName(opt.value);
  const saveSel = $("#save");
  state.saves.forEach((s, i) => { saveSel.options[i].textContent = `${s.name} — ${timeOf(s.mtime)}`; });

  const { key, cls, args = [] } = state.sync;
  setSync(key, cls, ...args);
  renderResearchInfo();
  render();
}

async function init() {
  applyLanguage();
  const { saves, characters } = await api("/api/saves");
  state.saves = saves;
  state.characters = characters;

  for (const key of Object.keys(characters)) $("#character").add(new Option(charName(key), key));
  loadResearch();

  const saveSel = $("#save");
  if (!saves.length) {
    setSync("noSaves", "error");
    return;
  }
  fillSaves(saves);
  // Il più recente è il primo: è quello con cui hai giocato per ultimo.
  state.path = saves[0].path;
  saveSel.addEventListener("change", () => { state.path = saveSel.value; loadRelics(); });

  await loadRelics();
  setInterval(poll, POLL_MS);
}

async function loadRelics(force = false) {
  setSync("reading");
  try {
    const solo = state.junk.solo ? 1 : 0;
    const { mtime, relics } = await api(
      `/api/relics?path=${encodeURIComponent(state.path)}&solo=${solo}${force ? "&force=1" : ""}`);
    // Il gioco ha salvato: l'eventuale avviso "non ha ancora salvato" non serve più.
    if (mtime !== state.mtime) $("#notice").hidden = true;
    state.mtime = mtime;
    state.relics = relics;
    state.byUid = new Map(relics.map((r) => [r.uid, r]));
    setSync("synced", "live", timeOf(mtime));
    render();
  } catch (err) {
    setSync(err.message, "error");
  }
}

function fillSaves(saves) {
  const saveSel = $("#save");
  saveSel.replaceChildren(...saves.map((s) => new Option(`${s.name} — ${timeOf(s.mtime)}`, s.path)));
  if (state.path) saveSel.value = state.path;
}

// Tasto Aggiorna: ricerca di nuovo i salvataggi e rilegge quello scelto anche se sembra invariato.
async function refresh() {
  const before = state.mtime;
  try {
    const { saves } = await api("/api/saves");
    state.saves = saves;
    if (!saves.length) return setSync("noSaves", "error");
    if (!saves.some((s) => s.path === state.path)) state.path = saves[0].path;
    fillSaves(saves);
  } catch (err) {
    return setSync(err.message, "error");
  }
  await loadRelics(true);
  if (state.sync.cls === "error") return;
  setSync("refreshed", "live", timeOf(state.mtime));
  const notice = $("#notice");
  notice.hidden = state.mtime !== before;
  if (!notice.hidden) notice.textContent = T().notSavedYet(timeOf(state.mtime));
}

// Se il gioco salva, il file cambia: lo rileggiamo da soli.
async function poll() {
  try {
    const { mtime } = await api(`/api/status?path=${encodeURIComponent(state.path)}`);
    if (mtime !== state.mtime) await loadRelics();
  } catch (err) {
    setSync(err.message, "error");
  }
}

// Motivo per buttare la reliquia, oppure null.
function verdictOf(relic) {
  if (relic.verdict) return relic.verdict;
  if (relic.best < state.junk.threshold && relic.top_effect < 4) return { kind: "weak" };
  return null;
}

function matches(relic) {
  const f = state.filters;
  if (f.color !== "all" && relic.color !== f.color) return false;
  if (f.kind === "normal" && relic.deep) return false;
  if (f.kind === "deep" && !relic.deep) return false;
  if (f.character) {
    // Serve almeno un effetto che vale per il personaggio, e nessun effetto esclusivo di un altro
    // personaggio. Gli effetti limitati a più personaggi (es. cambio abilità dell'arma) non escludono:
    // per chi non può usarli semplicemente non si attivano.
    const usable = relic.effects.some((e) => appliesTo(e, f.character));
    const foreign = relic.effects.some((e) => e.characters.length === 1 && e.characters[0] !== f.character);
    if (!usable || foreign) return false;
  }
  if (f.text) {
    const hay = [nm(relic), ...relic.effects.flatMap((e) => [nm(e), e.curse ? nm(e.curse) : ""])]
      .join(" ").toLowerCase();
    if (!f.text.split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function highlight(text) {
  let html = esc(text);
  for (const w of state.filters.text.split(/\s+/).filter(Boolean)) {
    const re = new RegExp(esc(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    html = html.replace(re, (m) => `<mark>${m}</mark>`);
  }
  // Evidenzia il prefisso [Personaggio].
  return html.replace(/^(\[[^\]]+\])/, '<span class="who">$1</span>');
}

const appliesTo = (effect, character) => !effect.characters.length || effect.characters.includes(character);

function effectList(relic, withScores) {
  const who = state.filters.character;
  return relic.effects.map((e, i) => {
    const score = withScores ? `<span class="score s${relic.effect_scores[i]}">${relic.effect_scores[i]}</span>` : "";
    const curse = e.curse ? `<span class="curse">${highlight(nm(e.curse))}</span>` : "";
    // Con un personaggio selezionato, gli effetti che non valgono per lui sono attenuati.
    const off = who && !appliesTo(e, who) ? ` class="off" title="${esc(T().notFor(charName(who)))}"` : "";
    return `<li${off}>${score}${highlight(nm(e))}${curse}</li>`;
  }).join("");
}

// Posizione nella griglia del gioco: 8 reliquie per riga, più recenti per prime.
function gridPos(relic) {
  const i = state.filters.color === "all" ? relic.slot : relic.slot_color;
  return T().gridPos(Math.floor(i / 8) + 1, (i % 8) + 1);
}

function reasonOf(relic, verdict) {
  const t = T();
  if (verdict.kind === "duplicate") return t.reasonDuplicate;
  if (verdict.kind === "dominated") {
    const keep = state.byUid.get(verdict.keep);
    return `${t.reasonDominated(keep.deep)}
      <div class="keeper ${keep.color}"><b>${esc(nm(keep))}</b><ul>${effectList(keep, false)}</ul></div>`;
  }
  const n = relic.best_for.length;
  const who = n === Object.keys(state.characters).length ? t.anyCharacter
    : n > 3 ? t.nCharacters(n) : t.withCharacters(relic.best_for.map(charName).join(", "));
  return t.reasonWeak(relic.best, who, state.junk.threshold);
}

function relicCard(r) {
  const t = T();
  const verdict = state.tab === "junk" ? verdictOf(r) : null;
  const who = state.filters.character;
  const badges = [
    who ? `<span class="badge score-badge" title="${esc(t.scoreFor(charName(who)))}">${r.scores[who]}</span>` : "",
    r.deep ? `<span class="badge">${t.deep}</span>` : "",
    verdict ? `<span class="badge junk ${verdict.kind}">${t.verdict[verdict.kind]}</span>` : "",
  ].join("");
  return `
    <article class="relic ${r.color}${r.deep ? " deep" : ""}">
      <div class="pos" title="${esc(t.gridHelp)}">${gridPos(r)}</div>
      <h3><span>${highlight(nm(r))}</span><span class="badges">${badges}</span></h3>
      <ul>${effectList(r, state.tab === "junk")}</ul>
      ${verdict ? `<div class="reason">${reasonOf(r, verdict)}</div>` : ""}
    </article>`;
}

function render() {
  if (state.tab === "characters") return renderCharacters();
  const t = T();
  const total = state.relics.length;
  let list = state.relics.filter(matches);
  let summary;

  if (state.tab === "junk") {
    const junk = list.filter((r) => verdictOf(r));
    const count = (k) => junk.filter((r) => verdictOf(r).kind === k).length;
    $("#nDuplicate").textContent = count("duplicate");
    $("#nDominated").textContent = count("dominated");
    $("#nWeak").textContent = count("weak");
    list = state.junk.kind === "all" ? junk : junk.filter((r) => verdictOf(r).kind === state.junk.kind);
    summary = t.junkSummary(junk.length, total) + (list.length !== junk.length ? t.shownCount(list.length) : "");
  } else {
    const deep = state.relics.filter((r) => r.deep).length;
    summary = list.length === total ? t.allSummary(total, total - deep, deep) : t.filteredSummary(list.length, total);
  }

  $("#summary").textContent = total ? summary : "";
  // L'elenco arriva già nell'ordine del gioco: prima le normali, poi le profonde.
  let lastDeep = null;
  const cards = list.slice(0, state.shown).map((r) => {
    const head = r.deep !== lastDeep ? `<h2 class="section">${r.deep ? t.sectionDeep : t.sectionNormal}</h2>` : "";
    lastDeep = r.deep;
    return head + relicCard(r);
  });
  $("#list").innerHTML = list.length ? cards.join("") : total ? `<p class="empty">${t.empty}</p>` : "";
  $("#more").hidden = list.length <= state.shown;
}

function refilter() {
  state.shown = PAGE;
  render();
}

function setChip(group, chip) {
  document.querySelectorAll(`${group} .chip`).forEach((c) => c.classList.toggle("on", c === chip));
}

$("#lang").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-lang]");
  if (!btn) return;
  state.lang = btn.dataset.lang;
  save("lang", state.lang);
  applyLanguage();
});

document.querySelector(".tabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab[data-tab]");
  if (!tab) return;
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === tab));
  state.tab = tab.dataset.tab;
  const chars = state.tab === "characters";
  $("#junkBar").hidden = state.tab !== "junk";
  $("#charView").hidden = !chars;
  for (const id of ["#filters", "#summary", "#list", "#more"]) $(id).hidden = chars;
  refilter();
});

$("#search").addEventListener("input", (e) => { state.filters.text = e.target.value.trim().toLowerCase(); refilter(); });
$("#kind").addEventListener("change", (e) => { state.filters.kind = e.target.value; refilter(); });
$("#character").addEventListener("change", (e) => { state.filters.character = e.target.value; refilter(); });
$("#colors").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  setChip("#colors", chip);
  state.filters.color = chip.dataset.color;
  refilter();
});
$("#kinds").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  setChip("#kinds", chip);
  state.junk.kind = chip.dataset.kind;
  refilter();
});
$("#threshold").value = state.junk.threshold;
$("#thresholdValue").textContent = state.junk.threshold;
$("#threshold").addEventListener("input", (e) => {
  state.junk.threshold = Number(e.target.value);
  $("#thresholdValue").textContent = e.target.value;
  save("threshold", e.target.value);
  refilter();
});
$("#solo").checked = state.junk.solo;
$("#solo").addEventListener("change", (e) => {
  state.junk.solo = e.target.checked;
  save("solo", e.target.checked ? "1" : "0");
  loadRelics();
});
$("#showMore").addEventListener("click", () => { state.shown += PAGE; render(); });
$("#refresh").addEventListener("click", async () => {
  const btn = $("#refresh");
  btn.disabled = true;
  try { await refresh(); } finally { btn.disabled = false; }
});

// Si parte quando anche characters.js è caricato.
document.addEventListener("DOMContentLoaded", () => init().catch((err) => setSync(err.message, "error")));
