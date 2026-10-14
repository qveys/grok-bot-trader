#!/usr/bin/env python3
"""Équipe trading — Tableau de bord : générateur statique.

Lit (en LECTURE SEULE) les fichiers de /workspace/predict-market-bot, quelques
sources publiques (RSS, RPC Arbitrum, Fear & Greed) et le solde Revolut X
(`revx account balances --json`, lecture seule), puis écrit du JSON + HTML/JS/CSS
statiques dans /workspace/dashboard/site/.

Aucun appel IA. Aucune commande d'ordre. Robuste aux fichiers manquants.
"""
from __future__ import annotations

import csv
import glob
import html
import json
import math
import os
import re
import shutil
import hashlib
import subprocess
import sys
import time
import traceback
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo("Europe/Brussels")
UTC = timezone.utc
NOW = datetime.now(UTC)

CFG = {
    "SHOW_REAL": True,
    "SITE_TITLE": "Équipe trading — Tableau de bord",
    "BOT_DIR": "/workspace/predict-market-bot",
    "VIBE_DIR": "/workspace/tools/vibe-trading",
    "PROXY": "http://127.0.0.1:8791",
    "METAMASK_ADDRESS": "0xb88D4A78e960F04E8c9a5da2B91Bf74c49c271e8",
    "ARBITRUM_RPC": "https://arb1.arbitrum.io/rpc",
    "REVX_BIN": "/home/box/.local/bin/revx",
    "SENTIMENT_CACHE_MIN": 30,
    "NEWS_CACHE_MIN": 5,
}
try:
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as _f:
        CFG.update({k: v for k, v in json.load(_f).items() if not k.startswith("_")})
except Exception:
    pass
if os.environ.get("SHOW_REAL") is not None:
    CFG["SHOW_REAL"] = os.environ["SHOW_REAL"].strip().lower() in ("1", "true", "yes", "oui")

BOT = CFG["BOT_DIR"]
VIBE = CFG["VIBE_DIR"]
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "src")
DATA_OUT = os.path.join(SITE, "data")
SHARED_DATA = os.path.join(ROOT, "data")  # lisible par les bots (news.json)
CACHE = os.path.join(ROOT, "cache")
WARNINGS: list[str] = []
sys.path.insert(0, ROOT)
import prices as PRICES  # noqa: E402
PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
PROJECT_START = datetime.fromisoformat(CFG.get("PROJECT_START", "2026-10-06")).replace(tzinfo=TZ).astimezone(UTC)


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print("[warn]", msg, file=sys.stderr)


# ----------------------------------------------------------------- helpers
def p(*parts: str) -> str:
    return os.path.join(BOT, *parts)


def read_text(path: str, default: str = "") -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return default


def read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_jsonl(path: str) -> list:
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def tail_jsonl(path: str, n: int = 50) -> list:
    """Lit seulement la fin d'un gros fichier jsonl."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 200 * n))
            lines = f.read().decode("utf-8", "replace").splitlines()[-n:]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out
    except Exception:
        return []


def parse_ts(v, naive_tz=UTC):
    """Renvoie un datetime aware (UTC) ou None."""
    if v is None or v == "":
        return None
    try:
        if isinstance(v, (int, float)):
            x = float(v)
            if x > 1e12:
                x /= 1000.0
            return datetime.fromtimestamp(x, UTC)
        s = str(v).strip().replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=naive_tz)
        return d.astimezone(UTC)
    except Exception:
        return None


def iso(d):
    return d.astimezone(UTC).isoformat().replace("+00:00", "Z") if d else None


def mtime(path: str):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), UTC)
    except Exception:
        return None


def fnum(v, default=None):
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def rnd(v, n=2):
    return None if v is None else round(v, n)


# Vocabulaire validé par Quentin (8 oct.) : « idée à la hausse » (acheter puis revendre plus haut) et
# « idée à la baisse » (vendre des pièces qu'on a, puis racheter plus bas ; D-018 en est une).
# L'ancienne expression n'apparaît jamais sur le site, même quand elle vient des textes des bots/outils.
_OLD_SF = re.compile(r"(vendre|vente)[ _-]+d['’]abord(\s+puis\s+racheter)?", re.I)
def _new_words(m):
    w = "l'idée à la baisse" + (" (vendre puis racheter plus bas)" if m.group(2) else "")
    return w[0].upper() + w[1:] if m.group(0)[:1].isupper() else w

def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    txt = json.dumps(obj, ensure_ascii=False, indent=1, default=str)
    if os.path.abspath(path).startswith(os.path.abspath(DATA_OUT)):
        txt = _OLD_SF.sub(_new_words, txt)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(txt)
    os.replace(tmp, path)


def opener():
    proxy = CFG.get("PROXY")
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def http_get(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 20) -> bytes:
    h = {"User-Agent": "Mozilla/5.0 (PM-Pipeline-dashboard; +static)"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with opener().open(req, timeout=timeout) as r:
        return r.read()


def cache_get(name: str, max_age_min: float):
    path = os.path.join(CACHE, name)
    d = read_json(path)
    if d is None:
        return None, None
    age = time.time() - os.path.getmtime(path)
    return d, age <= max_age_min * 60


def cache_put(name: str, obj) -> None:
    write_json(os.path.join(CACHE, name), obj)


# Liste blanche STRICTE : uniquement des commandes de lecture. Jamais place / cancel / replace.
REVX_ALLOWED = {
    ("account", "balances"),
    ("market", "tickers"), ("market", "ticker"), ("market", "candles"),
    ("order", "history"), ("order", "open"), ("order", "active"), ("order", "fills"), ("order", "get"),
    ("trade", "private"), ("trade", "history"),
    ("transaction", "list"), ("transaction", "get"),
}
REVX_FORBIDDEN = {"place", "cancel", "replace", "configure", "strategy", "monitor", "connector", "events"}


def revx_read(args: list[str], timeout: int = 40):
    """Appelle revx en LECTURE SEULE (liste blanche stricte)."""
    if len(args) < 2 or (args[0], args[1]) not in REVX_ALLOWED or any(a in REVX_FORBIDDEN for a in args):
        raise ValueError("commande revx non autorisée: %r" % (args,))
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(CFG["REVX_BIN"]) + ":" + env.get("PATH", "")
    env.setdefault("HTTPS_PROXY", CFG["PROXY"])
    env.setdefault("HTTP_PROXY", CFG["PROXY"])
    r = subprocess.run([CFG["REVX_BIN"], *args], capture_output=True, text=True, timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    return json.loads(r.stdout)


def md_inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?![\s_])(.+?)(?<![\s_])_(?![\w_])", r"<em>\1</em>", s)   # _italique_ (pas les noms_de_fichiers)
    return s


def md_to_html(md: str) -> str:
    out, in_list, in_table = [], False, False
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if not in_table:
                if in_list:
                    out.append("</ul>"); in_list = False
                out.append('<div class="table-wrap"><table class="mini">'); in_table = True
            out.append("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table></div>"); in_table = False
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if in_list:
                out.append("</ul>"); in_list = False
            lvl = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{md_inline(m.group(2))}</h{lvl}>")
            continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{md_inline(m.group(1))}</li>")
            continue
        if in_list and line.strip() == "":
            out.append("</ul>"); in_list = False
            continue
        if line.strip() == "---":
            out.append("<hr>")
        elif line.strip().startswith(">"):
            out.append(f"<blockquote>{md_inline(line.strip()[1:].strip())}</blockquote>")
        elif line.strip():
            out.append(f"<p>{md_inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table></div>")
    return "\n".join(out)


def strip_md(s: str) -> str:
    s = re.sub(r"\*\*|`", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------- prices
def load_prices():
    """Prix EUR (mid) : tickers Revolut X (lecture publique), sinon derniers ticks du collecteur."""
    prices, source = {}, None
    try:
        d = revx_read(["market", "tickers", "--json"])
        for t in d.get("data", []):
            sym = str(t.get("symbol", "")).replace("/", "-")
            mid = fnum(t.get("mid")) or fnum(t.get("last_price"))
            if not mid:
                continue
            last = fnum(t.get("last_price")) or mid
            ch = fnum(t.get("price_change_24h"))
            pct = (ch / (last - ch) * 100.0) if ch is not None and (last - ch) else None
            prices[sym] = {"mid": mid, "change_24h_pct": rnd(pct, 2), "high_24h": fnum(t.get("high_24h")),
                           "low_24h": fnum(t.get("low_24h"))}
        ts = parse_ts(d.get("metadata", {}).get("timestamp")) or NOW
        source = {"name": "Revolut X (prix publics)", "at": iso(ts)}
        cache_put("prices.json", {"prices": prices, "source": source})
    except Exception as e:
        warn(f"prix revx indisponibles: {e}")
        c, _ = cache_get("prices.json", 1e9)
        if c:
            prices, source = c["prices"], dict(c["source"], stale=True)
    # SOURCE PRINCIPALE pour BTC/ETH/SOL : ticks 30 s du collecteur de l'équipe (prices.py)
    live = PRICES.write(os.path.join(DATA_OUT, "prices.json"))
    for pair, v in live.get("pairs", {}).items():
        if v.get("mid") and v.get("ts"):
            prices[pair] = dict(prices.get(pair, {}), mid=v["mid"], change_24h_pct=v.get("change_24h_pct"),
                                tick_ts=v["ts"], stale=v.get("stale"), from_ticks=True)
    if live.get("last_tick_at"):
        source = {"name": "Collecteur 30 s de l'équipe (repli : Revolut X)", "at": live["last_tick_at"], "stale": live.get("stale")}
    return prices, source


def price_eur(prices: dict, cur: str):
    if cur == "EUR":
        return 1.0
    for sym in (f"{cur}-EUR",):
        if sym in prices:
            return prices[sym]["mid"]
    if f"{cur}-USD" in prices and "EUR-USD" in prices:
        return prices[f"{cur}-USD"]["mid"] / prices["EUR-USD"]["mid"]
    if cur in ("USDC", "USDT", "USD") and "EUR-USDC" in prices:
        return 1.0 / prices["EUR-USDC"]["mid"]
    if cur in ("USDC", "USDT") and "USDC-EUR" in prices:
        return prices["USDC-EUR"]["mid"]
    return None


# ----------------------------------------------------------------- journals
def parse_trading_journal():
    txt = read_text(p("knowledge", "trading_journal.md"))
    part = txt.split("## Entrées", 1)[1] if "## Entrées" in txt else ""
    entries = []
    for block in re.split(r"\n### ", "\n" + part)[1:]:
        lines = block.strip().splitlines()
        head = [h.strip() for h in lines[0].split("|")]
        e = {"date": head[0] if head else "", "pair": head[1] if len(head) > 1 else "",
             "kind": head[2] if len(head) > 2 else "", "link": head[3] if len(head) > 3 else "", "fields": {}}
        for ln in lines[1:]:
            m = re.match(r"^\s*-\s*([^:]+?)\s*:\s*(.*)$", ln)
            if m:
                e["fields"][strip_md(m.group(1))] = strip_md(m.group(2))
        entries.append(e)
    return entries


def parse_decision_log():
    txt = read_text(p("knowledge", "decision_log.md"))
    part = txt.split("## Entrées", 1)[1] if "## Entrées" in txt else ""
    out = []
    for block in re.split(r"\n### ", "\n" + part)[1:]:
        lines = block.strip().splitlines()
        head = lines[0]
        parts = [h.strip() for h in head.split("|")]
        when = parts[0] if parts else ""
        pair = parts[1] if len(parts) > 1 else ""
        rest = " | ".join(parts[2:]) if len(parts) > 2 else ""
        m = re.match(r"(D-\d+)\s*(?:—\s*(.*))?", rest)
        did = m.group(1) if m else rest
        title = (m.group(2) or "") if m else ""
        dt = None
        try:
            dt = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=TZ).astimezone(UTC)
        except Exception:
            pass
        fields, bullets = {}, []
        for ln in lines[1:]:
            mm = re.match(r"^\s*-\s*(.+?)\s*:\s*(.*)$", ln)
            if ln.strip().startswith("-"):
                bullets.append(md_inline(re.sub(r"^\s*-\s*", "", ln)))
            if mm:
                fields[strip_md(mm.group(1))] = strip_md(mm.group(2))

        def find(prefix):
            for k, v in fields.items():
                if k.lower().startswith(prefix.lower()):
                    return v
            return None

        dec = find("Décision") or ""
        decision = "ACHETER" if re.search(r"\bACHETER\b", dec) and "PAS ACHETER" not in dec else ("PAS ACHETER" if "PAS ACHETER" in dec else (
            "PAS VENDRE" if "PAS VENDRE" in dec else ("VENDRE" if re.search(r"\bVENDRE\b", dec) else (dec or "?"))))
        blob = head + "\n" + "\n".join(lines[1:])
        # Type d'idée et sens : lus dans le carnet (champs « Idée » / « Type » et « Sens » écrits par PM-Predict), sinon déduits.
        idea_txt = (find("Type d") or find("Idée") or "")
        idea_type = "baisse" if re.search(r"à la baisse|\bbaisse\b", idea_txt, re.I) else ("hausse" if re.search(r"à la hausse|\bhausse\b", idea_txt, re.I) else None)
        side_txt = find("Sens")
        if idea_type is None:
            idea_type = "baisse" if (did == "D-018" or re.search(r"vendre haut|vendre d.abord|racheter plus bas|idée à la baisse|\bD-018\b", blob, re.I)) else None
        kind = "sell_first" if idea_type == "baisse" else "buy"
        mode = "reel" if re.search(r"\blive\b|réel", dec, re.I) and decision == "ACHETER" else "sim"
        # Bilans « Test du passé » / Compound / vibe-trading : pas des décisions
        # achat/vente — ils vont dans Performance › Tests du passé (autre source).
        head_blob = " ".join([head, str(did or ""), str(title or ""), when or ""])
        is_past_test = bool(re.search(
            r"Test du passé|bilan\s+Compound|vibe[- ]?trading\s+bilan",
            head_blob, re.I))
        has_decision_id = bool(re.match(r"^D-\d+$", str(did or "").strip()))
        if is_past_test and not has_decision_id:
            continue
        # Carte vide / sans id ni décision réelle → ne pas polluer Décisions écrites
        if not has_decision_id and decision in ("?", "") and not (title or "").strip():
            continue
        out.append({
            "id": did, "title": strip_md(title), "time": iso(dt), "time_text": when, "pair": pair,
            "decision": decision, "decision_text": dec, "mode": mode, "kind": kind, "idea_type": idea_type, "side_text": side_txt,
            "idea": find("Idée"), "sell_rule": find("Règle"),
            "context": find("Relevé") or find("Quand on achète"),
            "forecast": find("Prévision mesurable") or find("**Prévision"),
            "expected_gain": find("Gain espéré"),
            "max_loss": find("Perte max"),
            "cost": find("Coût aller-retour"),
            "gate_3x": find("Gain ≥ 3"),
            "why": find("Pourquoi"),
            "backtest": find("Test du passé"),
            "score": find("Score"),
            "bullets": bullets,
        })
    return out


# ----------------------------------------------------------------- règles d'équipe (source unique)
MOIS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
RULE_GROUPS = [("simulation", "Simulation"), ("live", "Réel"), ("horaires", "Horaires"),
               ("surveillance", "Surveillance et sonnettes"), ("equipe", "Équipe et carnets")]
# Portée affichée à côté de chaque groupe (le texte des règles n'est jamais réécrit, seulement rangé).
RULE_SCOPE = {"simulation": "sim", "live": "reel"}


def _rule_group_of_section(title):
    t = title.lower()
    for rx, g in ((r"officielles", "top"), (r"surveill|sonnette", "surveillance"), (r"horaire", "horaires"),
                  (r"simulation|taille|pièces|motifs", "simulation"),
                  (r"test du passé|résultats des tests|anti-faillite|fructifier|espérance|live", "live"),
                  (r"carnet|organisation|façon|bot|sources", "equipe")):
        if re.search(rx, t):
            return g
    return "equipe"


def _rule_group_of_item(sec_group, raw):
    """Une règle qui commence par « Simulation… » va dans le groupe Simulation, une qui commence par « Live… »,
    « En live », « Pas de live », « Ticket mini live » ou « Pas de vrai achat » dans le groupe Réel, quelle que soit
    sa section d'origine (le titre de la section reste affiché). Le reste suit sa section."""
    s = re.sub(r"^\*\*", "", raw.strip()).lower()
    if sec_group == "top":
        return sec_group
    if s.startswith("simulation"):
        return "simulation"
    if re.match(r"^(live\b|en live\b|pas de live\b|ticket mini live\b|pas de vrai achat\b)", s):
        return "live"
    if sec_group == "horaires" and re.search(r"signaux de vie|^sonnette", s):
        return "surveillance"
    return sec_group


