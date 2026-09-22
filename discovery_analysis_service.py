from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from analysis_service import run_stock_analysis


# 무료 OpenRouter 사용량 보호용
MAX_DEEP_CANDIDATES = 3


def _normalize_analysis_date(value: Any) -> str:
    """
    Convert date-like values into YYYY-MM-DD.
    """

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.isoformat()

    value = str(value).strip()

    parsed = datetime.strptime(
        value,
        "%Y-%m-%d",
    ).date()

    return parsed.isoformat()


def _validate_discovery_frame(
    discovery_result: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate the Quant Screener output before deep analysis.
    """

    if not isinstance(
        discovery_result,
        pd.DataFrame,
    ):
        raise TypeError(
            "discovery_result must be a pandas DataFrame."
        )

    if discovery_result.empty:
        raise ValueError(
            "The discovery result is empty."
        )

    required_columns = {
        "rank",
        "symbol",
        "name",
        "sector",
        "quant_score",
    }

    missing = required_columns.difference(
        discovery_result.columns
    )

    if missing:
        raise ValueError(
            "Discovery result is missing columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    return discovery_result.copy()


def analyze_discovery_candidates(
    discovery_result: pd.DataFrame,
    analysis_date: Any,
    top_k: int = 1,
    research_depth: str = "Shallow",
) -> list[dict[str, Any]]:
    """
    Run TradingAgents on the highest-ranked Quant candidates.

    The function intentionally caps deep-analysis candidates
    at 3 to avoid excessive LLM calls.

    Each stock is isolated:
    if one candidate fails, the others continue.
    """

    frame = _validate_discovery_frame(
        discovery_result
    )

    try:
        requested_top_k = int(
            top_k
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "top_k must be an integer."
        ) from exc

    if requested_top_k < 1:
        raise ValueError(
            "top_k must be at least 1."
        )

    top_k = min(
        requested_top_k,
        MAX_DEEP_CANDIDATES,
        len(frame),
    )

    clean_date = _normalize_analysis_date(
        analysis_date
    )

    selected = (
        frame
        .sort_values(
            "rank",
            ascending=True,
        )
        .head(top_k)
    )

    results: list[
        dict[str, Any]
    ] = []

    for _, row in selected.iterrows():

        ticker = str(
            row["symbol"]
        ).strip().upper()

        base_result = {
            "rank": int(
                row["rank"]
            ),

            "ticker": ticker,

            "company": (
                str(row["name"])
                if pd.notna(
                    row["name"]
                )
                else ticker
            ),

            "sector": (
                str(row["sector"])
                if pd.notna(
                    row["sector"]
                )
                else ""
            ),

            "quant_score": float(
                row["quant_score"]
            ),

            "status": "pending",

            "error": None,
        }

        try:
            analysis = run_stock_analysis(
                ticker=ticker,
                analysis_date=clean_date,
                research_depth=research_depth,

                use_market=True,
                use_fundamentals=True,
                use_news=True,
                use_sentiment=True,
            )

            base_result.update(
                {
                    "status":
                    "completed",

                    "rating":
                    analysis.get(
                        "rating",
                        "",
                    ),

                    "final_decision":
                    analysis.get(
                        "final_decision",
                        "",
                    ),

                    "investment_plan":
                    analysis.get(
                        "investment_plan",
                        "",
                    ),

                    "trader_plan":
                    analysis.get(
                        "trader_plan",
                        "",
                    ),

                    "research_manager":
                    analysis.get(
                        "research_manager",
                        "",
                    ),

                    "risk_manager":
                    analysis.get(
                        "risk_manager",
                        "",
                    ),

                    "bull_case":
                    analysis.get(
                        "bull_case",
                        "",
                    ),

                    "bear_case":
                    analysis.get(
                        "bear_case",
                        "",
                    ),

                    "market_report":
                    analysis.get(
                        "market_report",
                        "",
                    ),

                    "fundamentals_report":
                    analysis.get(
                        "fundamentals_report",
                        "",
                    ),

                    "news_report":
                    analysis.get(
                        "news_report",
                        "",
                    ),

                    "sentiment_report":
                    analysis.get(
                        "sentiment_report",
                        "",
                    ),
                }
            )

        except Exception as exc:

            base_result.update(
                {
                    "status":
                    "failed",

                    "rating":
                    "",

                    "error":
                    str(exc),
                }
            )

        results.append(
            base_result
        )

    return results


def discovery_summary_frame(
    deep_results: list[
        dict[str, Any]
    ],
) -> pd.DataFrame:
    """
    Convert deep-analysis results into a compact
    Streamlit-friendly summary table.
    """

    rows: list[
        dict[str, Any]
    ] = []

    for item in deep_results:

        rows.append(
            {
                "Quant Rank":
                item.get(
                    "rank"
                ),

                "Ticker":
                item.get(
                    "ticker"
                ),

                "Company":
                item.get(
                    "company"
                ),

                "Quant Score":
                item.get(
                    "quant_score"
                ),

                "TradingAgents Rating":
                (
                    item.get(
                        "rating"
                    )
                    or "—"
                ),

                "Status":
                item.get(
                    "status"
                ),
            }
        )

    return pd.DataFrame(
        rows
    )