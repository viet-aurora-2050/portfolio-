"""Trendfolge-Strategie: MA-Crossover + RSI-Filter. Reines Python, keine Dependencies."""

from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values, period):
    """Wilder's RSI. `values` sind Schlusskurse, aeltester zuerst."""
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


@dataclass
class Indicators:
    ma_short: float
    ma_long: float
    ma_short_prev: float
    ma_long_prev: float
    rsi: float


def compute_indicators(closes, cfg):
    short_p, long_p, rsi_p = cfg["ma_short_period"], cfg["ma_long_period"], cfg["rsi_period"]
    if len(closes) < long_p + 1 or len(closes) < rsi_p + 2:
        return None
    ma_short, ma_long = sma(closes, short_p), sma(closes, long_p)
    ma_short_prev, ma_long_prev = sma(closes[:-1], short_p), sma(closes[:-1], long_p)
    r = rsi(closes, rsi_p)
    if None in (ma_short, ma_long, ma_short_prev, ma_long_prev, r):
        return None
    return Indicators(ma_short, ma_long, ma_short_prev, ma_long_prev, r)


def compute_signal(closes, cfg, has_open_position):
    """
    BUY: bullischer Crossover (MA-short kreuzt MA-long von unten) UND RSI nicht ueberkauft,
    nur wenn keine Position offen ist (der Bot geht nicht short).
    SELL: bearischer Crossover ODER RSI ueberkauft, nur wenn eine Position offen ist.
    """
    ind = compute_indicators(closes, cfg)
    if ind is None:
        return Signal.HOLD, None

    bullish_cross = ind.ma_short_prev <= ind.ma_long_prev and ind.ma_short > ind.ma_long
    bearish_cross = ind.ma_short_prev >= ind.ma_long_prev and ind.ma_short < ind.ma_long

    if not has_open_position:
        if bullish_cross and ind.rsi < cfg["rsi_overbought"]:
            return Signal.BUY, ind
        return Signal.HOLD, ind

    if bearish_cross or ind.rsi > cfg["rsi_overbought"]:
        return Signal.SELL, ind
    return Signal.HOLD, ind