def load_team_rules():
    """references/regles-litterature.md (PM-Orchestrator, lecture seule) → règles affichées sur À propos.
    Aucune copie en dur : tout le texte vient du fichier."""
    path = p("references", "regles-litterature.md")
    txt = read_text(path)
    if not txt.strip():
        return {"available": False, "source": "references/regles-litterature.md"}
    mt = mtime(path)
    loc = mt.astimezone(TZ) if mt else None
    dates = sorted(set(re.findall(r"\b(20\d\d-\d\d-\d\d)\b", txt)))
    title = ""
    top, intro, groups = [], [], {g: [] for g, _ in RULE_GROUPS}
    sec_title, sec_group, cur = None, None, None

    def add(raw):
        nonlocal cur
        raw = raw.strip()
        if not raw:
            return
        if sec_group == "top":
            top.append(md_inline(raw)) if re.match(r"^\d+\.\s", raw) is None else top.append(md_inline(re.sub(r"^\d+\.\s*", "", raw)))
            return
        g = _rule_group_of_item(sec_group or "equipe", raw)
        lst = groups[g]
        if not lst or lst[-1]["title"] != sec_title:
            lst.append({"title": sec_title, "items": []})
        clean = re.sub(r"^\d+\.\s*", "", raw)
        clean = re.sub(r"\s*\(id\s+[0-9a-f-]{20,}\s*,?\s*", " (", clean)  # pas d'id de groupe dans le site
        clean = re.sub(r"\bid\s+[0-9a-f-]{20,}\b", "", clean)
        clean = re.sub(r"\(\s*,", "(", clean); clean = re.sub(r",\s*\)", ")", clean)
        clean = re.sub(r"\(\s*\)", "", clean)
        lst[-1]["items"].append(md_inline(clean))

    for ln in txt.splitlines():
        s = ln.rstrip()
        m = re.match(r"^#\s+(.*)", s)
        if m and not title:
            title = strip_md(m.group(1)); continue
        m = re.match(r"^##+\s+(.*)", s)
        if m:
            raw_t = strip_md(m.group(1))
            sec_group = _rule_group_of_section(raw_t)
            # titre court : sans la parenthèse « (validé …, 2026-10-08) »
            sec_title = re.sub(r"\s*\((?:[^()]*\d{4}-\d\d-\d\d[^()]*|validé[^()]*|chiffres[^()]*|obligatoire[^()]*|Quentin)\)\s*$", "", raw_t).strip()
            continue
        if not s.strip() or s.strip().startswith(">") or s.strip() == "---":
            continue
        if sec_group is None:
            continue
        mb = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", s)
        if mb:
            add(mb.group(1))
        elif sec_group == "top":
            intro.append(md_inline(s.strip()))
        else:
            add(s.strip().rstrip("\\").strip())
    out_groups = [{"key": g, "title": lab, "scope": RULE_SCOPE.get(g, "both"), "sections": groups[g], "count": sum(len(x["items"]) for x in groups[g])}
                  for g, lab in RULE_GROUPS if groups[g]]
    return {"available": True, "source": "references/regles-litterature.md", "title": title,
            "updated": iso(mt), "updated_date": loc.strftime("%Y-%m-%d") if loc else None,
            "updated_label": f"{loc.day} {MOIS_FR[loc.month - 1]} {loc.year} à {loc.hour}h{loc.minute:02d}" if loc else None,
            "latest_date_in_file": dates[-1] if dates else None,
            "official": top, "official_note": intro, "groups": out_groups}


TIME_PATTERNS = [
    re.compile(r"^\s*-\s*\*\*~?(\d{1,2})[h:](\d{2})\*\*\s*[—:-]*\s*(.*)$"),
    re.compile(r"^\s*-\s*~(\d{1,2})[h:](\d{2})\s*(?:\([^)]*\))?\s*[—:-]+\s*(.*)$"),
]
DATED_LINE = re.compile(r"^\s*-?\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s*[—:-]+\s*(.*)$")


# Journaux des bots — format commun (references/format-journal.md) : « ## 4. Journal », puis « ### 8 oct. 2026 »,
# puis « - **23h00** · 📌 texte (D-xxx) ». Seule la section 4 crée des lignes ; les sections 1 à 3 sont ignorées.
# Heure absente (« soir », « après-midi »…) : heure approximative pour le tri + libellé affiché (time_label).
FR_MONTHS = {"janv": 1, "janvier": 1, "févr": 2, "fevr": 2, "février": 2, "fevrier": 2, "mars": 3, "avr": 4, "avril": 4, "mai": 5,
             "juin": 6, "juil": 7, "juillet": 7, "août": 8, "aout": 8, "sept": 9, "septembre": 9, "oct": 10, "octobre": 10,
             "nov": 11, "novembre": 11, "déc": 12, "dec": 12, "décembre": 12, "decembre": 12}
APPROX_TIMES = {"nuit": (2, 0), "matin": (9, 0), "matinée": (9, 0), "midi": (12, 0), "après-midi": (15, 0), "apres-midi": (15, 0),
                "fin d'après-midi": (17, 30), "fin d’après-midi": (17, 30), "soir": (20, 0), "soirée": (20, 0), "fin de soirée": (22, 30)}
JL_DEFAULT = [["✅", "fait"], ["📌", "décision"], ["🔔", "alerte"], ["⚠️", "problème"], ["💡", "leçon"], ["📜", "règle reçue"]]


def journal_legend_read():
    """Types d'entrée des journaux : ligne « Types d'entrée : ✅ fait · 📌 décision · … » de references/format-journal.md."""
    jl = []
    m = re.search(r"^Types d.entr[ée]e\s*:\s*(.+?)\.?\s*$", read_text(p("references", "format-journal.md")), re.M)
    if m:
        for part in m.group(1).split("·"):
            mm = re.match(r"^\s*(\S+)\s+(.+?)\s*$", part)
            if mm:
                jl.append([mm.group(1), mm.group(2)])
    return {"items": jl or JL_DEFAULT, "source": "references/format-journal.md" if jl else "défaut"}


