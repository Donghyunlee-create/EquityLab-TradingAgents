import os
from datetime import date, datetime
from typing import Any

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DEPTH_ROUNDS = {
    "Shallow": 1,
    "Medium": 3,
    "Deep": 5,
}


def _build_config(research_depth: str) -> dict[str, Any]:
    """
    Build a fresh TradingAgents config for one web analysis run.
    """

    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError(
            "OPENROUTER_API_KEY is not available. "
            "Check the Codespaces/Render environment secret."
        )

    rounds = DEPTH_ROUNDS.get(research_depth, 1)

    config = DEFAULT_CONFIG.copy()

    # LLM
    config["llm_provider"] = "openrouter"
    config["quick_think_llm"] = "openrouter/free"
    config["deep_think_llm"] = "openrouter/free"

    # Output
    config["output_language"] = "Korean"

    # Research depth
    config["max_debate_rounds"] = rounds
    config["max_risk_discuss_rounds"] = rounds

    # Web runs should start clean for now.
    config["checkpoint_enabled"] = False

    return config


def _normalize_date(value: Any) -> str:
    """
    Convert Streamlit date_input values or strings into YYYY-MM-DD.
    """

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        value = value.isoformat()

    value = str(value).strip()

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            "Analysis date must use YYYY-MM-DD format."
        ) from exc

    if parsed > date.today():
        raise ValueError(
            "Analysis date cannot be in the future."
        )

    return parsed.isoformat()


def _normalize_ticker(ticker: str) -> str:
    """
    Basic ticker cleanup.
    Examples:
    AAPL
    BRK-B
    0700.HK
    BTC-USD
    """

    ticker = str(ticker).strip().upper()

    if not ticker:
        raise ValueError("Ticker is required.")

    if len(ticker) > 30:
        raise ValueError("Ticker is too long.")

    return ticker


def _build_analyst_list(
    use_market: bool,
    use_fundamentals: bool,
    use_news: bool,
    use_sentiment: bool,
) -> list[str]:
    """
    Translate EquityLab UI choices into TradingAgents analyst IDs.
    """

    analysts: list[str] = []

    if use_market:
        analysts.append("market")

    if use_fundamentals:
        analysts.append("fundamentals")

    if use_news:
        analysts.append("news")

    # TradingAgents internally calls the sentiment analyst "social".
    if use_sentiment:
        analysts.append("social")

    if not analysts:
        raise ValueError(
            "At least one analyst must be selected."
        )

    return analysts


def _safe_get(
    mapping: Any,
    key: str,
    default: Any = "",
) -> Any:
    """
    Safely read nested TradingAgents state dictionaries.
    """

    if isinstance(mapping, dict):
        return mapping.get(key, default)

    return default


def run_stock_analysis(
    ticker: str,
    analysis_date: Any,
    research_depth: str = "Shallow",
    use_market: bool = True,
    use_fundamentals: bool = True,
    use_news: bool = True,
    use_sentiment: bool = True,
) -> dict[str, Any]:
    """
    Run the official TradingAgents pipeline for one stock
    and return UI-friendly structured results.
    """

    clean_ticker = _normalize_ticker(ticker)
    clean_date = _normalize_date(analysis_date)

    analysts = _build_analyst_list(
        use_market=use_market,
        use_fundamentals=use_fundamentals,
        use_news=use_news,
        use_sentiment=use_sentiment,
    )

    config = _build_config(research_depth)

    trading_agents = TradingAgentsGraph(
        selected_analysts=analysts,
        debug=False,
        config=config,
    )

    final_state, signal = trading_agents.propagate(
        clean_ticker,
        clean_date,
        asset_type="stock",
    )

    if not isinstance(final_state, dict):
        raise RuntimeError(
            "TradingAgents returned an unexpected result."
        )

    debate = _safe_get(
        final_state,
        "investment_debate_state",
        {},
    )

    risk = _safe_get(
        final_state,
        "risk_debate_state",
        {},
    )

    result = {
        # Run metadata
        "ticker": clean_ticker,
        "analysis_date": clean_date,
        "research_depth": research_depth,
        "analysts": analysts,

        # Final rating
        "rating": str(signal),

        # Analyst reports
        "market_report": _safe_get(
            final_state,
            "market_report",
        ),
        "fundamentals_report": _safe_get(
            final_state,
            "fundamentals_report",
        ),
        "news_report": _safe_get(
            final_state,
            "news_report",
        ),
        "sentiment_report": _safe_get(
            final_state,
            "sentiment_report",
        ),

        # Bull / Bear research
        "bull_case": _safe_get(
            debate,
            "bull_history",
        ),
        "bear_case": _safe_get(
            debate,
            "bear_history",
        ),
        "research_manager": _safe_get(
            debate,
            "judge_decision",
        ),

        # Trader
        "investment_plan": _safe_get(
            final_state,
            "investment_plan",
        ),
        "trader_plan": _safe_get(
            final_state,
            "trader_investment_plan",
        ),

        # Risk team
        "aggressive_risk_view": _safe_get(
            risk,
            "aggressive_history",
        ),
        "neutral_risk_view": _safe_get(
            risk,
            "neutral_history",
        ),
        "conservative_risk_view": _safe_get(
            risk,
            "conservative_history",
        ),
        "risk_manager": _safe_get(
            risk,
            "judge_decision",
        ),

        # Raw Portfolio Manager output
        "final_decision": _safe_get(
            final_state,
            "final_trade_decision",
        ),
    }

    return result