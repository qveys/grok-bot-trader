// pm-sonnette-cf — PROTOTYPE en OBSERVATION : refait les contrôles de la sonnette / du surveillant
// des arrêts (stop, objectif, zones, heure limite) hors de la box. Aucune sonnerie, aucun Telegram :
// chaque événement est journalisé (console + D1 obs_evenements) pour comparaison avec rings.jsonl.
const PAIRS = ["BTC-EUR", "ETH-EUR", "SOL-EUR"];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const n = (x) => (x == null || x === "" ? null : Number(x));

async function revxTickers() {
  const r = await fetch("https://revx.revolut.com/api/1.0/public/tickers?symbols=BTC/EUR,ETH/EUR,SOL/EUR&region=EEA",
    { headers: { accept: "application/json" } });
  if (!r.ok) throw new Error(`revx tickers ${r.status}`);
  const out = {};
  for (const t of (await r.json()).data || []) out[t.symbol.replace("/", "-")] = { mid: n(t.mid), last: n(t.last_price) };
  return out;
}
// bougies 1 min (bas/haut) depuis `since` : attrape les mèches entre deux contrôles
async function revxCandles(pair, since) {
  const r = await fetch(`https://revx.revolut.com/api/1.0/public/candles/${pair}?interval=1&since=${since}&region=EEA`);
  if (!r.ok) throw new Error(`revx candles ${pair} ${r.status}`);
  return ((await r.json()).data || []).map((c) => ({ t: c.start, lo: n(c.low), hi: n(c.high) }));
}
async function coinbaseTicker(pair) {
  const r = await fetch(`https://api.exchange.coinbase.com/products/${pair}/ticker`, { headers: { "user-agent": "pm-sonnette-cf/0" } });
  if (!r.ok) throw new Error(`coinbase ${pair} ${r.status}`);
  const j = await r.json();
  return { mid: (n(j.bid) + n(j.ask)) / 2, last: n(j.price) };
}

const isShort = (p) => ["short", "sell"].includes(String(p.side || "").toLowerCase()) || String(p.idea_type || "").toLowerCase() === "baisse";

// Pur : positions/zones + bas/haut par paire -> événements (même logique que watch_stops.gap_crossing)
export function evaluer(now, etat, marche) {
  const ev = [];
  const jour = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Brussels" }).format(new Date(now)); // AAAA-MM-JJ Bruxelles
  for (const p of etat.positions || []) {
    const m = marche[p.pair]; if (!m) continue;
    const stop = n(p.stop), tgt = n(p.target), s = isShort(p);
    const stopX = stop != null && (s ? m.hi >= stop : m.lo <= stop);
    const hitC = stopX ? (m.candles || []).find((c) => (s ? c.hi >= stop : c.lo <= stop)) : null;
    const tgtX = tgt != null && (s ? m.lo <= tgt : m.hi >= tgt);
    if (stopX) ev.push({ cle: `stop|${p.id}`, type: "stop_touche", bot: "risk", detail: { position_id: p.id, decision_id: p.decision_id, paire: p.pair, prix_stop: stop, bas: m.lo, haut: m.hi, minute_ms: hitC ? hitC.t : now, heure: new Date(hitC ? hitC.t : now).toISOString(), source: m.source, mode: p.mode,
      message_fr: `Arrêt touché ${p.decision_id || p.id} : ${p.pair} a atteint ${stop} € (${s ? "haut" : "bas"} ${s ? m.hi : m.lo} €). Fermer à ${stop} €.` } });
    else if (tgtX) ev.push({ cle: `objectif|${p.id}`, type: "objectif_touche", bot: "risk", detail: { position_id: p.id, paire: p.pair, prix_objectif: tgt, bas: m.lo, haut: m.hi, source: m.source } });
    if (p.deadline && now >= Date.parse(p.deadline)) ev.push({ cle: `heure_limite|${p.id}|${p.deadline}`, type: "heure_limite", bot: "predict", detail: { position_id: p.id, paire: p.pair, deadline: p.deadline } });
  }
  for (const z of etat.zones || []) {
    if (z.actif === false || (z.expire && now > Date.parse(z.expire))) continue;
    const m = marche[z.paire]; if (!m) continue;
    const prix = n(z.prix);
    const touche = String(z.sens) === "sous" ? m.lo <= prix : m.hi >= prix;
    if (touche) ev.push({ cle: `zone|${z.id}|${jour}`, type: "zone_touchee", bot: z.bot || "predict", detail: { zone_id: z.id, paire: z.paire, prix, sens: z.sens, bas: m.lo, haut: m.hi, source: m.source } });
  }
  return ev;
}

