// pm-veilleur : veille externe de l'ordinateur (box) de Quentin.
// POST /battement (Bearer secret) -> D1 ; cron */5 -> alertes Telegram (ou logs si Telegram absent).
const PANNE_S = 600;           // 10 min sans battement = ordinateur figé
const RAPPEL_MS = 2 * 3600e3;  // rappel toutes les 2 h max
const GRACE_MS = 5 * 60e3;     // après une reprise, laisser 5 min aux bots avant de les juger
const COMPO_S = 600;           // sonnette / surveillant figés > 10 min

const MSG = {
  panne: (m) => `Mon ordinateur ne répond plus depuis ${m} min. Les bots sont à l'arrêt, les arrêts des simulations ne sont plus surveillés.`,
  reprise: (m) => `Mon ordinateur répond de nouveau (arrêt de ${m} min).`,
  sonnette: (m) => `La sonnette ne fonctionne plus depuis ${m} min. L'ordinateur marche, mais les prix ne sont plus surveillés.`,
  sonnetteOk: () => `La sonnette fonctionne de nouveau.`,
  risk: (m, n) => `Le surveillant des arrêts de Risk ne fonctionne plus depuis ${m} min, alors que ${n} simulation(s) sont ouvertes. Les arrêts ne sont plus surveillés.`,
  riskOk: () => `Le surveillant des arrêts de Risk fonctionne de nouveau.`,
};

const mins = (s) => Math.max(1, Math.round(s / 60));

// Décision pure : (now, battement, etat) -> { messages:[{type,text}], etat }
export function verifier(now, hb, etat) {
  const e = { ...etat };
  const out = [];
  if (!hb) return { messages: out, etat: e, note: "aucun battement reçu" };
  const ageS = (now - hb.recu_ms) / 1000;
  const p = hb.payload || {};
  if (ageS > PANNE_S) {
    if (!e.box_alerte_ms) {
      out.push({ type: "panne", text: MSG.panne(mins(ageS)) });
      e.box_alerte_ms = now; e.box_rappel_ms = now;
    } else if (now - (e.box_rappel_ms || 0) >= RAPPEL_MS) {
      out.push({ type: "rappel", text: MSG.panne(mins(ageS)) });
      e.box_rappel_ms = now;
    }
    return { messages: out, etat: e, age_s: ageS };
  }
  if (e.box_alerte_ms) { // reprise non signalée par /battement (filet de sécurité)
    out.push({ type: "reprise", text: MSG.reprise(mins((now - e.box_alerte_ms) / 1000 + PANNE_S)) });
    delete e.box_alerte_ms; delete e.box_rappel_ms; e.box_up_ms = now;
  }
  if (now - (e.box_up_ms || 0) < GRACE_MS) return { messages: out, etat: e, age_s: ageS, note: "grâce après reprise" };
  // âge réel = âge envoyé + temps depuis l'envoi
  const extra = ageS;
  const sAge = p.sonnette_age_s == null ? null : p.sonnette_age_s + extra;
  const sBad = p.sonnette_vivante === false || sAge == null || sAge > COMPO_S;
  if (sBad && !e.sonnette_alerte) {
    out.push({ type: "sonnette", text: MSG.sonnette(mins(sAge ?? COMPO_S)) }); e.sonnette_alerte = 1;
  } else if (!sBad && e.sonnette_alerte) {
    out.push({ type: "sonnette_ok", text: MSG.sonnetteOk() }); delete e.sonnette_alerte;
  }
  const n = (p.risk_ouvertes_live || 0) + (p.risk_ouvertes_paper || 0);
  const rAge = p.risk_age_s == null ? null : p.risk_age_s + extra;
  const rBad = n > 0 && (p.risk_vivant === false || rAge == null || rAge > COMPO_S);
  if (rBad && !e.risk_alerte) {
    out.push({ type: "risk", text: MSG.risk(mins(rAge ?? COMPO_S), n) }); e.risk_alerte = 1;
  } else if (!rBad && e.risk_alerte) {
    out.push({ type: "risk_ok", text: MSG.riskOk() }); delete e.risk_alerte;
  }
  return { messages: out, etat: e, age_s: ageS };
}

async function lireBattement(env) {
  const r = await env.DB.prepare("SELECT recu_ms, payload FROM battement WHERE id = 1").first();
  return r ? { recu_ms: r.recu_ms, payload: JSON.parse(r.payload) } : null;
}
async function lireEtat(env) {
  const r = await env.DB.prepare("SELECT valeur FROM etat WHERE cle = 'alertes'").first();
  return r ? JSON.parse(r.valeur) : {};
}
async function ecrireEtat(env, e) {
  await env.DB.prepare("INSERT INTO etat (cle, valeur) VALUES ('alertes', ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur")
    .bind(JSON.stringify(e)).run();
}

async function telegram(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) {
    console.log(`[veilleur] Telegram non configuré — message non envoyé : ${text}`);
    return false;
  }
  try {
    const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text, disable_web_page_preview: true }),
    });
    console.log(`[veilleur] Telegram ${r.status} : ${text}`);
    return r.ok;
  } catch (err) {
    console.log(`[veilleur] Telegram erreur ${err} : ${text}`);
    return false;
  }
}

