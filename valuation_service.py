from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any
import math

import numpy as np
import pandas as pd
import yfinance as yf


ERP = 0.045
TERMINAL_GROWTH = 0.025
DCF_YEARS = 5


def _num(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if math.isfinite(value) else None


def _clamp(
    value: float,
    low: float,
    high: float,
) -> float:
    return max(
        low,
        min(high, value),
    )


def _median(
    values: list[float | None],
) -> float | None:
    clean = [
        value
        for value in values
        if value is not None
        and math.isfinite(value)
    ]

    return (
        float(median(clean))
        if clean
        else None
    )


# =========================================================
# MARKET DATA
# =========================================================

def _history(
    ticker: str,
) -> pd.DataFrame:

    frame = yf.download(
        ticker,
        period="1y",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if frame.empty:
        raise RuntimeError(
            f"No market history returned for {ticker}."
        )

    if isinstance(
        frame.columns,
        pd.MultiIndex,
    ):
        frame.columns = (
            frame.columns
            .get_level_values(0)
        )

    return frame


def _fast_value(
    fast_info: Any,
    key: str,
) -> float | None:

    try:
        return _num(
            fast_info[key]
        )

    except Exception:
        try:
            return _num(
                getattr(
                    fast_info,
                    key,
                )
            )
        except Exception:
            return None


def _latest_quote(
    ticker: str,
    history: pd.DataFrame,
) -> tuple[
    float | None,
    float | None,
    str,
]:

    try:
        fast_info = (
            yf.Ticker(ticker)
            .fast_info
        )

        last_price = _fast_value(
            fast_info,
            "last_price",
        )

        previous_close = _fast_value(
            fast_info,
            "previous_close",
        )

        if last_price is not None:
            return (
                last_price,
                previous_close,
                "Yahoo Finance fast_info",
            )

    except Exception:
        pass

    close = pd.to_numeric(
        history["Close"],
        errors="coerce",
    ).dropna()

    current = (
        _num(close.iloc[-1])
        if not close.empty
        else None
    )

    previous = (
        _num(close.iloc[-2])
        if len(close) >= 2
        else None
    )

    return (
        current,
        previous,
        "Yahoo Finance daily close",
    )


def _risk_free_rate() -> float:

    try:
        frame = yf.download(
            "^TNX",
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if isinstance(
            frame.columns,
            pd.MultiIndex,
        ):
            frame.columns = (
                frame.columns
                .get_level_values(0)
            )

        close = (
            pd.to_numeric(
                frame["Close"],
                errors="coerce",
            )
            .dropna()
        )

        if not close.empty:
            value = _num(
                close.iloc[-1]
            )

            if (
                value is not None
                and 0 < value < 20
            ):
                return (
                    value / 100.0
                )

    except Exception:
        pass

    # fallback only
    return 0.0425


# =========================================================
# TECHNICAL ENGINE
# =========================================================

def _technicals(
    history: pd.DataFrame,
) -> dict[
    str,
    float | None,
]:

    close = pd.to_numeric(
        history["Close"],
        errors="coerce",
    ).dropna()

    high = pd.to_numeric(
        history["High"],
        errors="coerce",
    ).dropna()

    low = pd.to_numeric(
        history["Low"],
        errors="coerce",
    ).dropna()

    if close.empty:
        raise RuntimeError(
            "Price history contains no usable prices."
        )

    result: dict[
        str,
        float | None,
    ] = {}

    # Moving averages
    for window in (
        20,
        50,
        120,
        200,
    ):
        result[
            f"ma{window}"
        ] = (
            _num(
                close
                .rolling(window)
                .mean()
                .iloc[-1]
            )
            if len(close) >= window
            else None
        )

    # Historical volatility
    daily_returns = (
        close
        .pct_change()
        .dropna()
    )

    result[
        "volatility_annualized"
    ] = (
        _num(
            daily_returns.std()
            * np.sqrt(252)
        )
        if not daily_returns.empty
        else None
    )

    # ATR
    previous_close = (
        close.shift(1)
    )

    true_range = pd.concat(
        [
            high - low,

            (
                high
                - previous_close
            ).abs(),

            (
                low
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result[
        "atr14"
    ] = (
        _num(
            true_range
            .rolling(14)
            .mean()
            .iloc[-1]
        )
        if len(
            true_range.dropna()
        ) >= 14
        else None
    )

    result[
        "fifty_two_week_low"
    ] = _num(
        low.tail(252).min()
    )

    result[
        "fifty_two_week_high"
    ] = _num(
        high.tail(252).max()
    )

    # Robust support/resistance.
    #
    # Instead of using one absolute extreme,
    # use recent price quantiles so one strange day
    # does not distort the level.

    result[
        "support_1"
    ] = (
        _num(
            low
            .tail(63)
            .quantile(0.20)
        )
        if len(low) >= 20
        else None
    )

    result[
        "support_2"
    ] = (
        _num(
            low
            .tail(126)
            .quantile(0.15)
        )
        if len(low) >= 40
        else None
    )

    result[
        "resistance_1"
    ] = (
        _num(
            high
            .tail(63)
            .quantile(0.80)
        )
        if len(high) >= 20
        else None
    )

    result[
        "resistance_2"
    ] = (
        _num(
            high
            .tail(126)
            .quantile(0.85)
        )
        if len(high) >= 40
        else None
    )

    return result


# =========================================================
# DCF ENGINE
# =========================================================

def _growth(
    info: dict[
        str,
        Any,
    ],
) -> float:

    values: list[
        float
    ] = []

    for key in (
        "revenueGrowth",
        "earningsGrowth",
        "earningsQuarterlyGrowth",
    ):
        value = _num(
            info.get(key)
        )

        if (
            value is not None
            and -0.5 < value < 1.5
        ):
            values.append(
                value
            )

    raw_growth = (
        float(
            median(values)
        )
        if values
        else 0.05
    )

    return _clamp(
        raw_growth,
        -0.05,
        0.20,
    )


def _dcf(
    info: dict[
        str,
        Any,
    ],
    risk_free: float,
) -> tuple[
    float | None,
    dict[str, float],
    list[str],
]:

    notes: list[
        str
    ] = []

    free_cash_flow = _num(
        info.get(
            "freeCashflow"
        )
    )

    shares = _num(
        info.get(
            "sharesOutstanding"
        )
    )

    cash = (
        _num(
            info.get(
                "totalCash"
            )
        )
        or 0.0
    )

    debt = (
        _num(
            info.get(
                "totalDebt"
            )
        )
        or 0.0
    )

    beta = _num(
        info.get("beta")
    )

    if beta is None:
        beta = 1.0

        notes.append(
            "Beta unavailable; "
            "beta = 1.0 fallback used."
        )

    discount_rate = _clamp(
        (
            risk_free
            + beta * ERP
        ),
        0.07,
        0.15,
    )

    stage1_growth = (
        _growth(info)
    )

    terminal_growth = min(
        TERMINAL_GROWTH,
        discount_rate - 0.02,
    )

    assumptions = {
        "discount_rate":
        discount_rate,

        "stage1_growth":
        stage1_growth,

        "terminal_growth":
        terminal_growth,
    }

    if (
        free_cash_flow is None
        or shares is None
        or shares <= 0
        or free_cash_flow <= 0
    ):
        notes.append(
            "DCF unavailable because usable "
            "positive free cash flow or "
            "share count was missing."
        )

        return (
            None,
            assumptions,
            notes,
        )

    projected: list[
        float
    ] = []

    cash_flow = (
        free_cash_flow
    )

    for year in range(
        1,
        DCF_YEARS + 1,
    ):
        fade = (
            year
            / DCF_YEARS
        )

        year_growth = (
            stage1_growth
            * (1 - fade)
            + terminal_growth
            * fade
        )

        cash_flow *= (
            1 + year_growth
        )

        projected.append(
            cash_flow
        )

    pv_fcfs = sum(
        cash_flow
        / (
            (1 + discount_rate)
            ** year
        )
        for (
            year,
            cash_flow,
        ) in enumerate(
            projected,
            start=1,
        )
    )

    terminal_value = (
        projected[-1]
        * (
            1 + terminal_growth
        )
        / (
            discount_rate
            - terminal_growth
        )
    )

    pv_terminal = (
        terminal_value
        / (
            (1 + discount_rate)
            ** DCF_YEARS
        )
    )

    equity_value = (
        pv_fcfs
        + pv_terminal
        + cash
        - debt
    )

    fair_value = (
        equity_value
        / shares
    )

    if (
        not math.isfinite(
            fair_value
        )
        or fair_value <= 0
    ):
        notes.append(
            "DCF produced a "
            "non-usable value."
        )

        return (
            None,
            assumptions,
            notes,
        )

    return (
        float(fair_value),
        assumptions,
        notes,
    )


# =========================================================
# FAIR VALUE MODEL
# =========================================================

def _fair_value_model(
    dcf: float | None,
    analyst: float | None,
) -> tuple[
    float | None,
    float | None,
    float | None,
    str,
    float | None,
    list[str],
]:

    if (
        dcf is None
        and analyst is None
    ):
        return (
            None,
            None,
            None,
            "UNAVAILABLE",
            None,
            [
                "No usable fair-value input."
            ],
        )

    # Only one model is available.
    if (
        dcf is None
        or analyst is None
    ):
        value = (
            dcf
            if dcf is not None
            else analyst
        )

        source = (
            "DCF"
            if dcf is not None
            else "analyst consensus"
        )

        return (
            value,
            value * 0.75,
            value * 1.25,
            "LOW",
            None,
            [
                f"Only {source} was available; "
                f"±25% fair-value range is shown."
            ],
        )

    low_model = min(
        dcf,
        analyst,
    )

    high_model = max(
        dcf,
        analyst,
    )

    ratio = (
        high_model
        / low_model
        if low_model > 0
        else float("inf")
    )

    # Small disagreement
    if ratio <= 1.35:
        dcf_weight = 0.60
        analyst_weight = 0.40
        confidence = "HIGH"
        base_margin = 0.15

    # Moderate disagreement
    elif ratio <= 1.75:
        dcf_weight = 0.70
        analyst_weight = 0.30
        confidence = "MEDIUM"
        base_margin = 0.22

    # Large disagreement
    else:
        dcf_weight = 0.80
        analyst_weight = 0.20
        confidence = "LOW"
        base_margin = 0.30

    fair_value = (
        dcf_weight * dcf
        + analyst_weight * analyst
    )

    dispersion = (
        abs(
            analyst - dcf
        )
        / fair_value
    )

    margin = max(
        base_margin,
        min(
            dispersion / 2.0,
            0.35,
        ),
    )

    fair_low = (
        fair_value
        * (
            1 - margin
        )
    )

    fair_high = (
        fair_value
        * (
            1 + margin
        )
    )

    notes = [
        (
            f"DCF weight {dcf_weight:.0%}, "
            f"analyst-consensus weight "
            f"{analyst_weight:.0%}. "
            f"Model disagreement implies "
            f"{confidence} confidence."
        )
    ]

    return (
        fair_value,
        fair_low,
        fair_high,
        confidence,
        dispersion * 100,
        notes,
    )


# =========================================================
# VALUATION ZONES
# =========================================================

def _zones(
    fair_value: float | None,
    fair_low: float | None,
    fair_high: float | None,
) -> dict[
    str,
    float | None,
]:

    if (
        fair_value is None
        or fair_low is None
        or fair_high is None
    ):
        return {
            key: None
            for key in (
                "deep_value_max",
                "undervalued_min",
                "undervalued_max",
                "fair_value_min",
                "fair_value_max",
                "expensive_min",
                "expensive_max",
                "rich_min",
            )
        }

    deep_value_max = (
        fair_low * 0.85
    )

    expensive_max = (
        fair_high * 1.15
    )

    return {
        "deep_value_max":
        deep_value_max,

        "undervalued_min":
        deep_value_max,

        "undervalued_max":
        fair_low,

        "fair_value_min":
        fair_low,

        "fair_value_max":
        fair_high,

        "expensive_min":
        fair_high,

        "expensive_max":
        expensive_max,

        "rich_min":
        expensive_max,
    }


def _status(
    price: float | None,
    zones: dict[
        str,
        float | None,
    ],
) -> str:

    if (
        price is None
        or zones[
            "fair_value_min"
        ] is None
    ):
        return "UNAVAILABLE"

    if (
        price
        < zones[
            "deep_value_max"
        ]
    ):
        return "DEEP VALUE"

    if (
        price
        < zones[
            "undervalued_max"
        ]
    ):
        return "UNDERVALUED"

    if (
        price
        <= zones[
            "fair_value_max"
        ]
    ):
        return "FAIR VALUE"

    if (
        price
        <= zones[
            "expensive_max"
        ]
    ):
        return "EXPENSIVE"

    return "RICH"


# =========================================================
# ENTRY / TRIM ENGINE
# =========================================================

def _overlap(
    low_a: float | None,
    high_a: float | None,
    low_b: float | None,
    high_b: float | None,
) -> tuple[float | None, float | None]:

    if None in (
        low_a,
        high_a,
        low_b,
        high_b,
    ):
        return None, None

    low = max(
        float(low_a),
        float(low_b),
    )

    high = min(
        float(high_a),
        float(high_b),
    )

    if low > high:
        return None, None

    return low, high


def _trade_bands(
    fair_value: float | None,
    zones: dict[str, float | None],
    technical: dict[str, float | None],
    current_price: float | None,
) -> dict[str, Any]:

    if (
        fair_value is None
        or zones.get("fair_value_min") is None
        or zones.get("fair_value_max") is None
    ):
        return {
            "valuation_entry_low": None,
            "valuation_entry_high": None,
            "technical_entry_low": None,
            "technical_entry_high": None,
            "entry_zone_low": None,
            "entry_zone_high": None,
            "entry_status": "UNAVAILABLE",

            "valuation_trim_low": None,
            "valuation_trim_high": None,
            "technical_trim_low": None,
            "technical_trim_high": None,
            "trim_zone_low": None,
            "trim_zone_high": None,
            "trim_status": "UNAVAILABLE",
        }

    atr = (
        technical.get("atr14")
        or 0.0
    )

    reference_price = (
        current_price
        if current_price is not None
        else fair_value
    )

    band_width = max(
        reference_price * 0.015,
        atr * 0.75,
    )

    # =====================================================
    # VALUATION ENTRY ZONE
    # =====================================================

    valuation_entry_low = zones[
        "undervalued_min"
    ]

    valuation_entry_high = zones[
        "fair_value_min"
    ]

    # =====================================================
    # TECHNICAL ENTRY ZONE
    # =====================================================

    technical_candidates = [
        value
        for value in (
            technical.get("support_1"),
            technical.get("support_2"),
            technical.get("ma120"),
            technical.get("ma200"),
        )
        if (
            value is not None
            and current_price is not None
            and current_price * 0.55
            <= value
            <= current_price * 1.02
        )
    ]

    technical_anchor = _median(
        technical_candidates
    )

    if technical_anchor is not None:

        technical_entry_low = max(
            technical_anchor
            - band_width,
            0.0,
        )

        technical_entry_high = min(
            technical_anchor
            + band_width,
            current_price
            if current_price is not None
            else technical_anchor + band_width,
        )

    else:

        technical_entry_low = None
        technical_entry_high = None

    (
        convergent_entry_low,
        convergent_entry_high,
    ) = _overlap(
        valuation_entry_low,
        valuation_entry_high,
        technical_entry_low,
        technical_entry_high,
    )

    entry_status = (
        "CONVERGENT"
        if convergent_entry_low is not None
        else "NO CONVERGENCE"
    )

    # =====================================================
    # VALUATION TRIM / REASSESS ZONE
    # =====================================================

    valuation_trim_low = zones[
        "expensive_min"
    ]

    valuation_trim_high = zones[
        "rich_min"
    ]

    # =====================================================
    # TECHNICAL RESISTANCE ZONE
    # =====================================================

    resistance_candidates = [
        value
        for value in (
            technical.get("resistance_1"),
            technical.get("resistance_2"),
        )
        if (
            value is not None
            and current_price is not None
            and current_price * 0.90
            <= value
            <= current_price * 1.50
        )
    ]

    resistance_anchor = _median(
        resistance_candidates
    )

    if resistance_anchor is not None:

        technical_trim_low = max(
            resistance_anchor
            - band_width,
            0.0,
        )

        technical_trim_high = (
            resistance_anchor
            + band_width
        )

    else:

        technical_trim_low = None
        technical_trim_high = None

    (
        convergent_trim_low,
        convergent_trim_high,
    ) = _overlap(
        valuation_trim_low,
        valuation_trim_high,
        technical_trim_low,
        technical_trim_high,
    )

    trim_status = (
        "CONVERGENT"
        if convergent_trim_low is not None
        else "NO CONVERGENCE"
    )

    return {
        "valuation_entry_low":
        _num(valuation_entry_low),

        "valuation_entry_high":
        _num(valuation_entry_high),

        "technical_entry_low":
        _num(technical_entry_low),

        "technical_entry_high":
        _num(technical_entry_high),

        "entry_zone_low":
        _num(convergent_entry_low),

        "entry_zone_high":
        _num(convergent_entry_high),

        "entry_status":
        entry_status,

        "valuation_trim_low":
        _num(valuation_trim_low),

        "valuation_trim_high":
        _num(valuation_trim_high),

        "technical_trim_low":
        _num(technical_trim_low),

        "technical_trim_high":
        _num(technical_trim_high),

        "trim_zone_low":
        _num(convergent_trim_low),

        "trim_zone_high":
        _num(convergent_trim_high),

        "trim_status":
        trim_status,
    }



# =========================================================
# MAIN
# =========================================================

def analyze_valuation(
    ticker: str,
) -> dict[
    str,
    Any,
]:

    ticker = (
        str(ticker)
        .strip()
        .upper()
    )

    if not ticker:
        raise ValueError(
            "Ticker is required."
        )

    history = (
        _history(ticker)
    )

    try:
        info = (
            yf.Ticker(ticker)
            .get_info()
        )

    except Exception:
        info = {}

    if not isinstance(
        info,
        dict,
    ):
        info = {}

    (
        current_price,
        previous_close,
        quote_source,
    ) = _latest_quote(
        ticker,
        history,
    )

    day_change_pct = (
        (
            current_price
            / previous_close
            - 1
        )
        * 100
        if (
            current_price is not None
            and previous_close
            not in (
                None,
                0,
            )
        )
        else None
    )

    technical = (
        _technicals(
            history
        )
    )

    (
        dcf_value,
        assumptions,
        dcf_notes,
    ) = _dcf(
        info,
        _risk_free_rate(),
    )

    analyst_target = (
        _num(
            info.get(
                "targetMeanPrice"
            )
        )
    )

    (
        fair_value,
        fair_low,
        fair_high,
        confidence,
        dispersion_pct,
        blend_notes,
    ) = _fair_value_model(
        dcf_value,
        analyst_target,
    )

    zones = _zones(
        fair_value,
        fair_low,
        fair_high,
    )

    trade_bands = _trade_bands(
        fair_value=fair_value,
        zones=zones,
        technical=technical,
        current_price=current_price,
    )

    upside_downside_pct = (
        (
            fair_value
            / current_price
            - 1
        )
        * 100
        if (
            fair_value is not None
            and current_price
            not in (
                None,
                0,
            )
        )
        else None
    )

    notes = [
        *dcf_notes,
        *blend_notes,

        (
            "Fair-value range widens when "
            "DCF and analyst consensus disagree."
        ),

        (
            "Support/resistance uses recent "
            "price quantiles plus MA120/MA200 "
            "and ATR."
        ),

        (
            "Entry and Trim/Reassess bands "
            "are research bands, not automatic "
            "trade instructions."
        ),

        (
            f"Quote source: {quote_source}. "
            f"Yahoo Finance data may be "
            f"delayed or incomplete."
        ),
    ]

    return {
        "ticker":
        ticker,

        "timestamp_utc":
        datetime
        .now(
            timezone.utc
        )
        .isoformat(),

        "quote_source":
        quote_source,

        # Market
        "current_price":
        current_price,

        "previous_close":
        previous_close,

        "day_change_pct":
        _num(
            day_change_pct
        ),

        # Valuation
        "fair_value":
        _num(
            fair_value
        ),

        "fair_value_low":
        _num(
            fair_low
        ),

        "fair_value_high":
        _num(
            fair_high
        ),

        "valuation_confidence":
        confidence,

        "model_dispersion_pct":
        _num(
            dispersion_pct
        ),

        "dcf_fair_value":
        _num(
            dcf_value
        ),

        "analyst_target":
        _num(
            analyst_target
        ),

        "upside_downside_pct":
        _num(
            upside_downside_pct
        ),

        "valuation_status":
        _status(
            current_price,
            zones,
        ),

        # Zones
        **{
            key:
            _num(value)

            for (
                key,
                value,
            ) in zones.items()
        },

        # -----------------------------------------------
        # PRICE MAP
        # -----------------------------------------------

        # Valuation-only accumulation range
        "valuation_entry_zone_low":
        trade_bands["valuation_entry_low"],

        "valuation_entry_zone_high":
        trade_bands["valuation_entry_high"],

        # Technical support / accumulation range
        "technical_entry_zone_low":
        trade_bands["technical_entry_low"],

        "technical_entry_zone_high":
        trade_bands["technical_entry_high"],

        # Only populated when valuation + technical overlap
        "entry_zone_low":
        trade_bands["entry_zone_low"],

        "entry_zone_high":
        trade_bands["entry_zone_high"],

        "entry_zone_status":
        trade_bands["entry_status"],

        # Valuation-only expensive / trim range
        "valuation_trim_zone_low":
        trade_bands["valuation_trim_low"],

        "valuation_trim_zone_high":
        trade_bands["valuation_trim_high"],

        # Technical resistance range
        "technical_trim_zone_low":
        trade_bands["technical_trim_low"],

        "technical_trim_zone_high":
        trade_bands["technical_trim_high"],

        # Only populated when valuation + technical overlap
        "trim_zone_low":
        trade_bands["trim_zone_low"],

        "trim_zone_high":
        trade_bands["trim_zone_high"],

        "trim_zone_status":
        trade_bands["trim_status"],

        # Technical
        "support_1":
        _num(
            technical.get(
                "support_1"
            )
        ),

        "support_2":
        _num(
            technical.get(
                "support_2"
            )
        ),

        "resistance_1":
        _num(
            technical.get(
                "resistance_1"
            )
        ),

        "resistance_2":
        _num(
            technical.get(
                "resistance_2"
            )
        ),

        "ma20":
        _num(
            technical.get(
                "ma20"
            )
        ),

        "ma50":
        _num(
            technical.get(
                "ma50"
            )
        ),

        "ma120":
        _num(
            technical.get(
                "ma120"
            )
        ),

        "ma200":
        _num(
            technical.get(
                "ma200"
            )
        ),

        "atr14":
        _num(
            technical.get(
                "atr14"
            )
        ),

        "volatility_annualized":
        _num(
            technical.get(
                "volatility_annualized"
            )
        ),

        "fifty_two_week_low":
        _num(
            technical.get(
                "fifty_two_week_low"
            )
        ),

        "fifty_two_week_high":
        _num(
            technical.get(
                "fifty_two_week_high"
            )
        ),

        # DCF assumptions
        "discount_rate":
        _num(
            assumptions.get(
                "discount_rate"
            )
        ),

        "stage1_growth":
        _num(
            assumptions.get(
                "stage1_growth"
            )
        ),

        "terminal_growth":
        _num(
            assumptions.get(
                "terminal_growth"
            )
        ),

        "notes":
        notes,
    }
