from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from yfinance import EquityQuery


# ---------------------------------------------------------
# INVESTMENT UNIVERSES
# ---------------------------------------------------------

UNIVERSE_URLS = {
    "S&P 500": (
        "https://en.wikipedia.org/wiki/"
        "List_of_S%26P_500_companies"
    ),
    "NASDAQ 100": (
        "https://en.wikipedia.org/wiki/Nasdaq-100"
    ),
    "Dow Jones": (
        "https://en.wikipedia.org/wiki/"
        "Dow_Jones_Industrial_Average"
    ),
}


# ---------------------------------------------------------
# BASE STRATEGY WEIGHTS
# ---------------------------------------------------------

STYLE_WEIGHTS = {
    "Balanced": {
        "valuation": 0.25,
        "growth": 0.25,
        "quality": 0.25,
        "momentum": 0.15,
        "risk": 0.10,
    },
    "Value": {
        "valuation": 0.45,
        "growth": 0.15,
        "quality": 0.25,
        "momentum": 0.05,
        "risk": 0.10,
    },
    "Growth": {
        "valuation": 0.10,
        "growth": 0.45,
        "quality": 0.25,
        "momentum": 0.10,
        "risk": 0.10,
    },
    "Quality": {
        "valuation": 0.15,
        "growth": 0.15,
        "quality": 0.45,
        "momentum": 0.10,
        "risk": 0.15,
    },
    "Momentum": {
        "valuation": 0.05,
        "growth": 0.15,
        "quality": 0.15,
        "momentum": 0.50,
        "risk": 0.15,
    },
}


# ---------------------------------------------------------
# SYMBOL HELPERS
# ---------------------------------------------------------

def _normalize_symbol(symbol: str) -> str:
    """
    Convert index constituent symbols into Yahoo-compatible symbols.

    Example:
    BRK.B -> BRK-B
    """

    return (
        str(symbol)
        .strip()
        .upper()
        .replace(".", "-")
    )


def _download_html(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 EquityLab/1.0"
            )
        },
        timeout=20,
    )

    response.raise_for_status()

    return response.text


def _find_symbol_column(
    table: pd.DataFrame,
) -> str | None:

    candidates = {
        "symbol",
        "ticker",
        "ticker symbol",
        "company symbol",
    }

    for column in table.columns:

        label = (
            str(column)
            .strip()
            .lower()
        )

        if label in candidates:
            return column

    return None


# ---------------------------------------------------------
# UNIVERSE CONSTITUENTS
# ---------------------------------------------------------

def get_universe_symbols(
    universe: str,
) -> list[str]:

    if universe not in UNIVERSE_URLS:
        raise ValueError(
            f"Unsupported universe: {universe}"
        )

    html = _download_html(
        UNIVERSE_URLS[universe]
    )

    tables = pd.read_html(
        StringIO(html)
    )

    for table in tables:

        symbol_column = _find_symbol_column(
            table
        )

        if symbol_column is None:
            continue

        symbols = [
            _normalize_symbol(value)
            for value
            in table[symbol_column]
            .dropna()
            .tolist()
        ]

        if (
            universe == "S&P 500"
            and len(symbols) >= 450
        ):
            return sorted(set(symbols))

        if (
            universe == "NASDAQ 100"
            and 90 <= len(symbols) <= 110
        ):
            return sorted(set(symbols))

        if (
            universe == "Dow Jones"
            and 25 <= len(symbols) <= 35
        ):
            return sorted(set(symbols))

    raise RuntimeError(
        f"Could not locate a constituent table "
        f"for {universe}."
    )


# ---------------------------------------------------------
# YAHOO SCREENER
# ---------------------------------------------------------

def _base_us_query(
    extra: list[EquityQuery],
) -> EquityQuery:

    return EquityQuery(
        "and",
        [
            EquityQuery(
                "eq",
                [
                    "region",
                    "us",
                ],
            ),

            EquityQuery(
                "is-in",
                [
                    "exchange",
                    "NMS",
                    "NYQ",
                    "NGM",
                    "NCM",
                ],
            ),

            EquityQuery(
                "gte",
                [
                    "intradaymarketcap",
                    2_000_000_000,
                ],
            ),

            *extra,
        ],
    )


