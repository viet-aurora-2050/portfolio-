"""Duenner Wrapper um coinbase-advanced-py. Kapselt alle direkten API-Aufrufe
an einer Stelle, damit Order-Groessen/Produkt-IDs zentral geprueft werden koennen."""

import time
import uuid

from coinbase.rest import RESTClient

_GRANULARITY_SECONDS = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}


class CoinbaseClient:
    def __init__(self, api_key, api_secret):
        self._client = RESTClient(api_key=api_key, api_secret=api_secret)

    def assert_safe_permissions(self):
        """Bricht den Start hart ab, wenn der API-Key Transfer/Withdraw-Rechte hat.
        Zusaetzliche Absicherung im Code - unabhaengig davon, was beim Erstellen
        des Keys auf coinbase.com eingestellt wurde."""
        perms = self._client.get_api_key_permissions()
        if getattr(perms, "can_transfer", False):
            raise RuntimeError(
                "API-Key erlaubt Transfer/Withdraw. Bot-Start abgebrochen - "
                "erstelle einen Key OHNE Transfer-Recht (siehe README.md)."
            )
        if not getattr(perms, "can_trade", False):
            raise RuntimeError("API-Key hat kein Trade-Recht - Bot kann keine Orders platzieren.")
        return perms

    def get_closes(self, product_id, granularity, num_candles):
        seconds = _GRANULARITY_SECONDS[granularity]
        end = int(time.time())
        start = end - seconds * (num_candles + 1)
        resp = self._client.get_candles(
            product_id=product_id, start=str(start), end=str(end), granularity=granularity
        )
        candles = sorted(resp.candles, key=lambda c: int(c.start))
        return [float(c.close) for c in candles]

    def get_current_price(self, product_id):
        return float(self._client.get_product(product_id=product_id).price)

    def get_usd_balance(self):
        cursor = None
        while True:
            resp = self._client.get_accounts(cursor=cursor)
            for acct in resp.accounts:
                if acct.currency == "USD":
                    return float(acct.available_balance.value)
            if not resp.has_next:
                return 0.0
            cursor = resp.cursor

    def market_buy(self, product_id, usd_amount):
        client_order_id = str(uuid.uuid4())
        resp = self._client.market_order_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            quote_size=f"{usd_amount:.2f}",
        )
        return client_order_id, resp

    def market_sell(self, product_id, base_size):
        client_order_id = str(uuid.uuid4())
        resp = self._client.market_order_sell(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=str(base_size),
        )
        return client_order_id, resp

    def wait_for_fill(self, order_id, timeout_seconds=20, poll_interval=2):
        """Pollt die Order, bis Fuellung (filled_size/average_filled_price) vorliegt
        oder das Timeout erreicht ist. Gibt (filled_size, avg_price) zurueck, oder
        (None, None) bei Timeout - der Aufrufer muss diesen Fall behandeln."""
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            order = self._client.get_order(order_id=order_id).order
            if order.filled_size and float(order.filled_size) > 0 and order.average_filled_price:
                return float(order.filled_size), float(order.average_filled_price)
            time.sleep(poll_interval)
        return None, None
