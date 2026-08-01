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