def _symbols_from_screen(
    query: EquityQuery,
    sort_field: str,
    sort_asc: bool,
    size: int = 100,
) -> list[str]:

    response = yf.screen(
        query,
        size=size,
        sortField=sort_field,
        sortAsc=sort_asc,
    )

    quotes = (
        response.get("quotes", [])
        if isinstance(response, dict)
        else []
    )

    symbols: list[str] = []

    for quote in quotes:

        if not isinstance(
            quote,
            dict,
        ):
            continue

        symbol = quote.get(
            "symbol"
        )

        if symbol:
            symbols.append(
                _normalize_symbol(
                    symbol
                )
            )

    return symbols


# ---------------------------------------------------------
# MULTI-FACTOR CANDIDATE POOL
# ---------------------------------------------------------

def _screen_candidate_pool(
    universe_symbols: list[str],
    max_candidates: int = 60,
) -> list[str]:

    universe_set = set(
        universe_symbols
    )

    screens = [
        # Value
        (
            _base_us_query(
                [
                    EquityQuery(
                        "btwn",
                        [
                            "peratio.lasttwelvemonths",
                            1,
                            40,
                        ],
                    )
                ]
            ),
            "peratio.lasttwelvemonths",
            True,
        ),

        # Growth
        (
            _base_us_query(
                [
                    EquityQuery(
                        "gte",
                        [
                            "totalrevenues1yrgrowth."
                            "lasttwelvemonths",
                            5,
                        ],
                    )
                ]
            ),
            "totalrevenues1yrgrowth."
            "lasttwelvemonths",
            False,
        ),

        # Quality
        (
            _base_us_query(
                [
                    EquityQuery(
                        "gte",
                        [
                            "returnonequity."
                            "lasttwelvemonths",
                            10,
                        ],
                    )
                ]
            ),
            "returnonequity."
            "lasttwelvemonths",
            False,
        ),

        # Momentum
        (
            _base_us_query([]),
            "fiftytwowkpercentchange",
            False,
        ),

        # Lower beta / risk
        (
            _base_us_query(
                [
                    EquityQuery(
                        "btwn",
                        [
                            "beta",
                            0,
                            2.5,
                        ],
                    )
                ]
            ),
            "beta",
            True,
        ),
    ]

    screened_lists: list[
        list[str]
    ] = []

    for (
        query,
        sort_field,
        sort_asc,
    ) in screens:

        try:
            symbols = (
                _symbols_from_screen(
                    query,
                    sort_field,
                    sort_asc,
                    size=100,
                )
            )

        except Exception:
            symbols = []

        filtered = [
            symbol
            for symbol in symbols
            if symbol in universe_set
        ]

        screened_lists.append(
            filtered
        )

    # Round-robin:
    # prevents one factor from dominating
    # the entire candidate pool.

    ordered: list[str] = []

    max_len = max(
        (
            len(items)
            for items in screened_lists
        ),
        default=0,
    )

    for index in range(
        max_len
    ):

        for items in screened_lists:

            if index >= len(items):
                continue

            symbol = items[index]

            if symbol not in ordered:
                ordered.append(
                    symbol
                )

            if (
                len(ordered)
                >= max_candidates
            ):
                return ordered

    return ordered


# ---------------------------------------------------------
# FALLBACK PRICE FILTER
# ---------------------------------------------------------

def _fallback_price_candidates(
    universe_symbols: list[str],
    max_candidates: int = 60,
) -> list[str]:

    data = yf.download(
        tickers=universe_symbols,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )

    if data.empty:
        return universe_symbols[
            :max_candidates
        ]

    try:
        close = data["Close"]

    except Exception:
        return universe_symbols[
            :max_candidates
        ]

    if isinstance(
        close,
        pd.Series,
    ):
        close = close.to_frame()

    scores: dict[
        str,
        float,
    ] = {}

    for symbol in close.columns:

        series = pd.to_numeric(
            close[symbol],
            errors="coerce",
        ).dropna()

        if len(series) < 130:
            continue

        ret_6m = (
            series.iloc[-1]
            / series.iloc[-126]
            - 1
        )

        volatility = (
            series
            .pct_change()
            .dropna()
            .std()
            * np.sqrt(252)
        )

        if (
            pd.notna(ret_6m)
            and pd.notna(volatility)
        ):
            scores[
                _normalize_symbol(
                    symbol
                )
            ] = float(
                ret_6m
                - 0.25
                * volatility
            )

    ranked = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    return ranked[
        :max_candidates
    ]


