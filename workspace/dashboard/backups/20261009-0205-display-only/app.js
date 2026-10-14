/* Équipe trading — Tableau de bord. JS sans dépendance (Chart.js seulement sur Performance). Aucun appel IA. */
(function () {
  "use strict";
  var TZ = "Europe/Brussels";
  var PAGE = document.body.getAttribute("data-page");
  var NAV = [["index", "Accueil"], ["trades", "Trades"], ["performance", "Performance"], ["research", "Analyses"], ["news", "Actualités"], ["about", "À propos"]];
  var STATE = { data: {}, ui: {}, deploy: null };
  var charts = {};

  // ------------------------------------------------------------ format
  // Texte lisible pour n'importe quelle valeur : un objet ou une liste ne s'affiche jamais « [object Object] ».
  function plain(v) {
    if (v == null) return "";
    if (Array.isArray(v)) return v.map(plain).filter(function (x) { return x !== ""; }).join(", ");
    if (typeof v === "object") return Object.keys(v).map(function (k) { var x = plain(v[k]); return x === "" ? "" : k.replace(/_/g, " ") + " : " + x; }).filter(function (x) { return x !== ""; }).join(" · ");
    return String(v);
  }
  function esc(s) { return s == null ? "" : plain(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function num(v, d) { if (v == null || isNaN(v)) return "—"; return Number(v).toLocaleString("fr-BE", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function eur(v, d, signed) {
    if (v == null || isNaN(v)) return "—";
    d = d == null ? 2 : d;
    var s = num(Math.abs(v), d) + " €";
    if (signed) return (v > 0 ? "+" : v < 0 ? "−" : "") + s;
    return (v < 0 ? "−" : "") + s;
  }
  function pct(v, d, signed) {
    if (v == null || isNaN(v)) return "—";
    d = d == null ? 2 : d;
    var s = num(Math.abs(v), d) + " %";
    if (signed) return (v > 0 ? "+" : v < 0 ? "−" : "") + s;
    return (v < 0 ? "−" : "") + s;
  }
  function price(v) { if (v == null) return "—"; var d = v >= 1000 ? 2 : v >= 1 ? 2 : 4; return num(v, d) + " €"; }
  function cls(v) { return v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : ""; }
  function d(iso) { return iso ? new Date(iso) : null; }
  function fmtTime(iso, withDate) {
    if (!iso) return "—";
    var o = { timeZone: TZ, hour: "2-digit", minute: "2-digit" };
    if (withDate !== false) { o.day = "2-digit"; o.month = "short"; }
    return new Intl.DateTimeFormat("fr-BE", o).format(new Date(iso)).replace(":", "h");
  }
  function fmtDay(iso) { return iso ? new Intl.DateTimeFormat("fr-BE", { timeZone: TZ, weekday: "short", day: "2-digit", month: "short" }).format(new Date(iso)) : "—"; }
  function ago(iso) {
    if (!iso) return "—";
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 0) { s = -s; return "dans " + dur(s); }
    if (s < 45) return "à l'instant";
    return "il y a " + dur(s);
  }
  function dur(s) {
    if (s < 60) return Math.round(s) + " s";
    var m = Math.round(s / 60); if (m < 60) return m + " min";
    var h = Math.floor(m / 60); if (h < 48) return h + " h" + (m % 60 && h < 10 ? " " + String(m % 60).padStart(2, "0") : "");
    return Math.round(h / 24) + " j";
  }
  // Couleurs : Achat violet, Vente jaune (pas vert/rouge, réservés au gain/perte) ; une couleur par monnaie.
  var CUR = { BTC: "#f7931a", ETH: "#60a5fa", SOL: "#2dd4bf", EUR: "#cbd5e1", USDC: "#93c5fd" };
  function curHtml(c) { c = String(c || ""); return '<span class="cur" style="color:' + (CUR[c.toUpperCase()] || "inherit") + '">' + esc(c) + "</span>"; }
  function pairHtml(p) { var a = String(p || "").split("-"); return a.length === 2 && /^[A-Z0-9]+$/.test(a[0]) ? '<span class="pair">' + curHtml(a[0]) + '<span class="pq">-</span>' + curHtml(a[1]) + "</span>" : esc(p); }
  // Prix court : 73 588 € · 2 263 € · 100,7 €
  function pxShort(v) { v = Number(v); if (isNaN(v)) return "—"; return num(v, v >= 1000 ? 0 : v >= 10 ? 1 : v >= 1 ? 2 : 4).replace(/,0$/, "") + " €"; }
  // Prix par paire écrits par un bot ({ "BTC-EUR": { prix, vs_ouverture_jour_pct }, source } ou { BTC: 73588 }) → « BTC 73 588 € · ETH 2 263 € »
  function prixHtml(o) {
    if (o == null || o === "") return "";
    if (typeof o !== "object" || Array.isArray(o)) return esc(o);
    var ORD = { BTC: 0, ETH: 1, SOL: 2 }, base = function (k) { return k.split("-")[0].toUpperCase(); };
    var ks = Object.keys(o).filter(function (k) { return /^[A-Za-z0-9]{2,10}(-[A-Za-z]{3,4})?$/.test(k) && !/^(source|sources|note|heure|time|at)$/i.test(k); })
      .sort(function (a, b) { var x = ORD[base(a)], y = ORD[base(b)]; return ((x != null ? x : 9) - (y != null ? y : 9)) || a.localeCompare(b); });
    var parts = ks.map(function (k) {
      var v = o[k], isO = v && typeof v === "object", pv = isO ? (v.prix != null ? v.prix : v.price != null ? v.price : v.mid) : v;
      var ch = isO ? (v.vs_ouverture_jour_pct != null ? v.vs_ouverture_jour_pct : v.change_24h_pct) : null;
      return '<span class="nowrap">' + curHtml(base(k)) + " " + (pv != null && !isNaN(Number(pv)) ? pxShort(pv) : esc(pv)) +
        (ch != null && !isNaN(Number(ch)) ? ' <span class="xs ' + cls(Number(ch)) + '" title="depuis l’ouverture du jour">' + pct(Number(ch), 1, true) + "</span>" : "") + "</span>";
    });
    return parts.length ? '<span title="' + esc(o.source || o.sources || "") + '">' + parts.join(" · ") + "</span>" : esc(o);
  }
  function sideBadge(side, pending) { return side === "achat" ? '<span class="badge b-buy">' + (pending ? "Achat prévu" : "Achat") + "</span>" : '<span class="badge b-sell">Vente</span>'; }
  function badgeMode(m) { return m === "reel" ? '<span class="badge b-real">Réel</span>' : '<span class="badge b-sim">argent fictif</span>'; }
  function el(id) { return document.getElementById(id); }

  // ------------------------------------------------------------ Brussels time helpers
  function bxParts(date) {
    var f = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "short", hour12: false });
    var o = {}; f.formatToParts(date).forEach(function (p) { o[p.type] = p.value; });
    return { y: +o.year, m: +o.month, d: +o.day, h: +o.hour % 24, mi: +o.minute, s: +o.second, wd: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(o.weekday) };
  }
  function bxOffsetMs(date) { var p = bxParts(date); return Date.UTC(p.y, p.m - 1, p.d, p.h, p.mi, p.s) - Math.floor(date.getTime() / 1000) * 1000; }
  function bxDate(y, m, dd, h, mi) { var guess = new Date(Date.UTC(y, m - 1, dd, h, mi)); return new Date(guess.getTime() - bxOffsetMs(guess)); }
  // Occurrences de créneaux "HH:MM" autour de maintenant (jours ouvrés si demandé)
  function slotWindow(slots, weekdays) {
    if (!slots || !slots.length) return null;
    var now = new Date(), occ = [];
    for (var k = -4; k <= 5; k++) {
      var base = new Date(now.getTime() + k * 86400000), p = bxParts(base);
      if (weekdays && (p.wd === 0 || p.wd === 6)) continue;
      slots.forEach(function (s) { var hm = s.split(":"); occ.push(bxDate(p.y, p.m, p.d, +hm[0], +hm[1])); });
    }
    occ.sort(function (a, b) { return a - b; });
    var prev = null, next = null;
    for (var i = 0; i < occ.length; i++) { if (occ[i] <= now) prev = occ[i]; else { next = occ[i]; break; } }
    return { prev: prev, next: next, progress: prev && next ? (now - prev) / (next - prev) : null };
  }

  // ------------------------------------------------------------ data
  function load(name) {
    return fetch("data/" + name + ".json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  var PAGE_DATA = { index: ["summary"], trades: ["trades", "summary"], performance: ["performance", "summary"], research: ["research", "summary"], news: ["news", "summary"], about: ["summary"] };

  // Source unique « quasi direct » : /api/live (Pages Function) lit dans Cloudflare D1 le paquet poussé par la box
  // (prix du collecteur 30 s + toutes les données des bots). Si D1 n'est pas branché (ou en local), on lit les
  // fichiers publiés data/*.json. On réessaie /api/live toutes les 5 min.
  STATE.api = null; STATE.apiRetry = 0;
  function loadMany(names) {
    if (STATE.api !== false || Date.now() > STATE.apiRetry) {
      return fetch("api/live?f=" + names.join(",") + "&t=" + Date.now(), { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      }).then(function (j) {
        if (!j || !j.available || !j.files) throw new Error("off");
        var out = names.map(function (n) { if (!j.files[n]) throw new Error("manque " + n); return j.files[n]; });
        STATE.api = true; STATE.apiPushedAt = j.pushed_at || null; STATE.apiStore = j.store || null;
        return out;
      }).catch(function () {
        STATE.api = false; STATE.apiRetry = Date.now() + 300000;
        return Promise.all(names.map(load));
      });
    }
    return Promise.all(names.map(load));
  }
  function sig(o) { return o ? (o.generated_at || "") + "|" + (o.deployed_at || "") : ""; }
  function refresh() {
    var names = (PAGE_DATA[PAGE] || ["summary"]).slice();
    var withPrices = STATE.api !== false;          // avec D1, les prix viennent dans le même paquet
    if (withPrices) names.push("prices");
    return loadMany(names).then(function (res) {
      var changed = !STATE.rendered;
      names.forEach(function (n, i) {
        if (n !== "prices" && sig(STATE.data[n]) !== sig(res[i])) changed = true;
        STATE.data[n] = res[i];
      });
      if (changed) { STATE.rendered = true; renderHeader(); renderPage(); renderFooter(); }
      else { renderPriceBar(); if (PAGE === "performance" && STATE.ui.pairLive) STATE.ui.pairLive(); if (PAGE === "research") renderZones(); }
    }).catch(function (e) {
      if (!STATE.data.summary) el("app").innerHTML = '<div class="notice warn">Impossible de lire les données (' + esc(e.message) + '). Le générateur build.py a-t-il tourné ?</div>';
    });
  }

  // ------------------------------------------------------------ header / footer
  function renderHeader() {
    var s = STATE.data.summary || {};
    var open = el("nav") && el("nav").classList.contains("open");
    el("hdr").innerHTML =
      '<div class="hdr"><div class="brandbox"><a class="brand" href="index.html"><b>Équipe trading</b><span>TABLEAU DE BORD · ' + esc((s.mode_fr || "").toUpperCase()) + '</span></a>' +
      '<button type="button" class="fresh" id="fresh" aria-expanded="false" aria-controls="freshpop"></button><div class="fresh-pop" id="freshpop" hidden></div></div>' +
      '<button class="nav-toggle" id="navbtn" aria-label="Menu" aria-expanded="' + (open ? "true" : "false") + '">☰</button>' +
      '<nav class="nav' + (open ? " open" : "") + '" id="nav">' + NAV.map(function (n) { return '<a href="' + n[0] + '.html"' + (n[0] === PAGE ? ' class="active"' : "") + ">" + n[1] + "</a>"; }).join("") + "</nav></div>" +
      '<div class="pricebar" id="pricebar"></div>';
    el("navbtn").onclick = function () { var n = el("nav"); n.classList.toggle("open"); this.setAttribute("aria-expanded", n.classList.contains("open")); };
    el("fresh").onclick = function (e) { e.stopPropagation(); STATE.ui.freshOpen = !STATE.ui.freshOpen; renderFresh(); };   // détail au toucher (mobile)
    renderPriceBar();
  }
  // Prix : data/prices.json (ticks 30 s du collecteur), relu toutes les 30 s. L'âge affiché vient du dernier tick.
  function livePrices() {
    var lp = STATE.data.prices, s = STATE.data.summary || {};
    if (lp && lp.pairs) return lp;
    var out = { pairs: {}, last_tick_at: (s.price_source || {}).at };
    Object.keys(s.prices || {}).forEach(function (k) { out.pairs[k] = { mid: s.prices[k].mid, change_24h_pct: s.prices[k].change_24h_pct, ts: s.prices[k].tick_ts }; });
    return out;
  }
  function staleLimit() { return 120; }
  function tickAge(lp) { return lp && lp.last_tick_at ? (Date.now() - new Date(lp.last_tick_at).getTime()) / 1000 : null; }
  function renderPriceBar() {
    var pbEl = el("pricebar"); if (!pbEl) return;
    var lp = livePrices();
    var pb = ["BTC-EUR", "ETH-EUR", "SOL-EUR"].map(function (k) {
      var p = lp.pairs[k]; if (!p) return "";
      return '<span class="pp">' + curHtml(k.split("-")[0]) + " <b>" + price(p.mid) + "</b> " + (p.change_24h_pct != null ? '<span class="' + cls(p.change_24h_pct) + '" title="variation 24 h (' + esc(p.change_source || "") + ')">' + pct(p.change_24h_pct, 1, true) + "</span>" : "") + "</span>";
    }).join("");
    pbEl.innerHTML = '<span class="pp muted">Prix EUR · 24 h</span>' + (pb || '<span class="pp">Prix indisponibles</span>');
    renderFresh();
  }
  // Fraîcheur (en-tête, sous « TABLEAU DE BORD ») : point + « à jour il y a 30 s », une seule ligne.
  // Âge affiché = envoi direct (/api/live pushed_at) ; sans envoi direct : le plus récent entre prix et page (ou publication).
  // Point : vert < 2 min, orange 2–10 min, rouge > 10 min (au moins orange si les prix sont anciens).
  // Détail (prix / page / direct) : infobulle (title) au survol, petit panneau au toucher.
  function ageTxt(sec) { if (sec == null) return "—"; if (sec < 0) sec = 0; return "il y a " + (sec < 90 ? Math.round(sec) + " s" : dur(sec)); }
  function isoAge(iso) { return iso ? (Date.now() - new Date(iso).getTime()) / 1000 : null; }
  function renderFresh() {
    var fe = el("fresh"), pop = el("freshpop"); if (!fe) return;
    var s = STATE.data.summary || {}, lp = livePrices(), pa = tickAge(lp), ga = isoAge(s.generated_at);
    var da = STATE.api ? isoAge(STATE.apiPushedAt) : null, ha = !STATE.api && hosted() ? isoAge(STATE.deploy.deployed_at) : null;
    var age = da != null ? da : [pa, ga, ha].filter(function (x) { return x != null; }).sort(function (x, y) { return x - y; })[0];
    var pxOld = pa == null || pa > staleLimit();
    var lvl = age == null || age > 600 ? "bad" : age > 120 || pxOld ? "mid" : "ok";
    var lines = ["Prix " + (pa != null ? ageTxt(pa) + (pxOld ? " (anciens)" : "") : "indisponibles"), "Page " + ageTxt(ga)];
    if (STATE.api) lines.push("Direct " + ageTxt(da));
    else if (hosted()) lines.push("Publié " + ageTxt(ha));
    lines.push("Relu toutes les 30 s");
    var html = '<span class="dot ' + lvl + '"></span>à jour ' + (age != null ? ageTxt(age) : "?");
    if (fe.getAttribute("data-h") !== html) { fe.innerHTML = html; fe.setAttribute("data-h", html); }
    fe.title = lines.join(" · ");
    fe.setAttribute("aria-label", "Données " + fe.textContent + ". " + lines.join(", "));
    var open = !!STATE.ui.freshOpen;
    fe.setAttribute("aria-expanded", open ? "true" : "false");
    if (pop) { pop.hidden = !open; if (open) pop.innerHTML = lines.map(esc).join("<br>"); }
  }
  document.addEventListener("click", function () { if (STATE.ui.freshOpen) { STATE.ui.freshOpen = false; renderFresh(); } });
  // Version en ligne (Cloudflare Pages) : data/deploy.json n'existe que dans la copie publiée.
  // Les données n'y changent qu'à chaque publication (~toutes les 15 min), on le dit clairement.
  function hosted() { return !!(STATE.deploy && STATE.deploy.deployed_at); }
  function renderFooter() {
    el("ftr").innerHTML = "<span>Équipe trading · tableau de bord personnel de Quentin · heures de Bruxelles</span><span>Simulation ≠ argent réel. Ce n'est pas un conseil financier.</span>";
  }

  // ------------------------------------------------------------ shared blocks
  function statCard(label, value, extra, c) { return '<div class="card"><div class="label">' + label + '</div><div class="mid ' + (c || "") + '">' + value + "</div>" + (extra ? '<div class="xs muted">' + extra + "</div>" : "") + "</div>"; }
  function secHead(t, sub) { return '<div class="sec-head"><h2>' + t + "</h2>" + (sub ? '<span class="sub">' + sub + "</span>" : "") + "</div>"; }

  // ------------------------------------------------------------ onglets (mémorisés dans l'adresse : page.html#onglet)
  function getTab(valid, def) { var h = decodeURIComponent((location.hash || "").replace(/^#/, "")); return valid.indexOf(h) >= 0 ? h : def; }   // ancre inconnue (ex. #cycles) → onglet par défaut
  function tabsBar(tabs, cur) {
    return '<div class="tabs" role="tablist">' + tabs.map(function (t) {
      return '<button class="tab' + (t[0] === cur ? " on" : "") + '" role="tab" aria-selected="' + (t[0] === cur) + '" data-tab="' + t[0] + '">' + t[1] + "</button>";
    }).join("") + "</div>";
  }
  function bindTabs(render) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-tab]"), function (b) {
      b.onclick = function () {
        var t = b.getAttribute("data-tab");
        if (history.replaceState) history.replaceState(null, "", "#" + t); else location.hash = t;
        render();
      };
    });
  }
  function chipsBar(items, cur, attr) {
    return '<div class="chips" style="margin-bottom:12px">' + items.map(function (c) {
      return '<button class="chip' + (c[0] === cur ? " on" : "") + '" data-' + attr + '="' + c[0] + '">' + c[1] + (c[2] != null ? ' <span class="n">' + c[2] + "</span>" : "") + "</button>";
    }).join("") + "</div>";
  }
  function bindChips(attr, key, render) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-" + attr + "]"), function (b) { b.onclick = function () { STATE.ui[key] = b.getAttribute("data-" + attr); render(); }; });
  }
  function coinQty(v) { return v == null ? "—" : Math.abs(v) < 1e-12 ? "0" : num(v, Math.abs(v) >= 1 ? 4 : 6); }
  function signedCoin(v, coin) { return v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + coinQty(Math.abs(v)) + (coin ? " " + esc(coin) : ""); }

  // ------------------------------------------------------------ ACCUEIL
  var HOME_TABS = [["apercu", "Vue d’ensemble"], ["reel", "Argent réel"], ["journal", "Journal des cycles"], ["sonnette", "Sonnette"]];
  function renderHome() {
    var s = STATE.data.summary, ru = s.rules, tab = getTab(HOME_TABS.map(function (x) { return x[0]; }), "apercu");
    var h = '<div class="topline">' +
      '<span class="badge ' + (ru.stop_file || ru.halted_file ? "b-err" : "b-ok") + '">Arrêt d\'urgence : ' + (ru.stop_file ? "OUI" : ru.halted_file ? "BLOQUÉ" : "non") + "</span>" +
      '<span class="badge ' + (ru.live_today >= ru.max_live_per_day ? "b-warn" : "b-mute") + '">Achats réels aujourd\'hui : ' + ru.live_today + " / " + ru.max_live_per_day + "</span>" +
      '<span class="badge b-mute">Achat réel préparé : ' + (ru.live_once_armed ? "oui" : "non") + "</span></div>";
    h += tabsBar(HOME_TABS, tab);
    if (tab === "apercu") h += homeOverview(s);
    else if (tab === "reel") h += homeReal(s);
    else if (tab === "journal") h += homeJournal(s);
    else h += sonnetteCard(s.sonnette);
    el("app").innerHTML = h;
    bindTabs(renderHome);
    if (tab === "journal") { renderRuns(); renderLog(); }
    if (tab === "apercu" && location.hash === "#cycles" && el("cycles")) el("cycles").scrollIntoView();
  }

  // Position ouverte : sens lu dans o.side (build.py pos_side, source unique). Vente = idée à la baisse, rachat prévu.
  function openPosHtml(o) {
    var v = o.side === "vente";
    return '<div class="openpos" data-side="' + esc(o.side) + '">' + pairHtml(o.pair) + " " + sideBadge(o.side) + " " + price(o.entry_price) +
      (o.target_price ? " · " + (v ? "rachat prévu " : "objectif ") + price(o.target_price) : (v ? " · rachat prévu" : "")) +
      " · stop " + price(o.stop_price) + (o.unrealized_eur != null ? ' · <span class="' + cls(o.unrealized_eur) + '">' + eur(o.unrealized_eur, 2, true) + "</span>" : "") +
      '<div class="xs muted">' + (v ? "Idée à la baisse" : "Idée à la hausse") + (o.decision_id ? " · " + esc(o.decision_id) : "") + " · simulation</div></div>";
  }
  // Rapprochement : départ + trades fermés + positions ouvertes − frais d'ouverture = solde affiché (écart visible sinon).
  function sg(v) { v = v || 0; return ' <span class="nw">' + (v < 0 ? "− " : "+ ") + eur(Math.abs(v)) + "</span>"; }
  function reconHtml(p) {
    var r = p.reconciliation; if (!r) return "";
    var gap = Math.abs(r.gap_eur || 0) > 0.01;
    return '<div class="xs mono recon' + (gap ? " warn" : " muted") + '" style="margin-top:8px">Départ <span class="nw">' + eur(r.start_eur) + "</span>" + sg(r.realized_eur) + " trades fermés" + sg(r.unrealized_eur) + " positions ouvertes" + sg(-(r.open_fees_eur || 0)) + " frais d’ouverture = " + '<span class="nw">' + eur(r.explained_eur) + "</span>" +
      (gap ? " · écart " + eur(r.gap_eur, 2, true) + " avec le solde affiché" : " ✓") + "</div>";
  }
  function homeOverview(s) {
    var p = s.paper, ru = s.rules;
    var h = '<section class="section">' + secHead("Portefeuille", "simulation et argent réel sont séparés") + '<div class="grid g2">';
    h += '<div class="card"><div class="card-title"><h3>Simulation</h3><span class="badge b-sim">Argent fictif</span></div>' +
      '<div class="flow"><div><div class="label">Départ</div><div class="mid text2">' + eur(p.invested_eur) + '</div></div><div class="arrow">→</div>' +
      '<div><div class="label">Solde</div><div class="big">' + eur(p.balance_eur) + "</div></div></div>" +
      '<div style="margin:6px 0 2px" class="label">Gain / perte total</div><div class="mid ' + cls(p.total_return_eur) + '">' + eur(p.total_return_eur, 2, true) + " (" + pct(p.total_return_pct, 2, true) + ")</div>" +
      '<hr class="sep"><div class="kv k3">' + kv("Liquidités", eur(p.cash_eur)) + kv("Engagé", eur(p.in_positions_eur)) + kv("Positions ouvertes", p.open_positions) + "</div>" + reconHtml(p) +
      '<div style="margin-top:14px"><div class="flow small text2" style="justify-content:space-between"><span>Capital utilisé</span><span class="mono">' + pct(p.deployed_pct, 1) + " / plafond " + pct(p.cap_pct, 0) + "</span></div>" +
      '<div class="bar"><i style="width:' + Math.min(100, p.cap_pct ? p.deployed_pct / p.cap_pct * 100 : 0) + '%"></i></div></div>' +
      (p.open_list.length ? '<div class="small" style="margin-top:10px">' + p.open_list.map(openPosHtml).join("") + "</div>" : "") +
      '<div class="xs muted" style="margin-top:10px">Dernier mouvement ' + fmtTime(p.updated_at) + " · baisse depuis le sommet " + pct(p.drawdown_pct, 2) + "</div>" +
      '<div class="links"><a href="performance.html#simulation">Résultats des trades simulés →</a></div></div>';
    h += realOverviewCard(s);
    h += "</div></section>";
    h += homeCycles(s);
    h += '<p class="xs muted">Règles de l’équipe (simulation et réel) : page <a href="about.html#regles">À propos</a>.</p>';
    return h;
  }

  function realOverviewCard(s) {
    var r = s.real || {}, le = s.live_equity || {}, mm = r.metamask || {};
    if (r.hidden) return '<div class="card"><div class="card-title"><h3>Argent réel</h3><span class="badge b-real">Réel</span></div><div class="notice">Soldes réels masqués (SHOW_REAL=false).</div></div>';
    var parts = [["Géré par le bot", le.present ? le.capital_reel : null, "#e2e8f0"], ["Pièces de Quentin sur Revolut X (hors bot)", le.present ? le.hors_bot_eur : null, "#94a3b8"], ["MetaMask", mm.value_eur, "#475569"]];
    var known = parts.reduce(function (a, x) { return a + (x[1] || 0); }, 0), tot = r.total_eur || 0, rest = tot - known;
    if (Math.abs(rest) >= 0.5) parts.push(["Autres / écarts de prix", rest, "#64748b"]);
    var h = '<div class="card"><div class="card-title"><h3>Argent réel</h3><span class="badge b-real">Réel · lecture seule</span></div>' +
      '<div class="label">Total estimé aujourd’hui</div><div class="big">' + eur(r.total_eur) + '</div><div class="xs muted">Revolut X + MetaMask, au dernier prix connu</div>' +
      '<div class="stack" style="margin-top:12px">' + parts.map(function (x) { return x[1] > 0 && tot > 0 ? '<i style="width:' + (x[1] / tot * 100) + "%;background:" + x[2] + '" title="' + esc(x[0]) + '"></i>' : ""; }).join("") + "</div>" +
      '<div class="legend">' + parts.map(function (x) { return '<div class="flow small" style="justify-content:space-between"><span><span class="sw" style="background:' + x[2] + '"></span>' + esc(x[0]) + '</span><span class="mono">' + eur(x[1]) + "</span></div>"; }).join("") + "</div>";
    if (le.present) {
      h += '<hr class="sep"><div class="flow" style="justify-content:space-between;margin-bottom:6px"><b>Capital du bot</b>' + (le.stale ? '<span class="badge b-warn">pas à jour</span>' : '<span class="xs muted">calculé ' + ago(le.ts) + "</span>") + "</div>" +
        '<div class="kv">' + kv("Perte du jour", '<span class="' + cls(-(le.perte_jour_pct || 0)) + '">' + pct(le.perte_jour_pct, 2) + "</span>") +
        kv("Baisse depuis le plus haut", le.baisse_depuis_plus_haut_pct == null ? "— <span class='xs muted'>(pas encore de plus haut)</span>" : pct(le.baisse_depuis_plus_haut_pct, 2)) +
        "</div>";
    } else h += '<hr class="sep"><p class="xs muted">Capital du bot : pas encore de fichier state/live_equity.json.</p>';
    h += '<div class="links"><a href="#reel">Pièces et ce qu’on peut vendre →</a><a href="performance.html#reel">Résultats des trades réels →</a></div></div>';
    return h;
  }

  function homeReal(s) {
    var r = s.real || {};
    if (r.hidden) return '<div class="notice">Soldes réels masqués (SHOW_REAL=false).</div>';
    var sl = s.sellable || {}, le = s.live_equity || {}, rv = r.revolut || {}, mm = r.metamask || {};
    var eurRow = (rv.assets || []).filter(function (a) { return a.currency === "EUR"; })[0];
    // Une ligne par pièce trouvée dans les soldes (Revolut X + MetaMask), même les petits montants ; triées par valeur.
    var rows = (sl.rows || []).slice().sort(function (a, b) { return ((b.total || 0) * (b.price_eur || 0)) - ((a.total || 0) * (a.price_eur || 0)); });
    var h = '<section class="section">' + secHead("Nos pièces", "Revolut X + MetaMask · « disponible » = vendable tout de suite") +
      '<div class="table-wrap"><table class="rtable"><thead><tr><th>Où</th><th>Pièce</th><th class="num">Total</th><th class="num">Disponible à vendre</th><th class="num">Bloqué (staking)</th><th class="num">Valeur</th></tr></thead><tbody>';
    if (eurRow) h += '<tr><td data-label="Où" class="small">Revolut X</td><td data-label="Pièce" class="mono">' + curHtml("EUR") + '</td><td data-label="Total" class="num">' + eur(eurRow.qty) + '</td><td data-label="Disponible à vendre" class="num">' + eur(eurRow.available) +
      (eurRow.reserved ? '<div class="xs muted">dont ' + eur(eurRow.reserved) + " dans un ordre</div>" : "") + '</td><td data-label="Bloqué (staking)" class="num">0</td><td data-label="Valeur" class="num">' + eur(eurRow.value_eur) + '<div class="xs muted">euros, pour acheter</div></td></tr>';
    h += rows.map(function (x) {
      return '<tr><td data-label="Où" class="small">' + esc(x.where) + (x.note ? '<div class="xs muted">' + esc(x.note) + "</div>" : "") + '</td><td data-label="Pièce" class="mono">' + curHtml(x.currency) +
        '</td><td data-label="Total" class="num">' + coinQty(x.total) + '</td><td data-label="Disponible à vendre" class="num">' + coinQty(x.available) + '<div class="xs muted">' + eur(x.available_eur) + "</div>" + (x.dust ? '<div><span class="badge b-mute" title="Montant sous le minimum de vente de Revolut X (≈ 1 €) : pas vendable pour l’instant">trop peu pour vendre</span></div>' : "") + (x.reserved_orders ? '<div class="xs muted">dont ' + coinQty(x.reserved_orders) + " dans un ordre</div>" : "") +
        '</td><td data-label="Bloqué (staking)" class="num">' + (x.blocked_staking ? coinQty(x.blocked_staking) + '<div class="xs muted">' + eur(x.blocked_eur) + "</div>" : "0") +
        '</td><td data-label="Valeur" class="num">' + eur(x.total != null && x.price_eur ? x.total * x.price_eur : null) + '<div class="xs muted">à ' + price(x.price_eur) + "</div></td></tr>";
    }).join("") + "</tbody></table></div>";
    h += '<div class="card flat" style="margin-top:10px"><div class="kv k3">' + kv("Pièces disponibles à vendre", eur(sl.total_available_eur)) + kv("Bloqué en staking", eur(sl.total_blocked_eur)) + kv("Lu", ago(sl.fetched_at) + (sl.stale ? ' <span class="warn">(ancien)</span>' : "")) + "</div></div></section>";
    h += '<section class="section"><div class="grid g2">';
    if (le.present) {
      var bp = le.bot_positions || {}, bk = Object.keys(bp);
      h += '<div class="card"><div class="card-title"><h3>Capital du bot — détail</h3><span class="badge b-real">Réel</span></div>' +
        '<p class="xs muted" style="margin-top:0">De quoi est fait le capital du bot (total sur la vue d’ensemble).</p><div class="kv k3">' + kv("Euros disponibles", eur(le.eur_available)) + kv("Euros dans un ordre", eur(le.eur_reserved)) + kv("Pièces achetées par le bot", eur(le.bot_positions_value)) + "</div>" +
        (bk.length ? '<div class="small mono" style="margin-top:8px">' + bk.map(function (k) { return "<div>" + curHtml(k) + " " + coinQty(bp[k].qty) + (bp[k].eur != null ? ' <span class="muted">· ' + eur(bp[k].eur) + "</span>" : "") + "</div>"; }).join("") + "</div>" : "") +
        '<p class="xs muted" style="margin-bottom:0">Référence du jour : ' + (le.ref_jour ? eur(le.ref_jour.valeur) : "—") + ". Les pièces que Quentin avait déjà (photo prise " + (le.hors_bot_depuis ? fmtTime(le.hors_bot_depuis) : "au premier lancement") + ") ne sont pas gérées par le bot. Source : state/live_equity.json, calculé " + ago(le.ts) + ".</p></div>";
    }
    var f = r.flows || {}, rw = f.rewards || {};
    h += '<div class="card"><div class="card-title"><h3>Origine des avoirs</h3><span class="xs muted">depuis le ' + fmtDay(r.project_start) + "</span></div>" +
      '<p class="xs muted" style="margin-top:0">Ce que le compte contenait au début du projet (achats d’avant, staking…). Ce ne sont pas des trades.</p>' +
      ((r.start_holdings || []).length ? '<div class="table-wrap"><table class="mini"><tbody>' + r.start_holdings.map(function (a) { return "<tr><td class='mono'>" + curHtml(a.currency) + "</td><td class='num'>" + num(a.qty, a.currency === "EUR" ? 2 : 6) + "</td><td class='num'>" + eur(a.value_now_eur) + "<div class='xs muted'>valeur actuelle</div></td></tr>"; }).join("") + "</tbody></table></div>" : '<p class="empty">—</p>') +
      '<p class="xs">Mouvements depuis : dépôts ' + eur(f.deposits_eur || 0) + " · retraits " + eur(f.withdrawals_eur || 0) + (Object.keys(rw).length ? " · récompenses de staking " + Object.keys(rw).map(function (k) { return num(rw[k], 8) + " " + esc(k); }).join(", ") : "") + "</p>" +
      (mm.address ? '<p class="xs muted" style="margin-bottom:0">MetaMask (Arbitrum) : <span class="break mono">' + esc(mm.address) + "</span> · " + esc((r.metamask_trades || {}).text || "suivi des trades MetaMask : pas encore") + "</p>" : "") +
      ((r.errors || []).concat(r.history_errors || []).length ? '<p class="xs warn">' + esc((r.errors || []).concat(r.history_errors || []).join(" / ")) + "</p>" : "") + "</div>";
    h += "</div></section>";
    return h;
  }

  function homeCycles(s) {
    return '<section class="section">' + secHead("Cycles automatiques", '<span class="dot ok"></span>' + esc(s.status_line)) + '<div class="grid g3" id="cycles">' + s.cycles.map(cycleCard).join("") + "</div>" +
      '<p class="xs muted">Compte à rebours jusqu’au prochain passage, calculé dans votre navigateur à partir des horaires des routines (heure de Bruxelles). « ≈ » : horaire approximatif ; « – – : – – » : pas d’horaire fixe (sur demande). Le détail de chaque passage est dans l’onglet <a href="#journal">Journal des cycles</a>.</p></section>';
  }
  function homeJournal(s) {
    return '<section class="section" id="routines">' + secHead("Passages des routines", "chaque routine note son début et sa fin") + '<div id="rrun"></div></section>' +
      '<section class="section">' + secHead("Journal des cycles", "derniers passages (fichiers et journaux de l'équipe)") + '<div id="logf" class="chips" style="margin-bottom:12px"></div><div id="logt"></div></section>';
  }
  // Passages des routines (state/routine_runs.jsonl) : chaque « demarre » est apparié au « fini » / « arret »
  // suivant du même bot + même routine. Sans fin : « En cours » si début < 30 min, sinon « Pas fini ».
  var RUN_OPEN_MAX_MS = 30 * 60000;
  function routinePassages(events) {
    var open = {}, out = [];
    (events || []).forEach(function (e) {
      var k = e.bot + "|" + String(e.routine || "").toLowerCase();
      if (e.etape === "demarre") {
        open[k] = { bot: e.bot, routine: e.routine, start: e.ts, startNote: e.note, end: null, etape: null, note: "" };
        out.push(open[k]);
      } else if (e.etape === "fini" || e.etape === "arret") {
        var p = open[k];
        if (p) { p.end = e.ts; p.etape = e.etape; p.note = e.note; delete open[k]; }
        else out.push({ bot: e.bot, routine: e.routine, start: null, end: e.ts, etape: e.etape, note: e.note });   // fin sans début noté
      }
    });
    var now = Date.now();
    out.forEach(function (p) {
      p.at = p.start || p.end;
      p.status = p.etape === "fini" ? "fini" : p.etape === "arret" ? "arret" : (now - new Date(p.start).getTime() < RUN_OPEN_MAX_MS ? "encours" : "pasfini");
    });
    return out.sort(function (a, b) { return a.at < b.at ? 1 : a.at > b.at ? -1 : 0; });
  }
  var RUN_ST = { fini: ["✅ Fini", "b-ok"], arret: ["⛔ Arrêt", "b-err"], encours: ["⏳ En cours", "b-info"], pasfini: ["❓ Pas fini", "b-warn"] };
  function renderRuns() {
    var box = el("rrun"), s = STATE.data.summary; if (!box || !s) return;
    var all = routinePassages((s.routine_runs || {}).events), bots = Array.from(new Set(all.map(function (p) { return p.bot; }))).sort();
    var f = bots.indexOf(STATE.ui.runBot) >= 0 ? STATE.ui.runBot : "all", lim = STATE.ui.runLimit || 15;
    var rows = all.filter(function (p) { return f === "all" || p.bot === f; });
    if (!all.length) { box.innerHTML = '<p class="empty">Aucun passage enregistré pour l’instant.</p>'; return; }
    var h = bots.length > 1 ? '<div class="filters">' + chipsBar([["all", "Tous les bots", all.length]].concat(bots.map(function (b) { return [esc(b), esc(b), all.filter(function (p) { return p.bot === b; }).length]; })), f === "all" ? "all" : esc(f), "rb") + "</div>" : "";
    h += '<div class="table-wrap"><table class="rtable"><thead><tr><th>Quand</th><th>Bot</th><th>Routine</th><th>Résultat</th></tr></thead><tbody>' +
      rows.slice(0, lim).map(function (p) {
        var st = RUN_ST[p.status], note = p.status === "fini" || p.status === "arret" ? p.note : p.status === "pasfini" ? "fin jamais notée" : p.startNote;
        var sub = !p.start ? "début non noté" : p.end ? "durée " + dur(Math.max(0, (new Date(p.end) - new Date(p.start)) / 1000)) : ago(p.start);
        return '<tr><td data-label="Quand" class="mono small nowrap">' + fmtTime(p.at) + '<div class="xs muted">' + esc(sub) + '</div></td><td data-label="Bot" class="mono">' + esc(p.bot) +
          '</td><td data-label="Routine" class="small">' + esc(p.routine) + '</td><td data-label="Résultat" class="small"><span class="badge ' + st[1] + '">' + st[0] + "</span>" + (note ? ' <span class="text2">' + esc(note) + "</span>" : "") + "</td></tr>";
      }).join("") + "</tbody></table></div>" +
      (rows.length > lim ? '<button class="btn" id="rmore" style="margin-top:10px">Voir plus (' + (rows.length - lim) + ")</button>" : "") +
      '<p class="xs muted">Les 7 derniers jours, le plus récent en haut. « Pas fini » : commencé il y a plus de 30 min sans fin notée. Heures de Bruxelles.</p>';
    box.innerHTML = h;
    bindChips("rb", "runBot", function () { STATE.ui.runLimit = 15; renderRuns(); });
    if (el("rmore")) el("rmore").onclick = function () { STATE.ui.runLimit = lim + 30; renderRuns(); };
  }


  // --- statut + compte à rebours des cycles
  function collectorTickMs() {
    var t = [], lp = STATE.data.prices, s = STATE.data.summary || {};
    if (lp && lp.last_tick_at) t.push(new Date(lp.last_tick_at).getTime());
    if (s.price_source && s.price_source.at) t.push(new Date(s.price_source.at).getTime());
    return t.length ? Math.max.apply(null, t) : null;
  }
  function bxDayIndex(dt) { var q = bxParts(dt); return Math.floor(Date.UTC(q.y, q.m - 1, q.d) / 86400000); }
  function mmss(sec) { sec = Math.max(0, Math.floor(sec)); var m = Math.floor(sec / 60), r = sec % 60; return (m ? m + " min " : "") + String(r).padStart(2, "0") + " s"; }
  function cycleStatus(c) {
    if (c.every_sec) {
      var lt = collectorTickMs(), age = lt ? (Date.now() - lt) / 1000 : null;
      if (age != null && age < staleLimit()) return { cls: "b-ok", text: "En marche", dot: true, note: "dernier prix il y a " + Math.max(0, Math.round(age)) + " s" };
      var s = STATE.data.summary || {}, dataAge = s.generated_at ? (Date.now() - new Date(s.generated_at)) / 1000 : 0;
      if (c.last_ok && c.tick_age_at_build_s != null && c.tick_age_at_build_s < 120 && dataAge > 120)
        return { cls: "b-info", text: "En marche (dernière mise à jour)", note: "en marche quand les données ont été lues, il y a " + dur(dataAge) };
      return { cls: "b-err", text: "Arrêté ?", note: age != null ? "aucun prix depuis " + dur(age) : "aucun prix reçu" };
    }
    if (!c.slots || !c.slots.length) return { cls: "b-mute", text: "Sur demande" };
    if (c.key === "scan") {
      var q = bxParts(new Date()), mins = q.h * 60 + q.mi, inWin = q.wd > 0 && q.wd < 6 && mins >= 900 && mins <= 1020;
      return inWin ? { cls: "b-ok", text: "En séance" } : { cls: "b-mute", text: "Hors fenêtre" };
    }
    return { cls: "b-info", text: "Planifié" };
  }
  // --- Cycles : cartes avec compte à rebours « afficheur LED » HH:MM:SS (copié du site modèle, CycleCountdowns),
  //     une couleur par cycle, qui tourne chaque seconde ; badge Planifié / Bientôt (< 90 s) / En retard ; barre « cycle écoulé ».
  var CY_COLORS = { scan: "#c084fc", research: "#00d4d4", predict: "#f5a623", risk: "#38bdf8", compound: "#fde047", orchestrator: "#94a3b8", ticks: "#e2e8f0" };
  var SEG = { 0: [1, 1, 1, 1, 1, 1, 0], 1: [0, 1, 1, 0, 0, 0, 0], 2: [1, 1, 0, 1, 1, 0, 1], 3: [1, 1, 1, 1, 0, 0, 1], 4: [0, 1, 1, 0, 0, 1, 1], 5: [1, 0, 1, 1, 0, 1, 1],
    6: [1, 0, 1, 1, 1, 1, 1], 7: [1, 1, 1, 0, 0, 0, 0], 8: [1, 1, 1, 1, 1, 1, 1], 9: [1, 1, 1, 1, 0, 1, 1], "-": [0, 0, 0, 0, 0, 0, 1] };
  function ledDigit(ch) { var s = SEG[ch] || [0, 0, 0, 0, 0, 0, 0]; return '<span class="lg">' + ["t", "ur", "lr", "b", "ll", "ul", "m"].map(function (k, i) { return '<i class="s ' + k + (s[i] ? " on" : "") + '"></i>'; }).join("") + "</span>"; }
  var LED_COLON = '<span class="lc"><i></i><i></i></span>';
  function ledHtml(t) {
    if (t.demand) return ledDigit("-") + ledDigit("-") + LED_COLON + ledDigit("-") + ledDigit("-");
    var a = Math.abs(t.secs), h = Math.floor(a / 3600), m = Math.floor(a % 3600 / 60), s = a % 60, d2 = function (n) { return String(n).padStart(2, "0").split("").map(ledDigit).join(""); };
    return (h > 0 ? String(h).split("").map(ledDigit).join("") + LED_COLON : "") + d2(m) + LED_COLON + d2(s);
  }
  function cycleTiming(c) {
    if (c.every_sec) {   // collecteur : prochain relevé = dernier prix connu + 30 s (puis + 30 s…)
      var lt = collectorTickMs(); if (!lt) return { demand: true };
      var n = lt + c.every_sec * 1000; while (n <= Date.now()) n += c.every_sec * 1000;
      return { secs: Math.floor((n - Date.now()) / 1000), interval: c.every_sec, next: n };
    }
    if (!c.slots || !c.slots.length) return { demand: true };
    var w = slotWindow(c.slots, c.weekdays);
    if (!w || !w.next) return { demand: true };
    return { secs: Math.floor((w.next - Date.now()) / 1000), interval: w.prev ? Math.round((w.next - w.prev) / 1000) : null, next: +w.next };
  }
  function timingBadge(t, c) {
    if (c && c.every_sec) return "";
    if (t.demand) return '<span class="badge b-mute">Sur demande</span>';
    if (t.secs < 0) return '<span class="badge b-err pulse">En retard</span>';
    if (t.secs < 90) return '<span class="badge b-warn">Bientôt</span>';
    return '<span class="badge b-mute">Planifié</span>';
  }
  function nextLabel(c, t) {
    if (t.demand) return c.every_sec ? "en attente du premier prix" : "pas d’horaire fixe : lancé quand il faut";
    if (c.every_sec) return "prochain relevé de prix";
    var at = new Date(t.next), dd = bxDayIndex(at) - bxDayIndex(new Date());
    var day = dd === 0 ? "aujourd’hui" : dd === 1 ? "demain" : new Intl.DateTimeFormat("fr-BE", { timeZone: TZ, weekday: "long" }).format(at);
    return "prochain passage : " + day + " à " + (c.approx ? "≈ " : "") + fmtTime(at.toISOString(), false);
  }
  function cycleCard(c) {
    var st = cycleStatus(c), t = cycleTiming(c), col = CY_COLORS[c.key] || "#94a3b8";
    var pc = !t.demand && t.interval ? Math.min(100, Math.max(0, (t.interval - Math.max(t.secs, 0)) / t.interval * 100)) : null;
    return '<div class="card cycle cy" data-key="' + c.key + '" style="--c:' + col + ";border-color:" + col + '40">' +
      '<div class="head"><div><div class="cy-name">' + esc(c.name) + '</div><div class="cy-freq">' + esc(c.schedule) + "</div></div>" +
      '<div class="cy-badges"><span data-cb="' + c.key + '">' + timingBadge(t, c) + "</span>" + (st.text === "Planifié" || st.text === "Sur demande" ? "" : '<span class="badge ' + st.cls + '">' + (st.dot ? '<span class="dot ok"></span>' : "") + esc(st.text) + "</span>") + "</div></div>" +
      '<div class="ledbox' + (t.demand ? " idle" : "") + (t.secs < 0 ? " late" : "") + '"><span class="led" data-led="' + c.key + '">' + ledHtml(t) + "</span></div>" +
      '<div class="cy-next xs" data-cn="' + c.key + '">' + esc(nextLabel(c, t)) + "</div>" +
      (pc != null ? '<div class="cy-el"><div class="flow xs mono" style="justify-content:space-between"><span class="muted">cycle écoulé</span><span data-cp="' + c.key + '" style="color:var(--c)">' + pc.toFixed(0) + ' %</span></div><div class="cy-bar"><i data-cbar="' + c.key + '" style="width:' + pc + '%"></i></div></div>' : "") +
      '<div class="t small" style="margin-top:10px">' + esc(c.title) + " — " + esc(c.desc) + "</div><ul>" + c.bullets.map(function (b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>" +
      (st.note ? '<div class="xs muted">' + esc(st.note) + "</div>" : "") +
      (c.last_note ? '<div class="xs ' + (c.last_ok ? "muted" : "warn") + '">' + esc(c.last_note) + "</div>" : "") +
      (c.key === "risk" ? '<div class="xs muted">Surveillance des stops : ' + (c.watch_stops_running ? "en marche" : "pas de programme actif (aucune position ouverte)") + "</div>" : "") +
      '<div class="foot"><span class="cy-lbl">Dernier passage</span><span>' + (c.last_ok ? '<span class="dot ok"></span>' : '<span class="dot"></span>') + '<b style="color:var(--c)">' + ago(c.last_run) + "</b></span></div></div>";
  }
  function tickCountdowns() {
    var s = STATE.data.summary; if (!s || !s.cycles || !document.querySelector("[data-led]")) return;
    s.cycles.forEach(function (c) {
      var led = document.querySelector('[data-led="' + c.key + '"]'); if (!led) return;
      var t = cycleTiming(c);
      led.innerHTML = ledHtml(t);
      led.parentNode.classList.toggle("late", t.secs < 0);
      var b = document.querySelector('[data-cb="' + c.key + '"]'); if (b) b.innerHTML = timingBadge(t, c);
      var n = document.querySelector('[data-cn="' + c.key + '"]'); if (n) n.textContent = nextLabel(c, t);
      if (!t.demand && t.interval) {
        var pc = Math.min(100, Math.max(0, (t.interval - Math.max(t.secs, 0)) / t.interval * 100));
        var p = document.querySelector('[data-cp="' + c.key + '"]'), br = document.querySelector('[data-cbar="' + c.key + '"]');
        if (p) p.textContent = pc.toFixed(0) + " %"; if (br) br.style.width = pc + "%";
      }
    });
  }

  // ------------------------------------------------------------ TRADES (une ligne par achat ou vente)
  // Numérotation unique « Trade N · 1/2 » (ordre chronologique d'ouverture), tri par heure d'exécution (plus récent d'abord).
  // Les lignes de test/démo (auto-test Polymarket) ne sont pas affichées. Type et sens viennent des fichiers de l'équipe.
  function buildLegs(T) {
    var groups = [];
    (T.trades || []).forEach(function (t) {
      if (t.kind === "autotest" || !/^[A-Z0-9]+-[A-Z]+$/.test(String(t.pair || ""))) return;   // test / démo : rien
      var idea = t.idea_type === "baisse" ? "baisse" : "hausse";
      var base = { mode: t.mode, pair: t.pair, origin: t.origin, idea: idea, kind: t.kind, decision: t.decision_link };
      var legs = [], two = !!((t.buy_time || t.buy_price) && t.sell_time);
      if (t.kind === "start_sale") base.depart = true;
      if (t.buy_time || (t.buy_price != null && !t.sell_time)) legs.push(Object.assign({}, base, {
        sens: "achat", time: t.buy_time, price: t.buy_price, amount: t.amount_eur, qty: t.qty, statusRaw: t.sell_time ? "Revendu ensuite (ligne 2/2)" : t.status,
        stop: t.sell_time ? null : t.stop_price, why: t.sell_time ? null : t.reason, bot: t.bot_reason, open: !t.sell_time && t.kind === "trade",
        result: !t.sell_time && t.pnl_eur != null && t.kind === "trade" ? { eur: t.pnl_eur, pct: t.pnl_pct, latent: true } : null }));
      if (t.sell_time) legs.push(Object.assign({}, base, {
        sens: "vente", time: t.sell_time, price: t.sell_price, amount: t.sell_amount, qty: t.qty, statusRaw: t.status, closeReason: t.close_reason,
        stop: t.stop_price, why: t.reason, lesson: t.lesson, result: t.pnl_eur != null ? { eur: t.pnl_eur, pct: t.pnl_pct } : null }));
      if (legs.length) groups.push(legs);
    });
    ((T.sell_first || {}).cycles || []).forEach(function (c) {
      var base = { mode: c.mode, pair: c.pair, idea: c.idea_type === "hausse" ? "hausse" : "baisse", decision: c.decision_id, coin: c.coin };
      var legs = [Object.assign({}, base, { sens: "vente", time: c.sell_time, price: c.sell_price, amount: c.sell_amount || c.sell_eur, qty: c.qty_sold,
        statusRaw: c.done ? "Racheté ensuite (ligne 2/2)" : "En attente du rachat", why: c.reason, inferred: c.inferred, waiting: !c.done })];
      if (c.done) legs.push(Object.assign({}, base, { sens: "achat", time: c.rebuy_time, price: c.rebuy_price, amount: c.rebuy_eur, qty: c.qty_bought,
        statusRaw: c.status, rebuyReason: c.rebuy_reason, result: { coins: c.coin_gain, coinsPct: c.coin_gain_pct, eur: c.eur_gain, fees: c.fees_eur } }));
      else legs.push(Object.assign({}, base, { sens: "achat", pending: true, time: null, statusRaw: "Rachat prévu",
        plan: { target: c.target_price, safety: c.safety_price }, result: c.coin_gain_if_now != null ? { coins: c.coin_gain_if_now, coinsPct: c.coin_gain_if_now_pct, eur: c.eur_gain_if_now, latent: true } : null }));
      groups.push(legs);
    });
    ((T.real || {}).open_orders || []).forEach(function (o) {
      groups.push([{ mode: "reel", pair: o.pair, origin: o.bot ? "bot" : null, idea: "hausse", sens: o.side === "sell" ? "vente" : "achat",
        time: o.created || null, price: o.price, amount: o.amount_eur, qty: o.qty, statusRaw: "Ordre en attente dans le carnet Revolut X", order: true }]);
    });
    // numéro unique : ordre chronologique de la première ligne
    groups.forEach(function (g) { g.first = g.reduce(function (a, l) { return l.time && (!a || l.time < a) ? l.time : a; }, null) || "9999"; });
    groups.sort(function (a, b) { return a.first.localeCompare(b.first); });
    var legs = [];
    groups.forEach(function (g, i) { g.forEach(function (l, j) { l.num = i + 1; l.step = g.length > 1 ? (j + 1) + "/" + g.length : ""; legs.push(l); }); });
    // tri : heure d'exécution, plus récent d'abord (une ligne « prévue » sans heure en tête)
    legs.sort(function (a, b) { return (b.time || "9999").localeCompare(a.time || "9999") || (b.step || "").localeCompare(a.step || ""); });
    return legs;
  }
  // Statut court : une icône + un mot (le détail complet en info-bulle)
  function shortStatus(l) {
    var raw = l.statusRaw || "", r = l.result;
    if (l.pending) return ["⏳", "Prévu", "b-warn"];
    if (l.order) return ["⏳", "En attente", "b-warn"];
    if (/refus|erreur/i.test(raw)) return ["✖", "Refusé", "b-err"];
    if (/envoyé/i.test(raw)) return ["⏳", "Envoyé", "b-warn"];
    if (l.waiting) return ["⏳", "Attente", "b-warn"];
    if (l.depart) return ["↩", "Départ", "b-mute"];
    if (l.open) return ["⏳", "En cours", "b-warn"];
    if (/ensuite/i.test(raw)) return ["→", "Fermé", "b-mute"];
    if (/stop/i.test(raw + (l.closeReason || ""))) return ["⛔", "Stop", "b-mute"];
    if (/sécurité|securite|safety/i.test(raw + (l.rebuyReason || ""))) return ["🛡", "Sécurité", "b-mute"];
    if (/visé|vise|target/i.test(raw + (l.rebuyReason || ""))) return ["🎯", "Objectif", "b-mute"];
    return ["✔", "Terminé", "b-mute"];
  }
  function typeIcons(l) {
    var m = l.mode === "reel" ? ["💶", "Argent réel"] : ["🧪", "Simulation (argent fictif)"];
    var i = l.idea === "baisse" ? ["📉", "Idée à la baisse : vendre des pièces qu’on a, puis racheter plus bas"] : ["📈", "Idée à la hausse : acheter, puis revendre plus haut"];
    return '<span class="ticon" title="' + m[1] + '">' + m[0] + '</span><span class="ticon" title="' + i[1] + '">' + i[0] + "</span>" +
      (l.mode === "reel" && l.origin ? '<span class="xs muted" title="' + (l.origin === "bot" ? "passé par les bots" : "passé à la main") + '"> ' + esc(l.origin) + "</span>" : "") +
      (l.depart ? '<span class="xs muted" title="Vente de pièces achetées avant le projet (prix d’achat inconnu, pas comptée)"> départ</span>' : "");
  }
  function legRow(l) {
    var res = "—", r = l.result;
    if (r && r.coins != null) res = '<div class="' + cls(r.coins) + '">' + (r.latent ? '<span class="xs muted">si racheté maintenant</span><br>' : "") + signedCoin(r.coins, l.coin) + "</div>" + (r.eur != null ? '<div class="xs ' + cls(r.eur) + '">' + eur(r.eur, 2, true) + (r.fees ? " · frais " + eur(r.fees) : "") + "</div>" : "");
    else if (r && r.eur != null) res = '<div class="' + cls(r.eur) + '">' + (r.latent ? '<span class="xs muted">latent</span><br>' : "") + eur(r.eur, 2, true) + '</div><div class="xs ' + cls(r.pct) + '">' + pct(r.pct, 2, true) + "</div>";
    var st = shortStatus(l);
    var why = (l.why ? "<b>" + (l.sens === "vente" ? "Pourquoi vendu :" : "Pourquoi acheté :") + "</b> " + esc(l.why) + "<br>" : "") + (l.bot ? "<b>Raison du bot :</b> " + esc(l.bot) + "<br>" : "") + (l.lesson ? "<b>Leçon :</b> " + esc(l.lesson) : "") +
      (l.decision ? '<div class="xs"><a href="research.html#decisions">Décision ' + esc((String(l.decision).match(/D-\d+/) || ["écrite"])[0]) + " →</a></div>" : "");
    return '<tr class="leg"><td data-label="Trade" class="mono small nowrap">Trade ' + l.num + (l.step ? ' <span class="xs muted">· ' + l.step + "</span>" : "") +
      '</td><td data-label="Sens">' + sideBadge(l.sens, l.pending) +
      '</td><td data-label="Type" class="nowrap">' + typeIcons(l) +
      '</td><td data-label="Paire" class="mono nowrap">' + pairHtml(l.pair) +
      '</td><td data-label="Prix · heure" class="mono">' + (l.pending ? '<span class="small">visé ' + price(l.plan.target) + '</span><div class="xs muted">sécurité ' + price(l.plan.safety) + "</div>" : price(l.price) + '<div class="xs muted">' + fmtTime(l.time) + "</div>") +
      '</td><td data-label="Montant" class="num">' + (l.pending ? "—" : eur(l.amount) + (l.qty ? '<div class="xs muted">' + coinQty(l.qty) + "</div>" : "")) +
      '</td><td data-label="Résultat" class="num">' + res +
      '</td><td data-label="Statut" class="nowrap"><span class="badge ' + st[2] + '" title="' + esc(l.statusRaw || "") + '">' + st[0] + " " + st[1] + "</span>" + (l.stop ? '<div class="xs muted">stop ' + price(l.stop) + "</div>" : "") +
      '</td><td data-label="Raison · leçon" class="wide small text2">' + (why || '<span class="muted">—</span>') + "</td></tr>";
  }
  function renderTrades() {
    var T = STATE.data.trades, mf = STATE.ui.modeFilter || "all", sf = STATE.ui.sensFilter || "all", pf = STATE.ui.pairFilter || "all";
    var all = buildLegs(T);
    var by = function (fm, fs, fp) { return all.filter(function (l) {
      return (fm === "all" || l.mode === fm) && (fp === "all" || l.pair === fp) &&
        (fs === "all" || (fs === "achat" && l.sens === "achat") || (fs === "vente" && l.sens === "vente") || (fs === "hausse" && l.idea === "hausse") || (fs === "baisse" && l.idea === "baisse")); }); };
    var pairs = []; all.forEach(function (l) { if (pairs.indexOf(l.pair) < 0) pairs.push(l.pair); }); pairs.sort();
    var h = '<h1 class="page-title">Historique des trades</h1><p class="lead">Une ligne par achat ou par vente, la plus récente en haut. Les deux lignes d’un même trade portent le même numéro (Trade 3 · 1/2 puis 2/2). Les résultats chiffrés sont sur la page <a href="performance.html">Performance</a>.</p>';
    h += '<div class="filters">' + chipsBar([["all", "Tout", by("all", sf, pf).length], ["sim", "🧪 Simulation", by("sim", sf, pf).length], ["reel", "💶 Réel", by("reel", sf, pf).length]], mf, "m") +
      chipsBar([["all", "Achats et ventes", by(mf, "all", pf).length], ["achat", "Achats", by(mf, "achat", pf).length], ["vente", "Ventes", by(mf, "vente", pf).length], ["hausse", "📈 À la hausse", by(mf, "hausse", pf).length], ["baisse", "📉 À la baisse", by(mf, "baisse", pf).length]], sf, "s") +
      chipsBar([["all", "Toutes les paires", by(mf, sf, "all").length]].concat(pairs.map(function (p) { return [p, pairHtml(p), by(mf, sf, p).length]; })), pf, "pf") + "</div>";
    h += '<p class="legend-line xs muted">🧪 simulation · 💶 argent réel · 📈 idée à la hausse (acheter puis revendre plus haut) · 📉 idée à la baisse (vendre puis racheter plus bas) · statut : ⏳ en cours/en attente · ✔ terminé · 🎯 objectif atteint · 🛡 rachat de sécurité · ⛔ stop · → fermé (voir l’autre ligne). Survoler une icône pour le détail.</p>';
    var rows = by(mf, sf, pf);
    if (rows.length) h += '<div class="table-wrap"><table class="rtable ttable"><thead><tr><th>Trade</th><th>Sens</th><th>Type</th><th>Paire</th><th>Prix · heure</th><th class="num">Montant</th><th class="num">Résultat</th><th>Statut</th><th>Raison · leçon</th></tr></thead><tbody>' + rows.map(legRow).join("") + "</tbody></table></div>";
    else h += '<p class="empty">' + (sf === "baisse" ? "Aucune idée à la baisse pour l’instant." : "Aucune ligne pour ce filtre.") + "</p>";
    h += '<p class="xs muted">Les décisions écrites sont sur la page <a href="research.html#decisions">Analyses</a>. Sources — simulation : state/trades_log.jsonl (paper_fill.py, watch_stops.py ; champs side et idea_type) + guardian/state.json ; réel : historique Revolut X (lecture seule) + state/live_orders.jsonl ; raison et leçon : knowledge/trading_journal.md.</p>';
    el("app").innerHTML = h;
    bindChips("m", "modeFilter", renderTrades); bindChips("s", "sensFilter", renderTrades); bindChips("pf", "pairFilter", renderTrades);
  }

  // ------------------------------------------------------------ PERFORMANCE
  var PERF_TABS = [["simulation", "Simulation"], ["reel", "Argent réel"], ["monnaies", "Par monnaie"], ["tests", "Tests du passé"]];
  // Une seule vue d'ensemble : tous les trades ensemble (idées à la hausse et à la baisse), mêmes cartes pour la
  // simulation et l'argent réel. Un trade est gagnant si son résultat en euros, frais compris, est > 0.
  var IDEAS = [["all", "Tous"], ["hausse", "📈 Hausse"], ["baisse", "📉 Baisse"]];
  function overviewCards(P, mode) {
    var OV = (P.overview || {})[mode] || {}, idea = STATE.ui.perfIdea || "all";
    if (!OV[idea]) idea = "all";
    var st = OV[idea] || {}, e = P.equity || {}, RL = P.real || {}, drop, hold;
    var dropTxt = function (x) { return x ? eur(-x, 2) : eur(0, 2); };
    if (mode === "sim") {
      drop = statCard("Plus grosse baisse", dropTxt(st.max_drop_eur), idea === "all" ? "portefeuille : " + pct(e.max_drawdown_pct, 2) + " sous son sommet (limite 8 %)" : "pire suite de pertes", st.max_drop_eur ? "neg" : "");
      hold = statCard("Si on avait gardé du BTC", pct(e.hold_return_pct, 2, true), "depuis le " + fmtDay(e.start) + (e.btc_start ? " (de " + price(e.btc_start) + " à " + price(e.btc_end) + ")" : "") + " — nous : " + pct(P.paper.total_return_pct, 2, true), cls(e.hold_return_pct));
    } else {
      drop = statCard("Plus grosse baisse", dropTxt(st.max_drop_eur), idea === "all" && RL.bot_drop_pct != null ? "capital du bot : " + pct(RL.bot_drop_pct, 2) + " sous son plus haut" : "pire suite de pertes", st.max_drop_eur ? "neg" : "");
      hold = statCard("Si on avait gardé du BTC", RL.hold_return_pct == null ? "—" : pct(RL.hold_return_pct, 2, true), "depuis le " + fmtDay(RL.project_start) + (RL.btc_start ? " (de " + price(RL.btc_start) + " à " + price(RL.btc_end) + ")" : ""), cls(RL.hold_return_pct));
    }
    var bt = function (x) { return x ? pairHtml(x.pair) + (x.idea === "baisse" ? " · 📉" : " · 📈") : ""; };
    var counts = IDEAS.map(function (x) { var o = OV[x[0]] || {}; return [x[0], x[1], (o.closed || 0) + (o.open || 0)]; });
    return '<div class="filters">' + chipsBar(counts, idea, "pi") + "</div>" +
      '<div class="grid g4">' + statCard("Gain / perte réalisé", eur(st.realized_pnl_eur || 0, 2, true), "en euros, après frais", cls(st.realized_pnl_eur)) +
      statCard("Taux de réussite", st.win_rate_pct == null ? "—" : pct(st.win_rate_pct, 0), (st.wins || 0) + " gagnant(s) · " + (st.losses || 0) + " perdant(s)") +
      statCard("Trades terminés", st.closed || 0, (st.open || 0) + " en cours") +
      statCard("Meilleur trade", st.best ? eur(st.best.pnl_eur, 2, true) : "—", bt(st.best), st.best ? cls(st.best.pnl_eur) : "") +
      statCard("Pire trade", st.worst ? eur(st.worst.pnl_eur, 2, true) : "—", bt(st.worst), st.worst ? cls(st.worst.pnl_eur) : "") +
      drop + hold + "</div>" +
      '<p class="xs muted">Tous les trades ensemble : 📈 idée à la hausse (acheter puis revendre) et 📉 idée à la baisse (vendre puis racheter). Gagnant = résultat en euros, frais compris, au-dessus de 0. Le détail (et les pièces gagnées ou perdues) est dans la <a href="trades.html">liste des trades</a>.</p>';
  }
  function renderPerformance() {
    var P = STATE.data.performance, tab = getTab(PERF_TABS.map(function (x) { return x[0]; }), "simulation");
    var h = '<h1 class="page-title">Performance</h1><p class="lead">Les résultats des trades : simulation, argent réel, par monnaie, et les tests sur les prix passés.</p>' + tabsBar(PERF_TABS, tab);
    if (tab === "simulation") h += perfSim(P);
    else if (tab === "reel") h += perfReal(P);
    else if (tab === "monnaies") h += perfPairs(P);
    else h += perfTests(P);
    el("app").innerHTML = h;
    bindTabs(renderPerformance);
    STATE.ui.pairLive = null;
    if (tab === "simulation" || tab === "reel") bindChips("pi", "perfIdea", renderPerformance);
    if (tab === "simulation") drawEquity(P.equity);
    if (tab === "monnaies") {
      STATE.ui.pairLive = renderPair;
      Array.prototype.forEach.call(document.querySelectorAll("#pairtabs .tab"), function (b) { b.onclick = function () { STATE.ui.pair = b.getAttribute("data-p"); Array.prototype.forEach.call(document.querySelectorAll("#pairtabs .tab"), function (x) { x.classList.toggle("on", x === b); }); renderPair(); }; });
      renderPair();
    }
    if (tab === "tests") {
      bindChips("tg", "testGroup", renderPerformance);
      if (el("tmore")) el("tmore").onclick = function () { STATE.ui.testLimit = 999; renderPerformance(); };
    }
  }
  function perfSim(P) {
    var st = ((P.overview || {}).sim || {}).all || P.stats.sim, e = P.equity, g = P.go_nogo || {};
    var h = '<section class="section">' + secHead("Simulation", "argent fictif · " + num(P.paper.invested_eur, 0) + " € au départ") + overviewCards(P, "sim") + "</section>";
    h += '<section class="section">' + secHead("Courbe du portefeuille", "simulation vs garder du BTC") + '<div class="card"><div class="chart-box"><canvas id="eq"></canvas></div><p class="xs muted" style="margin:8px 0 0">Heure par heure. Le portefeuille ne bouge que quand un trade est vendu. BTC : prix Revolut X.</p></div></section>';
    var goals = [["Trades d'essai", st.closed, g.min_trades, st.closed + " / " + g.min_trades], ["Taux de réussite", st.win_rate_pct || 0, (g.min_win_rate || 0) * 100, pct(st.win_rate_pct, 0) + " / " + pct((g.min_win_rate || 0) * 100, 0)],
      ["Baisse max sous 8 %", e.max_drawdown_pct < (g.max_drawdown_pct || 0.08) * 100 ? 1 : 0, 1, pct(e.max_drawdown_pct, 2) + " (ok si < 8 %)"]];
    h += '<section class="section">' + secHead("Avant de passer au réel", "objectifs de l'équipe (references/go-nogo.md)") + '<div class="grid g3">' + goals.map(function (x) {
      var r = x[2] ? Math.min(1, x[1] / x[2]) : 0;
      return '<div class="card"><div class="label">' + x[0] + '</div><div class="mono" style="margin-bottom:8px">' + x[3] + '</div><div class="bar"><i style="width:' + Math.round(r * 100) + '%"></i></div></div>';
    }).join("") + '</div><p class="xs muted">Le score des prévisions est sur la page <a href="research.html#score">Analyses</a>.</p></section>';
    return h;
  }
  function perfReal(P) {
    var RL = P.real || {};
    if (RL.hidden) return '<div class="notice">Masqué (SHOW_REAL=false).</div>';
    var st = RL.stats || {};
    return '<section class="section">' + secHead("Argent réel", "Revolut X, depuis le " + fmtDay(RL.project_start)) +
      overviewCards(P, "reel") +
      '<div class="card flat" style="margin-top:4px"><div class="kv k3">' + kv("Positions ouvertes", (st.open_positions_count || 0) + (st.open_positions_count ? " · " + eur(st.open_positions_value_eur) : "")) +
      kv("Gain / perte latent", '<span class="' + cls(st.unrealized_pnl_eur) + '">' + eur(st.unrealized_pnl_eur || 0, 2, true) + "</span>") +
      kv("Ordres en attente", (st.open_orders_count || 0) + (st.open_orders_count ? " · " + eur(st.open_orders_eur) : "")) + "</div></div>" +
      '<p class="xs muted">' + ((st.closed || 0) === 0 ? "Aucun trade réel terminé depuis le début du projet : tout est à 0. " : "") + "Calcul automatique depuis l’historique Revolut X (achats et ventes appariés dans l’ordre). Les avoirs de départ ne comptent pas comme des trades. Les soldes sont sur l’<a href=\"index.html#reel\">accueil › Argent réel</a>." + (RL.history_stale ? ' <span class="warn">Historique pas à jour.</span>' : "") + "</p></section>";
  }
  function perfPairs(P) {
    var PR = P.pairs || {}, pk = Object.keys(PR), cur = STATE.ui.pair && PR[STATE.ui.pair] ? STATE.ui.pair : pk[1] || pk[0];
    STATE.ui.pair = cur;
    return '<section class="section">' + secHead("Par monnaie", "prix sur 7 jours + nos achats et ventes") +
      '<div class="tabs sub" id="pairtabs">' + pk.map(function (k) { return '<button class="tab' + (k === cur ? " on" : "") + '" data-p="' + k + '">' + pairHtml(k) + "</button>"; }).join("") + '</div><div id="pairbox"></div></section>';
  }

  // --- Tests du passé : un seul rendu (cartes) pour tous les tests
  function testCards(P) {
    var out = [];
    (P.sellrebuy_tests || []).forEach(function (t) {
      out.push({ group: "baisse", time: t.time, head: pairHtml(t.pair) + " · " + esc(t.timeframe), title: "Idée à la baisse : vendre puis racheter plus bas" + (t.kind === "robust" ? " · test de solidité" : ""),
        sub: (t.conditions || []).join(" · ") + " · " + (t.period || []).join(" → "), costs: t.costs_fr, robust: t.robust, summary: t.summary_fr,
        kvs: [["Pièces vs garder", '<span class="' + cls(t.coin_gain_pct) + '">' + pct(t.coin_gain_pct, 2, true) + "</span>"], ["Euros vs garder", '<span class="' + cls(t.eur_gain_vs_hold) + '">' + eur(t.eur_gain_vs_hold, 2, true) + "</span>"],
          ["Cycles", t.cycles + (t.win_rate_pct != null ? " · " + pct(t.win_rate_pct, 0) + " gagnés" : "")], ["Rachats", (t.rebuy_reasons.target || 0) + " visés · " + (t.rebuy_reasons.safety || 0) + " sécurité"],
          ["Pire baisse (pièces)", pct(t.max_drawdown_coins_pct, 1)], ["Frais payés", eur(t.fees_eur)]], gates: t.gates, status: t.status });
    });
    (P.backtests || []).forEach(function (b) {
      out.push({ group: "hausse", time: b.time, head: pairHtml(b.pair) + " · " + esc(b.timeframe), title: b.strategy_fr,
        sub: [b.stop_pct != null ? "stop " + num(b.stop_pct, 1) + " %" : "", b.target_pct != null ? "objectif " + num(b.target_pct, 1) + " %" : "", (b.period || []).filter(Boolean).join(" → ")].filter(Boolean).join(" · "), costs: b.costs, summary: b.summary_fr,
        kvs: [["Résultat", '<span class="' + cls(b.total_return_pct) + '">' + pct(b.total_return_pct, 1, true) + "</span>"], ["Garder", '<span class="' + cls(b.hold_return_pct) + '">' + pct(b.hold_return_pct, 1, true) + "</span>"],
          ["Trades", b.trades + (b.win_rate_pct != null ? " · " + pct(b.win_rate_pct, 0) + " gagnés" : "")], ["Baisse max", pct(b.max_drawdown_pct, 1)], ["Rapport gains / pertes", b.profit_factor != null ? num(b.profit_factor, 2) : "—"]], gates: b.gates });
    });
    (P.checks || []).forEach(function (c) {
      var r = c.result || {}, wf = c.walk_forward || {};
      out.push({ group: "hausse", time: c.time, head: pairHtml(c.pair) + " · " + esc(c.timeframe), title: c.strategy_fr + " · test de solidité", sub: (c.period || []).join(" → "),
        costs: c.costs ? "aller-retour " + pct(c.costs.round_trip_pct, 2) : null, summary: null,
        kvs: [["Résultat", '<span class="' + cls(r.total_return_pct) + '">' + pct(r.total_return_pct, 1, true) + "</span>"], ["Garder", pct(r.buy_hold_return_pct, 1, true)], ["Trades", r.trades],
          ["Baisse max", pct(r.max_drawdown_pct, 1)], ["Périodes gagnantes", wf.n_windows ? wf.profitable_windows + " / " + wf.n_windows : "—"]], gates: c.gates });
    });
    (P.vibe_reports || []).forEach(function (x) { out.push({ group: "hausse", time: x.time, head: esc(x.file), title: "Rapport", sub: "", summary: x.line, kvs: [] }); });
    out.sort(function (a, b) { return (b.time || "").localeCompare(a.time || ""); });
    return out;
  }
  // 2 pastilles par carte (build.py test_gates) : « Test du passé réussi » / « Autorisé en réel », vert = oui, rouge = non.
  function gateBadge(g, extra) {
    var tip = g.checks.map(function (c) { return (c.ok === true ? "✔ " : "✖ ") + c.t + (c.v ? " : " + c.v : ""); }).join("\n") + (extra ? "\n" + extra : "");
    return '<span class="badge gate ' + (g.ok ? "b-ok" : "b-err") + '" tabindex="0" title="' + esc(tip) + '">' + (g.ok ? "✔ " : "✖ ") + esc(g.label) + "</span>";
  }
  function gatesHtml(G) {
    var miss = G.past.checks.filter(function (c) { return c.ok !== true; }).map(function (c) { return c.t.toLowerCase() + (c.v ? " (" + c.v + ")" : ""); });
    var why = G.past.ok ? (G.live.ok ? "" : G.live.checks.filter(function (c) { return c.ok !== true; }).map(function (c) { return c.v; }).join(" · ")) : miss.join(" · ");
    return '<div class="gates" style="margin-top:8px">' + gateBadge(G.past, "Frais du test : " + G.past.fees) + gateBadge(G.live, G.live.note) + '<div class="gate-detail xs" hidden></div></div>' +
      (why ? '<div class="xs muted" style="margin-top:4px">' + (G.past.ok ? "Pas en réel : " : "Manque : ") + esc(why) + "</div>" : "");
  }
  document.addEventListener("click", function (e) {
    var g = e.target.closest && e.target.closest(".gate"); if (!g) return;
    var d = g.parentNode.querySelector(".gate-detail"); if (!d) return;
    var same = d.getAttribute("data-for") === g.textContent && !d.hidden;
    d.textContent = g.getAttribute("title"); d.setAttribute("data-for", g.textContent); d.hidden = same;
  });
  function testCardHtml(t) {
    return '<div class="card flat"><div class="card-title" style="margin-bottom:4px"><div class="mono small"><b>' + t.head + '</b> <span class="xs muted">· ' + fmtTime(t.time) + "</span></div>" + (t.status && t.status !== "ok" ? '<span class="badge b-warn">' + esc(t.status) + "</span>" : "") + "</div>" +
      '<div class="small"><b>' + esc(t.title) + "</b></div>" +
      (t.sub ? '<div class="xs muted">' + esc(t.sub) + "</div>" : "") + (t.costs ? '<div class="xs muted">Frais : ' + esc(t.costs) + "</div>" : "") +
      (t.robust ? '<div style="margin-top:6px"><span class="badge ' + (/ROBUST|SOLIDE|OUI|YES/i.test(t.robust.verdict || "") ? "b-ok" : /FRAGILE/i.test(t.robust.verdict || "") ? "b-warn" : "b-err") + '">Solidité : ' + esc((t.robust.verdict_fr || "").split(" :")[0] || t.robust.verdict || "?") + (t.robust.passed != null ? " · " + t.robust.passed + "/" + t.robust.of + " vérifications" : "") + "</span></div>" : "") +
      (t.summary ? '<p class="small" style="margin:8px 0">' + esc(t.summary) + "</p>" : "") +
      (t.robust ? '<div class="xs muted" style="margin-bottom:6px">' + [t.robust.windows_n ? "périodes gagnantes " + t.robust.windows_gain + "/" + t.robust.windows_n : "", t.robust.pbo != null ? "risque que ce soit de la chance " + pct(t.robust.pbo * 100, 0) : "", t.robust.random_p != null ? "mieux que vendre au hasard ? " + (t.robust.random_p < 0.05 ? "oui" : "non") : ""].filter(Boolean).join(" · ") + "</div>" : "") +
      (t.kvs.length ? '<div class="kv k3">' + t.kvs.map(function (x) { return kv(x[0], x[1]); }).join("") + "</div>" : "") +
      (t.gates ? gatesHtml(t.gates) : "") + "</div>";
  }
  function perfTests(P) {
    var all = testCards(P), gsel = STATE.ui.testGroup || "all", lim = STATE.ui.testLimit || 6;
    var list = all.filter(function (t) { return gsel === "all" || t.group === gsel; });
    var h = '<section class="section">' + secHead("Tests du passé", "on rejoue une idée sur les prix d’avant (sans IA)") +
      '<div class="notice" style="margin-bottom:12px">Un bon résultat sur le passé ne garantit rien pour demain. « Garder » = acheter au début et ne rien faire. Chaque carte a 2 pastilles, toujours les mêmes : « Test du passé réussi » (gain après frais, mieux que garder, au moins 20 opérations, gagnant sur les 2 moitiés de l’année, pire baisse &lt; 8 %) et « Autorisé en réel » (test réussi avec frais réels sur chaque ordre + gain ≥ 3× coûts). <span class="pos">Vert</span> = oui, <span class="neg">rouge</span> = non. Survoler ou toucher une pastille pour le détail.</div>' +
      chipsBar([["all", "Tous", all.length], ["hausse", "📈 Idées à la hausse", all.filter(function (t) { return t.group === "hausse"; }).length], ["baisse", "📉 Idées à la baisse", all.filter(function (t) { return t.group === "baisse"; }).length]], gsel, "tg");
    h += list.length ? '<div class="grid g2">' + list.slice(0, lim).map(testCardHtml).join("") + "</div>" + (list.length > lim ? '<button class="btn" id="tmore" style="margin-top:10px">Voir tous les tests (' + list.length + ")</button>" : "") : '<p class="empty">Aucun test pour l’instant. Les nouveaux apparaîtront ici automatiquement.</p>';
    if (P.sellrebuy_duplicates) h += '<p class="xs muted">' + P.sellrebuy_duplicates + " test(s) en double (mêmes réglages) cachés.</p>";
    h += '<p class="xs muted">Source : /workspace/tools/vibe-trading (home/runs, checks, reports).</p></section>';
    return h;
  }

  function sonnetteCard(so) {
    if (!so) return "";
    var h = '<div class="card"><div class="card-title"><h3>Sonnette</h3>' + (so.present ? '<span class="badge ' + (so.running ? "b-ok" : "b-err") + '"><span class="dot' + (so.running ? " ok" : "") + '"></span>' + (so.running ? "en marche" : "arrêtée") + "</span>" : '<span class="badge b-mute">pas trouvée</span>') + "</div>" +
      '<p class="xs muted" style="margin-top:0">3 sonnettes : PM-Predict et PM-Risk quand un prix touche une zone ou qu’un stop est proche, PM-Compound quand un trade est fermé. Elle ne passe aucun ordre.</p>';
    if (so.present) {
      var md = function (m) { return '<span class="badge ' + (m === "branchée" ? "b-ok" : "b-mute") + '">' + esc(m) + "</span>"; };
      var modes = { predict: so.predict_mode, risk: so.risk_mode, compound: so.compound_mode };
      // Par sonnette : vrais réveils et essais séparés (build.py load_sonnette → bells, depuis rings.jsonl + departs.jsonl)
      h += '<div class="bells">' + (so.bells || []).map(function (b) {
        var lr = b.last_real, chain = "";
        if (lr) {
          var lk = lr.link;
          chain = '<div class="xs bell-chain">Dernier vrai réveil ' + fmtTime(lr.at) + " : " + esc(lr.event) + (lr.pair ? " " + pairHtml(lr.pair) + (lr.price ? " " + price(lr.price) : "") : "") +
            " → " + esc(lr.result_fr) + " → " + (lk ? esc((lk.id ? lk.id + " · " : "") + lk.text) : "pas encore de résultat lié") + "</div>";
        }
        return '<div class="bell" data-bell="' + esc(b.key) + '"><div class="flow small" style="justify-content:space-between;gap:6px"><b>' + esc(b.bot) + "</b>" +
          (b.key === "departs" ? '<span class="badge b-mute">' + (b.observe ? "observation" : "active") + "</span>" : (modes[b.key] ? md(modes[b.key]) : "")) + "</div>" +
          '<div class="xs muted">' + esc(b.what) + "</div>" +
          '<div class="small mono bell-cnt">' + (b.key === "departs" ? "Vraies détections : " + b.real : "Vrais réveils : " + b.real + " · Essais : " + b.tests) + "</div>" + chain + "</div>";
      }).join("") + "</div>";
      h += '<div class="kv k3" style="margin-top:8px">' + kv("Dernier signe de vie", ago(so.heartbeat)) + kv("Fenêtre Predict", so.predict_window_open ? "ouverte" : "fermée") + "</div>";
      var warns = [];
      if (so.urgent_active) warns.push("alerte urgente en cours");
      if (so.prices_stale) warns.push("prix pas à jour");
      if (so.real_positions_without_stop) warns.push(so.real_positions_without_stop + " position(s) réelle(s) sans stop");
      if (so.zones_problems) warns.push(so.zones_problems + " zone(s) mal écrite(s)");
      if (!so.collector_running) warns.push("collecteur de prix arrêté");
      if (warns.length) h += '<div class="notice warn" style="margin-top:10px">' + esc(warns.join(" · ")) + "</div>";
    }
    var zs = (so.zones || []).filter(zoneOn);   // détail (une ligne par zone) : Analyses › Prévisions, pas ici
    h += '<hr class="sep"><div class="small"><b>Zones de réveil actives : ' + zs.length + "</b>" + (zs.length ? " · " + Array.from(new Set(zs.map(function (z) { return String(z.pair || "").split("-")[0]; }))).map(curHtml).join(", ") : "") +
      ' · <a href="research.html#predict">voir le détail dans Analyses › Prévisions</a></div>';
    var rg = so.rings || [];
    h += '<hr class="sep"><b class="small">Derniers coups de sonnette</b>' + (rg.length ? '<div class="table-wrap" style="margin-top:6px"><table class="rtable"><thead><tr><th>Heure</th><th>Bot</th><th>Résultat</th><th>Message</th></tr></thead><tbody>' +
      rg.slice(0, 6).map(function (r) {
        var b = r.result === "delivered" ? "b-ok" : r.result === "failed" ? "b-err" : "b-mute";
        return '<tr><td data-label="Heure" class="mono small">' + fmtTime(r.at) + '</td><td data-label="Bot" class="mono">' + esc(r.bot === "risk" ? "PM-Risk" : r.bot === "predict" ? "PM-Predict" : r.bot === "compound" ? "PM-Compound" : r.bot) + '</td><td data-label="Résultat"><span class="badge ' + b + '">' + esc(r.result_fr) + "</span>" + (r.http_status && r.result === "failed" ? ' <span class="xs muted">(code ' + r.http_status + ")</span>" : "") +
          '</td><td data-label="Message" class="wide small">' + (r.test ? '<span class="badge b-mute">essai</span> ' : "") + esc(r.message) + (r.pair ? ' <span class="mono xs">' + pairHtml(r.pair) + (r.price ? " " + price(r.price) : "") + "</span>" : "") + "</td></tr>";
      }).join("") + "</tbody></table></div>" : '<div class="xs muted" style="margin-top:4px">Aucun coup de sonnette.</div>');
    h += '<div class="xs muted" style="margin-top:6px">Source : tools/sonnette/state (état + journal des sonneries). Adresses et clés jamais affichées.</div></div>';
    return h;
  }

  function kv(l, v) { return '<div><div class="label">' + l + '</div><div class="mono">' + v + "</div></div>"; }
  // Règles communes : 2 règles officielles en haut, puis groupes repliés (Simulation, Live, Horaires, Surveillance, Équipe).
  function rulesHtml(TR) {
    if (!TR || !TR.available) return '<div class="card"><p class="empty">Fichier des règles introuvable (references/regles-litterature.md).</p></div>';
    var li = function (x) { return "<li>" + x + "</li>"; };
    var h = '<div class="card rules-card" id="rulescard" data-updated="' + esc(TR.updated_date || "") + '">' +
      '<div class="xs muted" style="margin-bottom:4px">Les 2 règles officielles</div><ol class="rules-top">' + (TR.official || []).map(li).join("") + "</ol>" +
      ((TR.official_note || []).length ? '<p class="small text2" style="margin:6px 0 10px">' + TR.official_note.join(" ") + "</p>" : "");
    h += (TR.groups || []).map(function (g) {
      var sc0 = g.scope === "sim" ? '<span class="badge b-sim">argent fictif</span>' : g.scope === "reel" ? '<span class="badge b-real">argent réel</span>' : '<span class="badge b-mute">simulation et réel</span>';
      return '<details class="rgroup" data-scope="' + esc(g.scope || "both") + '"><summary><span>' + esc(g.title) + ' <span class="xs muted">· ' + g.count + " règle" + (g.count > 1 ? "s" : "") + "</span> " + sc0 + "</span></summary>" +
        '<div class="inner md small">' + g.sections.map(function (sc) {
          return (sc.title && sc.title !== g.title ? '<div class="rsec">' + esc(sc.title) + "</div>" : "") + "<ul>" + sc.items.map(li).join("") + "</ul>";
        }).join("") + "</div></details>";
    }).join("");
    return h + '<p class="xs muted" style="margin:8px 0 0">Source unique : ' + esc(TR.source) + " (tenu par PM-Orchestrator).</p></div>";
  }
  function renderLog() {
    var s = STATE.data.summary, f = STATE.ui.logFilter || "Tous", lim = STATE.ui.logLimit || 15;
    var names = ["Tous"].concat(Array.from(new Set(s.log.map(function (e) { return e.script.replace(/ \(.*\)$/, ""); }))));
    el("logf").innerHTML = names.map(function (n) { return '<button class="chip' + (n === f ? " on" : "") + '" data-f="' + esc(n) + '">' + esc(n) + "</button>"; }).join("");
    Array.prototype.forEach.call(el("logf").querySelectorAll("button"), function (b) { b.onclick = function () { STATE.ui.logFilter = b.getAttribute("data-f"); STATE.ui.logLimit = 15; renderLog(); }; });
    var rows = s.log.filter(function (e) { return f === "Tous" || e.script.indexOf(f) === 0; });
    var st = function (x) { return x === "OK" ? "b-ok" : x === "ERREUR" ? "b-err" : x === "ALERTE" ? "b-warn" : "b-mute"; };
    var h = '<div class="table-wrap"><table class="rtable"><thead><tr><th>Programme</th><th>Début</th><th class="num">Durée</th><th class="num">Signaux</th><th class="num">Trades</th><th>Statut</th><th>Notes</th></tr></thead><tbody>' +
      rows.slice(0, lim).map(function (e) {
        return '<tr><td data-label="Programme" class="mono">' + esc(e.script) + '</td><td data-label="Début" class="mono" title="' + esc(e.time_label ? fmtDay(e.started) + " · " + e.time_label + " (heure non notée)" : fmtTime(e.started)) + '">' + (e.time_label ? esc(e.time_label) + '<div class="xs muted">' + fmtDay(e.started) + "</div>" : ago(e.started) + '<div class="xs muted">' + fmtTime(e.started) + "</div>") + '</td><td data-label="Durée" class="num">' + (e.duration != null ? esc(e.duration) : "") +
          '</td><td data-label="Signaux" class="num">' + (e.signals != null ? e.signals : "") + '</td><td data-label="Trades" class="num">' + (e.trades != null ? e.trades : "") + '</td><td data-label="Statut"><span class="badge ' + (e.status === "JOURNAL" && (e.kind === "problème" || e.kind === "alerte") ? "b-warn" : st(e.status)) + '">' + (e.status === "JOURNAL" ? (e.kind ? esc(e.emoji) + " " + esc(e.kind) : "note") : esc(e.status)) + '</span></td><td data-label="Notes" class="wide small text2 break">' + esc(e.notes) + '<div class="xs muted">' + esc(e.source) + "</div></td></tr>";
      }).join("") + "</tbody></table></div>" +
      (rows.length > lim ? '<button class="btn" id="more" style="margin-top:10px">Voir plus (' + (rows.length - lim) + ")</button>" : "") +
      '<p class="xs muted">« Durée » : non enregistrée par les programmes de l\'équipe (pas inventée). ✅ 📌 🔔 ⚠️ 💡 📜 = ligne du journal d\'un bot (section « Journal ») ; « soir », « après-midi » = heure non notée.</p>';
    el("logt").innerHTML = h;
    if (el("more")) el("more").onclick = function () { STATE.ui.logLimit = lim + 30; renderLog(); };
  }

  function decCard(x) {
    var yes = x.decision === "ACHETER" || x.decision === "VENDRE";
    return '<div class="card dec ' + (yes ? "yes" : "no") + '" style="margin-bottom:10px"><div class="card-title" style="margin-bottom:4px"><div><span class="mono"><b>' + esc(x.id) + "</b> · " + pairHtml(x.pair) + '</span> <span class="xs muted">' + esc(x.time_text) + "</span></div>" +
      '<div class="chips">' + badgeMode(x.mode) + (x.idea_type === "baisse" ? '<span class="ticon" title="Idée à la baisse">📉</span>' : x.idea_type === "hausse" ? '<span class="ticon" title="Idée à la hausse">📈</span>' : "") + '<span class="badge ' + (x.decision === "ACHETER" ? "b-buy" : x.decision === "VENDRE" ? "b-sell" : "b-mute") + '">' + esc(x.decision) + "</span></div></div>" +
      (x.idea && !x.title ? '<div class="small"><b>' + esc(x.idea) + "</b></div>" : "") +
      (x.side_text ? '<div class="small text2">Sens : ' + esc(x.side_text) + "</div>" : "") +
      (x.title ? '<div class="small"><b>' + esc(x.title) + "</b></div>" : "") +
      (x.why ? '<p class="why"><b>Pourquoi :</b> ' + esc(x.why) + "</p>" : (x.decision_text ? '<p class="why">' + esc(x.decision_text) + "</p>" : "")) +
      (x.gate_3x ? '<p class="why"><b>Gain ≥ 3× coût ?</b> ' + esc(x.gate_3x) + "</p>" : "") +
      (x.forecast ? '<p class="why"><b>Prévision :</b> ' + esc(x.forecast) + "</p>" : "") +
      (x.backtest ? '<p class="why"><b>Test du passé :</b> ' + esc(x.backtest) + "</p>" : "") +
      (x.score ? '<p class="why"><b>Résultat :</b> ' + esc(x.score) + "</p>" : "") +
      '<details><summary>Tout le détail</summary><div class="inner md"><ul>' + x.bullets.map(function (b) { return "<li>" + b + "</li>"; }).join("") + "</ul></div></details></div>";
  }

  function fmtMs(ms, withH) { var q = bxParts(new Date(ms)); return String(q.d).padStart(2, "0") + "/" + String(q.m).padStart(2, "0") + (withH ? " " + q.h + "h" + String(q.mi).padStart(2, "0") : ""); }
  function renderPair() {
    var P = STATE.data.performance, k = STATE.ui.pair, d = (P.pairs || {})[k]; if (!d || !el("pairbox")) return;
    var lp = livePrices(), live = (lp.pairs || {})[k] || {}, px = live.mid || d.price, st = d.stats, ho = d.holdings || {};
    function modeBox(mode) {
      var x = st[mode] || {}, hh = ho[mode];
      if (mode === "reel" && !hh) return '<div class="card flat"><div class="card-title"><h3>Réel</h3><span class="badge b-real">Réel</span></div><p class="small muted">Masqué.</p></div>';
      return '<div class="card flat"><div class="card-title"><h3>' + (mode === "sim" ? "Simulation" : "Réel") + "</h3>" + badgeMode(mode) + '</div><div class="kv">' +
        kv("Trades terminés", x.closed) + kv("Gain / perte (hausse + baisse)", '<span class="' + cls(x.pnl_eur) + '">' + eur(x.pnl_eur, 2, true) + "</span>") +
        kv("Taux de réussite", x.win_rate_pct == null ? "—" : pct(x.win_rate_pct, 0)) + kv("En cours", x.open) +
        (mode === "sim" ? kv("Détenu (simulé)", hh ? (hh.qty < 0 ? num(-hh.qty, 6) + ' <span class="badge b-sell">Vente</span><div class="xs muted">à racheter · ' + eur(-hh.value_eur) + "</div>" : num(hh.qty, 6) + '<div class="xs muted">' + eur(hh.value_eur) + "</div>") : "—") : kv("Pièces détenues", '<a href="index.html#reel">Accueil › Argent réel</a>')) + "</div></div>";
    }
    el("pairbox").innerHTML = '<div class="card"><div class="flow" style="justify-content:space-between;align-items:baseline"><div><div class="label">' + pairHtml(k) + ' · 7 derniers jours</div><div class="mid ' + cls(d.change_7d_pct) + '">' + pct(d.change_7d_pct, 2, true) + "</div></div>" +
      '<div class="small mono muted">bas ' + price(d.low_7d) + " · haut " + price(d.high_7d) + "</div></div>" +
      '<div class="xs muted" style="margin:4px 0 8px">Prix actuel et variation 24 h : dans la barre des prix en haut.</div>' +
      '<div class="chart-box"><canvas id="pc"></canvas></div>' +
      '<div class="chips xs" style="margin-top:8px"><span class="badge b-buy">△ achat simulé (creux)</span><span class="badge b-sell">▽ vente simulée (creux)</span><span class="badge b-buy">▲ achat réel (plein)</span><span class="badge b-sell">▼ vente réelle (plein)</span></div>' +
      '<p class="xs muted" style="margin:8px 0 0">Sources : ' + esc((d.sources || []).join(" + ")) + "." + (d.markers.length ? "" : " Aucun achat ni vente sur cette période.") + (d.markers_outside ? " " + d.markers_outside + " point(s) plus ancien(s) que 7 jours non affiché(s)." : "") + "</p></div>" +
      '<div class="grid g2" style="margin-top:12px">' + modeBox("sim") + modeBox("reel") + "</div>";
    drawPair(d, k);
  }
  function drawPair(d, k) {
    if (!window.Chart || !el("pc")) return;
    if (charts.pc) charts.pc.destroy();
    var narrow = window.innerWidth < 640;
    function mk(mode, side) { return d.markers.filter(function (m) { return m.mode === mode && m.side === side; }).map(function (m) { return { x: m.x, y: m.y, m: m }; }); }
    var SIDE = { achat: "#a78bfa", vente: "#f472b6" }, lc = CUR[k.split("-")[0]] || "#38bdf8";
    var ds = [{ label: k, data: d.series.map(function (p) { return { x: p[0], y: p[1] }; }), borderColor: lc, backgroundColor: lc + "14", fill: true, pointRadius: 0, borderWidth: 1.6, tension: 0.15, order: 5 }];
    [["sim", "achat"], ["sim", "vente"], ["reel", "achat"], ["reel", "vente"]].forEach(function (c) {
      var data = mk(c[0], c[1]); if (!data.length) return;
      ds.push({ type: "scatter", label: c[1] === "achat" ? (c[0] === "sim" ? "Achat simulé" : "Achat réel") : (c[0] === "sim" ? "Vente simulée" : "Vente réelle"), data: data, pointStyle: "triangle", rotation: c[1] === "vente" ? 180 : 0,
        pointRadius: narrow ? 7 : 9, pointHoverRadius: 11, backgroundColor: c[0] === "reel" ? SIDE[c[1]] : SIDE[c[1]] + "33", borderColor: SIDE[c[1]], borderWidth: 2, order: 1 });
    });
    charts.pc = new Chart(el("pc"), {
      type: "line", data: { datasets: ds },
      options: { responsive: true, maintainAspectRatio: false, animation: false, parsing: true, interaction: { mode: "nearest", intersect: false },
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          title: function (it) { return it.length ? fmtMs(it[0].parsed.x, true) : ""; },
          label: function (c) { var m = c.raw && c.raw.m; return m ? c.dataset.label + (m.sf ? " (idée à la baisse)" : "") + " : " + price(m.y) + (m.amount_eur ? " (" + eur(m.amount_eur) + ")" : "") : k + " : " + price(c.parsed.y); } } } },
        scales: { x: { type: "linear", min: d.series.length ? d.series[0][0] : undefined, max: d.series.length ? Math.max(d.series[d.series.length - 1][0], d.markers.reduce(function (a, m) { return Math.max(a, m.x); }, 0)) : undefined, ticks: { maxTicksLimit: narrow ? 4 : 8, maxRotation: 0, callback: function (v) { return fmtMs(v, false); } }, grid: { color: "#ffffff0a" } },
          y: { ticks: { callback: function (v) { return num(v, v >= 1000 ? 0 : 1) + " €"; } }, grid: { color: "#ffffff0a" } } } }
    });
  }

  function drawEquity(e) {
    if (!window.Chart || !el("eq")) return;
    var labels = e.labels.map(function (l) { var q = bxParts(new Date(l)); return String(q.d).padStart(2, "0") + "/" + String(q.m).padStart(2, "0") + " " + q.h + "h"; });
    var narrow = window.innerWidth < 640;
    if (charts.eq) charts.eq.destroy();
    Chart.defaults.color = "#8da0b8"; Chart.defaults.font.family = "ui-monospace, Menlo, monospace"; Chart.defaults.font.size = 11;
    charts.eq = new Chart(el("eq"), {
      type: "line",
      data: { labels: labels, datasets: [
        { label: "Portefeuille simulé", data: e.equity, borderColor: "#e2e8f0", backgroundColor: "#e2e8f014", fill: true, stepped: true, pointRadius: 0, borderWidth: 2 },
        { label: "Garder du BTC", data: e.hold_btc, borderColor: "#f7931a", borderDash: [5, 4], pointRadius: 0, borderWidth: 1.5, fill: false } ] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
        plugins: { legend: { labels: { boxWidth: 12 } }, tooltip: { callbacks: { label: function (c) { return c.dataset.label + " : " + eur(c.parsed.y); } } } },
        scales: { x: { ticks: { maxTicksLimit: narrow ? 4 : 8, maxRotation: 0, autoSkipPadding: 12 }, grid: { color: "#ffffff0a" } }, y: { ticks: { callback: function (v) { return num(v, 0) + " €"; } }, grid: { color: "#ffffff0a" } } } }
    });
  }

  // ------------------------------------------------------------ RESEARCH
  function fgFr(v) { return v == null ? "—" : v <= 24 ? "Peur extrême" : v <= 44 ? "Peur" : v <= 55 ? "Neutre" : v <= 75 ? "Avidité" : "Avidité extrême"; }
  function fgColor(v) { return v <= 24 ? "#ef4444" : v <= 44 ? "#f97316" : v <= 55 ? "#eab308" : v <= 75 ? "#84cc16" : "#22c55e"; }
  function objToHtml(o) {
    if (o == null) return "";
    if (typeof o !== "object") return esc(o);
    if (Array.isArray(o)) return "<ul>" + o.map(function (x) { return "<li>" + objToHtml(x) + "</li>"; }).join("") + "</ul>";
    return "<ul>" + Object.keys(o).map(function (k) { return "<li><b>" + esc(k.replace(/_/g, " ")) + " :</b> " + objToHtml(o[k]) + "</li>"; }).join("") + "</ul>";
  }
  // Zones de prix de PM-Predict (state/zones_reveil.json → summary.sonnette.zones : même paquet /api/live que le reste).
  // « sous » = idée à la baisse, « au-dessus » = idée à la hausse. Statut et écart recalculés ici à chaque nouveau prix.
  function zoneUp(z) { return !(String(z.side || "").indexOf("sous") === 0 || z.side === "below"); }
  function zoneOn(z) { return z.enabled !== false && (!z.expire || new Date(z.expire) > new Date()); }
  function renderZones() {
    var box = el("zonesbox"); if (!box) return;
    var so = (STATE.data.summary || {}).sonnette || {}, lp = livePrices(), ORD = { BTC: 0, ETH: 1, SOL: 2 };
    var zs = (so.zones || []).filter(function (z) { return String(z.bot || "predict").toLowerCase().indexOf("predict") >= 0; }).sort(function (a, b) {
      var pa = String(a.pair).split("-")[0], pb = String(b.pair).split("-")[0];
      return ((ORD[pa] != null ? ORD[pa] : 9) - (ORD[pb] != null ? ORD[pb] : 9)) || String(a.pair).localeCompare(String(b.pair)) || (a.price - b.price);
    });
    if (!zs.length) { box.innerHTML = '<p class="empty">Aucune zone pour l’instant. Predict les refait chaque jour vers 14h55.</p>'; return; }
    box.innerHTML = '<div class="table-wrap"><table class="rtable"><thead><tr><th>Paire</th><th>Idée</th><th class="num">Zone</th><th>Jusqu’à</th><th>Statut</th><th class="num">Prix actuel · écart</th></tr></thead><tbody>' + zs.map(function (z) {
      var up = zoneUp(z), on = zoneOn(z), px = ((lp.pairs || {})[z.pair] || {}).mid, gap = px && z.price ? (z.price - px) / px * 100 : null;
      var hit = px != null && (up ? px >= z.price : px <= z.price);
      var st = z.enabled === false ? ["b-mute", "coupée"] : on ? ["b-info", "⏳ active"] : ["b-mute", "expirée"];
      return '<tr><td data-label="Paire" class="mono nowrap">' + pairHtml(z.pair) + '</td><td data-label="Idée" class="nowrap"' + (z.reason ? ' title="' + esc(z.reason) + '"' : "") + ">" + (up ? "📈 à la hausse" : "📉 à la baisse") +
        '</td><td data-label="Zone" class="num nowrap"><b>' + (up ? "↑ " : "↓ ") + price(z.price) + '</b></td><td data-label="Jusqu’à" class="mono small nowrap">' + fmtTime(z.expire) +
        '</td><td data-label="Statut"><span class="badge ' + st[0] + '">' + st[1] + '</span></td><td data-label="Prix actuel · écart" class="num nowrap">' + (px != null ? price(px) + ' <span class="xs ' + (hit ? "warn" : "muted") + '">' + (hit ? "🔔 atteinte" : "à " + pct(gap, 1, true)) + "</span>" : "—") + "</td></tr>";
    }).join("") + "</tbody></table></div>" +
      '<p class="xs muted" style="margin:6px 0 0">📈 si le prix passe au-dessus de la zone, 📉 s’il passe en dessous : la sonnette réveille Predict pour revoir l’idée. Aucun ordre automatique. Écart = chemin qui reste depuis le prix actuel.</p>';
  }
  function renderResearch() {
    var R = STATE.data.research, fg = R.fear_greed, lr = R.last_research || {}, lp = R.last_predict || {};
    var h = '<h1 class="page-title">Analyses</h1><p class="lead">Le point marché de PM-Research, les prévisions de PM-Predict (zones de prix et avis) et l\'humeur générale du marché.</p>'; var hm = '<div class="grid g2">';
    if (fg && fg.fear_greed_now) {
      var v = fg.fear_greed_now.value, l7 = ((fg.history || {}).last_7 || []).slice().reverse();
      hm += '<div class="card"><div class="card-title"><h3>Humeur du marché</h3><span class="xs muted">Fear &amp; Greed · 0 = peur, 100 = avidité</span></div><div class="gauge"><div class="val" style="color:' + fgColor(v) + '">' + v + '</div><div><div class="mid">' + fgFr(v) + '</div><div class="xs muted">moyenne 30 j : ' + num((fg.history || {}).avg, 1) + "</div></div></div>" +
        '<div class="fg-bars" style="margin-top:12px">' + l7.map(function (x) { return '<div title="' + esc(x.date) + " : " + x.value + '" style="height:' + x.value + '%;background:' + fgColor(x.value) + '"></div>'; }).join("") + '</div><div class="flow xs muted" style="justify-content:space-between"><span>' + esc((l7[0] || {}).date || "") + "</span><span>" + esc((l7[l7.length - 1] || {}).date || "") + "</span></div>" +
        '<div class="xs muted" style="margin-top:6px">Vaut pour toutes les cryptos (surtout BTC). Source : alternative.me' + (fg.fetched_at ? " · lu " + ago(fg.fetched_at) : "") + "</div></div>";
    } else hm += '<div class="card"><h3>Humeur du marché</h3><p class="empty">Indisponible.</p></div>';
    hm += '<div class="card"><div class="card-title"><h3>Dernier point PM-Research</h3><span class="xs muted">' + fmtTime(lr.briefed_at) + "</span></div>" +
      '<div class="small text2">' + esc(lr.cycle || "") + (lr.prix ? " · Prix : " + prixHtml(lr.prix) : "") + '</div><div class="md small">' + objToHtml(lr.resume) + "</div>" + (lr.sources_note ? '<div class="xs muted">' + esc(lr.sources_note) + "</div>" : "") + "</div></div>";
    var so = (STATE.data.summary || {}).sonnette || {};
    var hp = '<section class="section">' + secHead("Zones de prix du jour", "PM-Predict · mises à jour " + fmtTime(so.zones_updated) + " · refaites chaque jour vers 14h55") + '<div class="card"><div id="zonesbox"></div></div></section>' +
      '<section class="section">' + secHead("Avis PM-Predict", "dernier cycle : " + fmtTime(lp.predicted_at)) + '<div class="card">' + '<div class="small text2">' + esc(lp.cycle || "") + "</div>" +
      (lp.signals ? '<div class="table-wrap"><table class="rtable"><thead><tr><th>Décision</th><th>Paire</th><th class="num">Dernier prix</th><th>Avis</th><th>Mesurable</th></tr></thead><tbody>' + lp.signals.map(function (s) {
        return '<tr><td data-label="Décision" class="mono">' + esc(s.decision_id) + '</td><td data-label="Paire" class="mono">' + pairHtml(s.pair) + '</td><td data-label="Dernier prix" class="num">' + price(s.mid_eur) + (s.mid_stale ? ' <span class="badge b-warn">ancien</span>' : "") + '</td><td data-label="Avis"><span class="badge ' + (s.decision === "NO_TRADE" ? "b-err" : "b-ok") + '">' + (s.decision === "NO_TRADE" ? "Pas acheter" : esc(s.decision)) + '</span></td><td data-label="Mesurable">' + (s.measurable ? "oui" : "non") + "</td></tr>";
      }).join("") + "</tbody></table></div>" : "") + (lp.handoff ? '<p class="small text2"><b>Passage de relais :</b> ' + esc(lp.handoff) + "</p>" : "") + "</div>" +
      "</section>";
    // Bilans « Test du passé » / cartes sans id D-xxx : exclus (filtre aussi côté build.py).
    var D = (R.decisions || []).filter(function (x) {
      var id = String((x && x.id) || "").trim();
      if (!/^D-\d+$/.test(id)) return false;
      if (!id && !(x.title || "").trim() && !(x.idea || "").trim()) return false;
      return true;
    }), df = STATE.ui.decf || "all", dl = STATE.ui.decLimit || 6;
    var isNo = function (x) { return !(x.decision === "ACHETER" || x.decision === "VENDRE"); };
    var dfl = D.filter(function (x) { return df === "all" || (df === "va" && x.kind === "sell_first") || (df === "oui" && !isNo(x)) || (df === "non" && isNo(x)); });
    var hd = '<section class="section" id="decisions">' + secHead("Décisions écrites", "le carnet de l'équipe, y compris les idées refusées (knowledge/decision_log.md)") +
      chipsBar([["all", "Toutes", D.length], ["oui", "Achat / vente décidé", D.filter(function (x) { return !isNo(x); }).length], ["non", "Refusées", D.filter(isNo).length], ["va", "Idée à la baisse", D.filter(function (x) { return x.kind === "sell_first"; }).length]], df, "df") +
      (dfl.length ? dfl.slice(0, dl).map(decCard).join("") : '<p class="empty">Aucune décision pour ce filtre.</p>') +
      (dfl.length > dl ? '<button class="btn" id="decmore">Voir plus (' + (dfl.length - dl) + ")</button>" : "") + "</section>";
    var t = R.scorecard.totals || {};
    var hs = '<section class="section">' + secHead("Score des prévisions", "mis à jour " + ago(R.scorecard.updated)) + '<div class="chips" style="margin-bottom:8px"><span class="badge b-ok">Gagnées ' + (t.gagne != null ? t.gagne : "—") + '</span><span class="badge b-err">Perdues ' + (t.perdu != null ? t.perdu : "—") + '</span><span class="badge b-mute">Annulées ' + (t.annule != null ? t.annule : "—") + '</span><span class="badge b-info">Réussite ' + esc(t.taux || "—") + '</span></div><details><summary>Détail du score</summary><div class="inner md">' + R.scorecard.html + "</div></details></section>";
    var ha = '<section class="section">' + secHead("Archives des points marché", "points précédents (le dernier est dans l’onglet Marché)") + ((R.briefs || []).length > 1 ? "" : '<p class="empty">Pas encore d’archive.</p>') + (R.briefs || []).slice(1).map(function (b, i) {
      return "<details><summary><span>" + fmtTime(b.time) + " · " + esc((b.data && b.data.cycle) || "Point marché") + '</span></summary><div class="inner md">' + (b.html || "") + (b.data ? objToHtml(b.data.resume || b.data) : "") + '<div class="xs muted">' + esc(b.files.join(", ")) + "</div></div></details>";
    }).join("") + "</section>";
    // Journaux : 2e barre d'onglets, un onglet par bot (+ journal des échecs)
    var JLBL = { "grok-bot": "Grok Bot" };   // libellés spéciaux ; Grok Bot en dernier, après les bots PM-*
    var JN = Object.keys(R.journals || {}).sort(function (a, b) { return (a === "grok-bot") - (b === "grok-bot") || a.localeCompare(b); })
      .map(function (k) { return [k, JLBL[k] || k.replace("pm-", "PM-").replace(/-(\w)/, function (m, c) { return "-" + c.toUpperCase(); }), R.journals[k]]; });
    if (R.failure_log && R.failure_log.html) JN.push(["echecs", "Échecs", R.failure_log]);
    var jcur = JN.some(function (x) { return x[0] === STATE.ui.journal; }) ? STATE.ui.journal : (JN[0] || [])[0], jsel = JN.filter(function (x) { return x[0] === jcur; })[0];
    var JLG = ((R.journal_legend || {}).items || []);   // légende : references/format-journal.md (build.py)
    var hj = '<section class="section">' + secHead("Journaux des bots", "ce que chaque bot a noté") +
      (JLG.length ? '<p class="jlegend xs muted" id="jlegend">' + JLG.map(function (x) { return '<span class="nowrap">' + esc(x[0]) + " " + esc(x[1]) + "</span>"; }).join(" · ") + "</p>" : "") +
      '<div class="tabs sub" role="tablist">' + JN.map(function (x) { return '<button class="tab' + (x[0] === jcur ? " on" : "") + '" data-j="' + x[0] + '">' + esc(x[1]) + "</button>"; }).join("") + "</div>" +
      (jsel ? '<div class="card"><div class="xs muted" style="margin-bottom:6px">mis à jour ' + ago(jsel[2].updated) + '</div><div class="md">' + jsel[2].html + "</div></div>" : '<p class="empty">Aucun journal.</p>') + "</section>";
    var RT = [["marche", "Marché"], ["predict", "Prévisions"], ["decisions", "Décisions écrites"], ["score", "Score"], ["archives", "Archives"], ["journaux", "Journaux des bots"]];
    var tab = getTab(RT.map(function (x) { return x[0]; }), "marche");
    h += tabsBar(RT, tab) + { marche: hm, predict: hp, decisions: hd, score: hs, archives: ha, journaux: hj }[tab];
    el("app").innerHTML = h;
    renderZones();
    bindTabs(renderResearch);
    Array.prototype.forEach.call(document.querySelectorAll("[data-j]"), function (b) { b.onclick = function () { STATE.ui.journal = b.getAttribute("data-j"); renderResearch(); }; });
    bindChips("df", "decf", function () { STATE.ui.decLimit = 6; renderResearch(); });
    if (el("decmore")) el("decmore").onclick = function () { STATE.ui.decLimit = dl + 20; renderResearch(); };

  }

  // ------------------------------------------------------------ NEWS
  function renderNews() {
    var N = STATE.data.news, src = STATE.ui.src || "Tous", tag = STATE.ui.tag || "";
    var items = (N.items || []).filter(function (x) { return (src === "Tous" || x.source === src) && (!tag || x.tags.indexOf(tag) >= 0); });
    var counts = {}; (N.items || []).forEach(function (x) { counts[x.source] = (counts[x.source] || 0) + 1; });
    var h = '<h1 class="page-title">Actualités <span class="badge ' + (newsFresh(N) ? "b-ok" : "b-warn") + '" style="vertical-align:middle"><span class="dot' + (newsFresh(N) ? " ok" : "") + '"></span>' + ago(N.generated_at) + '</span></h1><p class="lead">Les titres de CoinDesk, CoinTelegraph et Decrypt (en anglais), relus toutes les 5 minutes' + (hosted() ? " (ici, version en ligne publiée toutes les ~" + (STATE.deploy.interval_min || 15) + " min)" : "") + '. Les articles qui parlent de BTC, ETH ou SOL sont mis en avant.</p>';
    h += '<div class="chips" style="margin-bottom:8px">' + ["Tous", "CoinDesk", "CoinTelegraph", "Decrypt"].map(function (s) {
      return '<button class="chip' + (s === src ? " on" : "") + '" data-s="' + s + '">' + s + ' <span class="n">' + (s === "Tous" ? (N.items || []).length : counts[s] || 0) + "</span></button>";
    }).join("") + '</div><div class="chips" style="margin-bottom:16px">' + ["BTC", "ETH", "SOL"].map(function (t) {
      return '<button class="chip' + (t === tag ? " on" : "") + '" data-g="' + t + '">' + t + ' <span class="n">' + (N.items || []).filter(function (x) { return x.tags.indexOf(t) >= 0; }).length + "</span></button>";
    }).join("") + "</div>";
    var bad = Object.keys(N.sources || {}).filter(function (k) { return !N.sources[k].ok; });
    if (bad.length) h += '<div class="notice warn" style="margin-bottom:12px">Source(s) injoignable(s) au dernier passage : ' + esc(bad.join(", ")) + " (anciens titres gardés).</div>";
    if (!items.length) h += '<p class="empty">Aucun article.</p>';
    else {
      var top = items[0];
      h += '<a class="news-item news-top' + (top.tags.length ? " hl" : "") + '" href="' + esc(top.link) + '" target="_blank" rel="noopener noreferrer"><div class="meta"><span class="badge b-info">À la une</span><span>' + esc(top.source) + "</span><span>" + ago(top.published) + "</span>" + tagsHtml(top) + "</div><h3>" + esc(top.title) + "</h3><p>" + esc(top.summary) + '</p><div class="small" style="margin-top:8px;color:var(--info)">Lire l\'article ↗</div></a>';
      h += '<div class="grid g2" style="margin-top:12px">' + items.slice(1, 80).map(function (x) {
        return '<a class="news-item' + (x.tags.length ? " hl" : "") + '" href="' + esc(x.link) + '" target="_blank" rel="noopener noreferrer"><div class="meta"><span>' + esc(x.source) + "</span><span>" + ago(x.published) + '</span><span class="muted">' + fmtTime(x.published) + "</span>" + tagsHtml(x) + "</div><h3>" + esc(x.title) + "</h3><p>" + esc(x.summary) + "</p></a>";
      }).join("") + "</div>";
    }
    h += '<p class="xs muted" style="margin-top:14px">Liste mise à jour ' + ago(N.generated_at) + "." + (hosted() ? "" : " Aussi disponible pour les bots : /workspace/dashboard/data/news.json") + "</p>";
    el("app").innerHTML = h;
    Array.prototype.forEach.call(document.querySelectorAll("[data-s]"), function (b) { b.onclick = function () { STATE.ui.src = b.getAttribute("data-s"); renderNews(); }; });
    Array.prototype.forEach.call(document.querySelectorAll("[data-g]"), function (b) { b.onclick = function () { var g = b.getAttribute("data-g"); STATE.ui.tag = STATE.ui.tag === g ? "" : g; renderNews(); }; });
  }
  function newsFresh(N) { var a = N && N.generated_at ? (Date.now() - new Date(N.generated_at).getTime()) / 60000 : 1e9; return a < (hosted() ? 40 : 15); }
  function tagsHtml(x) { return x.tags.map(function (t) { return '<span class="badge b-ok">' + t + "</span>"; }).join(""); }

  // ------------------------------------------------------------ ABOUT
  function renderAbout() {
    var s = STATE.data.summary, ru = s.rules;
    var team = [["PM-Scan", "Relève les prix de BTC, ETH et SOL en euros et signale ce qui bouge anormalement."], ["PM-Research", "Lit les nouvelles et résume l'ambiance du marché en français simple."],
      ["PM-Predict", "Dit pour chaque crypto « acheter » ou « ne pas acheter », avec une prévision qu'on peut vérifier."], ["PM-Risk", "Le gardien : accepte ou refuse chaque achat et surveille les pertes."],
      ["PM-Compound", "Fait le bilan après chaque vente, note les prévisions et tire les leçons."], ["PM-Orchestrator", "Le chef d'orchestre : fait passer le relais entre les autres."]];
    var h = '<h1 class="page-title">À propos</h1><p class="lead">Équipe trading est une petite équipe de programmes qui apprend à trader des cryptos prudemment. Ce site montre tout ce qu\'elle fait, en simulation comme en réel, sans rien cacher.</p>';
    h += '<section class="section">' + secHead("L'équipe", "qui fait quoi") + '<div class="grid g3">' + team.map(function (t) { return '<div class="card"><h3 class="mono">' + t[0] + '</h3><p class="small text2" style="margin:0">' + t[1] + "</p></div>"; }).join("") + "</div>" +
      '<div class="notice" style="margin-top:12px">Le chemin d\'une idée : <b>Scan</b> (prix) → <b>Research</b> (contexte) → <b>Predict</b> (avis écrit) → <b>Risk</b> (oui / non) → achat → vente → <b>Compound</b> (bilan et leçon).</div></section>';
    // Règles : UNE seule place sur le site (ici). Source unique : references/regles-litterature.md (PM-Orchestrator),
    // lu par build.py → summary.team_rules (même paquet /api/live). Aucune copie en dur.
    var TR = s.team_rules || {};
    h += '<section class="section" id="regles">' + secHead("Règles communes", TR.updated_label ? "mises à jour le " + esc(TR.updated_label) : "") + rulesHtml(TR) + "</section>";
    h += '<section class="section">' + secHead("Comment marche ce site", "") + '<div class="card small text2"><p style="margin-top:0">Un petit script (build.py) relit toutes les 5 minutes les fichiers de l\'équipe, les prix publics, les soldes (en lecture seule) et les flux d\'actualités, puis fabrique ce site. <b>Aucune IA n\'est utilisée</b> pour le site et aucun ordre ne peut être passé d\'ici. Les pages se rechargent toutes les 60 secondes. Toutes les heures sont celles de Bruxelles.' + (hosted() ? " <b>Version en ligne</b> : une copie est publiée sur Cloudflare Pages toutes les ~" + (STATE.deploy.interval_min || 15) + " min (dernière publication " + ago(STATE.deploy.deployed_at) + "), protégée par mot de passe ; les chiffres peuvent donc avoir jusqu'à ~15 min de retard." : "") + '</p>' +
      "<p>Les soldes réels et l'adresse du portefeuille sont privés : ils ne s'affichent que si l'option SHOW_REAL est activée (actuellement : <b>" + (s.show_real ? "activée" : "désactivée") + "</b>). " + (hosted() ? "Cette version en ligne est protégée par identifiant et mot de passe." : "Pour une version en ligne, il faut la désactiver ou protéger le site par un mot de passe.") + "</p>" +
      "<p style='margin-bottom:0'>Inspiré de la mise en page d'un tableau de bord de trading public ; données, textes et code propres à Équipe trading. Ce n'est pas un conseil financier.</p></div></section>";
    el("app").innerHTML = h;
  }

  // ------------------------------------------------------------ boot
  // Sur mobile les tableaux deviennent des cartes : chaque cellule a un libellé + une valeur emballée.
  function wrapCells(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll("table.rtable td:not([data-w])"), function (td) {
      td.setAttribute("data-w", "1");
      if (!td.firstChild) return;
      var v = document.createElement("div"); v.className = "cv";
      while (td.firstChild) v.appendChild(td.firstChild);
      td.appendChild(v); td.setAttribute("data-w", "1");
    });
  }
  var mo = new MutationObserver(function () { wrapCells(document); });
  mo.observe(document.getElementById("app"), { childList: true, subtree: true });
  function renderPage() {
    try {
      ({ index: renderHome, trades: renderTrades, performance: renderPerformance, research: renderResearch, news: renderNews, about: renderAbout }[PAGE] || renderHome)();
    } catch (e) { el("app").innerHTML = '<div class="notice warn">Erreur d\'affichage : ' + esc(e.message) + "</div>"; console.error(e); }
  }
  function refreshPrices() {
    return load("prices").then(function (d) { STATE.data.prices = d; renderPriceBar(); if (PAGE === "performance" && STATE.ui.pairLive) STATE.ui.pairLive(); if (PAGE === "research") renderZones(); }).catch(function () {});
  }
  function loadDeploy() { return load("deploy").then(function (d) { STATE.deploy = d; }).catch(function () { STATE.deploy = null; }); }
  loadDeploy().then(refresh).then(function () { if (!STATE.api) return refreshPrices(); });
  setInterval(loadDeploy, 300000);
  setInterval(function () { if (STATE.api) refresh(); else refreshPrices(); }, 30000);   // D1 : tout toutes les 30 s ; sinon prix seuls
  setInterval(function () { if (!STATE.api) refresh(); }, 60000);                          // fichiers : données toutes les 60 s
  setInterval(tickCountdowns, 1000);                                                       // comptes à rebours des cycles
  window.addEventListener("hashchange", function () { if (STATE.data.summary) renderPage(); });
  setInterval(renderFresh, 5000);                                                          // âges de l'en-tête (« il y a X s »)
  setInterval(function () {                // « il y a X min » + barres de progression
    if (PAGE === "index" && STATE.data.summary && el("cycles")) el("cycles").innerHTML = STATE.data.summary.cycles.map(cycleCard).join("");
    if (PAGE === "index" && el("rrun")) renderRuns();                                      // « En cours » → « Pas fini » après 30 min
  }, 15000);
  window.addEventListener("resize", function () { if (charts.eq) charts.eq.resize(); if (charts.pc) charts.pc.resize(); });
})();
