"""Schickt Gewinn-Benachrichtigungen per Telegram. Loest NIEMALS selbst eine
Auszahlung aus - der Bot hat und braucht dafuer keine Transfer-Berechtigung.
Die eigentliche Auszahlung macht der Mensch danach manuell in der Coinbase-App
(fuer Fiat ist das ohnehin die einzige Moeglichkeit - Coinbase bietet aus
regulatorischen Gruenden keine API fuer Fiat-Auszahlungen)."""

import logging

import requests

log = logging.getLogger("trading-bot")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_growth_alert(bot_token, chat_id, baseline_usd, current_total_usd, threshold_usd):
    profit = current_total_usd - baseline_usd
    text = (
        "\U0001F4C8 Gewinn-Schwelle erreicht!\n\n"
        f"Start-Kapital (Baseline): {baseline_usd:.2f} USD\n"
        f"Aktueller Kontowert: {current_total_usd:.2f} USD\n"
        f"Gewinn: {profit:.2f} USD (Schwelle: {threshold_usd:.2f} USD)\n\n"
        "Der Bot zieht selbst KEIN Geld ab - das musst du manuell in der "
        "Coinbase-App bestaetigen (fuer Fiat-Auszahlung ohnehin Pflicht, "
        "fuer Krypto-Sends verlangt Coinbase bei aktivem 2FA einen Live-Code "
        "von dir)."
    )
    return _send(bot_token, chat_id, text)


def _send(bot_token, chat_id, text):
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=bot_token),
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        log.exception("Telegram-Benachrichtigung konnte nicht gesendet werden.")
        return False