def _fr_day(txt: str):
    """« 8 oct. 2026 », « mer. 8 octobre 2026 », « 2026-10-08 » → 'YYYY-MM-DD' (ou None)."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", txt)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})(?:er)?\s+([A-Za-zéûÉÛ]+)\.?\s+(\d{4})", txt)
    if m and m.group(2).lower() in FR_MONTHS:
        return f"{int(m.group(3)):04d}-{FR_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def journal_events(bot: str, path: str):
    txt = read_text(path)
    if not re.search(r"^##\s+4\b", txt, re.M):
        return journal_events_legacy(bot, path, txt)
    types = [(e, e.replace("\ufe0f", ""), lbl) for e, lbl in journal_legend_read()["items"]]
    evs, day, in_journal = [], None, False
    for ln in txt.splitlines():
        if re.match(r"^##\s", ln):                       # « ## 4. Journal » ouvre la section ; tout autre « ## » la ferme
            in_journal = bool(re.match(r"^##\s+4\b", ln)); day = None
            continue
        if not in_journal:
            continue
        m = re.match(r"^###\s+(.*)$", ln)
        if m:
            day = _fr_day(m.group(1))
            continue
        m = re.match(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*[·—:\-]?\s*(.*)$", ln)
        if not m or not day:
            continue
        when, rest = m.group(1).strip().lstrip("~").strip(), m.group(2).strip()
        mt = re.fullmatch(r"(\d{1,2})\s*[h:]\s*(\d{2})?", when)
        label = None
        if mt:
            hh, mm = int(mt.group(1)), int(mt.group(2) or 0)
        else:
            hh, mm = APPROX_TIMES.get(when.lower(), (12, 0)); label = when
        emoji, kind = None, None
        for e, en, lbl in types:                          # emoji en tête = type d'entrée (légende de format-journal.md)
            if rest.replace("\ufe0f", "").startswith(en):
                emoji, kind = e, lbl
                rest = re.sub("^" + re.escape(en) + "\ufe0f?", "", rest.replace(e, en, 1)).strip()
                break
        try:
            dt = datetime.strptime(f"{day} {hh:02d}:{mm:02d}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ).astimezone(UTC)
        except Exception:
            continue
        ev = {"script": bot, "started": iso(dt), "duration": None, "signals": None, "trades": None,
              "status": "JOURNAL", "notes": strip_md(rest)[:220], "source": os.path.relpath(path, BOT)}
        if kind:
            ev["kind"], ev["emoji"] = kind, emoji
        if label:
            ev["time_label"] = label
        evs.append(ev)
    return evs


def journal_events_legacy(bot: str, path: str, txt: str):
    """Ancien format (avant le 8 oct., 23h15) : « ## 2026-10-08 » + « - **13h05** — texte » ou « 2026-10-08 13:05 — texte »."""
    evs, day = [], None
    for ln in txt.splitlines():
        m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", ln)
        if m:
            day = m.group(1)
            continue
        m = DATED_LINE.match(ln)
        if m:
            d, hh, mm, note = m.group(1), m.group(2), m.group(3), m.group(4)
        else:
            d = day
            note = None
            for pat in TIME_PATTERNS:
                mt = pat.match(ln)
                if mt:
                    hh, mm, note = mt.group(1), mt.group(2), mt.group(3)
                    break
            if note is None or not d:
                continue
        try:
            dt = datetime.strptime(f"{d} {int(hh):02d}:{mm}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ).astimezone(UTC)
        except Exception:
            continue
        evs.append({"script": bot, "started": iso(dt), "duration": None, "signals": None, "trades": None,
                    "status": "JOURNAL", "notes": strip_md(note)[:220], "source": os.path.relpath(path, BOT)})
    return evs


# ----------------------------------------------------------------- trades
def pos_side(x):
    """Sens d'une position ouverte (source unique pour tout le site) : 'vente' = idée à la baisse (pièces vendues,
    rachat prévu), 'achat' = idée à la hausse. Lit side / idea_type / kind écrits par le gardien (guardian/state.json)."""
    sd = str(x.get("side") or "").lower()
    if sd in ("short", "sell", "vente"):
        return "vente"
    if sd in ("long", "buy", "achat"):
        return "achat"
    return "vente" if "baisse" in (str(x.get("idea_type")) + str(x.get("kind"))).lower() else "achat"


def _idea_of(r):
    """Type d'idée écrit par l'équipe dans la ligne (idea_type / kind / strategy) : 'hausse', 'baisse' ou None."""
    for k in ("idea_type", "kind", "strategy", "idea"):
        v = str(r.get(k) or "").lower()
        if "baisse" in v or "sell_first" in v or "sell_rebuy" in v:
            return "baisse"
        if "hausse" in v or v in ("long", "buy_first"):
            return "hausse"
    return None


def build_trades(guardian_state, real_trades=None, skip_ids=()):
    skip_ids = set(skip_ids or ())
    rows = [r for r in read_jsonl(p("state", "trades_log.jsonl")) if not (r.get("id") and r.get("id") in skip_ids)]
    tj = parse_trading_journal()
    trades, by_id = [], {}

    def mode_of(r, default="sim"):
        m = str(r.get("mode", "")).lower()
        return "reel" if m == "live" else ("sim" if m in ("paper", "sim", "simulation") else default)

    for r in rows:
        side = str(r.get("side", "")).lower()
        if mode_of(r) == "reel":  # le réel vient de l'historique Revolut X (source mécanique)
            continue
        if not r.get("pair") and r.get("market_id"):  # auto-test Polymarket du 6 oct.
            trades.append({
                "id": r.get("id"), "mode": "sim", "kind": "autotest", "pair": f"{r.get('market_id')} (test Polymarket)",
                "buy_time": iso(parse_ts(r.get("ts"))), "buy_price": fnum(r.get("price")), "amount_eur": fnum(r.get("size_eur")),
                "qty": fnum(r.get("contracts")), "sell_time": None, "sell_price": None, "pnl_eur": None, "pnl_pct": None,
                "status": "Auto-test (pas compté)", "reason": "Essai technique du programme, pas un vrai trade.", "lesson": None,
            })
            continue
        if side == "buy":
            t = {"id": r.get("id"), "mode": mode_of(r), "kind": "trade", "pair": r.get("pair"),
                 "buy_time": iso(parse_ts(r.get("ts"))), "buy_price": fnum(r.get("price")),
                 "amount_eur": fnum(r.get("amount_eur")), "qty": fnum(r.get("qty")),
                 "stop_pct": fnum(r.get("stop_pct")), "sell_time": None, "sell_price": None, "sell_amount": None,
                 "pnl_eur": None, "pnl_pct": None, "status": "En cours", "reason": None, "lesson": None,
                 "venue": r.get("venue"), "idea_type": _idea_of(r) or "hausse", "decision_link": r.get("decision_id")}
            trades.append(t)
            by_id[t["id"]] = t
        elif side == "sell":
            t = by_id.get(r.get("linked_position_id"))
            if t is None:
                t = {"id": r.get("id"), "mode": mode_of(r), "kind": "trade", "pair": r.get("pair"),
                     "buy_time": None, "buy_price": fnum(r.get("entry_price")), "amount_eur": None, "qty": fnum(r.get("qty"))}
                trades.append(t)
            t.update({"sell_time": iso(parse_ts(r.get("ts"))), "sell_price": fnum(r.get("price")),
                      "sell_amount": fnum(r.get("amount_eur")), "pnl_eur": fnum(r.get("realized_pnl_eur")),
                      "pnl_pct": fnum(r.get("realized_pnl_pct")), "close_reason": r.get("close_reason"),
                      "stop_price": fnum(r.get("stop_price_eur"))})
            cr = str(r.get("close_reason") or "")
            t["status"] = "Vendu (stop)" if "stop" in cr else "Vendu"
    # positions guardian absentes du log
    known = {t["id"] for t in trades}
    for pos in (guardian_state or {}).get("positions", []):
        # positions « à la baisse » (side=short, idea_type=baisse) : déjà comptées comme cycles à la baisse
        if pos.get("id") in skip_ids or str(pos.get("side")).lower() == "short" or "baisse" in (str(pos.get("idea_type")) + str(pos.get("kind"))).lower():
            continue
        if pos.get("id") in known:
            t = next(x for x in trades if x["id"] == pos.get("id"))
            if t["status"] == "En cours":
                t["pnl_eur"] = fnum(pos.get("unrealized_pnl_eur"))
                t["pnl_pct"] = fnum(pos.get("unrealized_pnl_pct"))
                t["stop_price"] = fnum(pos.get("stop_price_eur"))
            continue
        st = pos.get("status")
        trades.append({"id": pos.get("id"), "mode": "sim", "kind": "trade",
                       "pair": pos.get("pair"), "buy_time": iso(parse_ts(pos.get("opened_at"))),
                       "buy_price": fnum(pos.get("avg_price")), "amount_eur": fnum(pos.get("cost_eur")),
                       "qty": fnum(pos.get("qty")), "sell_time": iso(parse_ts(pos.get("closed_at"))),
                       "sell_price": fnum(pos.get("close_price_eur")),
                       "pnl_eur": fnum(pos.get("realized_pnl_eur") if st == "closed" else pos.get("unrealized_pnl_eur")),
                       "pnl_pct": fnum(pos.get("realized_pnl_pct") if st == "closed" else pos.get("unrealized_pnl_pct")),
                       "status": "Vendu" if st == "closed" else "En cours", "reason": None, "lesson": None})
    trades.extend(real_trades or [])
    # raisons / leçons depuis le journal des trades (même paire, même type essai/live, date de vente)
    def jmode(e):
        k = (e.get("kind") or "").lower()
        return "reel" if ("live" in k or "réel" in k or "reel" in k) else "sim"
    for t in trades:
        if t["kind"] != "trade" or not t.get("sell_time"):
            continue
        d_local = parse_ts(t["sell_time"]).astimezone(TZ).strftime("%Y-%m-%d")
        cand = [e for e in tj if e["pair"] == t["pair"] and jmode(e) == t["mode"]]
        match = next((e for e in cand if e["date"] == d_local), None) or (cand[0] if len(cand) == 1 and t["mode"] == "sim" else None)
        if match:
            f = match["fields"]
            t["reason"] = f.get("Pourquoi vente")
            t["lesson"] = f.get("Leçon (1 ligne)") or next((v for k, v in f.items() if k.startswith("Leçon")), None)
            t["result_text"] = f.get("Résultat")
            t["journal_kind"] = match["kind"]
            t["decision_link"] = match["link"]
    trades.sort(key=lambda t: t.get("sell_time") or t.get("buy_time") or t.get("time") or "", reverse=True)
    return trades


def fr_num(t):
    return t.replace(".", ",")


def load_team_perf():
    """Chiffres globaux des trades = state/performance.json (scripts/performance.py, étape Compound), TELS QUELS."""
    path = p("state", "performance.json")
    d = read_json(path, None)
    if not isinstance(d, dict):
        return {"present": False, "source": "state/performance.json", "owner": "PM-Compound"}
    return {"present": True, "source": "state/performance.json (scripts/performance.py)", "owner": "PM-Compound",
            "updated_at": iso(parse_ts(d.get("updated_at"))), "raw": d}


# ----------------------------------------------------------------- real balances

# ----------------------------------------------------------------- real money (Revolut X history, read-only)
def load_live_log():
    """state/live_orders.jsonl (écrit par guardian/scripts/live_place.py) → ordres envoyés par les bots."""
    out = []
    for r in read_jsonl(p("state", "live_orders.jsonl")):
        if r.get("dry_run"):
            continue
        cmd = r.get("cmd") or []
        coid = cmd[cmd.index("--client-order-id") + 1] if "--client-order-id" in cmd and cmd.index("--client-order-id") + 1 < len(cmd) else None
        oid, status = None, None
        try:
            so = json.loads(r.get("stdout") or "null")
            data = so.get("data", so) if isinstance(so, dict) else so
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict):
                oid = data.get("id") or data.get("venue_order_id") or data.get("order_id")
                coid = data.get("client_order_id") or coid
                status = data.get("status") or data.get("state")
        except Exception:
            pass
        o = r.get("order") or {}
        out.append({"at": iso(parse_ts(r.get("at"))), "ok": bool(r.get("ok")), "client_order_id": coid, "order_id": oid,
                    "status": status, "pair": str(o.get("pair") or "").upper() or None, "side": str(o.get("side") or "").lower() or None,
                    "price": fnum(o.get("price")), "amount_eur": fnum(o.get("amount_eur")),
                    "decision_id": o.get("decision_id") or o.get("decision") or o.get("id"),
                    "reason": o.get("reason") or o.get("note") or o.get("why"), "error": (r.get("stderr") or "")[-200:] if not r.get("ok") else None})
    return out


def _revx_cached(name, args, timeout=40):
    try:
        d = revx_read(args, timeout=timeout)
        cache_put(name, {"at": iso(NOW), "data": d})
        return d, False, None
    except Exception as e:
        c = read_json(os.path.join(CACHE, name))
        return (c or {}).get("data"), True, str(e)[:200]


def load_real_history(prices, balances):
    """Trades réels mécaniques depuis le début du projet : revx order history / order open / transaction list (lecture seule)."""
    start_arg = PROJECT_START.astimezone(TZ).strftime("%Y-%m-%d")
    start_ms = PROJECT_START.timestamp() * 1000
    errors = []
    oh, oh_stale, e1 = _revx_cached("revx_order_history.json", ["order", "history", "--start-date", start_arg, "--limit", "1000", "--json"])
    oo, oo_stale, e2 = _revx_cached("revx_order_open.json", ["order", "open", "--json"])
    tx, tx_stale, e3 = _revx_cached("revx_transactions.json", ["transaction", "list", "--start-date", start_arg, "--limit", "1000", "--json"])
    for lbl, e in (("historique des ordres", e1), ("ordres ouverts", e2), ("transactions", e3)):
        if e:
            errors.append(f"{lbl} : {e}")
    orders = [o for o in ((oh or {}).get("data") or []) if fnum(o.get("created_date"), 0) >= start_ms]
    open_orders = (oo or {}).get("data") or []
    txs = [t for t in (((tx or {}).get("data") if isinstance(tx, dict) else tx) or []) if fnum(t.get("created_date"), 0) >= start_ms]
    live_log = load_live_log()
    by_coid = {x["client_order_id"]: x for x in live_log if x.get("client_order_id")}
    by_oid = {x["order_id"]: x for x in live_log if x.get("order_id")}

    fills = []
    for o in orders:
        q = fnum(o.get("filled_quantity"), 0)
        if not q or q <= 0:
            continue
        base, _, quote = str(o.get("symbol", "")).replace("-", "/").partition("/")
        if quote != "EUR":
            errors.append(f"ordre {o.get('id')} en {quote} ignoré (pas en EUR)")
            continue
        bot = by_oid.get(o.get("id")) or by_coid.get(o.get("client_order_id"))
        fills.append({"order_id": o.get("id"), "client_order_id": o.get("client_order_id"), "base": base, "side": o.get("side"),
                      "qty": q, "eur": fnum(o.get("filled_amount"), 0), "time": parse_ts(o.get("updated_date") or o.get("created_date")),
                      "origin": "bot" if bot else "manuel", "bot": bot, "status": o.get("status"),
                      "post_only": "post_only" in (o.get("execution_instructions") or []), "source": "revx order history",
                      "avg_price": fnum(o.get("average_fill_price") or o.get("avg_fill_price") or o.get("executed_price"))})
    # achats / ventes faits dans l'app Revolut (un côté hors Revolut X) = vrais trades aussi, mais pas des bots
    have_orders = oh is not None
    for t in txs:
        if t.get("type") not in ("buy", "sell") or t.get("status") not in (None, "completed"):
            continue
        src, dst = t.get("source") or {}, t.get("destination") or {}
        both_x = (src.get("account") or {}).get("type") == "revolut_x" and (dst.get("account") or {}).get("type") == "revolut_x"
        if both_x and have_orders:
            continue  # déjà dans l'historique des ordres
        if t["type"] == "buy":
            base, q, eur, qc = dst.get("currency"), fnum(dst.get("amount"), 0), fnum(src.get("amount"), 0), src.get("currency")
        else:
            base, q, eur, qc = src.get("currency"), fnum(src.get("amount"), 0), fnum(dst.get("amount"), 0), dst.get("currency")
        if qc != "EUR" or not q:
            continue
        fills.append({"order_id": t.get("id"), "base": base, "side": t["type"], "qty": q, "eur": eur, "time": parse_ts(t.get("created_date")),
                      "origin": "manuel" if both_x else "app Revolut", "bot": None, "source": "revx transaction list"})
    fills.sort(key=lambda f: f["time"] or NOW)

    # Aucun appariement achat/vente ni résultat calculé ici : une ligne par ordre rempli, champs de Revolut X tels quels.
    trades = []
    for f in fills:
        trades.append({"id": f["order_id"], "mode": "reel", "kind": "fill", "pair": f"{f['base']}-EUR", "venue": "revolut_x",
                       "side": "achat" if f["side"] == "buy" else "vente", "time": iso(f["time"]), "qty": f["qty"], "eur": f["eur"],
                       "price": f.get("avg_price"), "origin": "bot" if f.get("bot") else f["origin"],
                       "decision_link": (f.get("bot") or {}).get("decision_id"), "bot_reason": (f.get("bot") or {}).get("reason"),
                       "pnl_eur": None, "status": "Rempli", "source": f["source"]})
    bot_orders = []
    for x in live_log:   # ordres des bots (state/live_orders.jsonl, écrit par live_place.py — PM-Risk), tels quels
        bot_orders.append({"at": x.get("at"), "pair": x.get("pair"), "side": x.get("side"), "price": x.get("price"), "amount_eur": x.get("amount_eur"),
                           "ok": x.get("ok"), "decision_id": x.get("decision_id"), "reason": x.get("reason") or x.get("error"),
                           "order_id": x.get("order_id"), "realized_pnl_eur": x.get("realized_pnl_eur")})
    oo_rows = []
    for o in open_orders:
        oo_rows.append({"pair": str(o.get("symbol", "")).replace("/", "-"), "side": o.get("side"), "price": fnum(o.get("price")),
                        "qty": fnum(o.get("quantity")), "created": iso(parse_ts(o.get("created_date"))), "status": o.get("status"),
                        "bot": bool(by_oid.get(o.get("id")) or by_coid.get(o.get("client_order_id")))})
    return {"trades": trades, "fills": trades, "bot_orders": bot_orders, "open_orders": oo_rows, "orders_since_start": len(orders),
            "live_log_count": len(live_log), "errors": errors, "stale": bool(oh_stale or tx_stale), "project_start": iso(PROJECT_START),
            "sources": ["revx order history --start-date " + start_arg, "revx order open", "revx transaction list --start-date " + start_arg,
                        "state/live_orders.jsonl (ordres des bots, live_place.py)"]}


def metamask_trades_status():
    logs = sorted(glob.glob(p("state", "metamask*.jsonl")) + glob.glob(p("knowledge", "metamask*.md")))
    if logs:
        n = sum(len(read_jsonl(f)) for f in logs if f.endswith(".jsonl"))
        return {"tracked": True, "files": [os.path.relpath(f, BOT) for f in logs], "rows": n}
    return {"tracked": False, "text": "Suivi des trades MetaMask : pas encore (aucun journal d'échanges de l'équipe ; references/metamask.md = règles seulement, trading MetaMask en pause)."}


