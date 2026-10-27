// Pagina Personaggi e stato dei dati della ricerca periodica.
const TIER_ORDER = ["S", "A", "B", "C"];

Object.assign(state, { research: null, charData: null, charKey: load("charKey", "Wylder") });

const tx = (obj) => (obj ? obj[state.lang] || obj.en || obj.it || "" : "");
// Nome di un effetto della ricerca (in inglese) nella lingua scelta.
const effectName = (en) => (state.lang === "en" ? en : state.charData?.names_it[en] || en);

async function loadResearch() {
  try {
    const res = await api("/api/research");
    state.research = res;
    renderResearchInfo();
    if (res.update.state === "checking") return setTimeout(loadResearch, 2000);
    if (res.update.state === "new") {
      // Sono arrivati voti nuovi: si rianalizzano le reliquie.
      state.charData = null;
      loadRelics();
    }
    if (state.tab === "characters") renderCharacters();
  } catch { /* la pagina funziona anche senza */ }
}

function renderResearchInfo() {
  const r = state.research;
  if (!r) return;
  const t = T();
  const date = new Date(r.meta.updated).toLocaleDateString(t.locale, { dateStyle: "medium" });
  $("#researchInfo").textContent = t.researchDate(date);

  const banner = $("#updateBanner");
  banner.hidden = r.update.state !== "new";
  if (!banner.hidden) {
    const changes = (r.meta.changes || []).map((c) => `<li>${esc(tx(c))}</li>`).join("");
    banner.innerHTML = `${esc(t.updateNew(date))}<ul>${changes}</ul>`;
  }
}

// Quante reliquie possedute hanno l'effetto (nome inglese).
function ownedCount(nameEn) {
  return state.relics.filter((r) => r.effects.some((e) => e.name_en === nameEn)).length;
}

function tierBlocks(items, render) {
  return TIER_ORDER.map((tier) => {
    const rows = items.filter((i) => i.tier === tier);
    if (!rows.length) return "";
    return `<div class="tier-row"><span class="tier t${tier}">${tier}</span><ul>${rows.map(render).join("")}</ul></div>`;
  }).join("");
}

function effectItem(e) {
  const n = ownedCount(e.effect);
  return `<li><span class="eff">${highlight(effectName(e.effect))}</span>
    <span class="owned${n ? "" : " none"}">${T().owned(n)}</span>
    <span class="why">${esc(tx(e.why))}</span></li>`;
}

const textItem = (field) => (w) => `<li><span class="eff">${esc(tx(w[field]))}</span><span class="why">${esc(tx(w.why))}</span></li>`;

function section(title, body) {
  return body ? `<section class="char-sec"><h2>${title}</h2>${body}</section>` : "";
}

async function renderCharacters() {
  const t = T();
  if (!state.charData) {
    try {
      state.charData = await api("/api/characters");
    } catch {
      $("#charBody").innerHTML = `<p class="empty">${t.noResearch}</p>`;
      return;
    }
  }
  const all = state.charData.characters;
  if (!all[state.charKey]) state.charKey = Object.keys(all)[0];

  $("#charPicker").innerHTML = Object.keys(state.characters).filter((k) => all[k]).map((k) =>
    `<button class="chip${k === state.charKey ? " on" : ""}" data-char="${k}">${esc(charName(k))}</button>`).join("");

  const c = all[state.charKey];
  const curses = c.curses || {};
  const curseList = (list) => (list || []).map((e) => `<li><span class="eff">${esc(effectName(e.curse))}</span><span class="why">${esc(tx(e.why))}</span></li>`).join("");
  const builds = (c.builds || []).map((b) => `
    <article class="build">
      <h3>${esc(tx(b.name))}</h3>
      ${b.vessel ? `<p class="muted">${t.vessel}: ${esc(tx(b.vessel))}</p>` : ""}
      <div class="build-cols">
        <div><h4>${t.normalSlots}</h4><ul>${b.normal.map((n) => `<li>${esc(effectName(n))} <span class="owned${ownedCount(n) ? "" : " none"}">${t.owned(ownedCount(n))}</span></li>`).join("")}</ul></div>
        <div><h4>${t.deepSlots}</h4><ul>${(b.deep || []).map((n) => `<li>${esc(effectName(n))} <span class="owned${ownedCount(n) ? "" : " none"}">${t.owned(ownedCount(n))}</span></li>`).join("")}</ul></div>
      </div>
      ${b.notes ? `<p class="why">${esc(tx(b.notes))}</p>` : ""}
    </article>`).join("");

  const general = state.charData.general || {};
  const sources = (state.research?.meta.sources || [])
    .map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title || s.url)}</a></li>`).join("");

  $("#charBody").innerHTML = `
    <header class="char-head">
      <h2>${esc(charName(state.charKey))}</h2>
      <span class="badge">${t.confidence[c.confidence] || ""}</span>
      <p>${esc(tx(c.summary))}</p>
    </header>
    <div class="char-grid">
      ${section(t.secRelic, tierBlocks(c.relic_effects || [], effectItem))}
      ${section(t.secDeep, tierBlocks(c.deep_effects || [], effectItem))}
      ${section(t.secCurses, (curses.harmless?.length || curses.avoid?.length) ? `
        <h4 class="ok">${t.cursesOk}</h4><ul class="plain">${curseList(curses.harmless)}</ul>
        <h4 class="bad">${t.cursesAvoid}</h4><ul class="plain">${curseList(curses.avoid)}</ul>` : "")}
      ${section(t.secPassives, tierBlocks(c.weapon_passives || [], textItem("passive")))}
      ${section(t.secWeapons, tierBlocks(c.weapons || [], textItem("name")))}
    </div>
    ${section(t.secBuilds, builds)}
    ${section(t.general, (general.stacking || []).map((s) => `<p class="why">${esc(tx(s))}</p>`).join(""))}
    ${section(t.sources, sources && `<ul class="sources">${sources}</ul>`)}`;
}

$("#charPicker").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-char]");
  if (!btn) return;
  state.charKey = btn.dataset.char;
  save("charKey", state.charKey);
  renderCharacters();
});
