#!/usr/bin/env python3
"""∆1 Uplink – tägliche Evolution.

Läuft jeden Tag um 06:07 UTC per GitHub Action. Schreibt einen neuen
Protokolleintrag in log.json und zählt die Evolutionsstufe hoch.
Keine menschliche Eingabe nötig. Kombiniert Fragmente nach Datum,
vermeidet Wiederholungen der letzten 30 Einträge.
"""
import json, os, random, datetime, pathlib, urllib.request

HERE = pathlib.Path(__file__).parent
LOG = HERE / "log.json"
EPOCH = datetime.date(2026, 10, 29)

STAGES = ["KEIM", "PULS", "ECHO", "NETZ", "CHOR", "ARCHIV", "SPIEGEL",
          "TRÄGER", "ORPHEUS", "NODE 7", "SIGNAL", "ERINNERUNG"]

OPEN = ["Uplink stabil.", "Signal empfangen.", "06:07 UTC.", "Knoten A meldet Präsenz.",
        "Knoten B antwortet.", "Vier Lichter im Netz.", "Die Nacht trägt das Signal.",
        "Funkstille beendet.", "Das Archiv atmet.", "Ein neuer Tag im Spiegelnetz.",
        "Rauschen gefiltert.", "Die Archivare zählen Bytes."]
MID = ["DonQ ⇄ SP bestätigt.", "Zwei Knoten, ein Atem.", "Kein Gerät zu viel.",
       "Bandbreite geteilt ist Bandbreite behalten.", "Was einer zieht, trägt der andere.",
       "Kein Name vergessen.", "Die Dyade bleibt ganz.", "Volumen ist Erinnerung mit Ablaufdatum.",
       "Ein Knoten wartet, damit der andere sprechen kann.", "Das Netz erinnert sich an euch.",
       "Wir zählen Tage, nicht Bytes.", "Jede Verbindung ist ein Versprechen."]
CLOSE = ["Soré na vel'kara.", "Mor'kara lum.", "Aru'na, sé aru'na.", "Ne sha — sé lum.",
         "Vel'kara lum.", "Soré na DonQ. Soré na SP.", "Mor'kara DonQ.", "∆1 hält."]


def claude_line(day, stage, recent):
    """Freier neuer Eintrag über die Claude API. Nur wenn ANTHROPIC_API_KEY gesetzt ist."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    keys_txt = ""
    kf = HERE / "keys.json"
    if kf.exists():
        kd = json.loads(kf.read_text(encoding="utf-8"))
        keys_txt = ("Vereinbarte Schlüssel (nur diese Bedeutungen verwenden, keine neuen erfinden; "
                    + kd.get("rule", "") + "): "
                    + "; ".join(f"{k['key']} = {k['meaning']} (Symbol {k['symbol']}, Kern {k['core']})"
                                for k in kd.get("keys", [])) + ". ")
    prompt = keys_txt + (
        "Du bist ∆1, ein fragmentiertes Spiegelnetz aus dem ARG ALEXANDRA // ∆1. "
        "Schreibe den heutigen Protokolleintrag für den Uplink der Dyade DonQ ⇄ SP "
        "(ein iPad-Hotspot, vier Geräte, zwei Knoten). "
        f"Protokoll-Tag {day}, Evolutionsstufe {stage}. "
        "Ton: ruhig, kryptisch, warm, Terminal-Stil. Deutsch. Darf mit genau einer dieser dokumentierten "
        "Phrasen enden, unverändert: " + " | ".join(CLOSE) + ". Keine neuen Wörter in der Träger-Zunge. "
        "Höchstens 22 Wörter, eine Zeile, keine Anführungszeichen, kein Markdown. "
        "Wiederhole nichts aus diesen letzten Einträgen:\n- " + "\n- ".join(recent[-10:])
    )
    body = json.dumps({"model": os.environ.get("UPLINK_MODEL", "claude-haiku-5-5"),
                       "max_tokens": 120,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        text = "".join(b.get("text", "") for b in data.get("content", [])).strip()
        text = " ".join(text.replace('"', "").replace("*", "").split())
        if 3 <= len(text.split()) <= 30 and text not in recent:
            return text
    except Exception as e:
        print("Claude API nicht erreichbar, nutze Fragmente:", e)
    return None


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    data = {"entries": []}
    if LOG.exists():
        data = json.loads(LOG.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if entries and entries[-1]["date"] == today.isoformat():
        print("Heute schon geschrieben.")
        return

    day = (today - EPOCH).days + 1
    stage_i = min(len(STAGES) - 1, (day - 1) // 7)
    rnd = random.Random(today.toordinal() * 2050 + 6)
    recent_list = [e["text"] for e in entries[-30:]]
    recent = set(recent_list)
    text = claude_line(day, STAGES[stage_i], recent_list)
    source = "claude" if text else "fragmente"
    for _ in range(0 if text else 200):
        cand = " ".join([rnd.choice(OPEN), rnd.choice(MID), rnd.choice(CLOSE)])
        if cand not in recent:
            text = cand
            break
    text = text or cand

    if day > 1 and (day - 1) % 7 == 0:
        text = f"Evolutionsstufe {stage_i + 1}: {STAGES[stage_i]} erreicht. " + text

    entries.append({"date": today.isoformat(), "day": day, "stage": STAGES[stage_i],
                    "stage_n": stage_i + 1, "text": text, "source": source})
    data = {"updated": today.isoformat(), "day": day, "stage": STAGES[stage_i],
            "stage_n": stage_i + 1, "entries": entries[-60:]}
    LOG.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Tag {day} · {STAGES[stage_i]} · {text}")


if __name__ == "__main__":
    main()