def load_real(prices):
    if not CFG["SHOW_REAL"]:
        return {"hidden": True}
    out = {"hidden": False, "revolut": None, "metamask": None, "errors": []}
    try:
        bal = revx_read(["account", "balances", "--json"])
        # Quantités brutes de Revolut X (lecture seule) ; aucune valeur en euros calculée ici (valeurs : live_equity.json).
        assets = [{"currency": b.get("currency"), "qty": fnum(b.get("total"), 0.0), "available": fnum(b.get("available")),
                   "staked": fnum(b.get("staked")), "reserved": fnum(b.get("reserved"))} for b in bal]
        out["revolut"] = {"assets": assets, "fetched_at": iso(NOW), "stale": False,
                          "source": "revx account balances --json (lecture seule)"}
        cache_put("real_revolut.json", out["revolut"])
    except Exception as e:
        out["errors"].append(f"Revolut X: {e}")
        c, _ = cache_get("real_revolut.json", 1e9)
        if c:
            out["revolut"] = dict(c, stale=True)
    try:
        out["history"] = load_real_history(prices, (out.get("revolut") or {}).get("assets"))
    except Exception as e:
        warn(f"historique réel: {e}")
        out["history"] = None
        out["errors"].append(f"Historique Revolut X : {e}")
    addr = CFG["METAMASK_ADDRESS"]
    try:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [addr, "latest"]}).encode()
        r = json.loads(http_get(CFG["ARBITRUM_RPC"], data=body, headers={"Content-Type": "application/json"}))
        eth = int(r["result"], 16) / 1e18
        out["metamask"] = {"address": addr, "network": "Arbitrum One", "eth": eth, "fetched_at": iso(NOW), "stale": False,
                           "source": "eth_getBalance via arb1.arbitrum.io (public)"}
        cache_put("real_metamask.json", out["metamask"])
    except Exception as e:
        out["errors"].append(f"MetaMask: {e}")
        c, _ = cache_get("real_metamask.json", 1e9)
        if c:
            out["metamask"] = dict(c, stale=True)
    out["metamask_trades"] = metamask_trades_status()
    return out


# ----------------------------------------------------------------- cycles
def last_of(*ds):
    ds = [d for d in ds if d]
    return max(ds) if ds else None


def build_cycles(scan_hist, last_scan, last_predict, last_research, alerts, preds):
    def jm(name):
        return mtime(p("knowledge", "bot_journals", name))

    scan_last = last_of(parse_ts(last_scan.get("scanned_at")) if last_scan else None,
                        parse_ts(scan_hist[-1].get("scanned_at")) if scan_hist else None)
    scan_ok = bool(last_scan) and not last_scan.get("error")
    pred_last = last_of(parse_ts((last_predict or {}).get("predicted_at")),
                        max([parse_ts(x.get("ts")) for x in preds if parse_ts(x.get("ts"))], default=None))
    res_last = parse_ts((last_research or {}).get("briefed_at"))
    risk_last = parse_ts((alerts or {}).get("checked_at"))
    tick_files = sorted(glob.glob(p("state", "price_ticks", "*.jsonl")))
    last_tick = tail_jsonl(tick_files[-1], 3) if tick_files else []
    tick_at = parse_ts(last_tick[-1].get("ts")) if last_tick else None
    pid = read_text(p("state", "price_ticks", "collector.pid")).strip()
    collector_alive = bool(pid.isdigit() and os.path.exists(f"/proc/{pid}"))
    tick_age = (NOW - tick_at).total_seconds() if tick_at else None
    watch_alive = False
    try:
        r = subprocess.run(["pgrep", "-f", "watch_stops.py"], capture_output=True, text=True, timeout=5)
        watch_alive = r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        pass
    scan_slots = [f"{h:02d}:{m:02d}" for h in (15, 16) for m in (0, 15, 30, 45)] + ["17:00"]

    cycles = [
        {"key": "scan", "name": "PM-Scan", "title": "Relevé des prix",
         "schedule": "≈ toutes les 15 min, 15h–17h, lundi–vendredi (+ soirées Fed sur demande)", "approx": True,
         "slots": scan_slots, "weekdays": True,
         "desc": "Lit les prix publics de BTC, ETH et SOL en euros et repère ce qui bouge anormalement.",
         "bullets": ["Prix BTC-EUR, ETH-EUR, SOL-EUR (sources publiques)",
                     "Signale une forte variation (≥ 10 %) ou un écart achat/vente trop grand",
                     "Garde un historique de chaque relevé",
                     "Ne passe jamais d'ordre"],
         "last_run": iso(scan_last), "last_ok": scan_ok,
         "last_note": (last_scan or {}).get("error") and "Dernier relevé raté : pas de réponse des sources de prix",
         "journal_updated": iso(jm("pm-scan.md"))},
        {"key": "research", "name": "PM-Research", "title": "Point marché",
         "schedule": "14h42 point du jour · 17h42 bilan (lundi–vendredi)",
         "slots": ["14:42", "17:42"], "weekdays": True,
         "desc": "Résume l'ambiance du marché et les nouvelles importantes en français simple.",
         "bullets": ["Croise plusieurs sources (jamais une seule)", "Point du jour avant la séance, bilan après",
                     "Archive chaque point dans research_briefs/", "Transmet à Predict ce qu'il faut surveiller"],
         "last_run": iso(res_last), "last_ok": True, "last_note": (last_research or {}).get("cycle"),
         "journal_updated": iso(jm("pm-research.md"))},
        {"key": "predict", "name": "PM-Predict", "title": "Avis acheter / ne pas acheter",
         "schedule": "14h55 zones de prix du jour · avis sur demande (après Research)",
         "slots": ["14:55"], "weekdays": False,
         "desc": "Donne pour chaque crypto un avis écrit : acheter ou pas, avec une prévision mesurable.",
         "bullets": ["Zones de prix du jour (à la hausse / à la baisse) : Analyses › Prévisions",
                     "Prévision : sens + heure limite + seuil en %", "Gain espéré doit faire au moins 3× les coûts",
                     "Écrit chaque décision (même les « non ») dans le carnet", "Pas de décision sans prix à jour"],
         "last_run": iso(last_of(pred_last, mtime(p("state", "zones_reveil.json")))), "last_ok": True, "last_note": (last_predict or {}).get("cycle"),
         "journal_updated": iso(jm("pm-predict.md"))},
        {"key": "risk", "name": "PM-Risk", "title": "Contrôle des risques",
         "schedule": "14h24 essai à blanc + alertes (lundi–vendredi) · valide chaque ordre",
         "slots": ["14:24"], "weekdays": True,
         "desc": "Accepte ou refuse chaque achat, surveille les pertes et les stops.",
         "bullets": ["Max 1 achat réel par jour", "Stop de la journée si perte ≥ 15 %",
                     "Arrêt total si baisse ≥ 8 % depuis le sommet", "Surveille les stops toutes les ~15 s"],
         "last_run": iso(risk_last), "last_ok": not (alerts or {}).get("alerted"),
         "last_note": ("ALERTE : " + ", ".join(k for k, v in (alerts or {}).get("flags", {}).items() if v)) if (alerts or {}).get("alerted") else "Aucune alerte",
         "journal_updated": iso(jm("pm-risk.md")), "watch_stops_running": watch_alive},
        {"key": "compound", "name": "PM-Compound", "title": "Bilan et leçons",
         "schedule": "Après chaque vente · bilan du soir 20h32 (score + test du passé)",
         "slots": ["20:32"], "weekdays": False,
         "desc": "Écrit le bilan après chaque vente, note les prévisions et tire les leçons.",
         "bullets": ["Journal des trades (gain/perte + leçon)", "Score des prévisions : gagné / perdu / annulé",
                     "Test sur 1 an de prix passés avant tout nouveau type de trade",
                     "Met en pause un type de trade perdant"],
         "last_run": iso(last_of(jm("pm-compound.md"), mtime(p("knowledge", "predict_scorecard.md")))), "last_ok": True,
         "last_note": "Dernière mise à jour du journal / du score", "journal_updated": iso(jm("pm-compound.md"))},
        {"key": "orchestrator", "name": "PM-Orchestrator", "title": "Chef d'orchestre",
         "schedule": "Sur demande : coordonne les autres à chaque séance",
         "slots": [], "weekdays": True,
         "desc": "Fait passer le relais : Scan → Research → Predict → Risk → Compound.",
         "bullets": ["Organise les séances (ex. soirée Fed)", "Délègue, n'exécute pas le travail des autres",
                     "Note les décisions de Quentin (plafonds, règles)", "Vérifie que la boucle est bouclée"],
         "last_run": iso(jm("pm-orchestrator.md")), "last_ok": True, "last_note": "Dernière note du journal",
         "journal_updated": iso(jm("pm-orchestrator.md"))},
        {"key": "ticks", "name": "Collecteur de prix", "title": "Prix toutes les 30 s",
         "schedule": "Toutes les 30 secondes, en continu", "every_sec": 30, "slots": [], "weekdays": False,
         "desc": "Petit programme (sans IA) qui note le prix de BTC, ETH et SOL toutes les 30 s.",
         "bullets": ["Sert à vérifier les prévisions après coup", "Sources : Binance → Coinbase → Kraken"],
         # Statut = fraîcheur des ticks (< 2 min) + pid quand on peut le vérifier. Le navigateur recalcule avec
         # le prix le plus récent (prices.json / direct), car le build tourne toutes les 5 min.
         "last_run": iso(tick_at), "last_ok": collector_alive or (tick_age is not None and tick_age < 120),
         "pid_alive": collector_alive if pid.isdigit() else None, "tick_age_at_build_s": rnd(tick_age, 0),
         "last_note": None, "journal_updated": None},
    ]
    return cycles


def build_log(scan_hist, last_scan, preds, last_predict, alerts, buy_wake, trades_raw, research_archives):
    ev = []
    for s in scan_hist:
        pr = s.get("prices", {})
        note = " · ".join(f"{k.split('-')[0]} {v.get('price_eur'):,.2f} € ({v.get('change_24h_pct'):+.1f} %)".replace(",", " ")
                          for k, v in sorted(pr.items()) if isinstance(v, dict) and v.get("price_eur") is not None and v.get("change_24h_pct") is not None)
        ev.append({"script": "PM-Scan", "started": iso(parse_ts(s.get("scanned_at"))), "signals": s.get("anomalous_count"),
                   "trades": None, "status": "OK", "notes": note, "source": "state/scan_history.jsonl"})
    for f, label in ((last_scan, "state/last_scan.json"), (read_json(p("state", "last_scan_failed.json"), {}), "state/last_scan_failed.json")):
        if f and f.get("error"):
            ev.append({"script": "PM-Scan", "started": iso(parse_ts(f.get("scanned_at"))), "signals": 0, "trades": None,
                       "status": "ERREUR", "notes": "Relevé raté : aucune source de prix n'a répondu (réseau)", "source": label})
    groups = {}
    for r in preds:
        groups.setdefault(r.get("ts"), []).append(r)
    for ts, rs in groups.items():
        ids = [r.get("decision_id") for r in rs if r.get("decision_id")]
        buys = [r for r in rs if str(r.get("decision", "")).upper() not in ("NO_TRADE", "")]
        note = ", ".join(f"{r.get('pair','?').split('-')[0]} : {'pas acheter' if r.get('decision') == 'NO_TRADE' else r.get('decision')}" for r in rs)
        if ids:
            note = f"{ids[0]}–{ids[-1]} · " + note if len(ids) > 1 else f"{ids[0]} · " + note
        ev.append({"script": "PM-Predict", "started": iso(parse_ts(ts)), "signals": len(rs), "trades": len(buys),
                   "status": "OK", "notes": note, "source": "state/predictions_log.jsonl"})
    if last_predict and last_predict.get("predicted_at"):
        t = iso(parse_ts(last_predict["predicted_at"]))
        if not any(e["script"] == "PM-Predict" and e["started"] == t for e in ev):
            sig = last_predict.get("signals", [])
            ev.append({"script": "PM-Predict", "started": t, "signals": len(sig), "trades": len(last_predict.get("tradeable", [])),
                       "status": "OK", "notes": (last_predict.get("cycle") or "") + " — " +
                       ", ".join(f"{s.get('decision_id')} {s.get('pair','').split('-')[0]} : pas acheter" for s in sig if s.get("decision") == "NO_TRADE"),
                       "source": "state/last_predict.json"})
    for a in research_archives:
        ev.append(a)
    if alerts and alerts.get("checked_at"):
        ev.append({"script": "PM-Risk (alertes)", "started": iso(parse_ts(alerts["checked_at"])), "signals": len(alerts.get("alerts", [])),
                   "trades": None, "status": "ALERTE" if alerts.get("alerted") else "OK",
                   "notes": f"{alerts.get('open_positions', 0)} position(s) ouverte(s) · perte jour {100*fnum(alerts.get('daily_loss_pct'),0):.2f} % · baisse {100*fnum(alerts.get('drawdown_pct'),0):.2f} %",
                   "source": "state/alerts_last.json"})
    if buy_wake and buy_wake.get("checked_at"):
        ev.append({"script": "PM-Risk (achat en attente)", "started": iso(parse_ts(buy_wake["checked_at"])),
                   "signals": buy_wake.get("pending_count"), "trades": None, "status": "ALERTE" if buy_wake.get("alerted") else "OK",
                   "notes": buy_wake.get("message_fr") or "Aucun achat en attente de validation", "source": "state/buy_wake.json"})
    for r in trades_raw:
        if not r.get("pair"):
            continue
        side = "Achat" if r.get("side") == "buy" else "Vente"
        mode = "réel" if r.get("mode") == "live" else "simulé"
        extra = f" · {r.get('realized_pnl_eur'):+.2f} €" if r.get("realized_pnl_eur") is not None else ""
        ev.append({"script": "Exécution (" + mode + ")", "started": iso(parse_ts(r.get("ts"))), "signals": None, "trades": 1,
                   "status": "OK", "notes": f"{side} {r.get('pair')} à {fnum(r.get('price'),0):,.2f} € ({fnum(r.get('amount_eur'),0):.2f} €){extra}".replace(",", " ")
                   + (" — stop touché" if "stop" in str(r.get("close_reason", "")) else ""), "source": "state/trades_log.jsonl"})
    for r in read_jsonl(p("state", "auto_stop_events.jsonl")):
        ev.append({"script": "Surveillance stops", "started": iso(parse_ts(r.get("ts"))), "signals": 1, "trades": 0,
                   "status": "ALERTE", "notes": (r.get("message_fr") or "") + (f" (position {r.get('position_id')})" if r.get("position_id") else ""),
                   "source": "state/auto_stop_events.jsonl"})
    tick_files = sorted(glob.glob(p("state", "price_ticks", "*.jsonl")))
    if tick_files:
        lt = tail_jsonl(tick_files[-1], 3)
        if lt:
            ev.append({"script": "Collecteur de prix", "started": iso(parse_ts(lt[-1].get("ts"))), "signals": None, "trades": None,
                       "status": "OK", "notes": " · ".join(f"{t.get('pair','').split('-')[0]} {fnum(t.get('mid'),0):,.2f} €".replace(",", " ") for t in lt),
                       "source": "state/price_ticks/" + os.path.basename(tick_files[-1])})
    # Tous les journaux du dossier (pas archives/ : glob du premier niveau seulement) ; grok-bot.md → « Grok Bot »
    for f in sorted(glob.glob(p("knowledge", "bot_journals", "*.md"))):
        k = os.path.basename(f)[:-3]
        bot = {"grok-bot": "Grok Bot"}.get(k) or re.sub(r"^pm-(\w)", lambda m: "PM-" + m.group(1).upper(), k)
        ev.extend(journal_events(bot, f))
    # Fenêtre de 7 jours (comme les journaux des bots et le journal des routines) + plafond de sécurité de 1 000 lignes
    since = iso(NOW - timedelta(days=7))
    ev = [e for e in ev if e.get("started") and e["started"] >= since]
    ev.sort(key=lambda e: e["started"], reverse=True)
    return ev[:1000]


