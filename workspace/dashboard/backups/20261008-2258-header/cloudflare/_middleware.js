// Protection par mot de passe (HTTP Basic Auth) de TOUT le site, y compris /data/*.json.
// Utilisateur : quentin — mot de passe : variable/secret Cloudflare DASHBOARD_PASSWORD (jamais dans le code).
// S'applique à toutes les URL du projet : production ET aperçus (<hash>.<projet>.pages.dev).
const USER = "quentin";
const REALM = "PM Pipeline - Tableau de bord";
const ROBOTS = "User-agent: *\nDisallow: /\n";

function baseHeaders(h) {
  h.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  h.set("Referrer-Policy", "no-referrer");
  h.set("X-Content-Type-Options", "nosniff");
  h.set("X-Frame-Options", "DENY");
  return h;
}

function unauthorized(msg) {
  const h = baseHeaders(new Headers({
    "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
  }));
  return new Response(msg || "Accès protégé : identifiant et mot de passe requis.", { status: 401, headers: h });
}

const enc = new TextEncoder();
async function sha256(s) { return new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(s))); }

// Comparaison à temps constant : on compare les empreintes SHA-256 (même longueur).
async function safeEqual(a, b) {
  const [ha, hb] = await Promise.all([sha256(a), sha256(b)]);
  if (crypto.subtle && typeof crypto.subtle.timingSafeEqual === "function") {
    return crypto.subtle.timingSafeEqual(ha, hb);
  }
  let diff = 0;
  for (let i = 0; i < ha.length; i++) diff |= ha[i] ^ hb[i];
  return diff === 0;
}

function decodeBasic(header) {
  if (!header) return null;
  const m = /^Basic\s+([A-Za-z0-9+/=]+)\s*$/i.exec(header);
  if (!m) return null;
  let raw;
  try {
    const bin = atob(m[1]);
    raw = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
  } catch (e) { return null; }
  const i = raw.indexOf(":");
  if (i < 0) return null;
  return { user: raw.slice(0, i), pass: raw.slice(i + 1) };
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);

  // Seule exception : robots.txt (ne contient que « Disallow: / », aucune donnée).
  if (url.pathname === "/robots.txt") {
    return new Response(ROBOTS, { headers: baseHeaders(new Headers({ "Content-Type": "text/plain; charset=utf-8" })) });
  }

  const expected = env.DASHBOARD_PASSWORD;
  if (!expected) {
    // Échec fermé : sans secret configuré, rien n'est servi.
    return new Response("Site non configuré (mot de passe absent).", {
      status: 503, headers: baseHeaders(new Headers({ "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" })),
    });
  }

  const cred = decodeBasic(request.headers.get("Authorization"));
  if (!cred) return unauthorized();
  const okUser = await safeEqual(cred.user, USER);
  const okPass = await safeEqual(cred.pass, expected);
  if (!(okUser & okPass)) return unauthorized("Identifiant ou mot de passe incorrect.");

  const res = await next();
  const out = new Response(res.body, res);
  baseHeaders(out.headers);
  // Données privées : pas de cache partagé ; les JSON sont toujours relus.
  if (url.pathname.startsWith("/data/")) out.headers.set("Cache-Control", "private, no-cache, max-age=0");
  else if (url.pathname.startsWith("/api/")) out.headers.set("Cache-Control", "private, no-store");
  else out.headers.set("Cache-Control", "private, max-age=0, must-revalidate");
  return out;
}
