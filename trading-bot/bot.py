#!/usr/bin/env python3
"""Teilautomatisierter Trendfolge-Bot fuer Coinbase Advanced Trade.

Sicherheitsprinzipien (siehe README.md fuer Details):
  - Handelt NUR Produkte aus config.yaml -> whitelist. Wird an jeder Order-Stelle
    hart geprueft, unabhaengig vom Strategie-Signal.
  - max_amount_usd_per_trade und max_open_positions werden nie ueberschritten.
  - Bricht beim Start ab, wenn der API-Key Transfer/Withdraw-Rechte hat.
  - dry_run=true (Standard in config.yaml) platziert keine echten Orders.
  - Eine vorhandene STOP-Datei im trading-bot/-Verzeichnis haelt den Bot sofort an
    (naechster Zyklus startet keine neuen Trades mehr, offene Positionen werden
    weiter ueberwacht/abgesichert).
"""

import logging
import os
import signal
import sys
import time

import yaml
from dotenv import load_dotenv

from coinbase_client import CoinbaseClient
from risk import RiskManager, RiskViolation
from state import StateStore
from strategy import Signal, compute_signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOP_FILE = os.path.join(BASE_DIR, "STOP")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log")),
    ],
)
log = logging.getLogger("trading-bot")

_shutdown = False


def _handle_sigint(signum, frame):
    global _shutdown
    log.info("Beende nach aktuellem Zyklus (Signal empfangen)...")
    _shutdown = True


def load_config():
    with open(os.path.join(BASE_DIR, "config.yaml")) as f:
        return yaml.safe_load(f)


def run_cycle(client, risk, state, cfg):
    if os.path.exists(STOP_FILE):
        log.warning("STOP-Datei gefunden - ueberspringe neue Kaeufe, pruefe nur offene Positionen.")

    open_positions = state.all()

    # 1. Offene Positionen absichern (Stop-Loss / Take-Profit) - laeuft IMMER,
    #    auch wenn die STOP-Datei gesetzt ist.
    for product_id, pos in list(open_positions.items()):
        try:
            current_price = client.get_current_price(product_id)
        except Exception:
            log.exception("Konnte aktuellen Preis fuer %s nicht abrufen.", product_id)
            continue

        trigger = risk.check_stop_conditions(pos.entry_price, current_price)
        if trigger:
            log.info(
                "%s: %s ausgeloest (Einstieg %.2f, aktuell %.2f) - verkaufe %.8f.",
                product_id, trigger, pos.entry_price, current_price, pos.base_size,
            )
            _execute_sell(client, risk, state, cfg, product_id, pos.base_size)

    if os.path.exists(STOP_FILE):
        return

    # 2. Neue Signale pruefen und ggf. handeln.
    open_positions = state.all()
    for product_id in cfg["whitelist"]:
        has_position = product_id in open_positions
        try:
            closes = client.get_closes(
                product_id, cfg["candle_granularity"],
                num_candles=cfg["ma_long_period"] + cfg["rsi_period"] + 5,
            )
        except Exception:
            log.exception("Konnte Kerzen fuer %s nicht abrufen.", product_id)
            continue

        signal, ind = compute_signal(closes, cfg, has_position)
        if ind:
            log.info(
                "%s: MA_short=%.4f MA_long=%.4f RSI=%.1f -> %s",
                product_id, ind.ma_short, ind.ma_long, ind.rsi, signal.value,
            )

        if signal == Signal.BUY:
            _execute_buy(client, risk, state, cfg, product_id)
        elif signal == Signal.SELL and has_position:
            pos = open_positions[product_id]
            _execute_sell(client, risk, state, cfg, product_id, pos.base_size)


def _execute_buy(client, risk, state, cfg, product_id):
    try:
        risk.check_buy_allowed(product_id, state.all())
    except RiskViolation as e:
        log.info("Kauf %s verweigert: %s", product_id, e)
        return

    try:
        available = client.get_usd_balance()
    except Exception:
        log.exception("Konnte USD-Guthaben nicht abrufen.")
        return

    usd_amount = risk.capped_usd_amount(available)
    if usd_amount < 1:
        log.info("Zu wenig USD-Guthaben (%.2f) fuer einen Kauf von %s.", available, product_id)
        return

    if cfg["dry_run"]:
        log.info("[DRY-RUN] Wuerde %.2f USD in %s kaufen.", usd_amount, product_id)
        return

    log.info("Platziere Market-Buy: %.2f USD %s", usd_amount, product_id)
    client_order_id, resp = client.market_buy(product_id, usd_amount)
    if not resp.success:
        log.error("Kauf fehlgeschlagen: %s", resp.error_response)
        return

    filled_size, avg_price = client.wait_for_fill(resp.order_id)
    if filled_size is None:
        log.warning(
            "Order %s platziert, aber Fuellung nicht bestaetigt innerhalb des Timeouts. "
            "Bitte manuell in Coinbase pruefen, bevor der Bot diese Position verwaltet.",
            resp.order_id,
        )
        return

    state.open_position(product_id, filled_size, avg_price, client_order_id)
    log.info("Position eroeffnet: %s %.8f @ %.2f", product_id, filled_size, avg_price)


def _execute_sell(client, risk, state, cfg, product_id, base_size):
    try:
        risk.check_sell_allowed(product_id)
    except RiskViolation as e:
        log.error("Verkauf %s verweigert: %s", product_id, e)
        return

    if cfg["dry_run"]:
        log.info("[DRY-RUN] Wuerde %.8f %s verkaufen.", base_size, product_id)
        state.close_position(product_id)
        return

    log.info("Platziere Market-Sell: %.8f %s", base_size, product_id)
    client_order_id, resp = client.market_sell(product_id, base_size)
    if not resp.success:
        log.error("Verkauf fehlgeschlagen: %s", resp.error_response)
        return

    state.close_position(product_id)
    log.info("Position geschlossen: %s", product_id)


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    api_key = os.environ.get("COINBASE_API_KEY")
    api_secret = os.environ.get("COINBASE_API_SECRET")
    if not api_key or not api_secret:
        log.error("COINBASE_API_KEY / COINBASE_API_SECRET fehlen. Siehe .env.example.")
        sys.exit(1)

    cfg = load_config()
    client = CoinbaseClient(api_key, api_secret)

    log.info("Pruefe API-Key-Berechtigungen...")
    perms = client.assert_safe_permissions()
    log.info("API-Key OK (can_view=%s, can_trade=%s, can_transfer=%s).",
              perms.can_view, perms.can_trade, perms.can_transfer)

    if cfg["dry_run"]:
        log.warning("DRY-RUN aktiv - es werden KEINE echten Orders platziert.")
    else:
        log.warning("LIVE-MODUS aktiv - es werden ECHTE Orders mit echtem Geld platziert.")

    risk = RiskManager(cfg)
    state = StateStore()

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    log.info("Whitelist: %s | max_amount_usd_per_trade=%s | max_open_positions=%s",
              cfg["whitelist"], cfg["max_amount_usd_per_trade"], cfg["max_open_positions"])

    while not _shutdown:
        try:
            run_cycle(client, risk, state, cfg)
        except Exception:
            log.exception("Unerwarteter Fehler im Handelszyklus - Bot laeuft weiter.")
        for _ in range(cfg["poll_interval_seconds"]):
            if _shutdown:
                break
            time.sleep(1)

    log.info("Bot beendet.")


if __name__ == "__main__":
    main()
