"""Setzt die Sicherheitsgrenzen aus config.yaml durch - unabhaengig von der Strategie.
Jede Order muss hier durch, bevor sie an Coinbase geschickt wird."""


class RiskViolation(Exception):
    pass


class RiskManager:
    def __init__(self, cfg):
        self.whitelist = set(cfg["whitelist"])
        self.max_amount_usd_per_trade = float(cfg["max_amount_usd_per_trade"])
        self.max_open_positions = int(cfg["max_open_positions"])
        self.stop_loss_pct = float(cfg["stop_loss_pct"])
        take_profit = cfg.get("take_profit_pct")
        self.take_profit_pct = float(take_profit) if take_profit else None

    def check_buy_allowed(self, product_id, open_positions):
        if product_id not in self.whitelist:
            raise RiskViolation(f"{product_id} ist nicht in der Whitelist - Kauf verweigert.")
        if product_id in open_positions:
            raise RiskViolation(f"Bereits eine offene Position in {product_id}.")
        if len(open_positions) >= self.max_open_positions:
            raise RiskViolation(
                f"max_open_positions ({self.max_open_positions}) erreicht - Kauf verweigert."
            )

    def check_sell_allowed(self, product_id):
        if product_id not in self.whitelist:
            raise RiskViolation(f"{product_id} ist nicht in der Whitelist - Verkauf verweigert.")

    def capped_usd_amount(self, available_usd):
        return round(min(self.max_amount_usd_per_trade, available_usd), 2)

    def check_stop_conditions(self, entry_price, current_price):
        """Gibt 'stop_loss', 'take_profit' oder None zurueck."""
        change = (current_price - entry_price) / entry_price
        if change <= -self.stop_loss_pct:
            return "stop_loss"
        if self.take_profit_pct and change >= self.take_profit_pct:
            return "take_profit"
        return None
