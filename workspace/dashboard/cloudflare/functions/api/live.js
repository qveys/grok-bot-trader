// GET /api/live?f=summary,prices,... — mode « quasi direct ».
// La box pousse le paquet commun (prix du collecteur 30 s + données des bots = contenu de site/data/*.json),
// seulement quand il change. Source unique, aucune autre source de prix.
//  - D1 (binding LIVE_DB) : une ligne par fichier, poussée à chaque changement (≈ 30 s). Seule source (KV abandonné le 8 oct.).
// Protégée par le même mot de passe (functions/_middleware.js s'exécute avant).
// Sans binding : {available:false} → le navigateur lit les fichiers publiés data/*.json (secours).
const ALLOWED = new Set(["summary", "trades", "performance", "research", "news", "prices"]);
const H = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "private, no-store" };
const off = (reason, status) => new Response(JSON.stringify({ available: false, reason }), { status: status || 200, headers: H });

export async function onRequestGet({ request, env }) {
  const want = [...new Set((new URL(request.url).searchParams.get("f") || "").split(",").filter((x) => ALLOWED.has(x)))];
  if (!want.length) return off("no_files", 400);
  if (env.LIVE_DB) {
    try {
      const q = `SELECT name, pushed_at, body FROM live_files WHERE name IN (${want.map(() => "?").join(",")})`;
      const { results } = await env.LIVE_DB.prepare(q).bind(...want).all();
      if (results && results.length) {
        let pushed = "";
        const parts = results.map((r) => { if (r.pushed_at > pushed) pushed = r.pushed_at; return JSON.stringify(r.name) + ":" + r.body; });
        return new Response(`{"available":true,"store":"d1","pushed_at":${JSON.stringify(pushed)},"files":{${parts.join(",")}}}`, { headers: H });
      }
    } catch (e) { return off("d1_error"); }
    return off("empty");
  }
  return off("no_binding");
}