# ----------------------------------------------------------------- research
def build_research(last_research, last_predict, decisions):
    groups = {}
    for f in glob.glob(p("state", "research_briefs", "*")):
        name = os.path.basename(f)
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})", name)
        key = m.group(0) if m else name
        g = groups.setdefault(key, {"key": key, "files": [], "html": None, "data": None, "time": None})
        if m:
            g["time"] = iso(datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ).astimezone(UTC))
        g["files"].append(name)
        if f.endswith(".md"):
            g["html"] = md_to_html(read_text(f))
        elif f.endswith(".json"):
            g["data"] = read_json(f, {})
            if g["data"] and g["data"].get("briefed_at"):
                g["time"] = iso(parse_ts(g["data"]["briefed_at"]))
        g["time"] = g["time"] or iso(mtime(f))
    briefs = sorted(groups.values(), key=lambda g: g["time"] or "", reverse=True)
    journals = {}
    for f in sorted(glob.glob(p("knowledge", "bot_journals", "*.md"))):
        journals[os.path.basename(f)[:-3]] = {"updated": iso(mtime(f)), "html": md_to_html(read_text(f))}
    journal_legend = journal_legend_read()
    sc_txt = read_text(p("knowledge", "predict_scorecard.md"))
    totals = None
    m = re.search(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+)\|", sc_txt)
    if m:
        totals = {"gagne": int(m.group(1)), "perdu": int(m.group(2)), "annule": int(m.group(3)), "taux": m.group(4).strip()}
    # Fear & Greed (sans IA) — mis en cache
    fg, fresh = cache_get("sentiment.json", CFG["SENTIMENT_CACHE_MIN"])
    if not fresh:
        try:
            r = subprocess.run([os.path.join(VIBE, "backtest.sh"), "sentiment", "--history", "30", "--json"],
                               capture_output=True, text=True, timeout=90)
            d = json.loads(r.stdout.strip().splitlines()[-1])
            d["fetched_at"] = iso(NOW)
            cache_put("sentiment.json", d)
            fg = d
        except Exception as e:
            warn(f"Fear & Greed indisponible: {e}")
            if fg:
                fg = dict(fg, stale=True)
    return {
        "last_research": last_research, "last_predict": last_predict, "briefs": briefs[:12],
        "journals": journals,
        "journal_legend": journal_legend,
        "scorecard": {"totals": totals, "html": md_to_html(sc_txt), "updated": iso(mtime(p("knowledge", "predict_scorecard.md")))},
        "fear_greed": fg,
        "failure_log": {"html": md_to_html(read_text(p("knowledge", "failure_log.md"))), "updated": iso(mtime(p("knowledge", "failure_log.md")))},
    }


# ----------------------------------------------------------------- performance
def pair_charts(trades, prices, gstate, live_equity, sf_cycles=None):
    """Graphique par crypto : bougies 1 h sur 7 jours (Revolut X) + ticks 30 s du collecteur depuis la dernière bougie."""
    out = {}
    for pair in PAIRS:
        base = pair.split("-")[0]
        series, src = [], []
        try:
            d = revx_read(["market", "candles", pair, "--interval", "1h", "--since", "7d", "--json"], timeout=60)
            cs = [[int(fnum(c["start"])) + 3600_000, fnum(c["close"])] for c in d.get("data", []) if fnum(c.get("close"))]
            cache_put(f"candles_{pair}.json", cs)
            src.append("bougies 1 h Revolut X")
        except Exception as e:
            warn(f"bougies {pair}: {e}")
            cs = read_json(os.path.join(CACHE, f"candles_{pair}.json"), []) or []
            if cs:
                src.append("bougies 1 h Revolut X (cache)")
        cs.sort()
        series = [c for c in cs if c[0] <= NOW.timestamp() * 1000]
        last_ms = series[-1][0] if series else (NOW - timedelta(days=7)).timestamp() * 1000
        ticks = [t for t in PRICES.ticks_since(datetime.fromtimestamp(last_ms / 1000, UTC)) if t.get("pair") == pair and fnum(t.get("mid"))]
        lastk = 0
        for t in ticks:
            ms = int(t["_ts"].timestamp() * 1000)
            if ms - lastk >= 120_000 and ms > last_ms:
                series.append([ms, fnum(t["mid"])]); lastk = ms
        if ticks:
            src.append("ticks 30 s du collecteur (toutes les 2 min sur le graphique)")
            t = ticks[-1]
            series.append([int(t["_ts"].timestamp() * 1000), fnum(t["mid"])])
        x0 = series[0][0] if series else None
        markers, outside = [], 0
        for t in trades:
            if t.get("pair") != pair or t.get("kind") not in ("trade", "start_sale", "order"):
                continue
            for side, tk, pk in (("achat", "buy_time", "buy_price"), ("vente", "sell_time", "sell_price")):
                if t.get(tk) and t.get(pk):
                    ms = int(parse_ts(t[tk]).timestamp() * 1000)
                    if x0 and ms < x0:
                        outside += 1
                        continue
                    markers.append({"x": ms, "y": round(t[pk], 6), "side": side, "mode": t["mode"], "status": t.get("status"),
                                    "amount_eur": t.get("amount_eur") if side == "achat" else t.get("sell_amount"), "id": t.get("id")})
        for c in sf_cycles or []:
            if c.get("pair") != pair:
                continue
            for side, tk, pk, ak in (("vente", "sell_time", "sell_price", "sell_eur"), ("achat", "rebuy_time", "rebuy_price", "rebuy_eur")):
                if c.get(tk) and c.get(pk):
                    ms = int(parse_ts(c[tk]).timestamp() * 1000)
                    if x0 and ms < x0:
                        outside += 1
                        continue
                    markers.append({"x": ms, "y": round(c[pk], 6), "side": side, "mode": c["mode"], "status": c.get("status"),
                                    "amount_eur": c.get(ak), "id": c.get("id"), "sf": True})
        px = (prices.get(pair) or {}).get("mid")
        # Positions et avoirs : tels qu'écrits par leurs propriétaires (gardien = PM-Risk ; live_equity.json = outil sonnette).
        hold = {"sim": [{"side": pos_side(x), "qty": x.get("qty"), "entry_price": x.get("avg_price"), "mark_eur": x.get("mark_eur"),
                         "decision_id": x.get("decision_id")} for x in (gstate or {}).get("positions", [])
                        if x.get("pair") == pair and x.get("status") != "closed"]}
        le = live_equity if isinstance(live_equity, dict) and live_equity.get("present") else None
        if le:
            hold["reel"] = {"hors_bot": (le.get("hors_bot") or {}).get(base), "bot": (le.get("bot_positions") or {}).get(base)}
        first = series[0][1] if series else None
        out[pair] = {"series": series, "markers": markers, "markers_outside": outside, "sources": src, "holdings": hold,
                     "price": px, "change_7d_pct": rnd((px / first - 1) * 100, 2) if px and first else None,
                     "high_7d": max((v for _, v in series), default=None), "low_7d": min((v for _, v in series), default=None)}
    return out


def strategy_fr(s):
    return {"team_rebound": "Rebond après baisse", "team_breakout": "Cassure vers le haut", "sma_cross": "Croisement de moyennes",
            "ema_cross": "Croisement de moyennes (rapides)", "rsi_revert": "Achat après forte baisse (RSI)",
            "buy_hold": "Acheter et garder"}.get(s, s)


TEAM_VERDICT_KEYS = {"past": ("test_du_passe_reussi", "PM-Compound"), "live": ("autorise_en_reel", "PM-Risk")}


def team_gates(*docs):
    """« Test du passé réussi » / « Autorisé en réel » : seulement si un bot l'a ÉCRIT dans le fichier du test
    (clé verdict_equipe.test_du_passe_reussi par PM-Compound, verdict_equipe.autorise_en_reel par PM-Risk, ou les mêmes
    clés au premier niveau). Sinon ok=None → « non évalué par l'équipe ». Le site ne calcule aucun verdict."""
    out = {}
    for k, (key, owner) in TEAM_VERDICT_KEYS.items():
        val, by, at, why = None, None, None, None
        for d in docs:
            if not isinstance(d, dict):
                continue
            for src in (d.get("verdict_equipe") if isinstance(d.get("verdict_equipe"), dict) else {}, d):
                v = src.get(key)
                if isinstance(v, dict):
                    val, by, at, why = v.get("ok"), v.get("par") or v.get("by"), v.get("date") or v.get("at"), v.get("pourquoi") or v.get("why")
                elif isinstance(v, bool):
                    val = v
                if val is not None:
                    break
            if val is not None:
                break
        out[k] = {"ok": val if isinstance(val, bool) else None, "by": by, "at": at, "why": why, "owner": owner, "field": "verdict_equipe." + key}
    return out


def load_backtests():
    runs = []
    for d in sorted(glob.glob(os.path.join(VIBE, "home", "runs", "*")), reverse=True):
        mfile = os.path.join(d, "artifacts", "metrics.csv")
        if not os.path.exists(mfile):
            continue
        try:
            with open(mfile, encoding="utf-8") as f:
                row = next(csv.DictReader(f))
        except Exception:
            continue
        cfg = read_json(os.path.join(d, "config.json"), {})
        name = os.path.basename(d)
        m = re.match(r"(\d{8})_(\d{6})_\d+_([A-Z]+-[A-Z]+)_(\w+?)_(.+)$", name)
        when = None
        if m:
            try:
                when = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=TZ).astimezone(UTC)
            except Exception:
                pass
        pair = m.group(3) if m else ",".join(cfg.get("codes", []))
        tf = m.group(4) if m else cfg.get("interval")
        strat = m.group(5) if m else name
        fee = fnum(cfg.get("maker_rate"), None)
        tr = fnum(row.get("total_return"))
        bench = fnum(row.get("benchmark_return"))
        dd = fnum(row.get("max_drawdown"))
        n = int(fnum(row.get("trade_count"), 0) or 0)
        summ = None
        if tr is not None:
            summ = f"Sur la période, « {strategy_fr(strat)} » sur {pair} a fait {tr*100:+.1f} %".replace(".", ",")
            if bench is not None:
                summ += f" contre {bench*100:+.1f} % en gardant".replace(".", ",")
            summ += f", avec {n} trade(s)."
        gates = team_gates(cfg, row, read_json(os.path.join(d, "run_card.json"), {}))
        runs.append({
            "id": name, "time": iso(when or mtime(d)), "pair": pair, "timeframe": tf, "strategy": strat, "summary_fr": summ,
            "strategy_fr": strategy_fr(strat), "period": [cfg.get("evaluation_start_date") or cfg.get("start_date"), cfg.get("end_date")],
            "costs": ("0 frais (ordre qui attend)" if fee == 0 else (f"frais {fee*100:.2f} % + écart {fnum(cfg.get('slippage'),0)*100:.2f} %" if fee is not None else "?")),
            "stop_pct": rnd((fnum(cfg.get("spot_stop_loss")) or 0) * 100, 2) if cfg.get("spot_stop_loss") else None,
            "target_pct": rnd((fnum(cfg.get("spot_take_profit")) or 0) * 100, 2) if cfg.get("spot_take_profit") else None,
            "total_return_pct": rnd(tr * 100 if tr is not None else None, 2), "hold_return_pct": rnd(bench * 100 if bench is not None else None, 2),
            "max_drawdown_pct": rnd(dd * 100 if dd is not None else None, 2), "trades": n,
            "win_rate_pct": rnd(fnum(row.get("win_rate"), 0) * 100, 1), "profit_factor": rnd(fnum(row.get("profit_factor")), 2),
            "gates": gates,
        })
    checks = []
    for f in sorted(glob.glob(os.path.join(VIBE, "checks", "*.json"))):
        d = read_json(f, {})
        if not isinstance(d, dict) or "base_result" not in d:
            continue
        wf = (d.get("engine_validation", {}).get("walk_forward_windows", {}) or {}).get("consistency", {})
        pbo = None
        for k in ("pbo", "cscv", "overfitting"):
            v = d.get(k) or d.get("engine_validation", {}).get(k)
            if isinstance(v, dict):
                pbo = v.get("pbo") or v.get("probability_of_overfitting")
            elif isinstance(v, (int, float)):
                pbo = v
        checks.append({"file": os.path.basename(f), "time": iso(mtime(f)), "pair": d.get("pair"), "timeframe": d.get("timeframe"),
                       "strategy": d.get("strategy"), "strategy_fr": strategy_fr(d.get("strategy")), "result": d.get("base_result"),
                       "costs": d.get("costs"), "walk_forward": wf, "pbo": pbo, "period": d.get("period"),
                       "gates": team_gates(d)})
    return runs[:40], checks



