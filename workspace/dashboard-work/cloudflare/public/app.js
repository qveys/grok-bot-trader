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
      if (!STATE.data.summary) el("app").innerHTML = '<div class="notice warn">Impossible de lire les données (' + esc(e.message) + ') : le site n’a pas encore été fabriqué.</div>';
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
      '<span class="badge b-mute" title="state/live_day.json tel quel">Achats réels : ' + ((ru.live_day || {}).count != null ? ru.live_day.count : "—") + (ru.max_live_per_day != null ? " / " + ru.max_live_per_day : "") + ((ru.live_day || {}).date ? " le " + fmtDay(ru.live_day.date) : "") + "</span>" +
      '<span class="badge b-mute">Achat réel préparé : ' + (ru.live_once_armed ? "oui" : "non") + "</span></div>";
    // Bandeau « Nuit sans décision » : lu seulement dans status.json de la sonnette (night_sans_decision === true).
    // Heures de la nuit = celles écrites par la sonnette (detail.debut / detail.fin) ; drapeau non écrit → note neutre.
    var so_ = s.sonnette || {}, nd_ = so_.night_sans_decision_detail || {};
    var hmBx = function (iso) { if (!iso || isNaN(new Date(iso))) return null; var q = bxParts(new Date(iso)); return q.h + "h" + String(q.mi).padStart(2, "0"); };
    // Libellé : date (début de la nuit) et fenêtre écrites par la sonnette ; sinon debut / fin. Reste affiché toute la journée.
    var MOIS_ = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    var dNuit_ = String(nd_.date || nd_.nuit || ""), dm_ = /^(\d{4})-(\d{2})-(\d{2})/.exec(dNuit_);
    var dFr_ = dm_ ? (+dm_[3]) + " " + MOIS_[+dm_[2] - 1] : dNuit_ || null;
    var win_ = nd_.fenetre ? String(nd_.fenetre) : hmBx(nd_.debut) && hmBx(nd_.fin) ? hmBx(nd_.debut) + "–" + hmBx(nd_.fin) : "";
    if (so_.night_sans_decision === true) {
      h += '<div class="notice err" id="nuit-sans-decision" role="alert"><b>« Nuit sans décision »</b> — la nuit dernière' + (dFr_ ? " (" + esc(dFr_) + ")" : "") + (win_ ? ", " + esc(win_) : "") +
        ' <span class="small">: PM-Predict n’a écrit aucune décision.</span></div>';
    } else if (so_.night_sans_decision !== false) {
      h += '<div class="notice" id="nuit-pas-evaluee"><b>Nuit pas évaluée</b> — la sonnette n’a pas dit si PM-Predict a écrit une décision cette nuit.</div>';
    }
    var DDh = s.decision_duplicates || [];
    if (DDh.length) h += '<p id="dec-dup-note" class="small warn" style="margin:6px 0">⚠️ Numéro de décision en double (' + DDh.map(function (d) { return esc(d.id); }).join(", ") +
      ') : Predict doit le corriger · <a href="research.html#decisions">voir</a></p>';
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

  // Position ouverte : tout vient de guardian/state.json (PM-Risk) ; o.side = side du gardien (short → Vente, long → Achat).
  function openPosHtml(o) {
    var v = o.side === "vente";
    return '<div class="openpos" data-side="' + esc(o.side) + '" data-id="' + esc(o.id) + '">' + pairHtml(o.pair) + " " + sideBadge(o.side) + " " + num(o.qty, 6) + " à " + price(o.entry_price) +
      (o.target_price != null ? " · " + (v ? "rachat prévu " : "objectif ") + price(o.target_price) : "") +
      " · stop " + price(o.stop_price) + " · valeur gardien " + eur(o.mark_eur) +
      " · résultat latent " + (o.unrealized_eur != null ? '<span class="' + cls(o.unrealized_eur) + '">' + eur(o.unrealized_eur, 2, true) + (o.unrealized_pct != null ? " (" + pct(o.unrealized_pct, 2, true) + ")" : "") + "</span>" : '<span class="muted">non écrit</span>') +
      '<div class="xs muted">' + (v ? "Idée à la baisse" : "Idée à la hausse") + (o.decision_id ? " · " + esc(o.decision_id) : "") + " · simulation" +
      (o.last_mid_eur != null ? " · dernier prix " + price(o.last_mid_eur) : "") + (o.mark_ts ? " · évalué " + ago(o.mark_ts) : "") + "</div></div>";
  }
  // Contrôle avec Revolut X : guardian/state.json → rapprochement_revolut (PM-Risk), TEL QUEL. Le site n'additionne rien.
  // Champ absent → « pas évalué » ; texte (ex. « sans objet ») → recopié, « (simulation) » ajouté si PM-Risk écrit mode=simulation.
  function rapproVal(v, raw, money) {
    if (v == null) return '<span class="muted">pas évalué</span>';
    if (typeof v === "number") return money ? '<span class="' + cls(v) + '">' + eur(v, 2, true) + "</span>" : num(v, 2);
    var t = String(v);
    if (/^\s*sans objet\s*$/i.test(t) && String(raw.mode || "").toLowerCase() === "simulation") t += " (simulation)";
    return '<span class="muted">' + esc(t) + "</span>";
  }
  function reconHtml(p) {
    var R = p.rapprochement || {}, r = R.raw;
    var head = '<b>Contrôle avec Revolut X</b> <span class="muted">(PM-Risk)</span> : ';
    if (!R.present || !r) return '<div class="xs recon" id="rappro" data-present="false" style="margin-top:8px">' + head + '<span class="muted">pas évalué</span> — PM-Risk n’a pas encore écrit ce contrôle.</div>';
    var ec = typeof r.ecart_eur === "number" ? (r.ecart_eur == null ? "" : eur(r.ecart_eur, 2, true)) : null;
    return '<div class="xs recon" id="rappro" data-present="true" style="margin-top:8px" title="' + esc(R.source || "") + '">' + head +
      '<span class="nw">gain de l’équipe <b data-k="gain_equipe_eur">' + rapproVal(r.gain_equipe_eur, r, true) + "</b></span> · " +
      '<span class="nw">gain chez Revolut <b data-k="gain_revolut_eur">' + rapproVal(r.gain_revolut_eur, r, true) + "</b></span> · " +
      '<span class="nw">écart <b data-k="ecart_eur">' + (ec != null ? ec : rapproVal(r.ecart_eur, r, false)) + "</b></span>" +
      '<div class="muted">' + (r.controle_at ? "Contrôlé " + fmtTime(r.controle_at) + " (" + ago(r.controle_at) + ")" : "Heure du contrôle : pas écrite") + (r.note ? " · " + esc(r.note) : "") + "</div></div>";
  }
  function homeOverview(s) {
    var p = s.paper, ru = s.rules;
    var h = '<section class="section">' + secHead("Portefeuille", "simulation et argent réel sont séparés") + '<div class="grid g2">';
    h += '<div class="card"><div class="card-title"><h3>Simulation</h3><span class="badge b-sim">Argent fictif</span></div>' +
      '<div class="flow"><div><div class="label">Départ</div><div class="mid text2">' + eur(p.invested_eur) + '</div></div><div class="arrow">→</div>' +
      '<div><div class="label">Valeur (gardien)</div><div class="big" id="paper-equity">' + eur(p.balance_eur) + "</div>" +
      (p.total_pnl_eur != null ? '<div class="small mono ' + cls(p.total_pnl_eur) + '" id="paper-total" title="total_pnl_eur (gardien)">' + eur(p.total_pnl_eur, 2, true) + "</div>" : "") + "</div></div>" +
      '<hr class="sep"><div class="kv k3">' + kv("Liquidités", '<span id="paper-cash">' + eur(p.cash_eur) + "</span>") + kv("Sommet", '<span id="paper-peak">' + eur(p.peak_equity_eur) + "</span>") +
      kv("Baisse depuis le sommet", pct(p.drawdown_pct == null ? null : p.drawdown_pct * 100, 2)) + kv("Résultat du jour", '<span class="' + cls(p.daily_pnl_eur) + '">' + eur(p.daily_pnl_eur, 2, true) + '</span><div class="xs muted">' + (p.daily_pnl_date ? fmtDay(p.daily_pnl_date) : "") + "</div>") +
      kv("Positions ouvertes", p.open_positions) + kv("Exposé (simulation)", (p.exposure_eur != null ? '<span id="paper-exposure">' + eur(p.exposure_eur) + "</span> · " + pct(p.exposure_pct * 100, 1) : "—") + '<div class="xs muted">plafond ' + (p.cap_pct != null ? pct(p.cap_pct * 100, 0) : "—") + "</div>") + "</div>" + reconHtml(p) +
      (p.open_list.length ? '<div class="small" style="margin-top:10px">' + p.open_list.map(openPosHtml).join("") + "</div>" : "") +
      '<div class="xs muted" style="margin-top:10px" title="guardian/state.json">Chiffres de PM-Risk, mis à jour <span id="paper-updated" data-ts="' + esc(p.summary_updated_at || "") + '">' + fmtTime(p.summary_updated_at || p.updated_at) + " (" + ago(p.summary_updated_at || p.updated_at) + ")</span>. Tels quels." +
      (p.lock_busy ? ' <span class="warn">Fichier verrouillé par Risk pendant la lecture : dernière copie.</span>' : "") + "</div>" +
      '<div class="links"><a href="performance.html#simulation">Résultats des trades simulés →</a></div></div>';
    h += realOverviewCard(s);
    h += "</div></section>";
    h += homeCycles(s);
    h += '<p class="xs muted">Règles de l’équipe (simulation et réel) : page <a href="about.html#regles">À propos</a>.</p>';
    return h;
  }

  // Argent réel : chiffres de state/live_equity.json (écrit par tools/sonnette/live_equity.py) tels quels ; aucun total recalculé.
  function realOverviewCard(s) {
    var r = s.real || {}, le = s.live_equity || {}, mm = le.metamask || {};
    if (r.hidden) return '<div class="card"><div class="card-title"><h3>Argent réel</h3><span class="badge b-real">Réel</span></div><div class="notice">Soldes réels masqués (SHOW_REAL=false).</div></div>';
    var h = '<div class="card"><div class="card-title"><h3>Argent réel</h3><span class="badge b-real">Réel · lecture seule</span></div>';
    if (le.present) {
      var hb = le.hors_bot || {};
      h += '<div class="label">Capital du bot</div><div class="big" id="real-capital">' + eur(le.capital_reel) + '</div><div class="xs muted">' + (le.stale ? '<span class="warn">pas à jour</span> · ' : "") + "écrit " + ago(le.ts) + "</div>" +
        '<div class="kv k3" style="margin-top:10px">' + kv("Perte du jour", '<span class="' + cls(-(le.perte_jour_pct || 0)) + '">' + pct(le.perte_jour_pct, 2) + "</span>") +
        kv("Baisse depuis le plus haut", le.baisse_depuis_plus_haut_pct == null ? "— <span class='xs muted'>(pas encore de plus haut)</span>" : pct(le.baisse_depuis_plus_haut_pct, 2)) +
        kv("Référence du jour", le.ref_jour ? eur(le.ref_jour.valeur) : "—") + "</div>" +
        '<div class="small" style="margin-top:8px"><b>Pièces de Quentin (hors bot)</b>' + Object.keys(hb).map(function (k) { return '<div class="flow" style="justify-content:space-between"><span>' + curHtml(k) + " " + coinQty(hb[k].qty) + '</span><span class="mono">' + eur(hb[k].eur) + "</span></div>"; }).join("") + "</div>";
    } else h += '<p class="xs muted" title="state/live_equity.json">Soldes réels pas encore écrits par la sonnette.</p>';
    if (mm.eth != null) h += '<div class="small flow" style="margin-top:6px;justify-content:space-between"><span>MetaMask (Arbitrum) : ' + num(mm.eth, 6) + ' ETH' + (mm.stale ? ' <span class="warn xs">(ancien)</span>' : "") + '</span><span class="mono" id="real-mm-eur">' + eur(mm.eur) + "</span></div>";
    if (le.present) h += '<hr class="sep"><div class="flow" style="justify-content:space-between"><span class="label">Total réel (Revolut X + MetaMask)</span><span class="mid" id="real-total">' + (le.total_reel_eur == null ? "non écrit" : eur(le.total_reel_eur)) + "</span></div>" +
      (le.total_reel_complet === false ? '<div class="xs warn">Incomplet selon la sonnette' + ((le.total_reel_manque || []).length ? " : sans valeur pour " + esc(le.total_reel_manque.join(", ")) : "") + "</div>" : "") +
      '<div class="xs muted" title="state/live_equity.json">Écrit par la sonnette : euros + toutes les pièces Revolut X (bot et hors bot) + MetaMask.</div>';
    h += '<div class="links"><a href="#reel">Pièces et ce qu’on peut vendre →</a><a href="performance.html#reel">Trades réels →</a></div></div>';
    return h;
  }

  function homeReal(s) {
    var r = s.real || {};
    if (r.hidden) return '<div class="notice">Soldes réels masqués (SHOW_REAL=false).</div>';
    var sl = s.sellable || {}, le = s.live_equity || {}, er = sl.eur;
    var h = '<section class="section">' + secHead("Nos pièces", "Revolut X + MetaMask · « disponible » = vendable tout de suite") +
      '<div class="table-wrap"><table class="rtable" id="coins"><thead><tr><th>Où</th><th>Pièce</th><th class="num">Total</th><th class="num">Disponible à vendre</th><th class="num">Bloqué (staking)</th><th class="num">Valeur</th></tr></thead><tbody>';
    if (er) h += '<tr data-cur="EUR"><td data-label="Où" class="small">Revolut X</td><td data-label="Pièce" class="mono">' + curHtml("EUR") + '</td><td data-label="Total" class="num">' + eur(er.total) + '</td><td data-label="Disponible à vendre" class="num">' + eur(er.disponible) +
      (er.reserve ? '<div class="xs muted">dont ' + eur(er.reserve) + " dans un ordre</div>" : "") + '</td><td data-label="Bloqué (staking)" class="num">' + (er.stake ? eur(er.stake) : "0") + '</td><td data-label="Valeur" class="num">' + eur(er.eur) + "</td></tr>";
    h += (sl.rows || []).map(function (x) {
      return '<tr data-cur="' + esc(x.currency) + '" data-where="' + esc(x.where) + '"><td data-label="Où" class="small">' + esc(x.where) + (x.note ? '<div class="xs muted">' + esc(x.note) + "</div>" : "") + '</td><td data-label="Pièce" class="mono">' + curHtml(x.currency) +
        '</td><td data-label="Total" class="num">' + coinQty(x.total) + '</td><td data-label="Disponible à vendre" class="num">' + (x.available != null ? coinQty(x.available) : "—") + (x.reserved_orders ? '<div class="xs muted">dont ' + coinQty(x.reserved_orders) + " dans un ordre</div>" : "") +
        '</td><td data-label="Bloqué (staking)" class="num">' + (x.blocked_staking ? coinQty(x.blocked_staking) : "0") +
        '</td><td data-label="Valeur" class="num">' + (x.eur == null ? '<span class="xs muted">pas de prix</span>' : eur(x.eur) + (x.prix_eur != null ? '<div class="xs muted">à ' + price(x.prix_eur) + "</div>" : "")) + "</td></tr>";
    }).join("");
    if (le.total_reel_eur != null) h += '<tr class="total"><td data-label="Où" class="small"><b>Total réel</b></td><td></td><td></td><td></td><td></td><td data-label="Valeur" class="num"><b>' + eur(le.total_reel_eur) + "</b>" + (le.total_reel_complet === false ? '<div class="xs warn">incomplet</div>' : "") + "</td></tr>";
    h += "</tbody></table></div>";
    h += '<p class="xs muted" title="state/live_equity.json (Revolut X « account balances » et MetaMask « eth_getBalance », en lecture seule)">Soldes écrits par la sonnette ' + ago(sl.fetched_at) + (sl.stale ? ' <span class="warn">(ancien)</span>' : "") + ". Le site ne lit pas les soldes lui-même.</p></section>";
    if (le.present) {
      var bp = le.bot_positions || {}, bk = Object.keys(bp);
      h += '<section class="section"><div class="card"><div class="card-title"><h3>Capital du bot — détail</h3><span class="badge b-real">Réel</span></div><div class="kv k3">' +
        kv("Euros disponibles", eur(le.eur_available)) + kv("Euros dans un ordre", eur(le.eur_reserved)) + kv("Pièces achetées par le bot", eur(le.bot_positions_value)) + "</div>" +
        (bk.length ? '<div class="small mono" style="margin-top:8px">' + bk.map(function (k) { return "<div>" + curHtml(k) + " " + coinQty(bp[k].qty) + (bp[k].eur != null ? ' <span class="muted">· ' + eur(bp[k].eur) + "</span>" : "") + "</div>"; }).join("") + "</div>" : "") +
        '<p class="xs muted" style="margin-bottom:0" title="state/live_equity.json">Écrit par la sonnette ' + ago(le.ts) + ".</p></div></section>";
    }
    return h;
  }

  function homeCycles(s) {
    return '<section class="section">' + secHead("Cycles automatiques", '<span class="dot ok"></span>' + esc(s.status_line)) + '<div class="grid g3" id="cycles">' + allCycles(s).map(cycleCard).join("") + "</div>" +
      '<p class="xs muted" title="« ≈ » devant une heure : horaire approximatif. « – – : – – » : pas d’horaire fixe, lancé quand il faut.">Heures de Bruxelles. Le détail de chaque passage est dans l’onglet <a href="#journal">Journal des cycles</a>.</p></section>';
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
  var CY_COLORS = { scan: "#c084fc", research: "#00d4d4", predict: "#f5a623", risk: "#38bdf8", compound: "#fde047", orchestrator: "#94a3b8", ticks: "#e2e8f0", mouvement: "#f5a623" };
  var SEG = { 0: [1, 1, 1, 1, 1, 1, 0], 1: [0, 1, 1, 0, 0, 0, 0], 2: [1, 1, 0, 1, 1, 0, 1], 3: [1, 1, 1, 1, 0, 0, 1], 4: [0, 1, 1, 0, 0, 1, 1], 5: [1, 0, 1, 1, 0, 1, 1],
    6: [1, 0, 1, 1, 1, 1, 1], 7: [1, 1, 1, 0, 0, 0, 0], 8: [1, 1, 1, 1, 1, 1, 1], 9: [1, 1, 1, 1, 0, 1, 1], "-": [0, 0, 0, 0, 0, 0, 1] };
  function ledDigit(ch) { var s = SEG[ch] || [0, 0, 0, 0, 0, 0, 0]; return '<span class="lg">' + ["t", "ur", "lr", "b", "ll", "ul", "m"].map(function (k, i) { return '<i class="s ' + k + (s[i] ? " on" : "") + '"></i>'; }).join("") + "</span>"; }
  var LED_COLON = '<span class="lc"><i></i><i></i></span>';
  function ledHtml(t) {
    if (t.word) return '<span class="lw">' + esc(t.word) + "</span>";   // ex. « prêt » (réveil mouvement)
    if (t.demand) return ledDigit("-") + ledDigit("-") + LED_COLON + ledDigit("-") + ledDigit("-");
    var a = Math.abs(t.secs), h = Math.floor(a / 3600), m = Math.floor(a % 3600 / 60), s = a % 60, d2 = function (n) { return String(n).padStart(2, "0").split("").map(ledDigit).join(""); };
    return (h > 0 ? String(h).split("").map(ledDigit).join("") + LED_COLON : "") + d2(m) + LED_COLON + d2(s);
  }
  function cycleTiming(c) {
    if (c.mv) {   // réveil mouvement : décompte jusqu'à prochain_reveil_possible (sonnette), délai = intervalle_min_min (sonnette)
      var mv = c.mv, ms = mvSecs(mv), iv = mv.intervalle_min_min != null ? mv.intervalle_min_min * 60 : null;
      if (!mv.actif || ms == null) return { demand: true, off: !mv.actif };
      return ms <= 0 ? { secs: 0, interval: iv, ready: true, word: "prêt" } : { secs: ms, interval: iv, next: Date.parse(mv.prochain_reveil_possible) };
    }
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
    if (c && c.mv) {
      if (t.off) return '<span class="badge b-mute">Désactivé</span>';
      if (c.mv.attente_decision) return '<span class="badge b-info">Attend une décision</span>';
      if (t.ready) return '<span class="badge b-ok">Prêt</span>';
      if (t.demand) return '<span class="badge b-mute">Pas de référence</span>';
      return t.secs < 90 ? '<span class="badge b-warn">Bientôt</span>' : '<span class="badge b-mute">En pause</span>';
    }
    if (t.demand) return '<span class="badge b-mute">Sur demande</span>';
    if (t.secs < 0) return '<span class="badge b-err pulse">En retard</span>';
    if (t.secs < 90) return '<span class="badge b-warn">Bientôt</span>';
    return '<span class="badge b-mute">Planifié</span>';
  }
  function nextLabel(c, t) {
    if (c.mv) return t.off ? "réveil mouvement désactivé" : t.demand ? "pas encore de décision de référence" : t.ready ? "prêt : sonne dès qu’un prix bouge de plus de " + mvSeuil(c.mv) : "prochain réveil possible (à " + (c.mv.prochain_reveil_possible_fr || "—") + ")";
    if (t.demand) return c.every_sec ? "en attente du premier prix" : "pas d’horaire fixe : lancé quand il faut";
    if (c.every_sec) return "prochain relevé de prix";
    var at = new Date(t.next), dd = bxDayIndex(at) - bxDayIndex(new Date());
    var day = dd === 0 ? "aujourd’hui" : dd === 1 ? "demain" : new Intl.DateTimeFormat("fr-BE", { timeZone: TZ, weekday: "long" }).format(at);
    return "prochain passage : " + day + " à " + (c.approx ? "≈ " : "") + fmtTime(at.toISOString(), false);
  }
  function cycleCard(c) {
    var st = cycleStatus(c), t = cycleTiming(c), col = CY_COLORS[c.key] || "#94a3b8";
    var pc = !t.demand && t.interval ? Math.min(100, Math.max(0, (t.interval - Math.max(t.secs, 0)) / t.interval * 100)) : null;
    return '<div class="card cycle cy"' + (c.id ? ' id="' + c.id + '"' : "") + ' data-key="' + c.key + '" style="--c:' + col + ";border-color:" + col + '40"' + (c.tip ? ' title="' + esc(c.tip) + '"' : "") + ">" +
      '<div class="head"><div><div class="cy-name">' + esc(c.name) + '</div><div class="cy-freq">' + esc(c.schedule) + "</div></div>" +
      '<div class="cy-badges"><span data-cb="' + c.key + '">' + timingBadge(t, c) + "</span>" + (st.text === "Planifié" || st.text === "Sur demande" ? "" : '<span class="badge ' + st.cls + '">' + (st.dot ? '<span class="dot ok"></span>' : "") + esc(st.text) + "</span>") + "</div></div>" +
      '<div class="ledbox' + (t.demand ? " idle" : "") + (t.secs < 0 ? " late" : "") + '"><span class="led" data-led="' + c.key + '">' + ledHtml(t) + "</span></div>" +
      '<div class="cy-next xs" data-cn="' + c.key + '">' + esc(nextLabel(c, t)) + "</div>" +
      (pc != null ? '<div class="cy-el"><div class="flow xs mono" style="justify-content:space-between"><span class="muted">' + (c.elLabel || "cycle écoulé") + '</span><span data-cp="' + c.key + '" style="color:var(--c)">' + pc.toFixed(0) + ' %</span></div><div class="cy-bar"><i data-cbar="' + c.key + '" style="width:' + pc + '%"></i></div></div>' : "") +
      (c.html != null ? c.html : '<div class="t small" style="margin-top:10px">' + esc(c.title) + " — " + esc(c.desc) + "</div><ul>" + c.bullets.map(function (b) { return "<li>" + esc(b) + "</li>"; }).join("") + "</ul>") +
      (st.note ? '<div class="xs muted">' + esc(st.note) + "</div>" : "") +
      (c.last_note ? '<div class="xs ' + (c.last_ok ? "muted" : "warn") + '">' + esc(c.last_note) + "</div>" : "") +
      (c.key === "risk" ? '<div class="xs muted">Surveillance des stops : ' + (c.watch_stops_running ? "en marche" : "pas de programme actif (aucune position ouverte)") + "</div>" : "") +
      '<div class="foot"><span class="cy-lbl">Dernier passage</span><span>' + (c.last_ok ? '<span class="dot ok"></span>' : '<span class="dot"></span>') + '<b style="color:var(--c)">' + (c.last_run ? ago(c.last_run) : "aucun") + "</b></span></div></div>";
  }
  function tickCountdowns() {
    var s = STATE.data.summary; if (!s || !s.cycles || !document.querySelector("[data-led]")) return;
    allCycles(s).forEach(function (c) {
      var led = document.querySelector('[data-led="' + c.key + '"]'); if (!led) return;
      var t = cycleTiming(c);
      led.innerHTML = ledHtml(t);
      led.parentNode.classList.toggle("late", t.secs < 0); led.parentNode.classList.toggle("idle", !!t.demand);
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
      var idea = t.kind === "fill" ? (t.idea_type || null) : (t.idea_type === "baisse" ? "baisse" : "hausse");
      var base = { mode: t.mode, pair: t.pair, origin: t.origin, idea: idea, kind: t.kind, decision: t.decision_link };
      var legs = [], two = !!((t.buy_time || t.buy_price) && t.sell_time);
      if (t.kind === "fill" && t.bot_exit) return;   // ordre rempli d'une sortie automatique : montré sur la ligne de la sortie
      if (t.kind === "fill") {   // réel : un ordre rempli Revolut X = une ligne, sans résultat (non écrit par l'équipe)
        groups.push([Object.assign({}, base, { sens: t.side, time: t.time, price: t.price, amount: t.eur, qty: t.qty, statusRaw: "Rempli (Revolut X)", bot: t.bot_reason, result: null })]);
        return;
      }
      if (t.buy_time || (t.buy_price != null && !t.sell_time)) legs.push(Object.assign({}, base, {
        sens: "achat", time: t.buy_time, price: t.buy_price, amount: t.amount_eur, qty: t.qty, statusRaw: t.sell_time ? "Revendu ensuite (ligne 2/2)" : t.status,
        stop: t.sell_time ? null : t.stop_price, why: t.sell_time ? null : t.reason, bot: t.bot_reason, open: !t.sell_time && t.kind === "trade",
        result: !t.sell_time && t.pnl_eur != null && t.kind === "trade" ? { eur: t.pnl_eur, pct: t.pnl_pct, latent: true } : null }));
      if (t.sell_time) legs.push(Object.assign({}, base, {
        sens: "vente", time: t.sell_time, price: t.sell_price, amount: t.sell_amount, qty: t.qty, statusRaw: t.status, closeReason: t.close_reason,
        stop: t.stop_price, why: t.reason, lesson: t.lesson, result: t.pnl_eur != null ? { eur: t.pnl_eur, pct: t.pnl_pct } : null }));
      if (legs.length) groups.push(legs);
    });
    // Simulation : lignes de state/trades_log.jsonl regroupées par cycle_id seulement (build.py load_cycles). Une ligne sans
    // cycle_id = un trade seul. Prix, montants, gains et objectifs tels qu'écrits ; ouvert/fermé = gardien (PM-Risk).
    ((T.cycles || {}).list || []).forEach(function (c) {
      var base = { mode: c.mode, pair: c.pair, idea: c.idea_type || null, decision: c.decision_id, coin: c.coin, cycleId: c.cycle_id };
      var n = c.legs.length, hasBuyBack = false;
      var legs = c.legs.map(function (g, i) {
        var sens = g.side === "sell" ? "vente" : "achat", first = i === 0, last = i === n - 1;
        if (!first && sens === "achat") hasBuyBack = true;
        var hasRes = g.realized_pnl_eur != null || g.coins_gained != null;
        var l = Object.assign({}, base, { id: g.id, sens: sens, time: g.time, price: g.price, amount: g.amount_eur, qty: g.qty,
          statusRaw: first && n > 1 ? "Fermé ensuite (voir la ligne suivante)" : (g.reason_fr ? (sens === "achat" && c.idea_type === "baisse" ? "Racheté : " : "Fermé : ") + g.reason_fr : (c.open == null ? "État non écrit (ni le gardien ni la ligne)" : c.open ? "En cours" : "Terminé")),
          unknown: c.open == null && !g.reason_fr,
          closeReason: g.close_reason, rebuyReason: g.rebuy_reason,
          why: first ? c.reason : null, lesson: last && !c.open ? c.lesson : null,
          result: hasRes ? { coins: g.coins_gained, coinsPct: g.coins_gained_pct, eur: g.realized_pnl_eur, pct: g.realized_pnl_pct, fees: g.fees_eur } : null,
          more: { c: c, g: g, i: i } });
        if (first && c.open) {
          l.open = true; l.waiting = c.idea_type === "baisse"; l.stop = c.idea_type === "baisse" ? null : c.stop_price;
          l.statusRaw = c.idea_type === "baisse" ? "En attente du rachat" : "En cours";
          if (c.latent_pnl_eur != null) l.result = { eur: c.latent_pnl_eur, pct: c.latent_pnl_pct, latent: true };
        }
        return l;
      });
      if (c.open && !c.single && c.idea_type === "baisse" && !hasBuyBack && n && legs[0].sens === "vente")
        legs.push(Object.assign({}, base, { sens: "achat", pending: true, time: null, statusRaw: "Rachat prévu",
          plan: { target: c.target_price, safety: c.safety_price }, result: null }));
      groups.push(legs);
    });
    ((T.real || {}).open_orders || []).forEach(function (o) {
      groups.push([{ mode: "reel", pair: o.pair, origin: o.bot ? "bot" : null, idea: null, sens: o.side === "sell" ? "vente" : "achat",
        time: o.created || null, price: o.price, amount: null, qty: o.qty, statusRaw: "Ordre en attente dans le carnet Revolut X", order: true }]);
    });
    var fillIds = (T.trades || []).filter(function (t) { return t.kind === "fill"; }).map(function (t) { return t.id; });
    ((T.real || {}).bot_orders || []).forEach(function (o) {   // ordres des bots (state/live_orders.jsonl, PM-Risk)
      var sens = o.side === "sell" ? "vente" : "achat";
      if (o.kind === "auto_exit") {   // sortie automatique : une ligne, chiffres tels qu'écrits par live_place.py
        groups.push([{ mode: "reel", pair: o.pair, origin: "bot", idea: null, sens: sens, time: o.at || null, price: o.price,
          amount: o.quote_eur != null ? o.quote_eur : o.amount_eur, amountLabel: o.quote_eur != null ? (sens === "vente" ? "Vente : " + eur(o.quote_eur) + " reçus" : "Rachat : " + eur(o.quote_eur) + " payés") : (o.amount_eur != null ? "Coût de la position fermée : " + eur(o.amount_eur) : null),
          qty: o.qty, exitStatus: o.status || "inconnu", statusRaw: "Sortie automatique — " + (o.status_fr || "état non écrit"), why: o.reason, decision: o.decision_id, closeReason: o.close_reason,
          result: o.realized_pnl_eur != null ? { eur: o.realized_pnl_eur, gross: o.realized_pnl_gross_eur, fees: o.fees_eur, net: true } : null }]);
        return;
      }
      var ids = (o.ids || []).concat(o.order_id ? [o.order_id] : []);
      if (ids.some(function (i) { return fillIds.indexOf(i) >= 0; })) return;   // déjà rempli : la ligne Revolut X le montre
      groups.push([{ mode: "reel", pair: o.pair, origin: "bot", idea: null, sens: sens, time: o.at || null, price: o.price, amount: o.amount_eur,
        statusRaw: o.ok ? "Ordre envoyé — pas (encore) rempli" : "Ordre refusé", err: o.ok ? null : (o.error || "Ordre refusé"), why: o.ok ? o.reason : null, decision: o.decision_id,
        result: o.realized_pnl_eur != null ? { eur: o.realized_pnl_eur, gross: o.realized_pnl_gross_eur, fees: o.fees_eur, net: true } : null }]);
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
    if (l.unknown) return ["❔", "Inconnu", "b-mute"];
    if (l.exitStatus) return ({ done: ["✔", "Vendu", "b-mute"], partial: ["◐", "En partie", "b-warn"], no_fill: ["✖", "Pas vendu", "b-warn"],
      closed_by_target: ["🎯", "Objectif", "b-mute"], failed: ["✖", "Ratée", "b-err"], error: ["✖", "Ratée", "b-err"] })[l.exitStatus] || ["❔", "Inconnu", "b-mute"];
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
    if (l.mode === "reel" && (l.origin === "app Revolut" || l.origin === "manuel")) {   // ordre Revolut X relié à aucun ordre des bots
      // Achat BTC-EUR hors bots = arrondi « petite monnaie » de Revolut (petits achats automatiques depuis le compte principal).
      var rnd = l.pair === "BTC-EUR" && l.sens === "achat";
      return '<span class="ticon" title="' + m[1] + '">' + m[0] + '</span> <span class="small manual" data-manual="' + (rnd ? "arrondi" : "hors-bots") + '">' +
        (rnd ? "🪙 Arrondi Revolut (petite monnaie, hors bots)" : "Hors bots (app Revolut)") + "</span>";
    }
    var i = l.idea === "baisse" ? ["📉", "Idée à la baisse : vendre des pièces qu’on a, puis racheter plus bas"] : l.idea === "hausse" ? ["📈", "Idée à la hausse : acheter, puis revendre plus haut"] : ["❔", "Idée non écrite par l’équipe"];
    return '<span class="ticon" title="' + m[1] + '">' + m[0] + '</span><span class="ticon" title="' + i[1] + '">' + i[0] + "</span>" +
      (l.mode === "reel" && l.origin ? '<span class="xs muted" title="' + (l.origin === "bot" ? "passé par les bots" : "passé à la main") + '"> ' + esc(l.origin) + "</span>" : "") +
      (l.depart ? '<span class="xs muted" title="Vente de pièces achetées avant le projet (prix d’achat inconnu, pas comptée)"> départ</span>' : "");
  }
  function legRow(l) {
    var res = "—", r = l.result;
    if (r && r.coins != null) res = '<div class="' + cls(r.coins) + '">' + (r.latent ? '<span class="xs muted">si racheté maintenant</span><br>' : "") + signedCoin(r.coins, l.coin) + "</div>" + (r.eur != null ? '<div class="xs ' + cls(r.eur) + '">' + eur(r.eur, 2, true) + (r.fees ? " · frais " + eur(r.fees) : "") + "</div>" : "");
    else if (r && r.eur != null && r.net) res = '<div class="' + cls(r.eur) + '" title="realized_pnl_eur (net, live_orders.jsonl)">' + eur(r.eur, 2, true) + ' <span class="xs muted">net</span></div>' +
      (r.gross != null || r.fees != null ? '<div class="xs muted">brut ' + (r.gross != null ? eur(r.gross, 2, true) : "—") + " · frais " + (r.fees != null ? eur(r.fees) : "—") + "</div>" : "");
    else if (r && r.eur != null) res = '<div class="' + cls(r.eur) + '">' + (r.latent ? '<span class="xs muted">latent</span><br>' : "") + eur(r.eur, 2, true) + '</div><div class="xs ' + cls(r.pct) + '">' + pct(r.pct, 2, true) + "</div>";
    var st = shortStatus(l);
    var why = (l.err ? "<b>Refus :</b> " + esc(l.err) + "<br>" : "") + (l.why ? "<b>" + (l.sens === "vente" ? "Pourquoi vendu :" : "Pourquoi acheté :") + "</b> " + esc(l.why) + "<br>" : "") + (l.bot ? "<b>Raison du bot :</b> " + esc(l.bot) + "<br>" : "") + (l.lesson ? "<b>Leçon :</b> " + esc(l.lesson) : "") +
      (l.decision ? '<div class="xs"><a href="research.html' + ((String(l.decision).match(/D-\d+/) || [])[0] ? "?d=" + (String(l.decision).match(/D-\d+/))[0] : "") + '#decisions">Décision ' + esc((String(l.decision).match(/D-\d+/) || ["écrite"])[0]) + " →</a></div>" : "");
    return '<tr class="leg"' + (l.id ? ' data-id="' + esc(l.id) + '"' : "") + (l.cycleId ? ' data-cycle="' + esc(l.cycleId) + '"' : "") + ' data-num="' + l.num + '"' + (l.pending ? ' data-pending="1"' : "") + '><td data-label="Trade" class="mono small nowrap">Trade ' + l.num + (l.step ? ' <span class="xs muted">· ' + l.step + "</span>" : "") +
      '</td><td data-label="Sens">' + sideBadge(l.sens, l.pending) +
      '</td><td data-label="Type" class="nowrap">' + typeIcons(l) +
      '</td><td data-label="Paire" class="mono nowrap">' + pairHtml(l.pair) +
      '</td><td data-label="Prix · heure" class="mono">' + (l.pending ? '<span class="small">visé ' + price(l.plan.target) + '</span><div class="xs muted">sécurité ' + price(l.plan.safety) + "</div>" : price(l.price) + '<div class="xs muted">' + fmtTime(l.time) + "</div>") +
      '</td><td data-label="Montant" class="num">' + (l.pending ? "—" : (l.amountLabel ? '<span title="quote_eur (live_orders.jsonl)">' + esc(l.amountLabel) + "</span>" : eur(l.amount)) + (l.qty ? '<div class="xs muted">' + coinQty(l.qty) + "</div>" : "")) +
      '</td><td data-label="Résultat" class="num">' + res +
      '</td><td data-label="Statut" class="nowrap"><span class="badge ' + st[2] + '" title="' + esc(l.statusRaw || "") + '">' + st[0] + " " + st[1] + "</span>" + (l.stop ? '<div class="xs muted">stop ' + price(l.stop) + "</div>" : "") +
      '</td><td data-label="Raison · leçon" class="wide small text2">' + (why || '<span class="muted">—</span>') + "</td></tr>";
  }
  // Lignes en plus sous un trade simulé (même carte) : ce que PM-Risk / PM-Predict ont ÉCRIT, rien de recalculé.
  // Départ (pour une ligne de clôture), Montant écrit, Arrêt · objectif, Fermeture (raison + prix ; déclenchement si écrit), Décision.
  var CLOSE_TRIG = /stop|target|safety|visé|vise/i;
  function tmRow(k, label, html) { return '<div class="tm" data-more="' + k + '"><span class="tml">' + label + '</span><span class="tmv">' + html + "</span></div>"; }
  function tradeMore(l) {
    if (!l.more || l.pending) return "";
    var c = l.more.c, g = l.more.g, i = l.more.i, P = c.plan || {}, D = c.decision, CL = c.close || {}, out = [], first = c.legs[0];
    var isClose = !!(g.close_reason || g.rebuy_reason), sensFr = function (x) { return x === "sell" ? "Vente" : "Achat"; };
    if (i > 0 && first) out.push(tmRow("depart", sensFr(first.side) + " · départ", price(first.price) + " · " + fmtTime(first.time) + " · " +
      (first.amount_eur != null ? eur(first.amount_eur) + ' <span class="xs muted">(montant écrit ' + (first.side === "sell" ? "à la vente" : "à l’achat") + ")</span>" : "montant " + NE)));
    if (i > 0) out.push(tmRow("montant", "Montant de cette ligne", (g.amount_eur != null ? eur(g.amount_eur) + ' <span class="xs muted">(écrit ' + (g.side === "sell" ? "à la vente" : "au rachat") + ")</span>" : NE) +
      (g.realized_pnl_gross_eur != null || g.fees_eur != null ? " · résultat avant frais " + (g.realized_pnl_gross_eur != null ? eur(g.realized_pnl_gross_eur, 2, true) : NE) + " · frais " + (g.fees_eur != null ? eur(g.fees_eur) : NE) : "")));
    if (i === 0 || isClose) out.push(tmRow("plan", "Arrêt · objectif", "arrêt " + (P.stop != null ? price(P.stop) : NE) + " · objectif " + (P.target != null ? price(P.target) : NE) +
      (P.safety != null && P.safety !== P.stop ? " · sécurité " + price(P.safety) : "") + " · rappel " + (P.deadline ? fmtTime(P.deadline) : NE)));
    if (isClose) out.push(tmRow("fermeture", "Fermeture", esc(g.reason_fr || g.close_reason || g.rebuy_reason) + " · prix " + price(g.price) +
      (CLOSE_TRIG.test(String(g.close_reason || "") + String(g.rebuy_reason || "")) ? (CL.leg_id === g.id && CL.trigger_price != null ? " · déclenché à " + price(CL.trigger_price) + (CL.trigger_level != null ? " (seuil " + price(CL.trigger_level) + ")" : "") : " · prix du déclenchement : " + NE) : "")));
    if (i === 0 || isClose) {
      if (!D) out.push(tmRow("decision", "Décision", NE));
      else {
        var lvl = D.niveau ? " · " + esc(D.niveau) : (D.letter ? "" : ""), link = D.found ? '<a href="research.html?d=' + encodeURIComponent(D.id) + '#decisions" data-declink="' + esc(D.id) + '">' + esc(D.ref) + " →</a>" : esc(D.ref) + ' <span class="xs muted">(carte introuvable)</span>';
        out.push(tmRow("decision", "Décision", link + (D.letter ? " · proposition " + esc(D.letter) : "") + lvl +
          (i === 0 ? '<div class="xs">Prévision de Predict : ' + dv(D.forecast) + "</div>" +
            '<div class="xs">Risk : ' + ((D.risk || []).length ? D.risk.map(function (r) { return '<span class="mono">' + esc(r.heure || "") + "</span> " + esc(hidePaths(r.texte || "")); }).join("<br>") : NE) + "</div>" : "")));
      }
    }
    return out.length ? '<tr class="leg-more"' + (g.id ? ' data-more-for="' + esc(g.id) + '"' : "") + '><td colspan="9" class="wide" data-label="Détail"><div class="tmore">' + out.join("") + "</div></td></tr>" : "";
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
    if (rows.length) h += '<div class="table-wrap"><table class="rtable ttable"><thead><tr><th>Trade</th><th>Sens</th><th>Type</th><th>Paire</th><th>Prix · heure</th><th class="num">Montant</th><th class="num">Résultat</th><th>Statut</th><th>Raison · leçon</th></tr></thead><tbody>' + rows.map(function (l) { var mo = tradeMore(l); return (mo ? legRow(l).replace('<tr class="leg"', '<tr class="leg has-more"') : legRow(l)) + mo; }).join("") + "</tbody></table></div>";
    else h += '<p class="empty">' + (sf === "baisse" ? "Aucune idée à la baisse pour l’instant." : "Aucune ligne pour ce filtre.") + "</p>";
    h += '<p class="xs muted">Les décisions écrites sont sur la page <a href="research.html#decisions">Analyses</a>. <span id="trades-sources" title="simulation : state/trades_log.jsonl + guardian/state.json · réel : historique Revolut X + state/live_orders.jsonl · raison et leçon : knowledge/trading_journal.md">Simulation : chiffres de PM-Risk · Réel : historique Revolut X.</span></p>';
    el("app").innerHTML = h;
    bindChips("m", "modeFilter", renderTrades); bindChips("s", "sensFilter", renderTrades); bindChips("pf", "pairFilter", renderTrades);
  }

  // ------------------------------------------------------------ PERFORMANCE
  var PERF_TABS = [["simulation", "Simulation"], ["reel", "Argent réel"], ["monnaies", "Par monnaie"], ["tests", "Tests du passé"]];
  // Chiffres globaux = state/performance.json (scripts/performance.py, étape PM-Compound) TELS QUELS. Aucun total, taux ou
  // courbe recalculé par le site. Valeur du portefeuille / sommet / baisse : guardian/state.json (PM-Risk).
  function renderPerformance() {
    var P = STATE.data.performance, tab = getTab(PERF_TABS.map(function (x) { return x[0]; }), "simulation");
    var h = '<h1 class="page-title">Performance</h1><p class="lead">Les résultats des trades : simulation, argent réel, par monnaie, et les tests sur les prix passés.</p>' + tabsBar(PERF_TABS, tab);
    if (tab === "simulation") h += perfMode(P, "sim");
    else if (tab === "reel") h += perfMode(P, "reel");
    else if (tab === "monnaies") h += perfPairs(P);
    else h += perfTests(P);
    el("app").innerHTML = h;
    bindTabs(renderPerformance);
    STATE.ui.pairLive = null;
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
  // Performance › Simulation et Argent réel : UNE seule fonction, mêmes blocs dans le même ordre (data-block), nourrie par
  // perfModeData(mode). Chiffres tels qu'écrits : PM-Compound (performance.json → totaux.simulation / totaux.live),
  // PM-Risk (gardien) pour la simulation, la sonnette (live_equity.json) pour le réel. Pas écrit → « pas évalué » au même endroit.
  var PERF_BLOCKS = [["resultats", "Résultats des trades"], ["sens", "Par sens (📈 hausse · 📉 baisse)"], ["portefeuille", "Portefeuille"], ["objectifs", "Avant de passer au réel"], ["lignes", "Lignes enregistrées"]];
  function perfModeData(P, mode) {
    var TP = P.team_perf || {}, raw = TP.raw || {}, T = (raw.totaux || {})[mode === "reel" ? "live" : "simulation"], pp = P.paper || {}, le = P.live_equity || {}, RL = P.real || {}, g = P.go_nogo || {};
    var sim = mode === "sim";
    return {
      mode: mode, title: sim ? "Simulation" : "Argent réel",
      sub: sim ? "argent fictif · " + (pp.invested_eur != null ? eur(pp.invested_eur, 0) + " au départ" : "départ pas évalué") : "depuis le " + fmtDay(RL.project_start),
      compound: { present: !!TP.present, T: T && typeof T === "object" ? T : null, updated: TP.updated_at, owner: TP.owner, source: TP.source,
        maxdd: sim ? raw.max_drawdown_pct : undefined, maxddNote: sim ? "max_drawdown_pct" : "pas écrit pour le réel" },
      wallet: sim ? { value: pp.balance_eur, peak: pp.peak_equity_eur, dd: pp.drawdown_pct, start: pp.invested_eur, who: "gardien (PM-Risk)" }
        : { value: le.present ? le.capital_reel : null, peak: le.plus_haut, dd: le.baisse_depuis_plus_haut_pct, start: null, who: "sonnette (live_equity)" },
      goals: sim ? { n: raw.n_closed, wr: raw.win_rate, dd: pp.drawdown_pct } : { n: null, wr: null, dd: null }, g: g,
      // simulation : performance.json → ordres_des_bots / ordres_remplis (PM-Compound), tels qu'écrits (ex. « sans objet ») ; absent → « pas évalué »
      lines: sim ? { open: raw.n_open, bots: raw.ordres_des_bots, fills: raw.ordres_remplis } : { open: null, bots: (RL.bot_orders || []).length, fills: (RL.fills || []).length },
      stale: !sim && RL.history_stale
    };
  }
  function perfMode(P, mode) {
    if (mode === "reel" && (P.real || {}).hidden) return '<div class="notice">Masqué (SHOW_REAL=false).</div>';
    var D = perfModeData(P, mode), C = D.compound, T = C.T, NEv = '<span class="muted">pas évalué</span>';
    var v = function (x, f) { return x == null ? NEv : f(x); };
    var blk = function (k, inner, sub) { var t = PERF_BLOCKS.filter(function (b) { return b[0] === k; })[0][1]; return '<section class="section" data-block="' + k + '">' + secHead(t, sub || "") + inner + "</section>"; };
    var old = C.updated && (Date.now() - new Date(C.updated).getTime()) > 36 * 3600 * 1000;
    var h = '<section class="section">' + secHead(D.title, D.sub) + "</section>";
    // 1. Résultats (PM-Compound)
    h += blk("resultats", '<div class="grid g4" id="' + (mode === "reel" ? "live-totals" : "sim-totals") + '">' +
      statCard("Trades terminés", v(T && T.trades, String), T ? (T.gagnants == null ? "—" : T.gagnants) + " gagnant(s) · " + (T.perdants == null ? "—" : T.perdants) + " perdant(s)" : "pas évalué") +
      statCard("Gain / perte (net)", v(T && T.net_eur, function (x) { return eur(x, 2, true); }), "après frais", T && T.net_eur ? cls(T.net_eur) : "") +
      statCard("Taux de réussite", v(T && T.taux_reussite, function (x) { return pct(x * 100, 0); }), "part des trades gagnants") +
      statCard("Rapport gains / pertes", v(T && T.rapport_gains_pertes, function (x) { return num(x, 2); }), "gains ÷ pertes") +
      statCard("Gain moyen par trade", v(T && T.gain_moyen_eur, function (x) { return eur(x, 2, true); }), "écrit par PM-Compound", T && T.gain_moyen_eur ? cls(T.gain_moyen_eur) : "") +
      statCard("Montant total engagé", v(T && T.taille_totale_eur, function (x) { return eur(x); }), "somme écrite par PM-Compound") +
      statCard("Plus grosse baisse", v(C.maxdd, function (x) { return pct(x * 100, 2); }), C.maxddNote) + "</div>" +
      (T && T.note_fr ? '<p class="xs muted">' + esc(hidePaths(T.note_fr)) + "</p>" : "") +
      '<p class="xs ' + (old ? "warn" : "muted") + '">' + (C.present ? "Écrit par " + esc(C.owner || "PM-Compound") + " " + fmtTime(C.updated) + (old ? " — <b>pas à jour</b>." : ".") : "Pas encore écrit par PM-Compound.") + " Le site recopie ces chiffres sans les recalculer.</p>", "écrits par PM-Compound");
    // 2. Par sens
    var S = (T && T.par_sens) || {};
    h += blk("sens", '<div class="table-wrap"><table class="rtable"><thead><tr><th>Sens</th><th class="num">Trades</th><th class="num">Gagnants · perdants</th><th class="num">Net</th><th class="num">Réussite</th></tr></thead><tbody>' +
      [["hausse", "📈 À la hausse"], ["baisse", "📉 À la baisse"]].map(function (r) { var x = S[r[0]] || null;
        return '<tr data-sens="' + r[0] + '"><td data-label="Sens">' + r[1] + '</td><td data-label="Trades" class="num">' + v(x && x.trades, String) + '</td><td data-label="Gagnants · perdants" class="num">' + (x && (x.gagnants != null || x.perdants != null) ? (x.gagnants == null ? "—" : x.gagnants) + " · " + (x.perdants == null ? "—" : x.perdants) : NEv) +
          '</td><td data-label="Net" class="num ' + (x && x.net_eur ? cls(x.net_eur) : "") + '">' + v(x && x.net_eur, function (y) { return eur(y, 2, true); }) + '</td><td data-label="Réussite" class="num">' + v(x && x.taux_reussite, function (y) { return pct(y * 100, 0); }) + "</td></tr>"; }).join("") +
      "</tbody></table></div>", "écrit par PM-Compound");
    // 3. Portefeuille
    var W = D.wallet;
    h += blk("portefeuille", '<div class="grid g4">' + statCard(mode === "reel" ? "Capital du bot" : "Valeur du portefeuille", v(W.value, function (x) { return eur(x); }), W.who) +
      statCard("Sommet", v(W.peak, function (x) { return eur(x); }), W.who) + statCard("Baisse depuis le sommet", v(W.dd, function (x) { return pct(x * 100, 2); }), W.who) +
      statCard("Départ", v(W.start, function (x) { return eur(x, 0); }), mode === "reel" ? "pas écrit pour le réel" : W.who) + "</div>", "");
    // 4. Objectifs (config.json → go_nogo, tels quels) ; valeur pas écrite pour ce mode → « pas évalué »
    var g = D.g, G = D.goals;
    var goals = [["Trades d'essai", G.n, g.min_trades, (G.n == null ? NEv : G.n) + " / " + (g.min_trades == null ? NEv : g.min_trades)],
      ["Taux de réussite", G.wr == null ? null : G.wr * 100, g.min_win_rate == null ? null : g.min_win_rate * 100, (G.wr == null ? NEv : pct(G.wr * 100, 0)) + " / " + (g.min_win_rate == null ? NEv : pct(g.min_win_rate * 100, 0))],
      ["Baisse depuis le sommet", G.dd == null ? null : G.dd * 100, g.max_drawdown_pct == null ? null : g.max_drawdown_pct * 100, (G.dd == null ? NEv : pct(G.dd * 100, 2)) + " (limite " + (g.max_drawdown_pct == null ? NEv : pct(g.max_drawdown_pct * 100, 0)) + ")"]];
    h += blk("objectifs", '<div class="grid g3">' + goals.map(function (x, i) {
      var r = x[1] != null && x[2] ? Math.min(1, x[1] / x[2]) : 0;   // largeur de la barre seulement (affichage), pas un chiffre publié
      return '<div class="card" data-goal="' + i + '"><div class="label">' + x[0] + '</div><div class="mono" style="margin-bottom:8px">' + x[3] + "</div>" + (x[2] == null || x[1] == null ? "" : '<div class="bar"><i style="width:' + Math.round(r * 100) + '%"></i></div>') + "</div>";
    }).join("") + '</div><p class="xs muted">Objectifs écrits dans la configuration de l’équipe. Le score des prévisions est sur la page <a href="research.html#score">Analyses</a>.</p>', "objectifs de l'équipe");
    // 5. Lignes enregistrées
    var L = D.lines;
    h += blk("lignes", '<div class="grid g3">' + statCard("Positions ouvertes", v(L.open, String), mode === "reel" ? "pas écrit pour le réel" : "écrit par PM-Compound") +
      statCard("Ordres des bots", v(L.bots, function (x) { return esc(String(x)); }), mode === "reel" ? "écrits par PM-Risk" : L.bots == null ? "pas écrit pour la simulation" : "écrit par PM-Compound") +
      statCard("Ordres remplis (Revolut X)", v(L.fills, function (x) { return esc(String(x)); }), mode === "reel" ? "lignes brutes de l’historique" : L.fills == null ? "pas écrit pour la simulation" : "écrit par PM-Compound") + "</div>" +
      '<p class="xs muted">Lignes une par une : <a href="trades.html">liste des trades</a>.' + (D.stale ? ' <span class="warn">Historique pas à jour.</span>' : "") + "</p>", "");
    return h;
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
  // 2 pastilles par carte, verdict ÉCRIT par l'équipe dans le fichier du test (build.py team_gates) : vert = oui, rouge = non,
  // gris « non évalué par l'équipe » tant qu'aucun bot ne l'a écrit. Le site ne calcule aucun verdict.
  var GATE_LABEL = { past: "Test du passé réussi", live: "Autorisé en réel" };
  function gateBadge(k, g) {
    g = g || {};
    var c = g.ok === true ? "b-ok" : g.ok === false ? "b-err" : "b-mute";
    var tip = g.ok == null && g.grid ? "Grille d’essais : pas de verdict, exprès (PM-Risk / PM-Compound)." : g.ok == null ? "Non évalué par l’équipe : " + (g.owner || "?") + " n’a pas écrit " + (g.field || "") + " dans le fichier du test." :
      (g.ok ? "Oui" : "Non") + (g.by ? " — écrit par " + g.by : "") + (g.at ? " le " + g.at : "") + (g.why ? "\n" + g.why : "");
    return '<span class="badge gate ' + c + '" tabindex="0" data-gate="' + k + '" data-ok="' + (g.ok == null ? "na" : g.ok) + '" title="' + esc(tip) + '">' +
      (g.ok === true ? "✔ " : g.ok === false ? "✖ " : "") + GATE_LABEL[k] + (g.ok == null ? (g.grid ? " : pas de verdict (grille d’essais)" : " : non évalué par l’équipe") : "") + "</span>";
  }
  function gatesHtml(G) {
    return '<div class="gates" style="margin-top:8px">' + gateBadge("past", G.past) + gateBadge("live", G.live) + '<div class="gate-detail xs" hidden></div></div>';
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
      (t.robust ? '<div style="margin-top:6px"><span class="badge ' + (/ROBUST|SOLIDE|OUI|YES/i.test(t.robust.verdict || "") ? "b-ok" : /FRAGILE/i.test(t.robust.verdict || "") ? "b-warn" : "b-err") + '" style="white-space:normal" title="Verdict écrit par l’outil de test (vibe-trading)">Solidité (outil de test) : ' + esc((t.robust.verdict_fr || "").split(" :")[0] || t.robust.verdict || "?") + (t.robust.passed != null ? " · " + t.robust.passed + "/" + t.robust.of + " vérifications" : "") + "</span></div>" : "") +
      (t.summary ? '<p class="small" style="margin:8px 0">' + esc(t.summary) + "</p>" : "") +
      (t.robust ? '<div class="xs muted" style="margin-bottom:6px">' + [t.robust.windows_n ? "périodes gagnantes " + t.robust.windows_gain + "/" + t.robust.windows_n : "", t.robust.pbo != null ? "risque que ce soit de la chance " + pct(t.robust.pbo * 100, 0) : "", t.robust.random_p != null ? "mieux que vendre au hasard ? " + (t.robust.random_p < 0.05 ? "oui" : "non") : ""].filter(Boolean).join(" · ") + "</div>" : "") +
      (t.kvs.length ? '<div class="kv k3">' + t.kvs.map(function (x) { return kv(x[0], x[1]); }).join("") + "</div>" : "") +
      (t.gates ? gatesHtml(t.gates) : "") + "</div>";
  }
  function perfTests(P) {
    var all = testCards(P), gsel = STATE.ui.testGroup || "all", lim = STATE.ui.testLimit || 6;
    var list = all.filter(function (t) { return gsel === "all" || t.group === gsel; });
    var h = '<section class="section">' + secHead("Tests du passé", "on rejoue une idée sur les prix d’avant (sans IA)") +
      '<div class="notice" style="margin-bottom:12px">Un bon résultat sur le passé ne garantit rien pour demain. « Garder » = acheter au début et ne rien faire. Chaque carte a 2 pastilles : « Test du passé réussi » (écrit par PM-Compound) et « Autorisé en réel » (écrit par PM-Risk). <span class="pos">Vert</span> = oui, <span class="neg">rouge</span> = non, gris = non évalué par l’équipe (le site ne décide rien). Les chiffres viennent du fichier du test.</div>' +
      chipsBar([["all", "Tous", all.length], ["hausse", "📈 Idées à la hausse", all.filter(function (t) { return t.group === "hausse"; }).length], ["baisse", "📉 Idées à la baisse", all.filter(function (t) { return t.group === "baisse"; }).length]], gsel, "tg");
    h += list.length ? '<div class="grid g2">' + list.slice(0, lim).map(testCardHtml).join("") + "</div>" + (list.length > lim ? '<button class="btn" id="tmore" style="margin-top:10px">Voir tous les tests (' + list.length + ")</button>" : "") : '<p class="empty">Aucun test pour l’instant. Les nouveaux apparaîtront ici automatiquement.</p>';
    if (P.sellrebuy_duplicates) h += '<p class="xs muted">' + P.sellrebuy_duplicates + " test(s) en double (mêmes réglages) cachés.</p>";
    h += '<p class="xs muted" title="/workspace/tools/vibe-trading (home/runs, checks, reports)">Tests faits avec l’outil de test de l’équipe.</p></section>';
    return h;
  }

  // Réveil « mouvement » de PM-Predict : heure du prochain réveil possible écrite par la sonnette (status.json →
  // predict_mouvement.prochain_reveil_possible), telle quelle. Le navigateur ne fait que décompter jusqu'à cette heure.
  function mvSecs(mv) { var t = mv && mv.prochain_reveil_possible ? Date.parse(mv.prochain_reveil_possible) : NaN; return isNaN(t) ? null : Math.floor((t - Date.now()) / 1000); }
  function mvSeuil(mv) { return mv.seuil_pct == null ? "seuil pas évalué" : String(mv.seuil_pct).replace(".", ",") + " %"; }   // seuil écrit par la sonnette, rien d'inventé
  // Mouvement de chaque paire depuis la décision de référence : chiffre exact de la sonnette ; vert = monte, rouge = baisse.
  function mvPairsHtml(mv) {
    var rf = mv.reference || {}, mp = mv.mouvement_pct || {};
    return Object.keys(rf.prix || {}).sort().map(function (p) {
      var v = mp[p], t = v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + String(Math.abs(v)).replace(".", ",") + " %";
      return '<li class="mvp" data-mvpair="' + esc(p) + '" title="prix de référence ' + esc(price(rf.prix[p])) + '">' + pairHtml(p) + ' <b class="mono ' + (v ? cls(v) : "") + '">' + t + "</b></li>";
    }).join("");
  }
  // Carte « Réveil mouvement » = même carte que les autres cycles (cycleCard + cycleTiming + ledHtml + tickCountdowns).
  function mvCycle(s) {
    var mv = s && s.sonnette && s.sonnette.mouvement; if (!mv) return null;
    var rf = mv.reference || {};
    return { key: "mouvement", id: "cycle-mouvement", mv: mv, name: "Réveil mouvement", last_ok: true, last_run: mv.dernier_reveil, elLabel: "délai écoulé",
      schedule: "PM-Predict · " + (mv.seuil_pct == null ? "seuil pas évalué" : "prix qui bouge de plus de " + mvSeuil(mv)) + " · " + (mv.intervalle_min_min == null ? "délai pas évalué" : mv.intervalle_min_min + " min entre 2 réveils"),
      tip: "Réveille PM-Predict quand BTC, ETH ou SOL bouge de plus de " + mvSeuil(mv) + " depuis sa dernière décision. Chiffres écrits par la sonnette.",
      html: '<div class="t small" style="margin-top:10px">Mouvement depuis ' + esc(rf.decision_id || "la dernière décision") + (rf.decision_ts ? " (" + fmtTime(rf.decision_ts, false) + ")" : "") + "</div>" +
        '<ul class="mvpairs">' + mvPairsHtml(mv) + "</ul>" +
        '<div class="small" data-mvday>' + (mv.aujourd_hui == null ? "Réveils aujourd’hui : pas évalué" : mv.aujourd_hui + " réveil" + (mv.aujourd_hui > 1 ? "s" : "") + " aujourd’hui") + "</div>" +
        (mv.attente_decision ? '<div class="xs muted">Réveil envoyé : attend une nouvelle décision de PM-Predict.</div>' : "") };
  }
  // Cartes de Cycles automatiques : cycles des routines + la carte Réveil mouvement (seul endroit où elle est affichée).
  function allCycles(s) { var m = mvCycle(s); return (s.cycles || []).concat(m ? [m] : []); }

  function sonnetteCard(so) {
    if (!so) return "";
    var h = '<div class="card"><div class="card-title"><h3>Sonnette</h3>' + (so.present ? '<span class="badge ' + (so.running ? "b-ok" : "b-err") + '"><span class="dot' + (so.running ? " ok" : "") + '"></span>' + (so.running ? "en marche" : "arrêtée") + "</span>" : '<span class="badge b-mute">pas trouvée</span>') + "</div>" +
      '<p class="xs muted" style="margin-top:0">3 sonnettes : PM-Predict et PM-Risk quand un prix touche une zone ou qu’un stop est proche, PM-Compound quand un trade est fermé. Elle ne passe aucun ordre.</p>';
    if (so.present) {
      var md = function (m) { return '<span class="badge ' + (m === "branchée" ? "b-ok" : "b-mute") + '">' + esc(m) + "</span>"; };
      var modes = { predict: so.predict_mode, risk: so.risk_mode, compound: so.compound_mode };
      // Par sonnette : compteurs écrits par la sonnette (status.json → today), tels quels. « Vrais réveils / essais » :
      // affichés seulement quand la sonnette les écrit (totals.<bot>.vrais / essais) ; sinon « non écrit par la sonnette ».
      h += '<div class="bells">' + (so.bells || []).map(function (b) {
        var ve = b.real_events == null ? '<span class="muted">Vrais réveils / essais : non écrit par la sonnette</span>' : "Vrais réveils : " + b.real_events + " · Essais : " + b.tests;
        var lr = b.last_real ? '<div class="xs bell-chain">Dernier vrai réveil : ' + esc(typeof b.last_real === "string" ? b.last_real : JSON.stringify(b.last_real)) + "</div>" : "";
        return '<div class="bell" data-bell="' + esc(b.key) + '"><div class="flow small" style="justify-content:space-between;gap:6px"><b>' + esc(b.bot) + "</b>" + (modes[b.key] ? md(modes[b.key]) : "") + "</div>" +
          '<div class="xs muted">' + esc(b.what) + "</div>" +
          '<div class="small mono bell-cnt">Aujourd’hui : ' + (b.today_real_mode == null ? "—" : b.today_real_mode) + " envoyée(s) · " + (b.today_dry == null ? "—" : b.today_dry) + " à blanc</div>" +
          '<div class="xs bell-ve">' + ve + "</div>" + lr + "</div>";
      }).join("") + "</div>";
      h += '<div class="kv k3" style="margin-top:8px">' + kv("Dernier signe de vie", ago(so.heartbeat)) + kv("Fenêtre Predict", so.predict_window_open ? "ouverte" : "fermée") + "</div>";
      var warns = [];
      if (so.urgent_active) warns.push("alerte urgente en cours");
      if (so.prices_stale) warns.push("prix pas à jour");
      if (so.real_positions_without_stop) warns.push(so.real_positions_without_stop + " position(s) réelle(s) sans stop");
      if (so.zones_problems) warns.push(so.zones_problems + " zone(s) mal écrite(s)");
      if (!so.collector_running) warns.push("collecteur de prix arrêté");
      if (warns.length) h += '<div class="notice warn" style="margin-top:10px">' + esc(warns.join(" · ")) + "</div>";
      // Predict occupé (status.json → predict_occupe, tel quel) : affiché seulement quand actif === true.
      var po = so.predict_occupe;
      if (po && po.actif === true) h += '<div class="notice" id="predict-occupe" style="margin-top:10px">⏳ Predict réfléchit : les autres alertes attendent sa décision' +
        (po.minutes != null ? " (" + esc(String(po.minutes).replace(".", ",")) + " min max)" : "") + (po.jusqua_fr ? " · jusqu’à " + esc(po.jusqua_fr) : "") +
        (po.file ? " · " + po.file + " alerte" + (po.file > 1 ? "s" : "") + " en attente" : "") + "</div>";
      // Réveil mouvement : la carte est dans Vue d'ensemble › Cycles automatiques (une seule sur le site) ; ici un lien.
      if (so.mouvement) h += '<p class="small" id="mv-link" style="margin-top:10px">Réveil mouvement de PM-Predict : <a href="#apercu">voir la carte dans Cycles automatiques</a>.</p>';
      // Distance des zones : écrite par la sonnette (status.json → zones_distance), telle quelle. Vert = critère tenu.
      var zd = so.zones_distance;
      if (zd && zd.paires) {
        var zp = function (z) { return z ? price(z.prix) + ' (<span data-gap="' + esc(z.id || "") + '">' + zGap(z.ecart_pct) + '</span>, <span data-etat="' + esc(z.id || "") + '">' + zEtat(z.etat) + "</span>)" : "aucune"; };
        h += '<div class="small" id="zones-distance" style="margin-top:10px"><b>Zone la plus proche à ' + esc(String(zd.max_pct)) + ' % ou moins, de chaque côté</b>' +
          Object.keys(zd.paires).sort().map(function (k) {
            var z = zd.paires[k];
            return '<div class="flow small" data-pair="' + esc(k) + '" style="gap:6px;margin-top:4px"><span class="badge ' + (z.ok ? "b-ok" : "b-err") + '">' + (z.ok ? "OK" : "trop loin") + "</span> " + pairHtml(k) +
              ' <span class="xs muted">dessous ' + zp(z.dessous) + " · dessus " + zp(z.dessus) + (z.ok ? "" : " · " + esc(z.probleme || "")) + "</span></div>";
          }).join("") + "</div>";
      }
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
    h += '<div class="xs muted" style="margin-top:6px" title="tools/sonnette/state (état + journal des sonneries)">Écrit par la sonnette. Adresses et clés jamais affichées.</div></div>';
    return h;
  }

  function kv(l, v) { return '<div><div class="label">' + l + '</div><div class="mono">' + v + "</div></div>"; }
  // Règles communes : même structure que references/regles-litterature.md (PM-Orchestrator). Groupes = titres du fichier,
  // dans son ordre ; les 3 parties du haut (portée écrite dans leur titre) sont les groupes principaux. Les étiquettes
  // (Simulation) / (Réel) / (Les deux) écrites devant une règle deviennent des pastilles. Le site ne range rien lui-même.
  var RTAG = { sim: ["b-sim", "Simulation"], reel: ["b-real", "Réel"], both: ["b-mute", "Les deux"] };
  function rtag(t) { var x = RTAG[t]; return x ? '<span class="badge rtag ' + x[0] + '" data-tag="' + t + '">' + x[1] + "</span>" : ""; }
  function rulesHtml(TR) {
    if (!TR || !TR.available) return '<div class="card"><p class="empty" title="references/regles-litterature.md">Règles introuvables pour l’instant.</p></div>';
    var fill = function (html) { return String(html || "").replace(/<span class="rtag" data-tag="(\w+)"><\/span>/g, function (_, t) { return rtag(t); }); };
    var line = function (b) { return (b.tag ? rtag(b.tag) + " " : "") + fill(b.html); };
    var h = '<div class="card rules-card" id="rulescard" data-updated="' + esc(TR.updated_date || "") + '">' +
      ((TR.intro || []).length ? '<div class="small text2" style="margin:0 0 10px">' + TR.intro.map(function (x) { return "<div>" + fill(x) + "</div>"; }).join("") + "</div>" : "");
    var mainDone = false;
    h += (TR.groups || []).map(function (g) {
      var sep = "";
      if (!g.main && !mainDone) { mainDone = true; sep = '<div class="xs muted" style="margin:14px 0 4px">Détail par thème</div>'; }
      var body = "", list = null;
      var close = function () { if (list) { body += "</" + list + ">"; list = null; } };
      g.blocks.forEach(function (b) {
        if (b.kind === "li") {
          var want = b.ordered ? "ol" : "ul";
          if (list !== want) { close(); body += "<" + want + ">"; list = want; }
          body += '<li data-tag="' + esc(b.tag || "") + '">' + line(b) +
            (b.sub && b.sub.length ? "<ul>" + b.sub.map(function (x) { return x.para ? '<li class="rpara">' + line(x) + "</li>" : '<li data-tag="' + esc(x.tag || "") + '">' + line(x) + "</li>"; }).join("") + "</ul>" : "") + "</li>";
        } else if (b.kind === "table") {   // tableau du fichier : vrai tableau ; sur petit écran, une carte par ligne
          close();
          var heads = (b.head || []).map(function (c) { return String(c || "").replace(/<[^>]*>/g, "").trim(); });
          body += '<table class="rtable rtab"><thead><tr>' + (b.head || []).map(function (c) { return "<th>" + fill(c) + "</th>"; }).join("") + "</tr></thead><tbody>" +
            (b.rows || []).map(function (r) { return "<tr>" + r.map(function (c, i) { return '<td data-label="' + esc(heads[i] || "") + '">' + fill(c) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table>";
        } else { close(); body += '<p data-tag="' + esc(b.tag || "") + '">' + line(b) + "</p>"; }
      });
      close();
      var sc = g.main && g.scope ? " " + rtag(g.scope) : "";
      return sep + '<details class="rgroup' + (g.main ? " rmain" : "") + '" data-scope="' + esc(g.scope || "") + '"' + (g.main ? " open" : "") + "><summary><span>" + esc(g.title) +
        (g.count ? ' <span class="xs muted">· ' + g.count + " règle" + (g.count > 1 ? "s" : "") + "</span>" : "") + sc + "</span></summary>" +
        '<div class="inner md small">' + body + "</div></details>";
    }).join("");
    return h + '<p class="xs muted" style="margin:8px 0 0" title="' + esc(TR.source) + '">Règles tenues par PM-Orchestrator, recopiées telles quelles.</p></div>';
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

  // Numéro D-xxx écrit plusieurs fois (build.py → decision_duplicates) : avertissement orange, rien de renuméroté.
  function dupWarn(id) { return "⚠️ Numéro en double (" + esc(id) + ") : Predict doit le corriger"; }
  // Carte de décision : MÊME ordre de lignes pour toutes (docs/modele-decision.md). Valeurs telles qu'écrites par PM-Predict /
  // PM-Risk ; champ absent → « pas évalué ». Anciennes entrées : lecture au mieux par build.py, étiquette « ancien format ».
  var TRIG_FR = { sonnette_zone: "🔔 Sonnette (zone de prix)", sonnette_mouvement: "〰️ Sonnette (mouvement)", brief_research: "📰 Brief de Research",
    demande_quentin: "🙋 Demande de Quentin", demande_risk: "🙋 Demande de Risk", demande_orchestrator: "🙋 Demande d’Orchestrator", prevision_du_jour: "🗓️ Prévision du jour", nuit: "🌙 Nuit" };
  var STATUT_FR = { "proposée": "Proposée", "proposee": "Proposée", en_attente_de_place: "En attente de place", "simulée": "Simulée", simulee: "Simulée",
    "pas_simulée": "Pas simulée", pas_simulee: "Pas simulée", "fermée": "Fermée", fermee: "Fermée", "expirée": "Expirée", expiree: "Expirée", "annulée": "Annulée", annulee: "Annulée", active: "Active" };
  var DEC_FR = { simuler: "Simuler", simuler_si_place: "Simuler s’il y a de la place", ne_pas_simuler: "Ne pas simuler" };
  var NE = '<span class="muted">pas évalué</span>';
  // Texte des bots affiché tel quel, sauf les noms de fichiers techniques (remplacés, comme les notes du site)
  function hidePaths(t) { return String(t == null ? "" : t).replace(/(?:[\w.-]+\/)+[\w.-]+\.(?:jsonl|json|md|py|sh|csv|txt|env)\b/g, "un fichier de l’équipe"); }
  function dv(v) { return v == null || v === "" || (Array.isArray(v) && !v.length) ? NE : esc(hidePaths(v)); }
  function dline(k, label, html) { return '<div class="dl" data-line="' + k + '"><div class="dk">' + label + '</div><div class="dv">' + html + "</div></div>"; }
  function decGo(x) {
    var t = (x.proposals || []).map(function (p) { return String(p.decision || ""); }).concat([String(x.decision_text || x.decision || "")]);
    return t.some(function (s) { return /^(ACHETER|VENDRE|SIMULER|simuler)/.test(s.trim()) && !/^(NE PAS|ne_pas)/i.test(s.trim()); });
  }
  function decDown(x) { return x.kind === "sell_first" || (x.proposals || []).some(function (p) { return /baisse/i.test(String(p.idee || "")); }); }
  function moneyLine(m) {   // modèle : prix relevés (nombres écrits) → affichés à la française, rien de calculé
    if (!m || !m.prix_releves) return m && m.prix ? esc(m.prix) : NE;
    var P = m.prix_releves; return (P.heure ? esc(P.heure) + " · " : "") + Object.keys(P).filter(function (k) { return k !== "heure"; }).map(function (k) { return esc(k.split("-")[0]) + " " + price(P[k]); }).join(" · ");
  }
  function propCard(p, single) {
    var lvl = p.niveau ? p.niveau.charAt(0).toUpperCase() + p.niveau.slice(1) : null, st = p.statut ? (STATUT_FR[p.statut] || p.statut) : p.statut_ecrit;
    var plan = p.prix_entree != null || p.montant_eur != null ? (p.montant_eur != null ? eur(p.montant_eur) : "montant pas évalué") + (p.quantite != null ? " (" + esc(String(p.quantite).replace(".", ",")) + ")" : "") +
      " · entrée " + (p.prix_entree != null ? price(p.prix_entree) : NE) + " → visé " + (p.prix_vise != null ? price(p.prix_vise) : NE) + " · arrêt " + (p.prix_arret != null ? price(p.prix_arret) : NE) : NE;
    var rap = p.heure_limite && /^\d{4}-\d{2}-\d{2}T/.test(p.heure_limite) ? fmtTime(p.heure_limite) : dv(p.heure_limite);
    return '<div class="dprop" data-prop="' + esc(p.id || (single ? "unique" : "")) + '"><div class="dph"><b>' + (single ? "Décision unique" : esc(p.id || "")) + "</b> " + (lvl ? '<span class="badge b-mute">' + esc(lvl) + "</span>" : "") + "</div>" +
      dline("niveau", "Niveau", lvl ? esc(lvl) + (p.niveau_regle ? ' <span class="xs muted">' + esc(p.niveau_regle) + "</span>" : "") : NE) +
      dline("idee", "Idée · sens", p.idee || p.sens ? dv(p.idee) + " · " + dv(p.sens) : NE) +
      dline("plan", "Montant · prix", plan) +
      dline("prevision", "Prévision", dv(p.prevision)) +
      dline("confiance", "Confiance", dv(p.confiance)) +
      dline("rappel", "Rappel (heure limite)", rap) +
      dline("decision", "Décision de Predict", p.decision ? esc(DEC_FR[p.decision] || p.decision) : NE) +
      dline("statut", "Statut", st ? '<span class="badge b-mute" data-statut>' + esc(st) + "</span>" : NE) +
      ((p.notes || []).length || p.pourquoi || p.avis_research ? '<div class="xs muted" style="margin-top:4px">' + [p.avis_research ? "Avis Research : " + p.avis_research : null, p.pourquoi ? "Pourquoi : " + p.pourquoi : null].concat(p.notes || []).filter(Boolean).map(esc).join("<br>") + "</div>" : "") + "</div>";
  }
  function decCard(x) {
    var yes = decGo(x), old = x.format !== "modele", m = x.moment || {}, cancelled = x.status === "annulée" || x.status === "annulee";
    var trig = x.trigger ? ((TRIG_FR[x.trigger.type] || (x.trigger.type ? esc(x.trigger.type) : "")) + (x.trigger.detail ? (x.trigger.type ? " · " : "") + esc(x.trigger.detail) : "")) || NE : NE;
    var reel = m.reel_permis === true ? "permis" : m.reel_permis === false ? "interdit" + (m.reel_raison ? " · " + esc(m.reel_raison) : "") : dv(m.reel);
    var place = m.place_libre_eur != null ? eur(m.place_libre_eur) : dv(m.place);
    var props = (x.proposals || []).length ? x.proposals.map(function (p) { return propCard(p, false); }).join("") :
      propCard({ idee: x.idea_type ? "à la " + x.idea_type : x.idea, sens: x.side_text, prevision: x.forecast, confiance: x.confidence, heure_limite: x.deadline_text, decision: x.decision_text || x.decision, statut_ecrit: x.status_text }, true);
    var rev = (x.reviewed || []).length ? "<ul class=\"dlist\">" + x.reviewed.map(function (r) { return "<li>" + (typeof r === "string" ? esc(hidePaths(r)) : esc([r.id, r.verdict ? "idée " + r.verdict : null, r.texte].filter(Boolean).join(" · "))) + "</li>"; }).join("") + "</ul>" : NE;
    var sv = (x.suivi || []).length ? "<ul class=\"dlist\">" + x.suivi.map(function (s) { return "<li>" + '<span class="mono xs">' + esc(s.heure && /T/.test(s.heure) ? fmtTime(s.heure) : (s.heure || "")) + "</span> <b>" + esc(s.par || "") + "</b>" + (s.proposition ? " (" + esc(s.proposition) + ")" : "") + (s.statut ? ' <span class="badge b-mute">' + esc(STATUT_FR[s.statut] || s.statut) + "</span>" : "") + " " + esc(hidePaths(s.texte || "")) + "</li>"; }).join("") + "</ul>" : NE;
    return '<div class="card dec ' + (yes ? "yes" : "no") + (cancelled ? " cancelled" : "") + '" id="dec-' + esc(x.key || x.id || "") + '" data-key="' + esc(x.key || x.id || "") + '" data-did="' + esc(x.id || "") + '" data-format="' + (old ? "ancien" : "modele") + '" data-time="' + esc(x.time || "") + '" style="margin-bottom:10px">' +
      (x.dup ? '<div class="notice warn small" data-dupwarn style="margin:0 0 6px">' + dupWarn(x.id) + "</div>" : "") +
      '<div class="card-title" style="margin-bottom:6px"><div><span class="mono"><b>' + esc(x.id) + "</b> · " + (x.pair ? pairHtml(x.pair) : '<span class="muted">paires pas évaluées</span>') + '</span> <span class="xs muted">' + (x.time ? fmtTime(x.time) : esc(x.time_text || "")) + "</span></div>" +
      '<div class="chips">' + badgeMode(x.mode) + (cancelled ? '<span class="badge b-mute" data-cancel>Annulée</span>' : "") + (old ? '<span class="badge b-mute" data-oldfmt title="Écrite avant le modèle commun : lue au mieux, telle qu’écrite">ancien format</span>' : "") + "</div></div>" +
      (x.status_text ? '<div class="xs muted" style="margin-bottom:4px">' + esc(x.status_text) + (x.ancien_numero ? "" : "") + "</div>" : "") +
      dline("declencheur", "Pourquoi maintenant", trig) +
      dline("resume", "Résumé", dv(x.summary || x.title)) +
      dline("prix", "Prix au moment de la décision", moneyLine(m)) +
      dline("place", "Place libre", place) +
      dline("reel", "Argent réel", reel) +
      dline("avis", "Avis Research", dv(x.avis_research)) +
      dline("pourquoi", "Pourquoi", dv(x.why)) +
      dline("revus", "Trades ouverts revus", rev) +
      '<div class="dl dl-props" data-line="propositions"><div class="dk">' + ((x.proposals || []).length ? "Les propositions" : "La décision") + '</div><div class="dv">' + props + "</div></div>" +
      dline("valable", "Valable jusqu’à", dv(x.valid_until)) +
      dline("suivi", "Suivi (Risk, Predict)", sv) +
      (x.ancien_numero || x.remplacee_par ? dline("numero", "Numéro", (x.ancien_numero ? "ancien numéro " + esc(x.ancien_numero) : "") + (x.remplacee_par ? " · remplacée par " + esc(x.remplacee_par) : "")) : "") +
      '<details><summary>Tout le texte (tel qu’écrit)</summary><div class="inner md">' + (x.raw || x.bullets || []).map(function (b) { return "<div>" + b + "</div>"; }).join("") + "</div></details></div>";
  }


  function fmtMs(ms, withH) { var q = bxParts(new Date(ms)); return String(q.d).padStart(2, "0") + "/" + String(q.m).padStart(2, "0") + (withH ? " " + q.h + "h" + String(q.mi).padStart(2, "0") : ""); }
  function renderPair() {
    var P = STATE.data.performance, k = STATE.ui.pair, d = (P.pairs || {})[k]; if (!d || !el("pairbox")) return;
    var lp = livePrices(), live = (lp.pairs || {})[k] || {}, px = live.mid || d.price, ho = d.holdings || {};
    // Positions simulées : guardian/state.json (PM-Risk) ; pièces réelles : state/live_equity.json. Aucun total recalculé.
    function modeBox(mode) {
      if (mode === "reel") {
        var hr = ho.reel;
        if (!hr) return '<div class="card flat"><div class="card-title"><h3>Réel</h3><span class="badge b-real">Réel</span></div><p class="small muted" title="state/live_equity.json">Soldes réels pas encore écrits par la sonnette.</p></div>';
        return '<div class="card flat"><div class="card-title"><h3>Réel</h3><span class="badge b-real">Réel</span></div><div class="kv">' +
          kv("Pièces de Quentin (hors bot)", hr.hors_bot ? coinQty(hr.hors_bot.qty) + '<div class="xs muted">' + eur(hr.hors_bot.eur) + "</div>" : "—") +
          kv("Pièces du bot", hr.bot ? coinQty(hr.bot.qty) + (hr.bot.eur != null ? '<div class="xs muted">' + eur(hr.bot.eur) + "</div>" : "") : "0") + "</div></div>";
      }
      var ps = ho.sim || [];
      return '<div class="card flat"><div class="card-title"><h3>Simulation</h3>' + badgeMode("sim") + '</div><div class="small">' +
        (ps.length ? ps.map(function (x) { return "<div>" + sideBadge(x.side) + " " + coinQty(x.qty) + " à " + price(x.entry_price) + ' <span class="xs muted">· valeur gardien ' + eur(x.mark_eur) + (x.decision_id ? " · " + esc(x.decision_id) : "") + "</span></div>"; }).join("") : '<span class="muted">Aucune position ouverte.</span>') +
        '</div><div class="xs muted" style="margin-top:6px">Résultats par monnaie : non écrits par l’équipe (voir la <a href="trades.html">liste des trades</a>).</div></div>';
    }
    el("pairbox").innerHTML = '<div class="card"><div class="flow" style="justify-content:space-between;align-items:baseline"><div><div class="label">' + pairHtml(k) + ' · 7 derniers jours</div><div class="mid ' + cls(d.change_7d_pct) + '">' + pct(d.change_7d_pct, 2, true) + "</div></div>" +
      '<div class="small mono muted">bas ' + price(d.low_7d) + " · haut " + price(d.high_7d) + "</div></div>" +
      '<div class="xs muted" style="margin:4px 0 8px">Prix actuel et variation 24 h : dans la barre des prix en haut.</div>' +
      '<div class="chart-box"><canvas id="pc"></canvas></div>' +
      '<div class="chips xs" style="margin-top:8px"><span class="badge b-buy">△ achat simulé (creux)</span><span class="badge b-sell">▽ vente simulée (creux)</span><span class="badge b-buy">▲ achat réel (plein)</span><span class="badge b-sell">▼ vente réelle (plein)</span></div>' +
      '<p class="xs muted" style="margin:8px 0 0" title="' + esc((d.sources || []).join(" + ")) + '">Prix publics ; achats et ventes de l’équipe.' + (d.markers.length ? "" : " Aucun achat ni vente sur cette période.") + (d.markers_outside ? " " + d.markers_outside + " point(s) plus ancien(s) que 7 jours non affiché(s)." : "") + "</p></div>" +
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

  function fgFr(v) { return v == null ? "—" : v <= 24 ? "Peur extrême" : v <= 44 ? "Peur" : v <= 55 ? "Neutre" : v <= 75 ? "Avidité" : "Avidité extrême"; }
  function fgColor(v) { return v <= 24 ? "#ef4444" : v <= 44 ? "#f97316" : v <= 55 ? "#eab308" : v <= 75 ? "#84cc16" : "#22c55e"; }
  function objToHtml(o) {
    if (o == null) return "";
    if (typeof o !== "object") return esc(o);
    if (Array.isArray(o)) return "<ul>" + o.map(function (x) { return "<li>" + objToHtml(x) + "</li>"; }).join("") + "</ul>";
    return "<ul>" + Object.keys(o).map(function (k) { return "<li><b>" + esc(k.replace(/_/g, " ")) + " :</b> " + objToHtml(o[k]) + "</li>"; }).join("") + "</ul>";
  }
  // Zones de prix de PM-Predict (state/zones_reveil.json → summary.sonnette.zones : même paquet /api/live que le reste).
  // « sous » = idée à la baisse, « au-dessus » = idée à la hausse. Écart et état : écrits par la sonnette (status.json →
  // zones_distance), TELS QUELS et identiques sur toutes les pages. Le navigateur ne calcule ni écart ni état.
  function zoneUp(z) { return !(String(z.side || "").indexOf("sous") === 0 || z.side === "below"); }
  function zoneOn(z) { return z.enabled !== false && (!z.expire || new Date(z.expire) > new Date()); }
  function zGap(v) { return v == null ? '<span class="muted">pas évalué</span>' : String(v).replace(".", ",") + " %"; }   // chiffre exact de la sonnette, pas arrondi
  function zEtat(v) { return v == null || v === "" ? '<span class="muted">pas évalué</span>' : esc(String(v)); }   // tel qu'écrit (dedans / au-dessus / en dessous)
  // Ce que la sonnette a écrit pour une zone : côté (dessous/dessus) si c'est la zone la plus proche, sinon rien.
  function zoneMeasure(z) {
    var zd = ((STATE.data.summary || {}).sonnette || {}).zones_distance || {}, P = (zd.paires || {})[z.pair] || {};
    var side = P.dessous && P.dessous.id === z.id ? P.dessous : P.dessus && P.dessus.id === z.id ? P.dessus : null;
    var et = side && side.etat != null ? side.etat : P.etat && typeof P.etat === "object" ? P.etat[z.id] : typeof P.etat === "string" ? P.etat : null;
    return { gap: side ? side.ecart_pct : null, etat: et == null ? null : et, prix: P.prix };
  }
  function renderZones() {
    var box = el("zonesbox"); if (!box) return;
    var so = (STATE.data.summary || {}).sonnette || {}, ORD = { BTC: 0, ETH: 1, SOL: 2 };
    var zs = (so.zones || []).filter(function (z) { return String(z.bot || "predict").toLowerCase().indexOf("predict") >= 0; }).sort(function (a, b) {
      var pa = String(a.pair).split("-")[0], pb = String(b.pair).split("-")[0];
      return ((ORD[pa] != null ? ORD[pa] : 9) - (ORD[pb] != null ? ORD[pb] : 9)) || String(a.pair).localeCompare(String(b.pair)) || (a.price - b.price);
    });
    if (!zs.length) { box.innerHTML = '<p class="empty">Aucune zone pour l’instant. Predict les refait chaque jour vers 14h55.</p>'; return; }
    box.innerHTML = '<div class="table-wrap"><table class="rtable"><thead><tr><th>Paire</th><th>Idée</th><th class="num">Zone</th><th>Jusqu’à</th><th>Statut</th><th class="num">Écart (sonnette)</th><th>Prix / zone</th></tr></thead><tbody>' + zs.map(function (z) {
      var up = zoneUp(z), on = zoneOn(z), M = zoneMeasure(z);
      var st = z.enabled === false ? ["b-mute", "coupée"] : on ? ["b-info", "⏳ active"] : ["b-mute", "expirée"];
      return '<tr data-zone="' + esc(z.id || "") + '"><td data-label="Paire" class="mono nowrap">' + pairHtml(z.pair) + '</td><td data-label="Idée" class="nowrap"' + (z.reason ? ' title="' + esc(z.reason) + '"' : "") + ">" + (up ? "📈 à la hausse" : "📉 à la baisse") +
        '</td><td data-label="Zone" class="num nowrap"><b>' + (up ? "↑ " : "↓ ") + price(z.price) + '</b></td><td data-label="Jusqu’à" class="mono small nowrap">' + fmtTime(z.expire) +
        '</td><td data-label="Statut"><span class="badge ' + st[0] + '">' + st[1] + '</span></td><td data-label="Écart (sonnette)" class="num nowrap" data-gap>' + zGap(M.gap) +
        '</td><td data-label="Prix / zone" class="small" data-etat>' + zEtat(M.etat) + "</td></tr>";
    }).join("") + "</tbody></table></div>" +
      '<p class="xs muted" style="margin:6px 0 0">📈 si le prix passe au-dessus de la zone, 📉 s’il passe en dessous : la sonnette réveille Predict pour revoir l’idée. Aucun ordre automatique. Écart = chemin qui reste, écrit par la sonnette pour la zone la plus proche de chaque côté (les autres : « pas évalué »). Prix / zone = état écrit par la sonnette (dedans, au-dessus, en dessous) ; « pas évalué » tant qu’elle ne l’écrit pas.</p>';
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
    var isNo = function (x) { return !decGo(x); };
    var dfl = D.filter(function (x) { return df === "all" || (df === "va" && decDown(x)) || (df === "oui" && !isNo(x)) || (df === "non" && isNo(x)); });
    // lien depuis Trades : research.html?d=D-031#decisions → la carte est affichée (filtre « Toutes ») et mise en avant
    var focus = new URLSearchParams(location.search).get("d");
    if (focus && !STATE.ui.decFocusDone) { var fi = D.map(function (x) { return x.id; }).indexOf(focus); if (fi >= 0) { df = "all"; STATE.ui.decf = "all"; dfl = D; if (fi >= dl) dl = STATE.ui.decLimit = fi + 1; } }
    var DD = R.decision_duplicates || [];
    var hd = '<section class="section" id="decisions">' + secHead("Décisions écrites", "le carnet de l'équipe, y compris les idées refusées") +
      (DD.length ? '<div class="notice warn" id="dec-dup">' + DD.map(function (d) { return dupWarn(d.id) + ' <span class="xs">(' + d.count + " cartes : " + esc((d.times || []).join(", ")) + ")</span>"; }).join("<br>") + "</div>" : "") +
      chipsBar([["all", "Toutes", D.length], ["oui", "Achat / vente décidé", D.filter(function (x) { return !isNo(x); }).length], ["non", "Refusées", D.filter(isNo).length], ["va", "Idée à la baisse", D.filter(decDown).length]], df, "df") +
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
    var fq = new URLSearchParams(location.search).get("d");
    if (fq && !STATE.ui.decFocusDone && tab === "decisions") {
      var fc = document.querySelector('.card.dec[data-did="' + fq.replace(/[^A-Za-z0-9-]/g, "") + '"]');
      if (fc) { STATE.ui.decFocusDone = true; fc.classList.add("focus"); setTimeout(function () { fc.scrollIntoView({ block: "start" }); }, 50); }
    }

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
    h += '<p class="xs muted" style="margin-top:14px">Liste mise à jour ' + ago(N.generated_at) + "." + (hosted() ? "" : ' <span title="/workspace/dashboard/data/news.json">Aussi disponible pour les bots.</span>') + "</p>";
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
    h += '<section class="section">' + secHead("Comment marche ce site", "") + '<div class="card small text2"><p style="margin-top:0">Un petit programme relit toutes les 5 minutes les fichiers de l\'équipe, les prix publics, les soldes (en lecture seule) et les flux d\'actualités, puis fabrique ce site. <b>Aucune IA n\'est utilisée</b> pour le site et aucun ordre ne peut être passé d\'ici. Les pages se rechargent toutes les 60 secondes. Toutes les heures sont celles de Bruxelles.' + (hosted() ? " <b>Version en ligne</b> : une copie est publiée sur Cloudflare Pages toutes les ~" + (STATE.deploy.interval_min || 15) + " min (dernière publication " + ago(STATE.deploy.deployed_at) + "), protégée par mot de passe ; les chiffres peuvent donc avoir jusqu'à ~15 min de retard." : "") + '</p>' +
      "<p>Les soldes réels sont affichés derrière le mot de passe du site. L’adresse du portefeuille MetaMask n’est jamais publiée. Soldes réels (actuellement : <b>" + (s.show_real ? "activée" : "désactivée") + "</b>). " + (hosted() ? "Cette version en ligne est protégée par identifiant et mot de passe." : "Pour une version en ligne, il faut la désactiver ou protéger le site par un mot de passe.") + "</p>" +
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
  setInterval(function () { tickCountdowns(); }, 1000);                                                       // comptes à rebours des cycles
  window.addEventListener("hashchange", function () { if (STATE.data.summary) renderPage(); });
  setInterval(renderFresh, 5000);                                                          // âges de l'en-tête (« il y a X s »)
  setInterval(function () {                // « il y a X min » + barres de progression
    if (PAGE === "index" && STATE.data.summary && el("cycles")) el("cycles").innerHTML = allCycles(STATE.data.summary).map(cycleCard).join("");
    if (PAGE === "index" && el("rrun")) renderRuns();                                      // « En cours » → « Pas fini » après 30 min
  }, 15000);
  window.addEventListener("resize", function () { if (charts.eq) charts.eq.resize(); if (charts.pc) charts.pc.resize(); });
})();