# ---------------------------------------------------------
# FUNDAMENTAL DATA
# ---------------------------------------------------------

def _fetch_info(
    symbol: str,
) -> dict[str, Any]:

    try:
        info = (
            yf.Ticker(symbol)
            .get_info()
        )

    except Exception:
        return {
            "symbol": symbol
        }

    if not isinstance(
        info,
        dict,
    ):
        return {
            "symbol": symbol
        }

    return {
        "symbol": symbol,

        "name": (
            info.get("shortName")
            or info.get("longName")
            or symbol
        ),

        "sector": (
            info.get("sector")
            or ""
        ),

        "market_cap": (
            info.get("marketCap")
        ),

        "trailing_pe": (
            info.get("trailingPE")
        ),

        "price_to_book": (
            info.get("priceToBook")
        ),

        "ev_to_ebitda": (
            info.get(
                "enterpriseToEbitda"
            )
        ),

        "revenue_growth": (
            info.get(
                "revenueGrowth"
            )
        ),

        "earnings_growth": (
            info.get(
                "earningsGrowth"
            )
        ),

        "return_on_equity": (
            info.get(
                "returnOnEquity"
            )
        ),

        "profit_margin": (
            info.get(
                "profitMargins"
            )
        ),

        "debt_to_equity": (
            info.get(
                "debtToEquity"
            )
        ),

        "beta": (
            info.get("beta")
        ),
    }


def _fetch_fundamentals(
    symbols: list[str],
    max_workers: int = 6,
) -> pd.DataFrame:

    rows: list[
        dict[str, Any]
    ] = []

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {
            executor.submit(
                _fetch_info,
                symbol,
            ): symbol

            for symbol
            in symbols
        }

        for future in as_completed(
            futures
        ):

            try:
                rows.append(
                    future.result()
                )

            except Exception:
                rows.append(
                    {
                        "symbol":
                        futures[future]
                    }
                )

    frame = pd.DataFrame(
        rows
    )

    if frame.empty:
        return frame

    return (
        frame
        .drop_duplicates(
            "symbol"
        )
        .reset_index(
            drop=True
        )
    )


# ---------------------------------------------------------
# PRICE / TECHNICAL METRICS
# ---------------------------------------------------------

def _price_metrics(
    symbols: list[str],
) -> pd.DataFrame:

    if not symbols:
        return pd.DataFrame()

    data = yf.download(
        tickers=symbols,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )

    if data.empty:
        return pd.DataFrame(
            {
                "symbol":
                symbols
            }
        )

    try:
        close = data["Close"]

    except Exception:
        return pd.DataFrame(
            {
                "symbol":
                symbols
            }
        )

    if isinstance(
        close,
        pd.Series,
    ):
        close = close.to_frame(
            name=symbols[0]
        )

    rows: list[
        dict[str, Any]
    ] = []

    for symbol in symbols:

        if symbol not in close.columns:

            rows.append(
                {
                    "symbol":
                    symbol
                }
            )

            continue

        series = pd.to_numeric(
            close[symbol],
            errors="coerce",
        ).dropna()

        row: dict[
            str,
            Any,
        ] = {
            "symbol":
            symbol
        }

        if len(series) >= 22:

            row["return_1m"] = (
                series.iloc[-1]
                / series.iloc[-22]
                - 1
            )

        if len(series) >= 127:

            row["return_6m"] = (
                series.iloc[-1]
                / series.iloc[-127]
                - 1
            )

        if len(series) >= 200:

            row["return_1y"] = (
                series.iloc[-1]
                / series.iloc[0]
                - 1
            )

            daily_returns = (
                series
                .pct_change()
                .dropna()
            )

            row["volatility"] = (
                daily_returns.std()
                * np.sqrt(252)
            )

            ma120 = (
                series
                .rolling(120)
                .mean()
            )

            if (
                ma120.notna().sum()
                >= 21
            ):

                row[
                    "ma120_slope_1m"
                ] = (
                    ma120.iloc[-1]
                    / ma120.iloc[-22]
                    - 1
                )

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


# ---------------------------------------------------------
# SCORING HELPERS
# ---------------------------------------------------------