# ----------------------------------------------------------------- « vendre d'abord » (idée D-018)
SF_TAG = re.compile(r"\bbaisse\b|sell[_ -]?first|sell[_ -]?rebuy|sell[_ -]?then[_ -]?buy|vendre[_ ]+d.abord|vendre[_ ]+haut|D-?018", re.I)
SF_REBUY = re.compile(r"rebuy|re-buy|rachat|rachet|buy[_ -]?back", re.I)
SF_TEXT_KEYS = ("kind", "strategy", "cycle", "cycle_type", "idea", "idee", "decision_id", "decision", "type", "source", "note",
                "reason", "tag", "tags", "leg", "role", "close_reason", "rebuy_reason", "intent", "label")
SF_LINK_KEYS = ("cycle_id", "sell_first_id", "linked_sell_id", "sell_id", "open_id", "parent_id", "linked_id",
                "linked_position_id", "linked_cycle_id", "link", "opens_cycle")
SF_REASON_FR = {"target": "rachat au prix visé", "objectif": "rachat au prix visé", "dip": "rachat au prix visé",
                "safety": "rachat de sécurité", "securite": "rachat de sécurité", "sécurité": "rachat de sécurité", "stop": "rachat de sécurité",
                "stop_hit": "rachat de sécurité", "time": "rachat à l'heure limite", "timeout": "rachat à l'heure limite", "22h": "rachat à l'heure limite",
                "end": "rachat en fin de période", "manual": "rachat à la main"}


def _sf_text(r):
    return " ".join(str(r.get(k) or "") if not isinstance(r.get(k), (list, dict)) else json.dumps(r.get(k), ensure_ascii=False)
                    for k in SF_TEXT_KEYS)


def _sf_reason_fr(v):
    s = str(v or "").strip().lower()
    for k, fr in SF_REASON_FR.items():
        if k in s:
            return fr
    return str(v) if v else None


def load_sell_first(rows, prices):
    """Cycles « vendre d'abord, racheter plus bas » écrits dans state/trades_log.jsonl.

    Ouverture = ligne side=sell marquée vendre-d'abord (kind/strategy/decision_id…=D-018/sell_first/sell_rebuy,
    role/leg=open) OU vente sans position simulée ouverte ni lien vers un achat (on vend des pièces qu'on avait déjà).
    Rachat = ligne side=buy liée à la vente (cycle_id / linked_* / parent_id… = id de la vente) ou marquée rachat
    (rebuy/rachat) sur la même paire. Robuste aux champs manquants ; rien n'est inventé.
    """
    cycles, used, open_by_pair, by_key = [], set(), defaultdict(list), {}
    open_buys = defaultdict(float)  # positions simulées ouvertes (achat classique) par paire, en quantité
    for i, r in enumerate(rows):
        side = str(r.get("side", "")).lower()
        pair = str(r.get("pair") or "").upper()
        if not pair:
            continue
        mode = "reel" if str(r.get("mode", "")).lower() == "live" else "sim"
        txt = _sf_text(r)
        tagged = bool(SF_TAG.search(txt))
        links = [str(r.get(k)) for k in SF_LINK_KEYS if r.get(k)]
        if side == "sell":
            role = str(r.get("role") or r.get("leg") or "").lower()
            linked_to_buy = bool(r.get("linked_position_id") or r.get("entry_price"))
            is_open = (tagged and not SF_REBUY.search(str(r.get("role") or r.get("leg") or ""))) or role in ("open", "sell_open", "opening", "ouverture") \
                or bool(r.get("opens_cycle")) or (not linked_to_buy and open_buys[pair] <= 1e-12)
            if (linked_to_buy and not tagged) or _idea_of(r) == "hausse":   # l'équipe dit « hausse » : simple vente de fin de trade
                is_open = False
            if not is_open:
                q = fnum(r.get("qty"), 0) or 0
                open_buys[pair] = max(0.0, open_buys[pair] - q)
                continue
            px = fnum(r.get("price"))
            qty = fnum(r.get("qty")) or fnum(r.get("coins")) or fnum(r.get("qty_sold"))
            eur_amt = fnum(r.get("amount_eur"))   # écrit par l'outil qui passe l'ordre ; rien n'est déduit
            tp = fnum(r.get("target_price")) or fnum(r.get("rebuy_target_price")) or fnum(r.get("rebuy_price_target")) or fnum(r.get("prix_rachat"))
            sp = fnum(r.get("safety_price")) or fnum(r.get("rebuy_stop_price")) or fnum(r.get("stop_price_eur")) or fnum(r.get("prix_rachat_force"))
            c = {"id": r.get("id") or f"sf-{i}", "mode": mode, "pair": pair, "coin": pair.split("-")[0],
                 "decision_id": r.get("decision_id") or (re.search(r"D-?\d{3}", txt).group(0) if re.search(r"D-?\d{3}", txt) else None),
                 "sell_time": iso(parse_ts(r.get("ts"))), "sell_price": px, "qty_sold": qty, "sell_eur": eur_amt,
                 "target_price": tp, "safety_price": sp, "deadline": r.get("deadline") or r.get("expire") or r.get("max_time"),
                 "sell_fee_eur": fnum(r.get("fee_eur")), "rebuy_time": None, "rebuy_price": None, "qty_bought": None,
                 "rebuy_eur": None, "rebuy_reason": None, "status": "En attente du rachat", "done": False,
                 "reason": r.get("reason") or r.get("note"), "source_lines": [r.get("id")],
                 "idea_type": _idea_of(r) or "baisse",
                 "inferred": not tagged and role not in ("open", "sell_open", "opening", "ouverture") and not r.get("opens_cycle")}
            cycles.append(c)
            open_by_pair[pair].append(c)
            for k in [c["id"]] + [str(r.get(k)) for k in ("cycle_id", "sell_first_id") if r.get(k)]:
                by_key[str(k)] = c
            used.add(r.get("id"))
        elif side == "buy":
            c = next((by_key[l] for l in links if l in by_key and not by_key[l]["done"]), None)
            if c is None and (SF_REBUY.search(txt) or tagged) and open_by_pair[pair]:
                c = next((x for x in open_by_pair[pair] if not x["done"] and x["mode"] == mode), None)
            if c is None:
                open_buys[pair] += fnum(r.get("qty"), 0) or 0
                continue
            px = fnum(r.get("price"))
            qb = fnum(r.get("qty")) or fnum(r.get("coins")) or fnum(r.get("qty_bought"))
            eb = fnum(r.get("amount_eur"))
            # Résultat = champs écrits par l'outil (realized_pnl_eur / coins_gained / rebuy_reason) ; jamais recalculé ici.
            c.update({"rebuy_time": iso(parse_ts(r.get("ts"))), "rebuy_price": px, "qty_bought": qb, "rebuy_eur": eb,
                      "rebuy_reason": _sf_reason_fr(r.get("rebuy_reason") or r.get("close_reason") or r.get("reason_code") or r.get("exit_reason")),
                      "rebuy_fee_eur": fnum(r.get("fee_eur")), "done": True,
                      "coin_gain": fnum(r.get("coins_gained")) if r.get("coins_gained") is not None else fnum(r.get("coin_gain")),
                      "coin_gain_pct": fnum(r.get("coins_gained_pct")) if r.get("coins_gained_pct") is not None else fnum(r.get("coin_gain_pct")),
                      "eur_gain": fnum(r.get("realized_pnl_eur")) if r.get("realized_pnl_eur") is not None else fnum(r.get("eur_gain")),
                      "eur_gain_pct": fnum(r.get("realized_pnl_pct"))})
            c["source_lines"].append(r.get("id"))
            used.add(r.get("id"))
            c["status"] = "Racheté" + (f" ({c['rebuy_reason']})" if c["rebuy_reason"] else "")
    cycles.sort(key=lambda c: c.get("sell_time") or "", reverse=True)
    return {"cycles": cycles, "used_ids": sorted(x for x in used if x),
            "source": "state/trades_log.jsonl (paper_fill / watch_stops ; lignes side=sell d'ouverture + rachat lié)"}


def decisions_sell_first(decisions):
    out = []
    for d in decisions:
        blob = " ".join([d.get("id") or "", d.get("title") or "", d.get("decision_text") or ""] + list(d.get("bullets") or []))
        if d.get("id") == "D-018" or re.search(r"D-018|vendre haut|vendre d.abord|racheter plus bas", blob, re.I):
            out.append(d)
    return out


# ----------------------------------------------------------------- pièces disponibles à vendre (réel)
def sellable_coins(real):
    """Pièces par compte : quantités brutes (Revolut X : total / disponible / staking / dans un ordre ; MetaMask : solde).
    Aucune valeur en euros ni total calculé ici."""
    if not isinstance(real, dict) or real.get("hidden"):
        return {"hidden": True}
    rv = real.get("revolut") or {}
    rows = []
    for a in rv.get("assets") or []:
        if a.get("currency") in ("EUR", "USD") or not (a.get("qty") or 0) > 0:
            continue
        rows.append({"where": "Revolut X", "currency": a["currency"], "total": a.get("qty"), "available": a.get("available"),
                     "blocked_staking": a.get("staked"), "reserved_orders": a.get("reserved")})
    mm = real.get("metamask") or {}
    if mm.get("eth") is not None:
        rows.append({"where": "MetaMask (Arbitrum)", "currency": "ETH", "total": mm["eth"], "available": None, "blocked_staking": None,
                     "reserved_orders": None, "note": "il faut garder un peu d'ETH pour les frais du réseau"})
    return {"hidden": False, "rows": rows, "fetched_at": rv.get("fetched_at") or mm.get("fetched_at"), "stale": bool(rv.get("stale")),
            "source": "revx account balances --json (quantités) + MetaMask eth_getBalance"}


# ----------------------------------------------------------------- capital réel du bot (live_equity.json)
def load_live_equity():
    path = p("state", "live_equity.json")
    d = read_json(path, None)
    if not isinstance(d, dict):
        return {"present": False, "source": "state/live_equity.json"}
    ts = parse_ts(d.get("ts"))
    age = (NOW - ts).total_seconds() if ts else None
    hb = {}
    for k, v in (d.get("hors_bot") or {}).items():
        if isinstance(v, dict):
            hb[k] = {"qty": fnum(v.get("qty")), "eur": fnum(v.get("eur"))}
    bp = {}
    for k, v in (d.get("bot_positions") or {}).items():
        if isinstance(v, dict):
            bp[k] = {"qty": fnum(v.get("qty")), "eur": fnum(v.get("eur") or v.get("value_eur"))}
        else:
            bp[k] = {"qty": fnum(v), "eur": None}
    track = d.get("_track") or {}
    return {"present": True, "ts": iso(ts), "age_s": rnd(age, 0),
            "stale": bool(d.get("stale")) or (age is not None and age > 900),
            "stale_flag": bool(d.get("stale")),
            "capital_reel": fnum(d.get("capital_reel")), "eur_available": fnum(d.get("eur_available")), "eur_reserved": fnum(d.get("eur_reserved")),
            "bot_positions_value": fnum(d.get("bot_positions_value")), "bot_positions": bp,
            "perte_jour_pct": fnum(d.get("perte_jour_pct")), "baisse_depuis_plus_haut_pct": fnum(d.get("baisse_depuis_plus_haut_pct")),
            "plus_haut": d.get("plus_haut") if isinstance(d.get("plus_haut"), (int, float)) else (d.get("plus_haut") or {}).get("valeur") if isinstance(d.get("plus_haut"), dict) else None,
            "ref_jour": d.get("ref_jour") if isinstance(d.get("ref_jour"), dict) else None,
            "hors_bot": hb,
            "hors_bot_depuis": iso(parse_ts(track.get("hors_bot_depuis"))),
            "ajustements": len(d.get("ajustements") or []), "notes_fr": d.get("notes_fr"),
            "source": "state/live_equity.json (écrit par /workspace/tools/sonnette/live_equity.py)"}


# ----------------------------------------------------------------- sonnette (état seulement, jamais secrets.env)
SONNETTE = CFG.get("SONNETTE_DIR", "/workspace/tools/sonnette")
_URL_RE = re.compile(r"https?://\S+|\b[\w.-]+\.(?:com|net|org|io|sh|dev|app)/\S*", re.I)


def _clean_txt(s, n=220):
    s = _URL_RE.sub("[lien masqué]", str(s or ""))
    return s[:n]


def _mode_fr(v):
    s = str(v or "").lower()
    if s in ("dry", "test", "blanc", "à blanc", "a blanc", "off", "none", ""):
        return "à blanc"
    if s in ("real", "réel", "reel", "live", "on"):
        return "branchée"
    return s


SONNETTE_BELLS = [("predict", "PM-Predict", "prix dans une zone"), ("risk", "PM-Risk", "stop proche / touché, signal de vie manquant"),
                  ("compound", "PM-Compound", "trade fermé")]