async function envoyer(env, now, messages) {
  for (const m of messages) {
    const ok = await telegram(env, m.text);
    await env.DB.prepare("INSERT INTO journal (ts_ms, type, message, envoye) VALUES (?, ?, ?, ?)").bind(now, m.type, m.text, ok ? 1 : 0).run();
  }
  if (messages.length) await env.DB.prepare("DELETE FROM journal WHERE id < (SELECT MAX(id) - 500 FROM journal)").run();
}

function autorise(req, env) {
  const h = req.headers.get("authorization") || "";
  const s = env.BATTEMENT_SECRET || "";
  const want = `Bearer ${s}`;
  if (!s || h.length !== want.length) return false;
  let d = 0;
  for (let i = 0; i < h.length; i++) d |= h.charCodeAt(i) ^ want.charCodeAt(i);
  return d === 0;
}

const json = (o, status = 200) => new Response(JSON.stringify(o, null, 1), { status, headers: { "content-type": "application/json; charset=utf-8" } });

async function cron(env, now) {
  const [hb, etat] = await Promise.all([lireBattement(env), lireEtat(env)]);
  const res = verifier(now, hb, etat);
  console.log(`[veilleur] cron : âge battement ${res.age_s == null ? "?" : Math.round(res.age_s)} s, messages ${res.messages.length}${res.note ? ", " + res.note : ""}`);
  await envoyer(env, now, res.messages);
  if (JSON.stringify(res.etat) !== JSON.stringify(etat)) await ecrireEtat(env, res.etat);
  await env.DB.prepare("INSERT INTO etat (cle, valeur) VALUES ('dernier_cron', ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur")
    .bind(JSON.stringify({ ts_ms: now, age_s: res.age_s ?? null, messages: res.messages.map((m) => m.type), note: res.note || null })).run();
  return res;
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname === "/") return new Response("veilleur ok\n");
    if (!autorise(req, env)) return json({ ok: false, erreur: "non autorisé" }, 401);
    const now = Date.now();

    if (url.pathname === "/battement" && req.method === "POST") {
      const txt = await req.text();
      if (txt.length > 4000) return json({ ok: false, erreur: "trop gros" }, 413);
      let payload; try { payload = JSON.parse(txt || "{}"); } catch { return json({ ok: false, erreur: "json invalide" }, 400); }
      const [prev, etat] = await Promise.all([lireBattement(env), lireEtat(env)]);
      await env.DB.prepare("INSERT INTO battement (id, recu_ms, payload) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET recu_ms = excluded.recu_ms, payload = excluded.payload")
        .bind(now, JSON.stringify(payload)).run();
      const trou_s = prev ? (now - prev.recu_ms) / 1000 : 0;
      if (trou_s > PANNE_S || etat.box_alerte_ms) {
        const e = { ...etat, box_up_ms: now };
        const msgs = [];
        if (etat.box_alerte_ms) msgs.push({ type: "reprise", text: MSG.reprise(mins(trou_s)) });
        else console.log(`[veilleur] trou de ${Math.round(trou_s)} s sans alerte préalable (pas de message)`);
        delete e.box_alerte_ms; delete e.box_rappel_ms;
        await ecrireEtat(env, e);
        ctx.waitUntil(envoyer(env, now, msgs));
      }
      return json({ ok: true, recu_ms: now, trou_s: Math.round(trou_s) });
    }

    if (url.pathname === "/etat" && req.method === "GET") {
      const [hb, etat, dc, j] = await Promise.all([
        lireBattement(env), lireEtat(env),
        env.DB.prepare("SELECT valeur FROM etat WHERE cle = 'dernier_cron'").first(),
        env.DB.prepare("SELECT ts_ms, type, message, envoye FROM journal ORDER BY id DESC LIMIT 10").all(),
      ]);
      return json({ now, battement: hb, age_s: hb ? Math.round((now - hb.recu_ms) / 1000) : null, alertes: etat,
        dernier_cron: dc ? JSON.parse(dc.valeur) : null, journal: j.results,
        telegram_configure: !!(env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID) });
    }

    // Simulation sans effet : rien n'est écrit ni envoyé. Corps : {age_min, payload?, etat?}
    if (url.pathname === "/test-verif" && req.method === "POST") {
      const b = await req.json().catch(() => ({}));
      const hb = { recu_ms: now - (Number(b.age_min) || 0) * 60e3, payload: b.payload || (await lireBattement(env))?.payload || {} };
      const res = verifier(now, hb, b.etat || {});
      for (const m of res.messages) console.log(`[veilleur][TEST] alerte ${m.type} (non envoyée) : ${m.text}`);
      return json({ test: true, ...res });
    }

    if (url.pathname === "/test-telegram" && req.method === "POST") {
      const ok = await telegram(env, "Test : le veilleur de l’ordinateur est branché.");
      return json({ ok });
    }
    return json({ ok: false, erreur: "inconnu" }, 404);
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(cron(env, event.scheduledTime || Date.now()));
  },
};