def _numeric(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:

    if column not in frame:

        return pd.Series(
            np.nan,
            index=frame.index,
            dtype="float64",
        )

    return pd.to_numeric(
        frame[column],
        errors="coerce",
    )


def _percentile_score(
    values: pd.Series,
    higher_is_better: bool,
) -> pd.Series:

    values = pd.to_numeric(
        values,
        errors="coerce",
    )

    if (
        values.notna().sum()
        < 2
    ):

        return pd.Series(
            50.0,
            index=values.index,
        )

    ranks = (
        values
        .rank(
            pct=True,
            method="average",
        )
        * 100.0
    )

    if not higher_is_better:
        ranks = (
            100.0
            - ranks
        )

    return ranks.fillna(
        50.0
    )


def _mean_available(
    series_list: list[
        pd.Series
    ],
) -> pd.Series:

    frame = pd.concat(
        series_list,
        axis=1,
    )

    return (
        frame
        .mean(
            axis=1,
            skipna=True,
        )
        .fillna(
            50.0
        )
    )


# ---------------------------------------------------------
# USER-PREFERENCE WEIGHTS
# ---------------------------------------------------------

def _adjust_weights(
    style: str,
    horizon: str,
    risk_tolerance: str,
    enabled_factors: dict[
        str,
        bool,
    ],
) -> dict[str, float]:

    weights = (
        STYLE_WEIGHTS
        .get(
            style,
            STYLE_WEIGHTS[
                "Balanced"
            ],
        )
        .copy()
    )

    horizon_lower = (
        horizon.lower()
    )

    if "short" in horizon_lower:

        weights[
            "momentum"
        ] += 0.10

        weights[
            "growth"
        ] += 0.05

        weights[
            "valuation"
        ] -= 0.05

        weights[
            "quality"
        ] -= 0.05

        weights[
            "risk"
        ] -= 0.05

    elif "long" in horizon_lower:

        weights[
            "growth"
        ] += 0.05

        weights[
            "quality"
        ] += 0.10

        weights[
            "momentum"
        ] -= 0.10

        weights[
            "valuation"
        ] -= 0.05

    if (
        risk_tolerance
        == "Conservative"
    ):

        weights[
            "risk"
        ] += 0.15

        weights[
            "momentum"
        ] -= 0.05

        weights[
            "growth"
        ] -= 0.05

        weights[
            "valuation"
        ] -= 0.05

    elif (
        risk_tolerance
        == "Aggressive"
    ):

        weights[
            "growth"
        ] += 0.05

        weights[
            "momentum"
        ] += 0.10

        weights[
            "risk"
        ] -= 0.15

    for (
        factor,
        enabled,
    ) in enabled_factors.items():

        if (
            factor in weights
            and not enabled
        ):
            weights[
                factor
            ] = 0.0

    for factor in list(
        weights
    ):

        weights[
            factor
        ] = max(
            weights[factor],
            0.0,
        )

    total = sum(
        weights.values()
    )

    if total <= 0:

        raise ValueError(
            "At least one screening "
            "factor must be enabled."
        )

    return {
        factor:
        weight / total

        for (
            factor,
            weight,
        ) in weights.items()
    }


# ---------------------------------------------------------
# MAIN DISCOVERY FUNCTION
# ---------------------------------------------------------

def discover_stocks(
    universe: str,
    horizon: str,
    style: str,
    risk_tolerance: str,
    enabled_factors: (
        dict[str, bool]
        | None
    ) = None,
    top_n: int = 10,
) -> pd.DataFrame:

    """
    Produce a ranked stock-research candidate list.

    This stage does NOT call an LLM.

    It uses:
    - index membership
    - Yahoo Finance screening
    - valuation metrics
    - growth metrics
    - profitability / quality metrics
    - price momentum
    - volatility and beta

    The highest-ranked candidates can later be passed
    into TradingAgents for deeper multi-agent analysis.
    """

    enabled_factors = (
        enabled_factors
        or {
            "valuation": True,
            "growth": True,
            "quality": True,
            "momentum": True,
            "risk": True,
        }
    )

    universe_symbols = (
        get_universe_symbols(
            universe
        )
    )

    candidates = (
        _screen_candidate_pool(
            universe_symbols,
            max_candidates=60,
        )
    )

    # If Yahoo screener fails or returns too few
    # constituents, fall back to price-based selection.

    if len(candidates) < 15:

        candidates = (
            _fallback_price_candidates(
                universe_symbols,
                max_candidates=60,
            )
        )

    fundamentals = (
        _fetch_fundamentals(
            candidates
        )
    )

    prices = (
        _price_metrics(
            candidates
        )
    )

    frame = (
        fundamentals
        .merge(
            prices,
            on="symbol",
            how="outer",
        )
    )

    if frame.empty:

        raise RuntimeError(
            "No usable market data "
            "was returned."
        )

    # -----------------------------------------------------
    # VALUATION
    # -----------------------------------------------------

    trailing_pe = (
        _numeric(
            frame,
            "trailing_pe",
        )
        .where(
            lambda s: s > 0
        )
    )

    price_to_book = (
        _numeric(
            frame,
            "price_to_book",
        )
        .where(
            lambda s: s > 0
        )
    )

    ev_to_ebitda = (
        _numeric(
            frame,
            "ev_to_ebitda",
        )
        .where(
            lambda s: s > 0
        )
    )

    frame[
        "valuation_score"
    ] = _mean_available(
        [
            _percentile_score(
                trailing_pe,
                False,
            ),
            _percentile_score(
                price_to_book,
                False,
            ),
            _percentile_score(
                ev_to_ebitda,
                False,
            ),
        ]
    )

    # -----------------------------------------------------
    # GROWTH
    # -----------------------------------------------------

    frame[
        "growth_score"
    ] = _mean_available(
        [
            _percentile_score(
                _numeric(
                    frame,
                    "revenue_growth",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "earnings_growth",
                ),
                True,
            ),
        ]
    )

    # -----------------------------------------------------
    # QUALITY
    # -----------------------------------------------------

    frame[
        "quality_score"
    ] = _mean_available(
        [
            _percentile_score(
                _numeric(
                    frame,
                    "return_on_equity",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "profit_margin",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "debt_to_equity",
                ),
                False,
            ),
        ]
    )

    # -----------------------------------------------------
    # MOMENTUM
    # -----------------------------------------------------

    frame[
        "momentum_score"
    ] = _mean_available(
        [
            _percentile_score(
                _numeric(
                    frame,
                    "return_1m",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "return_6m",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "return_1y",
                ),
                True,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "ma120_slope_1m",
                ),
                True,
            ),
        ]
    )

    # -----------------------------------------------------
    # RISK
    # -----------------------------------------------------

    frame[
        "risk_score"
    ] = _mean_available(
        [
            _percentile_score(
                _numeric(
                    frame,
                    "volatility",
                ),
                False,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "beta",
                ),
                False,
            ),

            _percentile_score(
                _numeric(
                    frame,
                    "debt_to_equity",
                ),
                False,
            ),
        ]
    )

    # -----------------------------------------------------
    # FINAL WEIGHTED SCORE
    # -----------------------------------------------------

    weights = _adjust_weights(
        style=style,
        horizon=horizon,
        risk_tolerance=(
            risk_tolerance
        ),
        enabled_factors=(
            enabled_factors
        ),
    )

    frame[
        "quant_score"
    ] = 0.0

    for (
        factor,
        weight,
    ) in weights.items():

        frame[
            "quant_score"
        ] += (
            frame[
                f"{factor}_score"
            ]
            * weight
        )

    frame = (
        frame
        .sort_values(
            "quant_score",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    frame["rank"] = (
        np.arange(
            1,
            len(frame) + 1,
        )
    )

    # -----------------------------------------------------
    # CLEAN OUTPUT
    # -----------------------------------------------------

    output_columns = [
        "rank",
        "symbol",
        "name",
        "sector",
        "quant_score",

        "valuation_score",
        "growth_score",
        "quality_score",
        "momentum_score",
        "risk_score",

        "trailing_pe",
        "price_to_book",

        "revenue_growth",
        "earnings_growth",

        "return_on_equity",
        "profit_margin",

        "return_6m",
        "return_1y",

        "volatility",
        "beta",
    ]

    for column in output_columns:

        if column not in frame:
            frame[column] = np.nan

    return (
        frame[
            output_columns
        ]
        .head(
            top_n
        )
        .reset_index(
            drop=True
        )
    )