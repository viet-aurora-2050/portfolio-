# Trading-Bot (Coinbase Advanced Trade)

Teilautomatisierter Trendfolge-Bot (MA-Crossover + RSI) mit fest programmierten
Sicherheitsgrenzen. Handelt **nur** Produkte aus einer Whitelist, **nur** bis zu
einem festen Maximalbetrag pro Trade, und sichert offene Positionen automatisch
per Stop-Loss/Take-Profit ab.

## Was der Bot NICHT kann

- Keine Auszahlungen/Transfers - der API-Key darf dafuer keine Berechtigung haben
  (der Bot prueft das beim Start selbst und bricht sonst ab).
- Keine Trades ausserhalb der `whitelist` in `config.yaml`.
- Keine Trades ueber `max_amount_usd_per_trade` hinaus.
- Kein Short-Selling - der Bot verkauft nur Positionen, die er selbst eroeffnet hat.

## 1. Coinbase API-Key erstellen (scoped, ohne Withdraw)

1. Auf https://www.coinbase.com/settings/api einloggen (Coinbase Advanced Trade /
   CDP API Keys - die Oberflaeche kann sich bei Coinbase gelegentlich aendern,
   die Kernpunkte bleiben aber gleich).
2. "New API Key" / "API-Key erstellen" waehlen.
3. Bei den Berechtigungen **nur** ankreuzen:
   - `View` (Konten/Preise lesen)
   - `Trade` (Orders platzieren)
   - **NICHT** `Transfer` / `Withdraw` ankreuzen - das ist die wichtigste
     Absicherung ueberhaupt: selbst wenn Key/Secret abhandenkommen, kann niemand
     Geld von deinem Account abziehen, nur innerhalb des Accounts handeln.
4. Optional: den Key auf ein separates Portfolio/Sub-Account innerhalb von
   Coinbase beschraenken, damit der Bot nicht auf dein gesamtes Vermoegen zugreift.
5. Key-Name (`organizations/.../apiKeys/...`) und den privaten Schluessel
   (PEM-Block) kopieren.

## 2. Einrichtung

```bash
cd trading-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` mit den Werten aus Schritt 1 fuellen. **Diese Datei niemals committen**
(sie steht in `.gitignore`).

`config.yaml` durchgehen und an deine Praeferenzen anpassen:
`whitelist`, `max_amount_usd_per_trade`, `max_open_positions`, `stop_loss_pct`,
`take_profit_pct`, MA-/RSI-Parameter, `poll_interval_seconds`.

`dry_run: true` ist der Standard - der Bot loggt dann jede Entscheidung, platziert
aber keine echten Orders. Erst wenn du das Verhalten ein paar Zyklen beobachtet
hast, in `config.yaml` auf `dry_run: false` umstellen, um live zu handeln.

## 3. Starten

```bash
python3 bot.py
```

Der Bot laeuft in einer Endlosschleife (`poll_interval_seconds` zwischen den
Zyklen), loggt nach `bot.log` und auf stdout, und persistiert offene Positionen
in `state/positions.json`.

Mit `Strg+C` (SIGINT) stoppt er sauber nach dem aktuellen Zyklus.

## Sofort-Stopp (Kill-Switch)

Eine leere Datei namens `STOP` im `trading-bot/`-Verzeichnis anlegen:

```bash
touch STOP
```

Der Bot eroeffnet dann **keine neuen** Positionen mehr, ueberwacht aber weiterhin
bestehende offene Positionen fuer Stop-Loss/Take-Profit. `STOP`-Datei loeschen,
um wieder normal zu starten.

## Gewinn-Benachrichtigung statt Auto-Auszahlung (Human-in-the-loop)

Der Bot kann selbst **kein** Geld transferieren oder auszahlen - dafuer gibt es
zwei Gruende, die nichts mit einer Design-Vorliebe zu tun haben:

1. **Fiat-Auszahlungen** (Bank/SEPA) bietet Coinbase grundsaetzlich **nicht**
   per API an - das ist eine regulatorische Einschraenkung von Coinbase selbst.
   Das geht nur manuell in der Coinbase-App/-Website, unabhaengig davon, was
   dieser Bot tut.
2. **Krypto-Sends** an externe Adressen laufen ueber eine ganz andere, aeltere
   Coinbase-API (nicht die Advanced-Trade-API, die dieser Bot fuers Handeln
   nutzt) und verlangen bei aktivem 2FA einen **live** 2FA-Code pro Transaktion.
   Echte, stille Vollautomatisierung ist also selbst mit vollen Rechten technisch
   nicht vorgesehen, solange 2FA aktiv ist (was du aus Sicherheitsgruenden
   beibehalten solltest).

Stattdessen: `growth_notify` in `config.yaml` aktivieren. Der Bot verfolgt dann
den Gesamtwert deines Accounts (USD-Guthaben + offene Positionen zu aktuellem
Kurs), setzt beim allerersten Lauf eine Baseline, und schickt dir per Telegram
eine Nachricht, sobald der Gewinn gegenueber der Baseline `profit_threshold_usd`
uebersteigt (mit `renotify_cooldown_hours` gegen Spam). Du entscheidest dann
selbst, ob und wie viel du auszahlst.

Einrichtung:

1. In Telegram bei `@BotFather` einen neuen Bot anlegen (`/newbot`), Token
   kopieren.
2. Dem neuen Bot einmal eine beliebige Nachricht schicken.
3. `https://api.telegram.org/bot<TOKEN>/getUpdates` im Browser oder per curl
   aufrufen, `"chat":{"id": ...}` ablesen.
4. `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` in `.env` eintragen.
5. In `config.yaml`: `growth_notify.enabled: true` und `profit_threshold_usd`
   nach Wunsch setzen.

Falls du danach doch Krypto per API versenden willst: das erfordert einen
separaten, aeltereren Coinbase-API-Key mit `send`-Berechtigung (v2 Wallet-API,
nicht die hier verwendete Advanced-Trade-API) und ist bewusst nicht Teil dieses
Bots - sprich mich an, falls du das trotz der 2FA-Einschraenkung zusaetzlich
willst, dann bauen wir das als eigenen, klar abgegrenzten Schritt mit expliziter
Bestaetigung pro Auszahlungsadresse.

## Dauerbetrieb (optional)

Fuer echten Dauerbetrieb z.B. als systemd-Service oder in `screen`/`tmux`
laufen lassen, damit der Bot nicht bei jedem Terminal-Schliessen stirbt. Ein
systemd-Unit-Beispiel liegt bewusst nicht bei - je nach Server/Deploy-Ziel
unterscheidet sich das zu stark, um es sinnvoll zu pauschalisieren.

## Wichtiger Hinweis

Das ist ein einfacher, transparenter Trendfolge-Bot - keine Anlageberatung und
keine Garantie fuer Gewinne. MA-Crossover-Strategien koennen in Seitwaertsmaerkten
viele kleine Verlust-Trades produzieren. Fang mit kleinen Betraegen an
(`max_amount_usd_per_trade`) und beobachte das Verhalten, bevor du den Betrag
erhoehst.
