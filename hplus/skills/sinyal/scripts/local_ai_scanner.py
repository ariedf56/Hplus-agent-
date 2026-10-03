"""
POWERFUL LOCAL AI SCANNER V2
================================

Purpose:
    Local multi-factor market decision engine.

Output:
    BUY
    SELL
    BUY_LIMIT
    SELL_LIMIT
    HOLD

Important:
    Score is NOT win probability.
    Confidence is NOT guaranteed probability of profit.

The scanner consumes the output of MarketAnalyzer.process_all().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import math


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class ScannerConfig:
    max_spread_points: float = 45.0

    extreme_chop: float = 61.8
    trending_chop: float = 38.2
    strong_ker: float = 0.60
    weak_ker: float = 0.25

    minimum_direction_score: float = 50.0
    strong_direction_score: float = 72.0

    minimum_confidence: float = 0.58
    strong_confidence: float = 0.75

    # Location thresholds
    near_level_atr_multiplier: float = 0.75
    limit_zone_atr_multiplier: float = 1.25

    # Maximum contribution of individual engines
    max_factor_contribution: float = 1.0


# ============================================================
# HELPERS
# ============================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sign(value: float) -> int:
    if value > 0:
        return 1

    if value < 0:
        return -1

    return 0


def directional_value(
    value: float,
    bullish_text: Tuple[str, ...],
    bearish_text: Tuple[str, ...],
) -> float:

    text = str(value).upper()

    if any(x in text for x in bullish_text):
        return 1.0

    if any(x in text for x in bearish_text):
        return -1.0

    return 0.0


# ============================================================
# FACTOR OBJECT
# ============================================================

@dataclass
class Evidence:
    name: str
    score: float
    quality: float
    weight: float
    reason: str

    @property
    def contribution(self) -> float:
        return self.score * self.quality * self.weight


# ============================================================
# MAIN ENGINE
# ============================================================

class PowerfulLocalAIScanner:

    def __init__(
        self,
        config: ScannerConfig | None = None,
    ):
        self.config = config or ScannerConfig()

    # ========================================================
    # PUBLIC ENTRY
    # ========================================================

    def scan(self, processed: Dict[str, Any]) -> Dict[str, Any]:

        validation = self.validate_data(processed)

        if not validation["valid"]:
            return self._hold_result(
                reason=validation["reason"],
                risk_flags=validation["errors"],
            )

        permission = self.evaluate_permission(processed)

        if not permission["allowed"]:
            return self._hold_result(
                reason=permission["reason"],
                risk_flags=permission["risk_flags"],
                permission=permission,
            )

        regime = self.evaluate_regime(processed)

        factors = {
            "macro": self.evaluate_macro(processed),
            "trend": self.evaluate_trend(processed, regime),
            "structure": self.evaluate_structure(processed, regime),
            "momentum": self.evaluate_momentum(processed, regime),
            "flow": self.evaluate_order_flow(processed, regime),
            "smc": self.evaluate_smc(processed, regime),
            "liquidity": self.evaluate_liquidity(processed, regime),
            "location": self.evaluate_location(processed, regime),
            "exhaustion": self.evaluate_exhaustion(processed),
            "execution": self.evaluate_execution(processed),
            "news": self.evaluate_news(processed, regime),
            "dxy": self.evaluate_dxy(processed, regime),
        }

        fusion = self.fuse_evidence(
            factors=factors,
            regime=regime,
        )

        timing = self.evaluate_timing(
            processed=processed,
            direction_score=fusion["direction_score"],
        )

        candidates = self.evaluate_entry_candidates(
            processed=processed,
            regime=regime,
            fusion=fusion,
            timing=timing,
        )

        confidence = self.calculate_confidence(
            processed=processed,
            regime=regime,
            factors=factors,
            fusion=fusion,
            timing=timing,
            candidates=candidates,
        )

        decision = self.build_decision(
            processed=processed,
            permission=permission,
            regime=regime,
            factors=factors,
            fusion=fusion,
            timing=timing,
            candidates=candidates,
            confidence=confidence,
        )

        return {
            "allowed": True,
            "regime": regime,
            "permission": permission,
            "factors": factors,
            "fusion": fusion,
            "timing": timing,
            "candidates": candidates,
            "confidence": confidence,
            "decision": decision,
        }

    # ========================================================
    # 1. VALIDATOR
    # ========================================================

    def validate_data(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        errors: List[str] = []

        if not isinstance(processed, dict):
            return {
                "valid": False,
                "errors": ["processed bukan dictionary"],
                "reason": "Invalid processed analysis",
            }

        required = [
            "market_info",
            "market_regime",
            "ut_bot_h1",
            "m5_structure_shift",
            "m5_indicators",
        ]

        for key in required:
            if key not in processed:
                errors.append(f"Missing field: {key}")

        market_info = processed.get("market_info", {})

        if not isinstance(market_info, dict):
            errors.append("market_info invalid")

        price = safe_float(
            processed.get("m5_indicators", {}).get("current_price"),
            0.0,
        )

        if price <= 0:
            errors.append("Invalid current price")

        spread = safe_float(
            market_info.get("spread"),
            999999,
        )

        if spread < 0:
            errors.append("Invalid spread")

        if errors:
            return {
                "valid": False,
                "errors": errors,
                "reason": "Data validation gagal",
            }

        return {
            "valid": True,
            "errors": [],
            "reason": "Data valid",
        }

    # ========================================================
    # 2. PERMISSION
    # ========================================================

    def evaluate_permission(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        flags = []

        market_info = processed.get("market_info", {})

        spread = safe_float(
            market_info.get("spread"),
            999999,
        )

        if spread > self.config.max_spread_points:

            return {
                "allowed": False,
                "reason": f"Spread terlalu besar: {spread:.1f} pts",
                "risk_flags": ["EXTREME_SPREAD"],
            }

        # v5: berita TIDAK lagi memveto. Berita adalah informasi arah
        # yang dihitung sebagai faktor NEWS di bawah (evaluate_news),
        # bukan alasan memblokir entry. Yang memveto hanya kondisi
        # struktur pasar (spread ekstrem, chop ekstrem, likuiditas).

        regime = processed.get(
            "market_regime",
            {},
        )

        chop = safe_float(
            regime.get("choppiness_index"),
            50.0,
        )

        if chop >= self.config.extreme_chop:

            return {
                "allowed": False,
                "reason": f"Extreme choppy market: CHOP {chop:.1f}",
                "risk_flags": ["EXTREME_CHOP"],
            }

        session = processed.get(
            "session_context_utc",
            {},
        )

        session_name = str(
            session.get(
                "current_trading_session",
                "",
            )
        ).upper()

        if "OFF_PEAK" in session_name:

            return {
                "allowed": False,
                "reason": "Session OFF_PEAK",
                "risk_flags": ["OFF_PEAK"],
            }

        ut = processed.get(
            "ut_bot_h1",
            {},
        )

        if bool(ut.get("low_liq", False)):

            return {
                "allowed": False,
                "reason": "H1 mendeteksi low liquidity",
                "risk_flags": ["LOW_LIQUIDITY"],
            }

        if spread > 35:
            flags.append("THIN_LIQUIDITY")

        if chop > 55:
            flags.append("ELEVATED_CHOP")

        return {
            "allowed": True,
            "reason": "Permission passed",
            "risk_flags": flags,
        }

    # ========================================================
    # 3. REGIME
    # ========================================================

    def evaluate_regime(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        raw = processed.get(
            "market_regime",
            {},
        )

        chop = safe_float(
            raw.get("choppiness_index"),
            50.0,
        )

        ker = safe_float(
            raw.get("efficiency_ratio_ker"),
            0.5,
        )

        if (
            chop >= self.config.extreme_chop
            or ker < self.config.weak_ker
        ):
            regime = "CHOPPY"

        elif (
            chop <= self.config.trending_chop
            and ker >= self.config.strong_ker
        ):
            regime = "TRENDING"

        elif chop >= 50 or ker < 0.40:
            regime = "TRANSITION"

        else:
            regime = "NORMAL"

        return {
            "name": regime,
            "chop": chop,
            "ker": ker,
            "raw_status": raw.get(
                "regime_status",
                "UNKNOWN",
            ),
        }

    # ========================================================
    # 4. MACRO
    # ========================================================

    def evaluate_macro(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        h4 = processed.get(
            "h4_macro_trend",
            {},
        )

        direction = str(
            h4.get(
                "h4_trend_direction",
                "SIDEWAYS",
            )
        ).upper()

        if direction == "BULLISH":

            evidence.append(
                Evidence(
                    "H4_TREND",
                    1.0,
                    1.0,
                    0.90,
                    "H4 trend bullish",
                )
            )

        elif direction == "BEARISH":

            evidence.append(
                Evidence(
                    "H4_TREND",
                    -1.0,
                    1.0,
                    0.90,
                    "H4 trend bearish",
                )
            )

        else:

            evidence.append(
                Evidence(
                    "H4_TREND",
                    0.0,
                    0.5,
                    0.90,
                    "H4 trend sideways",
                )
            )

        return self._factor_result(
            "MACRO",
            evidence,
        )

    # ========================================================
    # 5. TREND
    # ========================================================

    def evaluate_trend(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        ut = processed.get(
            "ut_bot_h1",
            {},
        )

        ut_direction = str(
            ut.get(
                "direction",
                "NEUTRAL",
            )
        ).upper()

        ema_above = bool(
            ut.get(
                "above_ema200",
                False,
            )
        )

        # H1 UT + EMA200 are treated as ONE trend group.
        if ut_direction == "BULLISH" and ema_above:

            evidence.append(
                Evidence(
                    "H1_PRIMARY_TREND",
                    1.0,
                    1.0,
                    1.00,
                    "UT Bot bullish + price above EMA200",
                )
            )

        elif ut_direction == "BEARISH" and not ema_above:

            evidence.append(
                Evidence(
                    "H1_PRIMARY_TREND",
                    -1.0,
                    1.0,
                    1.00,
                    "UT Bot bearish + price below EMA200",
                )
            )

        elif ut_direction == "BULLISH":

            evidence.append(
                Evidence(
                    "H1_PRIMARY_TREND",
                    0.55,
                    0.75,
                    1.00,
                    "UT bullish tetapi EMA200 belum confirm",
                )
            )

        elif ut_direction == "BEARISH":

            evidence.append(
                Evidence(
                    "H1_PRIMARY_TREND",
                    -0.55,
                    0.75,
                    1.00,
                    "UT bearish tetapi EMA200 belum confirm",
                )
            )

        m30 = processed.get(
            "m30_trendline",
            {},
        )

        m30_direction = str(
            m30.get(
                "trend_direction",
                "SIDEWAYS",
            )
        ).upper()

        if m30_direction == "BULLISH":

            evidence.append(
                Evidence(
                    "M30_TREND",
                    1.0,
                    0.8,
                    0.65,
                    "M30 slope bullish",
                )
            )

        elif m30_direction == "BEARISH":

            evidence.append(
                Evidence(
                    "M30_TREND",
                    -1.0,
                    0.8,
                    0.65,
                    "M30 slope bearish",
                )
            )

        return self._factor_result(
            "TREND",
            evidence,
        )

    # ========================================================
    # 6. STRUCTURE
    # ========================================================

    def evaluate_structure(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        m15 = processed.get(
            "m15_structure",
            {},
        )

        m15_structure = str(
            m15.get(
                "market_structure",
                "NEUTRAL",
            )
        ).upper()

        if "BULLISH" in m15_structure:

            evidence.append(
                Evidence(
                    "M15_STRUCTURE",
                    1.0,
                    0.85,
                    0.80,
                    "M15 bullish structure",
                )
            )

        elif "BEARISH" in m15_structure:

            evidence.append(
                Evidence(
                    "M15_STRUCTURE",
                    -1.0,
                    0.85,
                    0.80,
                    "M15 bearish structure",
                )
            )

        mss = processed.get(
            "m5_structure_shift",
            {},
        )

        mss_status = str(
            mss.get(
                "m5_structure_shift",
                "NONE",
            )
        ).upper()

        if "BULLISH" in mss_status:

            evidence.append(
                Evidence(
                    "M5_MSS",
                    1.0,
                    1.0,
                    0.95,
                    "M5 bullish MSS/breakout",
                )
            )

        elif "BEARISH" in mss_status:

            evidence.append(
                Evidence(
                    "M5_MSS",
                    -1.0,
                    1.0,
                    0.95,
                    "M5 bearish MSS/breakout",
                )
            )

        return self._factor_result(
            "STRUCTURE",
            evidence,
        )

    # ========================================================
    # 7. MOMENTUM
    # ========================================================

    def evaluate_momentum(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        m5 = processed.get(
            "m5_indicators",
            {},
        )

        price = safe_float(
            m5.get("current_price"),
        )

        ma14 = safe_float(
            m5.get("ma14"),
        )

        ma50 = safe_float(
            m5.get("ma50"),
        )

        rsi = safe_float(
            m5.get("rsi"),
            50.0,
        )

        macd = safe_float(
            m5.get("macd"),
        )

        macd_signal = safe_float(
            m5.get("macd_signal"),
        )

        # MA alignment
        if (
            price > ma14
            and ma14 > ma50
        ):

            evidence.append(
                Evidence(
                    "MA_ALIGNMENT",
                    1.0,
                    0.85,
                    0.70,
                    "Price > MA14 > MA50",
                )
            )

        elif (
            price < ma14
            and ma14 < ma50
        ):

            evidence.append(
                Evidence(
                    "MA_ALIGNMENT",
                    -1.0,
                    0.85,
                    0.70,
                    "Price < MA14 < MA50",
                )
            )

        # MACD
        if macd > macd_signal:

            evidence.append(
                Evidence(
                    "MACD",
                    1.0,
                    0.75,
                    0.55,
                    "MACD bullish",
                )
            )

        elif macd < macd_signal:

            evidence.append(
                Evidence(
                    "MACD",
                    -1.0,
                    0.75,
                    0.55,
                    "MACD bearish",
                )
            )

        # RSI is contextual, not blindly contrarian.
        if regime["name"] == "TRENDING":

            if 52 <= rsi <= 72:

                evidence.append(
                    Evidence(
                        "RSI",
                        0.65,
                        0.75,
                        0.45,
                        "RSI supports bullish trend",
                    )
                )

            elif 28 <= rsi <= 48:

                evidence.append(
                    Evidence(
                        "RSI",
                        -0.65,
                        0.75,
                        0.45,
                        "RSI supports bearish trend",
                    )
                )

        else:

            if 45 <= rsi <= 65:

                evidence.append(
                    Evidence(
                        "RSI",
                        0.0,
                        0.5,
                        0.30,
                        "RSI neutral",
                    )
                )

        return self._factor_result(
            "MOMENTUM",
            evidence,
        )

    # ========================================================
    # 8. ORDER FLOW
    # ========================================================

    def evaluate_order_flow(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        cvd = processed.get(
            "cvd_order_flow",
            {},
        )

        cvd_bias = str(
            cvd.get(
                "cvd_bias",
                "NEUTRAL",
            )
        ).upper()

        absorption = str(
            cvd.get(
                "absorption_status",
                "NONE",
            )
        ).upper()

        if "BUYERS_DOMINANT" in cvd_bias:

            evidence.append(
                Evidence(
                    "CVD",
                    1.0,
                    0.80,
                    0.85,
                    "CVD buyers dominant",
                )
            )

        elif "SELLERS_DOMINANT" in cvd_bias:

            evidence.append(
                Evidence(
                    "CVD",
                    -1.0,
                    0.80,
                    0.85,
                    "CVD sellers dominant",
                )
            )

        if "BULLISH" in absorption:

            evidence.append(
                Evidence(
                    "ABSORPTION",
                    1.0,
                    0.95,
                    0.85,
                    "Bullish absorption",
                )
            )

        elif "BEARISH" in absorption:

            evidence.append(
                Evidence(
                    "ABSORPTION",
                    -1.0,
                    0.95,
                    0.85,
                    "Bearish absorption",
                )
            )

        micro = processed.get(
            "micro_structure",
            {},
        )

        micro_score = safe_float(
            micro.get("score"),
        )

        micro_score = clamp(
            micro_score / 10.0,
            -1.0,
            1.0,
        )

        if micro_score != 0:

            evidence.append(
                Evidence(
                    "M1_MICRO_FLOW",
                    micro_score,
                    0.80,
                    0.70,
                    f"M1 microstructure score {micro_score:.2f}",
                )
            )

        return self._factor_result(
            "ORDER_FLOW",
            evidence,
        )

    # ========================================================
    # 9. SMC
    # ========================================================

    def evaluate_smc(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        smc = processed.get(
            "smc_concepts",
            {},
        )

        ob = str(
            smc.get(
                "order_block_status",
                "NONE",
            )
        ).upper()

        fvg = str(
            smc.get(
                "fvg_status",
                "NONE",
            )
        ).upper()

        if "BULLISH" in ob:

            evidence.append(
                Evidence(
                    "BULLISH_OB",
                    1.0,
                    0.85,
                    0.75,
                    "Bullish order block",
                )
            )

        elif "BEARISH" in ob:

            evidence.append(
                Evidence(
                    "BEARISH_OB",
                    -1.0,
                    0.85,
                    0.75,
                    "Bearish order block",
                )
            )

        if "BULLISH" in fvg:

            evidence.append(
                Evidence(
                    "BULLISH_FVG",
                    1.0,
                    0.80,
                    0.65,
                    "Bullish FVG",
                )
            )

        elif "BEARISH" in fvg:

            evidence.append(
                Evidence(
                    "BEARISH_FVG",
                    -1.0,
                    0.80,
                    0.65,
                    "Bearish FVG",
                )
            )

        return self._factor_result(
            "SMC",
            evidence,
        )

    # ========================================================
    # 10. LIQUIDITY
    # ========================================================

    def evaluate_liquidity(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        liq = processed.get(
            "liquidity_erl_irl",
            {},
        )

        zone = str(
            liq.get(
                "discount_premium_zone",
                "NEUTRAL",
            )
        ).upper()

        if "DISCOUNT" in zone:

            evidence.append(
                Evidence(
                    "DISCOUNT_ZONE",
                    1.0,
                    0.75,
                    0.65,
                    "Price berada di discount zone",
                )
            )

        elif "PREMIUM" in zone:

            evidence.append(
                Evidence(
                    "PREMIUM_ZONE",
                    -1.0,
                    0.75,
                    0.65,
                    "Price berada di premium zone",
                )
            )

        return self._factor_result(
            "LIQUIDITY",
            evidence,
        )

    # ========================================================
    # 11. LOCATION
    # ========================================================

    def evaluate_location(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        price = safe_float(
            processed.get(
                "m5_indicators",
                {},
            ).get("current_price"),
        )

        atr = safe_float(
            processed.get(
                "m5_indicators",
                {},
            ).get("atr"),
            1.5,
        )

        if atr <= 0:
            atr = 1.5

        snr = processed.get(
            "h1_snr",
            {},
        )

        support = safe_float(
            snr.get("support"),
        )

        resistance = safe_float(
            snr.get("resistance"),
        )

        distance_support = (
            abs(price - support)
            if support > 0
            else float("inf")
        )

        distance_resistance = (
            abs(resistance - price)
            if resistance > 0
            else float("inf")
        )

        threshold = (
            atr
            * self.config.near_level_atr_multiplier
        )

        if distance_support <= threshold:

            evidence.append(
                Evidence(
                    "NEAR_H1_SUPPORT",
                    1.0,
                    0.90,
                    0.85,
                    "Harga dekat H1 support",
                )
            )

        if distance_resistance <= threshold:

            evidence.append(
                Evidence(
                    "NEAR_H1_RESISTANCE",
                    -1.0,
                    0.90,
                    0.85,
                    "Harga dekat H1 resistance",
                )
            )

        rbs = processed.get(
            "rbs_sbr_structure",
            {},
        )

        rbs_status = str(
            rbs.get(
                "rbs_sbr_status",
                "NONE",
            )
        ).upper()

        if "RBS" in rbs_status:

            evidence.append(
                Evidence(
                    "RBS",
                    1.0,
                    0.90,
                    0.80,
                    "Resistance menjadi support",
                )
            )

        elif "SBR" in rbs_status:

            evidence.append(
                Evidence(
                    "SBR",
                    -1.0,
                    0.90,
                    0.80,
                    "Support menjadi resistance",
                )
            )

        return self._factor_result(
            "LOCATION",
            evidence,
        )

    # ========================================================
    # 12. EXHAUSTION
    # ========================================================

    def evaluate_exhaustion(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        exhaustion = processed.get(
            "candle_exhaustion",
            {},
        )

        detected = bool(
            exhaustion.get(
                "exhaustion_detected",
                False,
            )
        )

        pressure = str(
            exhaustion.get(
                "pressure_bias",
                "NEUTRAL",
            )
        ).upper()

        volume_spike = bool(
            exhaustion.get(
                "volume_spike",
                False,
            )
        )

        if detected:

            # Exhaustion is primarily a risk penalty.
            if "BUYING" in pressure:

                evidence.append(
                    Evidence(
                        "BUY_EXHAUSTION",
                        -0.60,
                        1.0,
                        0.85,
                        "Buying pressure menunjukkan exhaustion",
                    )
                )

            elif "SELLING" in pressure:

                evidence.append(
                    Evidence(
                        "SELL_EXHAUSTION",
                        0.60,
                        1.0,
                        0.85,
                        "Selling pressure menunjukkan exhaustion",
                    )
                )

        if volume_spike:

            evidence.append(
                Evidence(
                    "VOLUME_SPIKE",
                    0.0,
                    0.70,
                    0.35,
                    "Volume spike — perlu konfirmasi",
                )
            )

        return self._factor_result(
            "EXHAUSTION",
            evidence,
        )

    # ========================================================
    # 13. EXECUTION
    # ========================================================

    def evaluate_execution(
        self,
        processed: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        market_info = processed.get(
            "market_info",
            {},
        )

        spread = safe_float(
            market_info.get("spread"),
            999,
        )

        if spread <= 20:

            quality = 1.0

        elif spread <= 30:

            quality = 0.80

        elif spread <= 35:

            quality = 0.60

        else:

            quality = 0.30

        evidence.append(
            Evidence(
                "SPREAD_QUALITY",
                quality,
                1.0,
                1.0,
                f"Spread {spread:.1f} pts",
            )
        )

        return self._factor_result(
            "EXECUTION",
            evidence,
        )

    # ========================================================
    # 11. NEWS — sentimen berita + sentimen pasar sebagai faktor arah
    # ========================================================
    # v5: berita dihitung, bukan diveto. Tiga evidence:
    #   NEWS_DIRECTION  : bias headline per-aset (-1..1)
    #   NEWS_SHOCK      : berita dampak-3 yang masih segar (<2 jam)
    #   MARKET_SENTIMENT: Fear & Greed Index
    # Skor faktor ini ikut fusion seperti 10 faktor lainnya.

    def evaluate_news(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        ni = processed.get("news_intelligence", {}) or {}
        bias_aset = safe_float(
            ni.get("news_bias_aset", ni.get("news_bias", 0.0)),
            0.0,
        )
        kekuatan = clamp(
            safe_float(ni.get("news_strength", 0.0), 0.0),
            0.0,
            1.0,
        )
        jumlah = int(ni.get("jumlah", 0) or 0)

        if jumlah > 0 and abs(bias_aset) >= 0.05:
            arah_txt = "bullish" if bias_aset > 0 else "bearish"
            evidence.append(
                Evidence(
                    "NEWS_DIRECTION",
                    clamp(bias_aset, -1.0, 1.0),
                    kekuatan,
                    1.00,
                    f"{jumlah} headline, bias {arah_txt} {bias_aset:+.2f}",
                )
            )

        shock = ni.get("news_shock", {}) or {}
        if bool(shock.get("aktif")) and int(shock.get("arah", 0)) != 0:
            arah = int(shock["arah"])
            judul = str((shock.get("judul") or ["berita"])[0])[:80]
            evidence.append(
                Evidence(
                    "NEWS_SHOCK",
                    float(arah),
                    1.00,
                    0.80,
                    f"Shock {'bearish' if arah < 0 else 'bullish'}: {judul}",
                )
            )

        fund = processed.get("fundamental", {}) or {}
        bias_fund = safe_float(fund.get("bias", 0.0), 0.0)
        fg = fund.get("fear_greed", {}) or {}
        if abs(bias_fund) >= 0.2:
            evidence.append(
                Evidence(
                    "MARKET_SENTIMENT",
                    clamp(bias_fund, -1.0, 1.0),
                    0.70,
                    0.60,
                    f"Fear & Greed {fg.get('nilai', '?')} "
                    f"({fg.get('klasifikasi', '?')})",
                )
            )

        return self._factor_result(
            "NEWS",
            evidence,
        )

    # ========================================================
    # 13b. DXY (khusus emas — faktor ke-12)
    #
    # Riset 2026-10-01: korelasi invers DXY↔emas ~-0.70 s/d -0.85,
    # TAPI pecah saat risk-off ekstrem (keduanya naik bareng) dan
    # melemah struktural pasca-2022 (premi de-dolarisasi).
    # -> dipakai sebagai KONFIRMASI (weight moderat), bukan hukum.
    # Untuk aset non-emas (processed tanpa blok "dxy"): netral.
    # ========================================================

    def evaluate_dxy(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        evidence = []

        dxy = processed.get("dxy", {}) or {}
        tren = str(dxy.get("trend", "NEUTRAL")).upper()
        nilai = safe_float(dxy.get("nilai", 0.0), 0.0)

        if tren == "UP":
            # Dolar menguat -> headwind untuk emas (bearish XAUUSD).
            evidence.append(
                Evidence(
                    "DXY_STRENGTH",
                    -1.0,
                    0.70,
                    0.80,
                    f"DXY uptrend ({nilai}) -> headwind emas",
                )
            )
        elif tren == "DOWN":
            # Dolar melemah -> tailwind untuk emas (bullish XAUUSD).
            evidence.append(
                Evidence(
                    "DXY_STRENGTH",
                    1.0,
                    0.70,
                    0.80,
                    f"DXY downtrend ({nilai}) -> tailwind emas",
                )
            )

        return self._factor_result(
            "DXY",
            evidence,
        )

    # ========================================================
    # 14. EVIDENCE FUSION
    # ========================================================

    def fuse_evidence(
        self,
        factors: Dict[str, Dict[str, Any]],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:

        regime_weights = self._regime_weights(
            regime["name"]
        )

        contributions = []

        buy_evidence = 0.0
        sell_evidence = 0.0

        total_weight = 0.0

        factor_details = {}

        for factor_name, factor in factors.items():

            raw_score = safe_float(
                factor.get("score"),
            )

            quality = clamp(
                safe_float(
                    factor.get("quality"),
                    0.0,
                ),
                0.0,
                1.0,
            )

            regime_weight = regime_weights.get(
                factor_name,
                1.0,
            )

            contribution = (
                raw_score
                * quality
                * regime_weight
            )

            contribution = clamp(
                contribution,
                -1.0,
                1.0,
            )

            contributions.append(
                contribution
            )

            if contribution > 0:
                buy_evidence += contribution

            elif contribution < 0:
                sell_evidence += abs(
                    contribution
                )

            total_weight += (
                quality
                * regime_weight
            )

            factor_details[factor_name] = {
                "score": raw_score,
                "quality": quality,
                "regime_weight": regime_weight,
                "contribution": contribution,
                "reason": factor.get(
                    "reason",
                    "",
                ),
            }

        if total_weight > 0:

            net = (
                sum(contributions)
                / total_weight
            )

        else:

            net = 0.0

        direction_score = clamp(
            net * 100.0,
            -100.0,
            100.0,
        )

        non_zero = [
            x
            for x in contributions
            if abs(x) >= 0.15
        ]

        if non_zero:

            agreement = (
                abs(sum(non_zero))
                / sum(abs(x) for x in non_zero)
            )

        else:

            agreement = 0.0

        bullish_count = sum(
            1
            for x in non_zero
            if x > 0
        )

        bearish_count = sum(
            1
            for x in non_zero
            if x < 0
        )

        total_directional = (
            bullish_count
            + bearish_count
        )

        if total_directional:

            conflict = (
                min(
                    bullish_count,
                    bearish_count,
                )
                / total_directional
            )

        else:

            conflict = 0.0

        return {
            "buy_evidence": round(
                buy_evidence,
                4,
            ),
            "sell_evidence": round(
                sell_evidence,
                4,
            ),
            "direction_score": round(
                direction_score,
                2,
            ),
            "agreement": round(
                agreement,
                3,
            ),
            "conflict": round(
                conflict,
                3,
            ),
            "factors": factor_details,
        }

    # ========================================================
    # 15. TIMING
    # ========================================================

    def evaluate_timing(
        self,
        processed: Dict[str, Any],
        direction_score: float,
    ) -> Dict[str, Any]:

        micro = processed.get(
            "micro_structure",
            {},
        )

        micro_score = safe_float(
            micro.get("score"),
        )

        micro_shift = str(
            micro.get(
                "structure_shift_micro",
                "NONE",
            )
        ).upper()

        volume_velocity = safe_float(
            micro.get(
                "volume_velocity",
                1.0,
            ),
            1.0,
        )

        timing_score = 0.0
        reasons = []

        if direction_score > 0:

            if micro_score > 0:
                timing_score += 0.45
                reasons.append(
                    "M1 flow bullish"
                )

            if "BULLISH" in micro_shift:
                timing_score += 0.35
                reasons.append(
                    "M1 bullish breakout"
                )

        elif direction_score < 0:

            if micro_score < 0:
                timing_score += 0.45
                reasons.append(
                    "M1 flow bearish"
                )

            if "BEARISH" in micro_shift:
                timing_score += 0.35
                reasons.append(
                    "M1 bearish breakout"
                )

        if volume_velocity > 1.5:

            timing_score += 0.20

            reasons.append(
                "Volume velocity meningkat"
            )

        timing_score = clamp(
            timing_score,
            0.0,
            1.0,
        )

        if timing_score >= 0.70:

            state = "ENTRY_NOW"

        elif timing_score >= 0.40:

            state = "WAIT_CONFIRMATION"

        else:

            state = "WAIT_PULLBACK"

        return {
            "score": round(
                timing_score,
                3,
            ),
            "state": state,
            "reasons": reasons,
        }

    # ========================================================
    # 16. ENTRY CANDIDATES
    # ========================================================

    def evaluate_entry_candidates(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
        fusion: Dict[str, Any],
        timing: Dict[str, Any],
    ) -> Dict[str, Any]:

        price = safe_float(
            processed.get(
                "m5_indicators",
                {},
            ).get("current_price"),
        )

        atr = safe_float(
            processed.get(
                "m5_indicators",
                {},
            ).get("atr"),
            1.5,
        )

        if atr <= 0:
            atr = 1.5

        score = safe_float(
            fusion.get(
                "direction_score",
            )
        )

        location = processed.get(
            "liquidity_erl_irl",
            {},
        )

        zone = str(
            location.get(
                "discount_premium_zone",
                "NEUTRAL",
            )
        ).upper()

        snr = processed.get(
            "h1_snr",
            {},
        )

        support = safe_float(
            snr.get("support"),
        )

        resistance = safe_float(
            snr.get("resistance"),
        )

        candidates = {
            "buy": {
                "quality": 0.0,
                "price": price,
            },
            "sell": {
                "quality": 0.0,
                "price": price,
            },
            "limit_buy": {
                "quality": 0.0,
                "price": 0.0,
            },
            "limit_sell": {
                "quality": 0.0,
                "price": 0.0,
            },
        }

        # -------------------------
        # MARKET BUY
        # -------------------------

        if score >= self.config.minimum_direction_score:

            quality = 0.50

            if timing["state"] == "ENTRY_NOW":
                quality += 0.25

            if "DISCOUNT" in zone:
                quality += 0.10

            if support > 0:

                distance = abs(
                    price - support
                )

                if distance <= atr * 0.75:
                    quality += 0.10

            candidates["buy"]["quality"] = clamp(
                quality,
                0.0,
                1.0,
            )

        # -------------------------
        # MARKET SELL
        # -------------------------

        if score <= -self.config.minimum_direction_score:

            quality = 0.50

            if timing["state"] == "ENTRY_NOW":
                quality += 0.25

            if "PREMIUM" in zone:
                quality += 0.10

            if resistance > 0:

                distance = abs(
                    resistance - price
                )

                if distance <= atr * 0.75:
                    quality += 0.10

            candidates["sell"]["quality"] = clamp(
                quality,
                0.0,
                1.0,
            )

        # -------------------------
        # LIMIT BUY
        # -------------------------

        if score >= self.config.minimum_direction_score:

            limit_price = None

            if support > 0:

                if support < price:
                    limit_price = support

            if limit_price is None:

                limit_price = price - (
                    atr * 0.75
                )

            limit_quality = 0.55

            if "DISCOUNT" in zone:
                limit_quality += 0.15

            if timing["state"] == "WAIT_PULLBACK":
                limit_quality += 0.10

            candidates["limit_buy"] = {
                "quality": clamp(
                    limit_quality,
                    0.0,
                    1.0,
                ),
                "price": round(
                    limit_price,
                    3,
                ),
            }

        # -------------------------
        # LIMIT SELL
        # -------------------------

        if score <= -self.config.minimum_direction_score:

            limit_price = None

            if resistance > 0:

                if resistance > price:
                    limit_price = resistance

            if limit_price is None:

                limit_price = price + (
                    atr * 0.75
                )

            limit_quality = 0.55

            if "PREMIUM" in zone:
                limit_quality += 0.15

            if timing["state"] == "WAIT_PULLBACK":
                limit_quality += 0.10

            candidates["limit_sell"] = {
                "quality": clamp(
                    limit_quality,
                    0.0,
                    1.0,
                ),
                "price": round(
                    limit_price,
                    3,
                ),
            }

        return candidates

    # ========================================================
    # 17. CONFIDENCE
    # ========================================================

    def calculate_confidence(
        self,
        processed: Dict[str, Any],
        regime: Dict[str, Any],
        factors: Dict[str, Dict[str, Any]],
        fusion: Dict[str, Any],
        timing: Dict[str, Any],
        candidates: Dict[str, Any],
    ) -> Dict[str, Any]:

        direction_strength = clamp(
            abs(
                safe_float(
                    fusion["direction_score"]
                )
            ) / 100.0,
            0.0,
            1.0,
        )

        agreement = clamp(
            safe_float(
                fusion["agreement"]
            ),
            0.0,
            1.0,
        )

        conflict = clamp(
            safe_float(
                fusion["conflict"]
            ),
            0.0,
            1.0,
        )

        timing_score = clamp(
            safe_float(
                timing["score"]
            ),
            0.0,
            1.0,
        )

        execution = factors.get(
            "execution",
            {},
        )

        execution_quality = clamp(
            safe_float(
                execution.get(
                    "quality",
                    0.0,
                )
            ),
            0.0,
            1.0,
        )

        exhaustion = factors.get(
            "exhaustion",
            {},
        )

        exhaustion_penalty = abs(
            min(
                safe_float(
                    exhaustion.get(
                        "score",
                        0.0,
                    )
                ),
                0.0,
            )
        )

        location_quality = 0.0

        for key in (
            "buy",
            "sell",
            "limit_buy",
            "limit_sell",
        ):

            location_quality = max(
                location_quality,
                safe_float(
                    candidates[key].get(
                        "quality",
                        0.0,
                    )
                ),
            )

        # Composite confidence.
        confidence = (
            direction_strength * 0.35
            + agreement * 0.20
            + timing_score * 0.15
            + location_quality * 0.15
            + execution_quality * 0.10
            - conflict * 0.10
            - exhaustion_penalty * 0.05
        )

        confidence = clamp(
            confidence,
            0.0,
            0.95,
        )

        return {
            "value": round(
                confidence,
                4,
            ),
            "direction_strength": round(
                direction_strength,
                4,
            ),
            "agreement": round(
                agreement,
                4,
            ),
            "conflict_penalty": round(
                conflict,
                4,
            ),
            "timing": round(
                timing_score,
                4,
            ),
            "location": round(
                location_quality,
                4,
            ),
            "execution": round(
                execution_quality,
                4,
            ),
        }

    # ========================================================
    # 18. FINAL DECISION
    # ========================================================

    def build_decision(
        self,
        processed: Dict[str, Any],
        permission: Dict[str, Any],
        regime: Dict[str, Any],
        factors: Dict[str, Dict[str, Any]],
        fusion: Dict[str, Any],
        timing: Dict[str, Any],
        candidates: Dict[str, Any],
        confidence: Dict[str, Any],
    ) -> Dict[str, Any]:

        score = safe_float(
            fusion["direction_score"]
        )

        conf = safe_float(
            confidence["value"]
        )

        reasons = []

        # ----------------------------------------------------
        # Insufficient direction
        # ----------------------------------------------------

        if abs(score) < self.config.minimum_direction_score:

            return {
                "action": "HOLD",
                "confidence": round(
                    conf,
                    4,
                ),
                "reason": (
                    f"Directional evidence belum cukup "
                    f"(score={score:.1f})"
                ),
                "reasons": [
                    "Direction score di bawah threshold"
                ],
                "risk_flags": self._risk_flags(
                    processed,
                    fusion,
                ),
            }

        # ----------------------------------------------------
        # Conflict too high
        # ----------------------------------------------------

        if fusion["conflict"] >= 0.50:

            return {
                "action": "HOLD",
                "confidence": round(
                    min(conf, 0.55),
                    4,
                ),
                "reason": (
                    "Konflik antar faktor terlalu tinggi"
                ),
                "reasons": [
                    f"Conflict={fusion['conflict']:.2f}"
                ],
                "risk_flags": [
                    "HIGH_FACTOR_CONFLICT"
                ],
            }

        # ----------------------------------------------------
        # Confidence too low
        # ----------------------------------------------------

        if conf < self.config.minimum_confidence:

            return {
                "action": "HOLD",
                "confidence": round(
                    conf,
                    4,
                ),
                "reason": (
                    f"Confidence belum memenuhi threshold "
                    f"({conf:.2f})"
                ),
                "reasons": [
                    f"Direction={score:.1f}",
                    f"Agreement={fusion['agreement']:.2f}",
                    f"Timing={timing['score']:.2f}",
                ],
                "risk_flags": self._risk_flags(
                    processed,
                    fusion,
                ),
            }

        # ----------------------------------------------------
        # BUY side
        # ----------------------------------------------------

        if score >= self.config.minimum_direction_score:

            market_quality = safe_float(
                candidates["buy"]["quality"]
            )

            limit_quality = safe_float(
                candidates["limit_buy"]["quality"]
            )

            if (
                timing["state"] == "ENTRY_NOW"
                and market_quality >= limit_quality
            ):

                action = "BUY"

            else:

                action = "BUY_LIMIT"

        # ----------------------------------------------------
        # SELL side
        # ----------------------------------------------------

        elif score <= -self.config.minimum_direction_score:

            market_quality = safe_float(
                candidates["sell"]["quality"]
            )

            limit_quality = safe_float(
                candidates["limit_sell"]["quality"]
            )

            if (
                timing["state"] == "ENTRY_NOW"
                and market_quality >= limit_quality
            ):

                action = "SELL"

            else:

                action = "SELL_LIMIT"

        else:

            action = "HOLD"

        # ----------------------------------------------------
        # Reasons
        # ----------------------------------------------------

        reasons.append(
            f"Direction score={score:.1f}"
        )

        reasons.append(
            f"Agreement={fusion['agreement']:.2f}"
        )

        reasons.append(
            f"Conflict={fusion['conflict']:.2f}"
        )

        reasons.append(
            f"Regime={regime['name']}"
        )

        reasons.append(
            f"Timing={timing['state']}"
        )

        reasons.append(
            f"Confidence={conf:.2f}"
        )

        # Limit price
        target_price = 0.0

        if action == "BUY_LIMIT":

            target_price = candidates[
                "limit_buy"
            ]["price"]

        elif action == "SELL_LIMIT":

            target_price = candidates[
                "limit_sell"
            ]["price"]

        return {
            "action": action,
            "confidence": round(
                conf,
                4,
            ),
            "target_price": target_price,
            "limit_price": target_price,
            "current_price": safe_float(
                processed.get(
                    "m5_indicators",
                    {},
                ).get(
                    "current_price"
                )
            ),
            "atr": safe_float(
                processed.get(
                    "m5_indicators",
                    {},
                ).get(
                    "atr"
                ),
                1.5,
            ),
            "reason": " | ".join(reasons),
            "reasons": reasons,
            "risk_flags": self._risk_flags(
                processed,
                fusion,
            ),
        }

    # ========================================================
    # REGIME WEIGHTS
    # ========================================================

    def _regime_weights(
        self,
        regime: str,
    ) -> Dict[str, float]:

        if regime == "TRENDING":

            return {
                "macro": 1.10,
                "trend": 1.20,
                "structure": 1.15,
                "momentum": 1.00,
                "flow": 1.00,
                "smc": 0.95,
                "liquidity": 0.85,
                "location": 0.90,
                "exhaustion": 0.80,
                "execution": 1.00,
                "news": 1.00,
            }

        if regime == "TRANSITION":

            return {
                "macro": 1.10,
                "trend": 0.95,
                "structure": 1.10,
                "momentum": 0.90,
                "flow": 1.10,
                "smc": 1.00,
                "liquidity": 1.00,
                "location": 1.10,
                "exhaustion": 1.10,
                "execution": 1.00,
                "news": 1.00,
            }

        if regime == "CHOPPY":

            return {
                "macro": 0.75,
                "trend": 0.70,
                "structure": 0.85,
                "momentum": 0.75,
                "flow": 1.10,
                "smc": 1.10,
                "liquidity": 1.20,
                "location": 1.20,
                "exhaustion": 1.20,
                "execution": 1.10,
                "news": 0.90,
            }

        return {
            "macro": 1.00,
            "trend": 1.00,
            "structure": 1.00,
            "momentum": 1.00,
            "flow": 1.00,
            "smc": 1.00,
            "liquidity": 1.00,
            "location": 1.00,
            "exhaustion": 1.00,
            "execution": 1.00,
                "news": 1.00,
        }

    # ========================================================
    # FACTOR BUILDER
    # ========================================================

    def _factor_result(
        self,
        name: str,
        evidence: List[Evidence],
    ) -> Dict[str, Any]:

        if not evidence:

            return {
                "name": name,
                "score": 0.0,
                "quality": 0.0,
                "reason": "No evidence",
                "evidence": [],
            }

        weighted_sum = 0.0
        weight_sum = 0.0

        for item in evidence:

            weighted_sum += (
                item.score
                * item.quality
                * item.weight
            )

            weight_sum += (
                item.quality
                * item.weight
            )

        if weight_sum > 0:

            score = (
                weighted_sum
                / weight_sum
            )

        else:

            score = 0.0

        quality = clamp(
            weight_sum
            / len(evidence),
            0.0,
            1.0,
        )

        reasons = [
            item.reason
            for item in evidence
        ]

        return {
            "name": name,
            "score": round(
                clamp(score, -1.0, 1.0),
                4,
            ),
            "quality": round(
                quality,
                4,
            ),
            "reason": " | ".join(
                reasons
            ),
            "evidence": [
                {
                    "name": item.name,
                    "score": item.score,
                    "quality": item.quality,
                    "weight": item.weight,
                    "contribution": item.contribution,
                    "reason": item.reason,
                }
                for item in evidence
            ],
        }

    # ========================================================
    # RISK FLAGS
    # ========================================================

    def _risk_flags(
        self,
        processed: Dict[str, Any],
        fusion: Dict[str, Any],
    ) -> List[str]:

        flags = []

        if fusion.get(
            "conflict",
            0,
        ) >= 0.30:

            flags.append(
                "FACTOR_CONFLICT"
            )

        chop = safe_float(
            processed.get(
                "market_regime",
                {},
            ).get(
                "choppiness_index",
                50,
            )
        )

        if chop > 55:

            flags.append(
                "HIGH_CHOP"
            )

        exhaustion = processed.get(
            "candle_exhaustion",
            {},
        )

        if exhaustion.get(
            "exhaustion_detected",
            False,
        ):

            flags.append(
                "CANDLE_EXHAUSTION"
            )

        return flags

    # ========================================================
    # HOLD RESULT
    # ========================================================

    def _hold_result(
        self,
        reason: str,
        risk_flags: List[str],
        permission: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        return {
            "allowed": False,
            "permission": permission or {
                "allowed": False,
            },
            "regime": {},
            "factors": {},
            "fusion": {
                "direction_score": 0.0,
                "buy_evidence": 0.0,
                "sell_evidence": 0.0,
                "agreement": 0.0,
                "conflict": 0.0,
            },
            "timing": {
                "score": 0.0,
                "state": "NO_TIMING",
                "reasons": [],
            },
            "candidates": {},
            "confidence": {
                "value": 0.0,
            },
            "decision": {
                "action": "HOLD",
                "confidence": 0.0,
                "reason": reason,
                "reasons": [reason],
                "risk_flags": risk_flags,
            },
        }


# ============================================================
# SIMPLE FUNCTION API
# ============================================================

_default_scanner = PowerfulLocalAIScanner()


def powerful_local_ai_scanner_v2(
    processed: Dict[str, Any],
) -> Dict[str, Any]:
    return _default_scanner.scan(processed)


# --- Scanner khusus emas: spread diumpan dalam POINT (1 pt = $0.01).
# Spread normal emas 15-60 pt, saat berita 70-150+ pt (riset 2026-10-01),
# jadi batas kripto (45) akan memblokir entry normal. Batas 150 hanya
# menahan kondisi spread benar-benar ekstrem; blackout rollover tetap
# diblokir lewat sesi OFF_PEAK.
_gold_scanner = PowerfulLocalAIScanner(
    ScannerConfig(max_spread_points=150.0)
)


def powerful_local_ai_scanner_xau(
    processed: Dict[str, Any],
) -> Dict[str, Any]:
    return _gold_scanner.scan(processed)


# Backward-compatible entry point consumed by main.py.
powerful_local_ai_scanner = powerful_local_ai_scanner_v2