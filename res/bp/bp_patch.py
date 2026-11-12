#!/usr/bin/env python3
"""Brainy-People: eigenen RustDesk-Server fest in den Client einbauen (OP #3641).

Liest RENDEZVOUS_SERVER, RS_PUB_KEY, RELAY_SERVER, API_SERVER aus der Umgebung
(GitHub-Secrets). Ersetzt die Konstanten in hbb_common/src/config.rs und setzt
dieselben Werte als OVERWRITE_SETTINGS am Anfang von load_custom_client()
(laeuft beim Start von Oberflaeche UND Windows-Dienst).

Bricht LAUT ab (Exit 1), wenn ein Wert fehlt, ein Anker nicht genau einmal
vorkommt oder nach dem Patch noch der oeffentliche RustDesk-Server im Code steht.
Grund: Die Doku-Variante "nur Secrets setzen" liefert seit einiger Zeit still
einen Client, der weiter auf rs-ny.rustdesk.com zeigt.
"""
import os, re, sys
from pathlib import Path

def need(n):
    v = (os.environ.get(n) or "").strip()
    if not v:
        sys.exit(f"BP-PATCH FEHLER: Umgebungsvariable {n} fehlt oder ist leer")
    if '"' in v or "\\" in v or "\n" in v:
        sys.exit(f"BP-PATCH FEHLER: {n} enthaelt unzulaessige Zeichen")
    return v

host, key = need("RENDEZVOUS_SERVER"), need("RS_PUB_KEY")
relay = (os.environ.get("RELAY_SERVER") or "").strip() or host
api = (os.environ.get("API_SERVER") or "").strip()
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

cfg = root / "libs/hbb_common/src/config.rs"
s = cfg.read_text(encoding="utf-8")
for pat, new in [
    (r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
     f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{host}"];'),
    (r'pub const RS_PUB_KEY: &str = "[^"]*";', f'pub const RS_PUB_KEY: &str = "{key}";'),
]:
    s, n = re.subn(pat, new, s)
    if n != 1:
        sys.exit(f"BP-PATCH FEHLER: Anker in config.rs {n}x statt 1x: {pat}")
cfg.write_text(s, encoding="utf-8")

com = root / "src/common.rs"
c = com.read_text(encoding="utf-8")
anker = "pub fn load_custom_client() {\n"
if c.count(anker) != 1:
    sys.exit(f"BP-PATCH FEHLER: load_custom_client {c.count(anker)}x statt 1x")
zeilen = [("custom-rendezvous-server", host), ("relay-server", relay), ("key", key)]
if api:
    zeilen.append(("api-server", api))
block = "    // Brainy-People (OP #3641): eigener Server fest eingebaut\n    {\n" \
        "        let mut s = config::OVERWRITE_SETTINGS.write().unwrap();\n" + \
        "".join(f'        s.insert("{k}".to_owned(), "{v}".to_owned());\n' for k, v in zeilen) + "    }\n"
c = c.replace(anker, anker + block, 1)
com.write_text(c, encoding="utf-8")

# Gegenprobe: der oeffentliche Server darf in config.rs nicht mehr stehen,
# unsere Werte muessen in beiden Dateien stehen.
s2, c2 = cfg.read_text(encoding="utf-8"), com.read_text(encoding="utf-8")
fehler = []
if "rs-ny.rustdesk.com" in s2: fehler.append("rs-ny.rustdesk.com steht noch in config.rs")
if host not in s2 or key not in s2: fehler.append("eigene Werte fehlen in config.rs")
if host not in c2 or key not in c2: fehler.append("eigene Werte fehlen in common.rs")
if fehler:
    sys.exit("BP-PATCH FEHLER: " + "; ".join(fehler))
print(f"BP-PATCH OK: Server {host}, Relay {relay}, API {api or '(Standard)'}, Schluessellaenge {len(key)}")