async function contrôle(env, now) {
  const row = await env.DB.prepare("SELECT recu_ms, etat FROM obs_etat WHERE id = 1").first();
  if (!row) { console.log("[observation] pas encore d'état reçu de la box"); return { note: "pas d'état" }; }
  const etat = JSON.parse(row.etat);
  const cur = await env.DB.prepare("SELECT valeur FROM obs_curseur WHERE cle = 'dernier_ms'").first();
  const since = cur ? Math.max(Number(cur.valeur), now - 6 * 3600e3) : now - 120e3; // 1er passage : 2 min seulement
  const marche = {}; const erreurs = [];
  let tick = {};
  try { tick = await revxTickers(); } catch (e) { erreurs.push(String(e)); }
  const besoin = new Set([...(etat.positions || []).map((p) => p.pair), ...(etat.zones || []).filter((z) => z.actif !== false).map((z) => z.paire)]);
  for (const pair of PAIRS.filter((p) => besoin.has(p))) {
    let lo = tick[pair]?.mid ?? null, hi = lo, source = "revx ticker", candles = [];
    try {
      const cs = candles = (await revxCandles(pair, since - 60e3)).filter((c) => c.t + 60e3 > since);
      for (const c of cs) { if (lo == null || c.lo < lo) lo = c.lo; if (hi == null || c.hi > hi) hi = c.hi; }
      if (cs.length) source = `revx 1m x${cs.length}`;
      await sleep(1100); // limite revx : 1 requête bougies / s
    } catch (e) { erreurs.push(String(e)); }
    if (lo == null) { try { const c = await coinbaseTicker(pair); lo = hi = c.mid; source = "coinbase ticker"; } catch (e) { erreurs.push(String(e)); } }
    if (lo != null) marche[pair] = { lo, hi, source, candles };
  }
  const ev = evaluer(now, etat, marche);
  let nouveaux = 0;
  for (const e of ev) {
    const r = await env.DB.prepare("INSERT OR IGNORE INTO obs_evenements (cle, ts_ms, type, detail) VALUES (?, ?, ?, ?)")
      .bind(e.cle, now, e.type, JSON.stringify({ bot: e.bot, ...e.detail })).run();
    if (r.meta.changes) { nouveaux++; console.log(`[observation] AURAIT SONNÉ ${e.bot} — ${e.type} ${JSON.stringify(e.detail)}`); }
  }
  await env.DB.prepare("INSERT INTO obs_curseur (cle, valeur) VALUES ('dernier_ms', ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur").bind(String(now)).run();
  await env.DB.prepare("DELETE FROM obs_evenements WHERE ts_ms < ?").bind(now - 14 * 86400e3).run();
  const age_etat_s = Math.round((now - row.recu_ms) / 1000);
  console.log(`[observation] contrôle : ${Object.keys(marche).length} paire(s), ${nouveaux} nouvel(s) événement(s), état box âgé de ${age_etat_s} s${erreurs.length ? ", erreurs: " + erreurs.join("; ") : ""}`);
  return { marche, evenements: ev, nouveaux, erreurs, age_etat_s };
}

function autorise(req, env) {
  const want = `Bearer ${env.BATTEMENT_SECRET || ""}`, h = req.headers.get("authorization") || "";
  if (!env.BATTEMENT_SECRET || h.length !== want.length) return false;
  let d = 0; for (let i = 0; i < h.length; i++) d |= h.charCodeAt(i) ^ want.charCodeAt(i); return d === 0;
}
const json = (o, s = 200) => new Response(JSON.stringify(o, null, 1), { status: s, headers: { "content-type": "application/json; charset=utf-8" } });

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (u.pathname === "/") return new Response("sonnette-cf (observation) ok\n");
    if (!autorise(req, env)) return json({ ok: false }, 401);
    if (u.pathname === "/etat-bots" && req.method === "POST") {
      const t = await req.text(); if (t.length > 50000) return json({ ok: false, erreur: "trop gros" }, 413);
      const e = JSON.parse(t);
      await env.DB.prepare("INSERT INTO obs_etat (id, recu_ms, etat) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET recu_ms = excluded.recu_ms, etat = excluded.etat").bind(Date.now(), JSON.stringify(e)).run();
      return json({ ok: true, positions: (e.positions || []).length, zones: (e.zones || []).length });
    }
    if (u.pathname === "/obs" && req.method === "GET") {
      const ev = await env.DB.prepare("SELECT ts_ms, type, cle, detail FROM obs_evenements ORDER BY ts_ms DESC LIMIT 50").all();
      const et = await env.DB.prepare("SELECT recu_ms, etat FROM obs_etat WHERE id = 1").first();
      return json({ etat: et ? { recu_ms: et.recu_ms, ...JSON.parse(et.etat) } : null, evenements: ev.results });
    }
    if (u.pathname === "/controle" && req.method === "POST") return json(await contrôle(env, Date.now()));
    return json({ ok: false }, 404);
  },
  async scheduled(ev, env, ctx) { ctx.waitUntil(contrôle(env, ev.scheduledTime || Date.now())); },
};