def load_sonnette(decisions=None):
    st = read_json(os.path.join(SONNETTE, "state", "status.json"), None)
    out = {"present": isinstance(st, dict), "source": "tools/sonnette/state/status.json + rings.jsonl (secrets.env jamais lu)"}
    zones_doc = read_json(p("state", "zones_reveil.json"), None)
    zones = []
    for z in ((zones_doc or {}).get("zones") or []) if isinstance(zones_doc, dict) else []:
        if not isinstance(z, dict):
            continue
        exp = parse_ts(z.get("expire"))
        active = z.get("actif", True) is not False and (exp is None or exp > NOW)
        zones.append({"id": z.get("id"), "pair": z.get("paire") or z.get("pair"), "side": z.get("sens") or z.get("side"),
                      "price": fnum(z.get("prix") or z.get("price")), "bot": z.get("bot"), "reason": _clean_txt(z.get("raison") or z.get("reason")),
                      "expire": iso(exp), "active": active, "enabled": z.get("actif", True) is not False})
    out["zones"] = zones
    out["zones_active"] = sum(1 for z in zones if z["active"])
    out["zones_file"] = "state/zones_reveil.json" + ("" if zones_doc is not None else " (absent)")
    out["zones_updated"] = iso(mtime(p("state", "zones_reveil.json"))) if zones_doc is not None else None  # Predict les refait chaque jour vers 14h55
    if isinstance(st, dict):
        hb = parse_ts(st.get("heartbeat"))
        age = (NOW - hb).total_seconds() if hb else None
        mode = st.get("mode") or {}
        today = st.get("today") or {}
        le = st.get("live_equity") or {}
        out.update({
            "heartbeat": iso(hb), "heartbeat_age_s": rnd(age, 0), "running": age is not None and age < 180,
            "predict_mode": _mode_fr(mode.get("predict")), "risk_mode": _mode_fr(mode.get("risk")),
            "compound_mode": _mode_fr(mode.get("compound")) if "compound" in mode else None,
            "predict_window_open": bool(st.get("predict_window_open")), "urgent_active": bool(st.get("urgent_active")),
            "prices_stale": bool(st.get("stale")), "last_tick_age_s": fnum(st.get("last_tick_age_s")),
            "zones_valid": st.get("zones_valid"), "zones_problems": len(st.get("zones_problems") or []),
            "zones_file_error": bool(st.get("zones_file_error")),
            "real_positions": len(st.get("real_positions") or []), "real_positions_without_stop": len(st.get("real_positions_without_stop") or []),
            "revx": (st.get("real_sources") or {}).get("revx"), "revx_open_orders": (st.get("real_sources") or {}).get("revx_open_orders"),
            "daily_loss_pct": (st.get("risk_metrics") or {}).get("daily_loss_pct"), "drawdown_pct": (st.get("risk_metrics") or {}).get("drawdown_pct"),
            "today": {"date": today.get("date"),
                      "predict": {"dry": (today.get("predict_delivered") or {}).get("dry", 0), "real": (today.get("predict_delivered") or {}).get("real", 0)},
                      "risk": {"dry": (today.get("risk_delivered") or {}).get("dry", 0), "real": (today.get("risk_delivered") or {}).get("real", 0)},
                      "compound": {"dry": (today.get("compound_delivered") or {}).get("dry", 0), "real": (today.get("compound_delivered") or {}).get("real", 0)}},
            "collector_running": bool((st.get("collector") or {}).get("running")),
            "capital_reel": fnum(le.get("capital_reel")),
        })
    rings = []
    for r in tail_jsonl(os.path.join(SONNETTE, "state", "rings.jsonl"), 40):
        pl = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        res = str(r.get("result") or "")
        rings.append({"at": iso(parse_ts(r.get("at") or pl.get("ts"))), "bot": r.get("bot") or pl.get("bot"),
                      "result": res, "result_fr": {"dry": "à blanc (pas envoyée)", "delivered": "reçue", "failed": "échec"}.get(res, res),
                      "http_status": r.get("http_status") if isinstance(r.get("http_status"), int) else None,
                      "kind": pl.get("kind"), "test": bool(pl.get("test") or pl.get("mode") == "test"),
                      "pair": pl.get("pair") or pl.get("paire"), "price": fnum(pl.get("price") or pl.get("prix")),
                      "zone": pl.get("zone_id"), "message": _clean_txt(pl.get("message_fr") or pl.get("message"))})
    rings.sort(key=lambda x: x["at"] or "", reverse=True)
    out["rings"] = rings[:12]
    out["rings_total"] = len(rings)
    # Compteurs = ceux que la sonnette écrit elle-même (status.json → today.*_delivered), tels quels. La sonnette n'écrit pas
    # encore « vrais réveils / essais » : affiché « non écrit par la sonnette » (aucun comptage fait par le site).
    td = (st or {}).get("today") or {} if isinstance(st, dict) else {}
    bells = []
    for key, name, what in SONNETTE_BELLS:
        dv = td.get(key + "_delivered") if isinstance(td.get(key + "_delivered"), dict) else None
        tot = ((st or {}).get("totals") or {}).get(key) if isinstance(st, dict) and isinstance((st or {}).get("totals"), dict) else None
        bells.append({"key": key, "bot": name, "what": what, "today_date": td.get("date"),
                      "today_real_mode": (dv or {}).get("real"), "today_dry": (dv or {}).get("dry"),
                      "real_events": (tot or {}).get("vrais") if isinstance(tot, dict) else None,
                      "tests": (tot or {}).get("essais") if isinstance(tot, dict) else None,
                      "last_real": (tot or {}).get("dernier_vrai") if isinstance(tot, dict) else None})
    out["bells"] = bells
    return out


# ----------------------------------------------------------------- tests du passé « vendre d'abord » + rapports

# ---------------------------------------------------------- passages des routines (journal commun)
ROUTINE_RUNS = os.environ.get("ROUTINE_RUNS_FILE") or p("state", "routine_runs.jsonl")  # écrit par tools/routine_log/log.py


def _bot_name(b):
    b = str(b or "").strip()
    m = re.match(r"^pm[-_ ]?([a-z]+)$", b, re.I)
    return "PM-" + m.group(1).capitalize() if m else b[:40]


def load_routine_runs(days=7, max_lines=300):
    """Dernières lignes du journal commun des routines (7 jours, 300 lignes max). Lecture seule.
    L'appariement démarre → fini/arrêt se fait dans le navigateur (statut « en cours » selon l'heure)."""
    out = {"source": "state/routine_runs.jsonl", "present": os.path.exists(ROUTINE_RUNS), "events": []}
    rows = deque(maxlen=max_lines)
    try:
        with open(ROUTINE_RUNS, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    rows.append(line)
    except Exception:
        return out
    since = NOW - timedelta(days=days)
    for line in rows:
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = parse_ts(r.get("ts"), naive_tz=TZ) if isinstance(r, dict) else None
        etape = str(r.get("etape") or "").strip().lower() if t else ""
        if not t or t < since or etape not in ("demarre", "fini", "arret"):
            continue
        out["events"].append({"ts": iso(t), "bot": _bot_name(r.get("bot")), "routine": _clean_txt(r.get("routine"), 80).strip(),
                              "etape": etape, "note": _clean_txt(r.get("note"), 160).strip()})
    out["events"].sort(key=lambda e: e["ts"])
    return out


def _rapport_clair(path):
    txt = read_text(path)
    m = re.search(r"##\s*En clair\s*\n+(.+?)(?:\n##|\Z)", txt, re.S)
    if m:
        return strip_md(" ".join(l.strip() for l in m.group(1).strip().splitlines() if l.strip()))[:400]
    return None


COST_FR = {"revolutx": "Revolut X", "uniswap": "Uniswap (Arbitrum)", "metamask-swap": "échange dans MetaMask"}


def load_sellrebuy_tests():
    runs, seen = [], set()
    dirs = sorted(glob.glob(os.path.join(VIBE, "home", "runs", "*")), reverse=True)
    for d in dirs:
        s = read_json(os.path.join(d, "summary.json"), None)
        if not isinstance(s, dict):
            continue
        base = s.get("base_full") if isinstance(s.get("base_full"), dict) else {}
        br = s.get("base_result") if isinstance(s.get("base_result"), dict) else {}

        def g(k):
            for src in (s, base, br):
                if src.get(k) is not None:
                    return src.get(k)
            return None
        if not (s.get("strategy") == "sell_rebuy" or g("coin_gain_vs_hold") is not None or g("coin_gain_vs_hold_pct") is not None):
            continue
        name = os.path.basename(d)
        vd = s.get("verdict") if isinstance(s.get("verdict"), dict) else None
        kind = "robust" if (vd or "robust" in name) else "base"
        prm = s.get("params") or {}
        ent = s.get("entries") or {}
        costs = s.get("costs") or {}
        key = json.dumps([kind, s.get("pair"), s.get("timeframe"), prm, ent, s.get("period"), g("coins_start"), costs], sort_keys=True)
        dup = key in seen
        seen.add(key)
        m = re.match(r"(\d{8})_(\d{6})_", name)
        when = None
        if m:
            try:
                when = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=TZ).astimezone(UTC)
            except Exception:
                pass
        tc = g("team_checks") or {}
        coin = s.get("coin") or (s.get("pair") or "?").split("-")[0]
        de = "d'" if coin[:1] in "AEIOUH" else "de "
        cg = fnum(g("coin_gain_vs_hold_pct"))
        n = int(fnum(g("cycles"), 0) or 0)
        dd = fnum(g("max_drawdown_coins_pct"))
        eg = fnum(g("eur_gain_vs_hold"))
        r3d = (tc.get("realized_avg_net_vs_3x_cost") or {}) if isinstance(tc, dict) else {}
        r3 = r3d.get("ok")
        gates = team_gates(s, base, br)
        sess = ent.get("session")
        cond = []
        if fnum(prm.get("rise")):
            cond.append(f"vente si +{fnum(prm.get('rise')):g} % en {fnum(prm.get('rise_hours'), 24):g} h")
        tm = fnum(prm.get("trend_ma"), 0) or 0
        cond.append(f"sous la moyenne {tm:g} h" if tm > 0 else "sans condition de moyenne")
        cond.append("rachat −" + (f"{fnum(prm.get('dip')):g}" if fnum(prm.get("dip")) is not None else "?") + " % / sécurité +" + (f"{fnum(prm.get('stop')):g}" if fnum(prm.get("stop")) is not None else "?") + " %")
        if fnum(prm.get("max_hours")):
            cond.append(f"max {fnum(prm.get('max_hours')):g} h")
        if fnum(prm.get("chunk")) and fnum(prm.get("chunk")) < 100:
            cond.append(f"vend {fnum(prm.get('chunk')):g} % des pièces")
        cond.append(f"ventes {sess} h en semaine" if sess else "ventes à toute heure")
        prof = costs.get("profile")
        tf_ = fnum(costs.get("market_order_fee"))
        lf_ = fnum(costs.get("limit_order_fee"))
        fx_ = fnum(costs.get("fixed_fee_eur_per_swap"))
        if lf_ is not None and tf_ is not None and abs(lf_ - tf_) > 1e-12:
            fee_txt = f"0 % pour la vente et le rachat visé (ordres qui attendent), {tf_*100:.2f} % pour le rachat de sécurité" if lf_ == 0 else \
                      f"{lf_*100:.2f} % (ordres qui attendent) / {tf_*100:.2f} % (rachat de sécurité)"
        elif tf_ is not None:
            fee_txt = f"{tf_*100:.3g} % à chaque vente et chaque rachat"
        else:
            fee_txt = ""
        cost_fr = COST_FR.get(prof, prof or "?") + (" · " + fee_txt.replace(".", ",") if fee_txt else "") + \
            (f" + {fx_:.2f} € de frais réseau par échange".replace(".", ",") if fx_ else "")
        rob = None
        if kind == "robust":
            wf = s.get("walk_forward_windows") or {}
            rt = s.get("monte_carlo_random_timing") or {}
            bs = s.get("bootstrap_avg_per_cycle") or {}
            rob = {"verdict": (vd or {}).get("verdict"), "verdict_fr": (vd or {}).get("verdict_fr"), "passed": (vd or {}).get("passed"), "of": (vd or {}).get("of"),
                   "pbo": (s.get("pbo_cscv") or {}).get("pbo"), "windows_gain": wf.get("windows_with_gain"), "windows_n": wf.get("n_windows"),
                   "random_p": rt.get("p_value"), "prob_positive": bs.get("prob_mean_positive"),
                   "grid_share_beating_hold": (s.get("grid") or {}).get("share_of_variants_beating_hold")}
        rb = g("rebuy_reasons") or {}
        runs.append({
            "id": name, "kind": kind, "time": iso(when or mtime(d)), "pair": s.get("pair"), "coin": coin, "timeframe": s.get("timeframe"),
            "idea": s.get("idea") or "D-018 vendre haut, racheter plus bas", "conditions": cond, "costs_fr": cost_fr, "costs_profile": prof,
            "period": [str(x)[:10] for x in (s.get("period") or [])],
            "coins_start": fnum(g("coins_start")), "coins_end": fnum(g("coins_end")),
            "coin_gain": fnum(g("coin_gain_vs_hold")), "coin_gain_pct": cg,
            "eur_end_strategy": fnum(g("eur_end_strategy")), "eur_end_hold": fnum(g("eur_end_hold")), "eur_gain_vs_hold": eg,
            "eur_return_hold_pct": fnum(g("eur_return_hold_pct")),
            "cycles": n, "wins": g("wins"), "losses": g("losses"), "win_rate_pct": fnum(g("win_rate_pct")),
            "rebuy_reasons": rb if isinstance(rb, dict) else {}, "max_drawdown_coins_pct": dd,
            "fees_eur": fnum(g("fees_paid_eur")), "avg_hours_out": fnum(g("avg_hours_out_of_market")),
            "gates": gates, "robust": rob,
            "summary_fr": (rob or {}).get("verdict_fr") or _rapport_clair(os.path.join(d, "rapport_fr.md")),
            "warnings": [_clean_txt(w, 160) for w in (s.get("warnings") or [])][:3],
            "duplicate": dup, "status": s.get("status"),
        })
    keep = [r for r in runs if not r["duplicate"]]
    return keep[:40], sum(1 for r in runs if r["duplicate"])


def load_vibe_reports():
    """Rapports JSON/MD supplémentaires (reports/, checks/*.json non reconnus) : une ligne en français, si présents."""
    out = []
    for f in sorted(glob.glob(os.path.join(VIBE, "reports", "**", "*.*"), recursive=True), reverse=True)[:30]:
        if not f.endswith((".json", ".md")):
            continue
        line = None
        if f.endswith(".md"):
            line = _rapport_clair(f)
            if not line:
                txt = [l.strip() for l in read_text(f).splitlines() if l.strip() and not l.startswith("#")]
                line = strip_md(txt[0])[:300] if txt else None
        else:
            d = read_json(f, {})
            if isinstance(d, dict):
                line = d.get("summary_fr") or d.get("resume_fr") or d.get("en_clair") or d.get("verdict_fr")
        out.append({"file": os.path.relpath(f, VIBE), "time": iso(mtime(f)), "line": _clean_txt(line, 400) if line else None})
    return out


# ----------------------------------------------------------------- news
FEEDS = [("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss"),
         ("CoinTelegraph", "https://cointelegraph.com/rss"),
         ("Decrypt", "https://decrypt.co/feed")]
TAGS = {"BTC": re.compile(r"\b(bitcoin|btc)\b", re.I), "ETH": re.compile(r"\b(ether|ethereum|eth)\b", re.I),
        "SOL": re.compile(r"\b(solana|sol)\b", re.I)}


def clean_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def fetch_news():
    prev = read_json(os.path.join(CACHE, "news_by_source.json"), {}) or {}
    cached_all, fresh = cache_get("news_full.json", CFG["NEWS_CACHE_MIN"] - 0.5)
    if fresh and cached_all:
        return cached_all
    by_src, status = {}, {}
    for src, url in FEEDS:
        try:
            raw = http_get(url, timeout=25)
            root = ET.fromstring(raw)
            items = []
            for it in root.iter("item"):
                title = clean_html(it.findtext("title"))
                link = (it.findtext("link") or "").strip()
                pub = it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")
                try:
                    dt = parsedate_to_datetime(pub).astimezone(UTC) if pub and "," in pub else parse_ts(pub)
                except Exception:
                    dt = parse_ts(pub)
                desc = clean_html(it.findtext("description"))
                if len(desc) > 260:
                    desc = desc[:257].rsplit(" ", 1)[0] + "…"
                text = f"{title} {desc}"
                tags = [k for k, rx in TAGS.items() if rx.search(text)]
                if title and link:
                    items.append({"title": title, "link": link, "source": src, "published": iso(dt), "summary": desc, "tags": tags})
            by_src[src] = items[:30]
            status[src] = {"ok": True, "count": len(items), "at": iso(NOW)}
        except Exception as e:
            warn(f"RSS {src}: {e}")
            by_src[src] = prev.get(src, [])
            status[src] = {"ok": False, "error": str(e)[:200], "kept": len(by_src[src])}
    cache_put("news_by_source.json", by_src)
    allitems = [x for v in by_src.values() for x in v]
    allitems.sort(key=lambda x: x.get("published") or "", reverse=True)
    out = {"generated_at": iso(NOW), "sources": status, "count": len(allitems),
           "note": "Titres RSS publics CoinDesk, CoinTelegraph, Decrypt (en anglais). Tags BTC/ETH/SOL détectés par mots-clés.",
           "items": allitems}
    cache_put("news_full.json", out)
    return out


# ----------------------------------------------------------------- main
def copy_static():
    """Copie src/ → site/. Les pages HTML reçoivent app.js?v=<empreinte> et style.css?v=<empreinte> : après chaque
    publication, le navigateur charge forcément la nouvelle version (pas de vieux fichier en cache)."""
    os.makedirs(SITE, exist_ok=True)
    ver = {}
    for n in ("app.js", "style.css"):
        try:
            ver[n] = hashlib.sha256(open(os.path.join(SRC, n), "rb").read()).hexdigest()[:10]
        except OSError:
            pass
    for f in glob.glob(os.path.join(SRC, "*")):
        if os.path.isfile(f):
            dst = os.path.join(SITE, os.path.basename(f))
            tmp = dst + ".tmp"
            if f.endswith(".html"):
                html = open(f, encoding="utf-8").read()
                for n, v in ver.items():
                    html = re.sub(r'(["\'])' + re.escape(n) + r'(\?v=[0-9a-f]+)?(["\'])', lambda m: m.group(1) + n + "?v=" + v + m.group(3), html)
                open(tmp, "w", encoding="utf-8").write(html)
            else:
                shutil.copyfile(f, tmp)
            os.replace(tmp, dst)


def main():
    t0 = time.time()
    os.makedirs(DATA_OUT, exist_ok=True)
    os.makedirs(SHARED_DATA, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    copy_static()

    mode = read_text(p("MODE"), "?").strip() or "?"
    cfg_bot = read_json(p("config.json"), {}) or {}
    gcfg = read_json(p("guardian", "config.json"), {}) or {}
    gstate = read_json(p("guardian", "state.json"), {}) or {}
    scan_hist = read_jsonl(p("state", "scan_history.jsonl"))
    last_scan = read_json(p("state", "last_scan.json"), {}) or {}
    last_predict = read_json(p("state", "last_predict.json"), {}) or {}
    last_research = read_json(p("state", "last_research.json"), {}) or {}
    alerts = read_json(p("state", "alerts_last.json"), {}) or {}
    buy_wake = read_json(p("state", "buy_wake.json"), {}) or {}
    live_day = read_json(p("state", "live_day.json"), {}) or {}
    preds = read_jsonl(p("state", "predictions_log.jsonl"))
    trades_raw = read_jsonl(p("state", "trades_log.jsonl"))

    prices, price_src = load_prices()
    real = load_real(prices)
    hist = (real or {}).get("history") or {}
    sell_first = load_sell_first(trades_raw, prices)
    trades = build_trades(gstate, hist.get("trades"), sell_first["used_ids"])
    decisions = parse_decision_log()
    sell_first["decisions"] = decisions_sell_first(decisions)[::-1]
    sellable = sellable_coins(real)
    live_equity = load_live_equity() if CFG["SHOW_REAL"] else {"hidden": True}
    sonnette = load_sonnette(decisions)
    sr_tests, sr_dups = load_sellrebuy_tests()
    vibe_reports = load_vibe_reports()
    routine_runs = load_routine_runs()

    # --- portefeuille simulé (guardian = venue Revolut X en simulation)
    risk = cfg_bot.get("risk", {})
    # Portefeuille simulé = guardian/state.json de PM-Risk, TEL QUEL (affichage seulement, aucun recalcul).
    gpos = gstate.get("positions", []) or []
    open_pos = [x for x in gpos if x.get("status") != "closed"]
    closed_pos = [x for x in gpos if x.get("status") == "closed"]
    open_list = [{"id": x.get("id"), "pair": x.get("pair"), "side": pos_side(x), "side_raw": x.get("side"), "idea_type": x.get("idea_type"),
                  "qty": x.get("qty"), "entry_price": x.get("avg_price"), "cost_eur": x.get("cost_eur"), "mark_eur": x.get("mark_eur"),
                  "unrealized_eur": x.get("unrealized_pnl_eur"), "target_price": x.get("target_price"), "stop_price": x.get("stop_price_eur"),
                  "fee_eur": x.get("fee_eur"), "decision_id": x.get("decision_id"), "opened_at": iso(parse_ts(x.get("opened_at")))} for x in open_pos]
    cap = fnum(gcfg.get("max_exposure_pct"), fnum(risk.get("max_total_exposure_pct")))
    today = NOW.astimezone(TZ).strftime("%Y-%m-%d")
    # Rapprochement : on additionne seulement des champs écrits par le gardien ; s'ils ne donnent pas equity_eur → écart affiché.
    def _sum(rows, k, sign=1):
        vals = [x.get(k) for x in rows]
        return {"value": round(sign * sum(v for v in vals if isinstance(v, (int, float))), 6),
                "missing": sum(1 for v in vals if not isinstance(v, (int, float)))}
    comps = [{"label": "départ", "field": "bankroll_eur", "value": gstate.get("bankroll_eur"), "missing": 0 if isinstance(gstate.get("bankroll_eur"), (int, float)) else 1},
             dict(_sum(closed_pos, "realized_pnl_eur"), label="trades fermés", field="positions[fermées].realized_pnl_eur"),
             dict(_sum(open_pos, "unrealized_pnl_eur"), label="positions ouvertes", field="positions[ouvertes].unrealized_pnl_eur"),
             dict(_sum(open_pos, "fee_eur", -1), label="frais d'ouverture", field="positions[ouvertes].fee_eur")]
    eq_g = gstate.get("equity_eur")
    explained = sum(c["value"] or 0 for c in comps)
    recon = {"components": comps, "sum_eur": round(explained, 6), "equity_eur": eq_g,
             "gap_eur": round(eq_g - explained, 6) if isinstance(eq_g, (int, float)) else None, "source": "guardian/state.json"}
    paper = {
        "label": "Simulation (argent fictif)", "source": "guardian/state.json (PM-Risk)", "owner": "PM-Risk",
        "updated_at": iso(parse_ts(gstate.get("updated_at"))),
        "invested_eur": gstate.get("bankroll_eur"), "balance_eur": eq_g, "cash_eur": gstate.get("cash_eur"),
        "peak_equity_eur": gstate.get("peak_equity_eur"), "drawdown_pct": gstate.get("drawdown_pct"),
        "daily_pnl_eur": gstate.get("daily_pnl_eur"), "daily_pnl_date": gstate.get("daily_pnl_date"),
        "halted": bool(gstate.get("halted")), "open_positions": len(open_list), "open_list": open_list,
        "cap_pct": cap, "reconciliation": recon,
    }
    if isinstance(real, dict) and not real.get("hidden"):
        # Réel : aucun résultat recalculé par le site (pas de P/L apparié, pas d'avoirs de départ déduits, pas de totaux).
        for k in ("open_orders", "fills", "bot_orders", "project_start", "sources", "stale", "errors", "orders_since_start", "live_log_count"):
            real["history_" + k if k in ("sources", "stale", "errors") else k] = hist.get(k)
        real.pop("history", None)
    rules = {
        "live_day": {"date": live_day.get("date"), "count": live_day.get("count")},   # state/live_day.json tel quel
        "max_daily_loss_pct": rnd(fnum(gcfg.get("max_daily_loss_pct"), fnum(risk.get("max_daily_loss_pct"))) * 100, 1),
        "max_drawdown_pct": rnd(fnum(gcfg.get("max_drawdown_pct"), fnum(risk.get("max_drawdown_pct"))) * 100, 1),
        "expectancy_multiple": (cfg_bot.get("official_rules") or {}).get("expectancy_min_multiple_of_cost", 3),
        "max_position_pct": rnd(fnum(gcfg.get("max_position_pct"), fnum(risk.get("max_position_pct"))) * 100, 1),
        "max_exposure_pct": rnd(cap * 100, 1) if cap is not None else None,
        "pairs": gcfg.get("pairs_whitelist") or (cfg_bot.get("official_rules") or {}).get("pairs_whitelist"),
        "post_only": gcfg.get("post_only"), "leverage": gcfg.get("leverage"), "market_orders": gcfg.get("market_orders"),
        "caps_source": "guardian/config.json",
        "stop_file": os.path.exists(p("STOP")), "halted_file": os.path.exists(p("HALTED")), "live_once_armed": os.path.exists(p("LIVE_ONCE")),
        "guardian_notes": gcfg.get("notes"),
    }

    # research archives -> log
    research_events = []
    for f in sorted(glob.glob(p("state", "research_briefs", "*_last_research.json"))) + [p("state", "last_research.json")]:
        d = read_json(f, {}) or {}
        if d.get("briefed_at"):
            research_events.append({"script": "PM-Research", "started": iso(parse_ts(d["briefed_at"])), "signals": None, "trades": None,
                                    "status": "OK", "notes": (d.get("cycle") or "Point marché") + (f" — prix : {d.get('prix')}" if isinstance(d.get("prix"), str) else ""),
                                    "source": os.path.relpath(f, BOT)})
    seen, uniq = set(), []
    for e in research_events:
        if e["started"] not in seen:
            seen.add(e["started"]); uniq.append(e)

    cycles = build_cycles(scan_hist, last_scan, last_predict, last_research, alerts, preds)
    log = build_log(scan_hist, last_scan, preds, last_predict, alerts, buy_wake, trades_raw, uniq)

    runs, checks = load_backtests()
    charts = pair_charts(trades, prices, gstate, live_equity, sell_first["cycles"])
    research = build_research(last_research, last_predict, decisions)
    news = fetch_news()

    status_line = "Pas de position ouverte — en veille" if not open_list else f"{len(open_list)} position(s) ouverte(s)"
    meta = {"generated_at": iso(NOW), "title": CFG["SITE_TITLE"], "mode": mode, "mode_fr": "Simulation" if mode == "paper" else ("Réel" if mode == "live" else mode),
            "show_real": bool(CFG["SHOW_REAL"]), "timezone": "Europe/Brussels", "warnings": WARNINGS,
            "prices": {k: v for k, v in prices.items() if k in ("BTC-EUR", "ETH-EUR", "SOL-EUR")}, "price_source": price_src}
    write_json(os.path.join(DATA_OUT, "summary.json"), {**meta, "paper": paper, "real": real, "rules": rules, "cycles": cycles,
                                                       "status_line": status_line, "log": log, "team_rules": load_team_rules(),
                                                       "sellable": sellable, "live_equity": live_equity, "sonnette": sonnette, "routine_runs": routine_runs,

                                                       "decision_counts": {"total": len(decisions), "refused": sum(1 for d in decisions if d["decision"] == "PAS ACHETER"),
                                                                           "buy": sum(1 for d in decisions if d["decision"] == "ACHETER")}})
    write_json(os.path.join(DATA_OUT, "trades.json"), {**meta, "trades": trades, "sell_first": {k: v for k, v in sell_first.items() if k != "decisions"},
                                                      "real": {k: (real or {}).get(k) for k in ("hidden", "open_orders", "bot_orders", "project_start", "history_sources", "history_stale", "history_errors", "metamask_trades", "live_log_count")}})
    write_json(os.path.join(DATA_OUT, "performance.json"), {**meta, "paper": paper, "team_perf": load_team_perf(),
                                                           "scorecard": research["scorecard"]["totals"], "backtests": runs, "checks": checks,
                                                           "pairs": charts, "live_equity": live_equity,
                                                           "real": {k: (real or {}).get(k) for k in ("hidden", "project_start", "history_stale", "fills", "bot_orders")},
                                                           "sellrebuy_tests": sr_tests, "sellrebuy_duplicates": sr_dups, "vibe_reports": vibe_reports,
                                                           "go_nogo": cfg_bot.get("go_nogo")})
    write_json(os.path.join(DATA_OUT, "research.json"), {**meta, **research, "decisions": decisions[::-1]})
    write_json(os.path.join(DATA_OUT, "news.json"), news)
    write_json(os.path.join(SHARED_DATA, "news.json"), news)
    write_json(os.path.join(DATA_OUT, "build.json"), {"generated_at": iso(NOW), "duration_s": round(time.time() - t0, 2), "warnings": WARNINGS})
    print(f"build OK en {time.time()-t0:.1f}s — {len(trades)} trades, {len(decisions)} décisions, {len(log)} lignes de log, "
          f"{news.get('count')} news, {len(runs)} tests, {len(sr_tests)} tests idée à la baisse, {len(sell_first['cycles'])} cycles à la baisse, {len(routine_runs['events'])} lignes de routines ; "
          f"avertissements: {len(WARNINGS)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
