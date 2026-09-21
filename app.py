import os
from datetime import date

import streamlit as st
from analysis_service import run_stock_analysis

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="EquityLab",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# APP STATE / ENVIRONMENT
# ---------------------------------------------------------
OPENROUTER_READY = bool(os.getenv("OPENROUTER_API_KEY"))


# ---------------------------------------------------------
# GLOBAL STYLE
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --bg: #090b10;
        --panel: rgba(255,255,255,0.035);
        --panel-strong: rgba(255,255,255,0.055);
        --border: rgba(255,255,255,0.09);
        --text: #f4f4f5;
        --muted: #9ca3af;
        --muted-2: #71717a;
        --accent: #8b5cf6;
        --accent-2: #38bdf8;
        --good: #22c55e;
        --warn: #f59e0b;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(139,92,246,0.14), transparent 30%),
            radial-gradient(circle at 90% 8%, rgba(56,189,248,0.10), transparent 28%),
            var(--bg);
        color: var(--text);
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 1240px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.035em;
    }

    .eyebrow {
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: #8b93a7;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        font-size: clamp(2.4rem, 5vw, 4.2rem);
        font-weight: 760;
        line-height: 0.98;
        letter-spacing: -0.06em;
        margin-bottom: 0.9rem;
    }

    .hero-subtitle {
        color: #a1a1aa;
        font-size: 1.02rem;
        max-width: 780px;
        line-height: 1.65;
        margin-bottom: 1.8rem;
    }

    .status-wrap {
        padding-top: 1.4rem;
        text-align: right;
        white-space: nowrap;
    }

    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 999px;
        margin-right: 7px;
        vertical-align: 1px;
    }

    .status-ok {
        background: var(--good);
    }

    .status-warn {
        background: var(--warn);
    }

    .status-text {
        color: var(--muted);
        font-size: 0.82rem;
    }

    .metric-card {
        border: 1px solid var(--border);
        background: var(--panel);
        border-radius: 18px;
        padding: 18px 20px;
        min-height: 108px;
        backdrop-filter: blur(8px);
    }

    .metric-label {
        color: #8b93a7;
        font-size: 0.78rem;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 1.42rem;
        font-weight: 680;
        letter-spacing: -0.025em;
    }

    .metric-note {
        color: var(--muted-2);
        font-size: 0.78rem;
        margin-top: 5px;
    }

    .section-card {
        border: 1px solid var(--border);
        background: var(--panel);
        border-radius: 20px;
        padding: 20px 22px;
        margin: 8px 0 16px 0;
    }

    .section-title {
        font-size: 1.10rem;
        font-weight: 680;
        margin-bottom: 5px;
    }

    .section-desc {
        color: #8b93a7;
        font-size: 0.90rem;
        line-height: 1.55;
    }

    div[data-testid="stForm"] {
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.018);
        border-radius: 18px;
        padding: 1rem 1rem 0.25rem 1rem;
    }

    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 12px;
        min-height: 44px;
        font-weight: 650;
        border: 1px solid rgba(255,255,255,0.12);
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea {
        border-radius: 12px !important;
    }

    div[data-testid="stTabs"] button {
        font-weight: 650;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    @media (max-width: 800px) {
        .block-container {
            padding-top: 1.2rem;
        }

        .status-wrap {
            text-align: left;
            padding-top: 0;
            padding-bottom: 0.8rem;
        }

        .metric-card {
            min-height: 96px;
            padding: 15px 16px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
top_left, top_right = st.columns([5, 1])

with top_left:
    st.markdown(
        """
        <div class="eyebrow">AI Equity Research Workspace</div>
        <div class="hero-title">EquityLab</div>
        <div class="hero-subtitle">
            Research individual companies, discover new opportunities,
            compare candidates, and evaluate portfolio fit — powered by
            TradingAgents.
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_right:
    dot_class = "status-ok" if OPENROUTER_READY else "status-warn"
    status_text = (
        "OpenRouter connected"
        if OPENROUTER_READY
        else "API key missing"
    )

    st.markdown(
        f"""
        <div class="status-wrap">
            <span class="status-dot {dot_class}"></span>
            <span class="status-text">{status_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# MARKET OVERVIEW
# Live data will be connected later.
# ---------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)

market_cards = [
    ("S&P 500", "—", "Live data coming next"),
    ("NASDAQ", "—", "Live data coming next"),
    ("VIX", "—", "Risk regime"),
    ("US 10Y", "—", "Macro context"),
]

for col, (label, value, note) in zip(
    (m1, m2, m3, m4),
    market_cards,
):
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")


# ---------------------------------------------------------
# MAIN NAVIGATION
# ---------------------------------------------------------
(
    tab_analyze,
    tab_discover,
    tab_compare,
    tab_portfolio,
) = st.tabs(
    [
        "Analyze",
        "Discover",
        "Compare",
        "Portfolio",
    ]
)


# =========================================================
# ANALYZE
# =========================================================
with tab_analyze:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                Single Stock Research
            </div>
            <div class="section-desc">
                Run a complete multi-agent research process
                on one company.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "analyze_form",
        clear_on_submit=False,
    ):
        a1, a2, a3 = st.columns([2, 2, 1.5])

        with a1:
            analyze_ticker = (
                st.text_input(
                    "Ticker",
                    value="AAPL",
                    key="analyze_ticker",
                    placeholder="e.g. AAPL",
                )
                .strip()
                .upper()
            )

        with a2:
            analyze_date = st.date_input(
                "Analysis date",
                value=date.today(),
                key="analyze_date",
            )

        with a3:
            research_depth = st.selectbox(
                "Research depth",
                [
                    "Shallow",
                    "Medium",
                    "Deep",
                ],
                index=0,
                key="research_depth",
            )

        st.caption("Analyst team")

        analyst_cols = st.columns(4)

        with analyst_cols[0]:
            use_market = st.checkbox(
                "Market",
                value=True,
                key="use_market",
            )

        with analyst_cols[1]:
            use_fundamentals = st.checkbox(
                "Fundamentals",
                value=True,
                key="use_fundamentals",
            )

        with analyst_cols[2]:
            use_news = st.checkbox(
                "News",
                value=True,
                key="use_news",
            )

        with analyst_cols[3]:
            use_sentiment = st.checkbox(
                "Sentiment",
                value=True,
                key="use_sentiment",
            )

        run_analysis = st.form_submit_button(
            "Run full analysis",
            type="primary",
            width="stretch",
        )

    if run_analysis:
        if not analyze_ticker:
            st.warning(
                "Enter a ticker before running the analysis."
            )

        elif not any(
            (
                use_market,
                use_fundamentals,
                use_news,
                use_sentiment,
            )
        ):
            st.warning(
                "Select at least one analyst."
            )

        else:
            try:
                with st.spinner(
                    f"TradingAgents is researching {analyze_ticker}..."
                ):
                    result = run_stock_analysis(
                        ticker=analyze_ticker,
                        analysis_date=analyze_date,
                        research_depth=research_depth,
                        use_market=use_market,
                        use_fundamentals=use_fundamentals,
                        use_news=use_news,
                        use_sentiment=use_sentiment,
                    )

                st.session_state["analysis_result"] = result
                st.session_state["analysis_error"] = None

            except Exception as exc:
                st.session_state["analysis_result"] = None
                st.session_state["analysis_error"] = str(exc)


# ---------------------------------------------------------
# ANALYSIS RESULT
# ---------------------------------------------------------

analysis_error = st.session_state.get("analysis_error")
analysis_result = st.session_state.get("analysis_result")

if analysis_error:
    st.error(
        "The analysis could not be completed."
    )

    with st.expander("Show error details"):
        st.code(analysis_error)


if analysis_result:
    st.success(
        f"{analysis_result['ticker']} analysis completed."
    )

    r1, r2, r3 = st.columns(3)

    with r1:
        st.metric(
            "Ticker",
            analysis_result["ticker"],
        )

    with r2:
        st.metric(
            "Final Rating",
            analysis_result["rating"],
        )

    with r3:
        st.metric(
            "Research Depth",
            analysis_result["research_depth"],
        )

    st.divider()

    result_tabs = st.tabs(
        [
            "Overview",
            "Fundamentals",
            "Market",
            "News",
            "Sentiment",
            "Bull vs Bear",
            "Risk",
        ]
    )

    # -----------------------------------------------------
    # OVERVIEW
    # -----------------------------------------------------
    with result_tabs[0]:
        st.subheader("Final Investment View")

        final_decision = (
            analysis_result.get("final_decision")
            or analysis_result.get("investment_plan")
            or "No final decision returned."
        )

        st.markdown(final_decision)

        trader_plan = analysis_result.get("trader_plan")

        if trader_plan:
            st.subheader("Trader Plan")
            st.markdown(trader_plan)

        research_manager = analysis_result.get(
            "research_manager"
        )

        if research_manager:
            st.subheader("Research Manager")
            st.markdown(research_manager)

    # -----------------------------------------------------
    # FUNDAMENTALS
    # -----------------------------------------------------
    with result_tabs[1]:
        fundamentals = analysis_result.get(
            "fundamentals_report"
        )

        if fundamentals:
            st.markdown(fundamentals)
        else:
            st.caption(
                "Fundamentals analyst was not selected "
                "or returned no report."
            )

    # -----------------------------------------------------
    # MARKET
    # -----------------------------------------------------
    with result_tabs[2]:
        market = analysis_result.get("market_report")

        if market:
            st.markdown(market)
        else:
            st.caption(
                "Market analyst was not selected "
                "or returned no report."
            )

    # -----------------------------------------------------
    # NEWS
    # -----------------------------------------------------
    with result_tabs[3]:
        news = analysis_result.get("news_report")

        if news:
            st.markdown(news)
        else:
            st.caption(
                "News analyst was not selected "
                "or returned no report."
            )

    # -----------------------------------------------------
    # SENTIMENT
    # -----------------------------------------------------
    with result_tabs[4]:
        sentiment = analysis_result.get(
            "sentiment_report"
        )

        if sentiment:
            st.markdown(sentiment)
        else:
            st.caption(
                "Sentiment analyst was not selected "
                "or returned no report."
            )

    # -----------------------------------------------------
    # BULL VS BEAR
    # -----------------------------------------------------
    with result_tabs[5]:
        bull_col, bear_col = st.columns(2)

        with bull_col:
            st.subheader("Bull Case")

            bull_case = analysis_result.get("bull_case")

            if bull_case:
                st.markdown(bull_case)
            else:
                st.caption("No bull case returned.")

        with bear_col:
            st.subheader("Bear Case")

            bear_case = analysis_result.get("bear_case")

            if bear_case:
                st.markdown(bear_case)
            else:
                st.caption("No bear case returned.")

    # -----------------------------------------------------
    # RISK
    # -----------------------------------------------------
    with result_tabs[6]:
        st.subheader("Risk Manager")

        risk_manager = analysis_result.get("risk_manager")

        if risk_manager:
            st.markdown(risk_manager)
        else:
            st.caption("No risk-manager report returned.")

        with st.expander("Aggressive View"):
            st.markdown(
                analysis_result.get(
                    "aggressive_risk_view"
                )
                or "No report."
            )

        with st.expander("Neutral View"):
            st.markdown(
                analysis_result.get(
                    "neutral_risk_view"
                )
                or "No report."
            )

        with st.expander("Conservative View"):
            st.markdown(
                analysis_result.get(
                    "conservative_risk_view"
                )
                or "No report."
            )

            
            
            

        
            
                
                
            
            
            
        
            
                
            

    
            
            
                
            


# =========================================================
# DISCOVER
# =========================================================
with tab_discover:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                Opportunity Discovery
            </div>
            <div class="section-desc">
                Screen a broad universe quantitatively,
                then send the strongest candidates to
                TradingAgents for deeper research.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "discover_form",
        clear_on_submit=False,
    ):
        d1, d2 = st.columns(2)

        with d1:
            universe = st.selectbox(
                "Investment universe",
                [
                    "S&P 500",
                    "NASDAQ 100",
                    "Dow Jones",
                    "Custom watchlist",
                ],
                key="discover_universe",
            )

            horizon = st.selectbox(
                "Investment horizon",
                [
                    "Short term · < 1 year",
                    "Medium term · 1–3 years",
                    "Long term · 3–5+ years",
                ],
                index=1,
                key="discover_horizon",
            )

        with d2:
            style = st.selectbox(
                "Strategy",
                [
                    "Balanced",
                    "Value",
                    "Growth",
                    "Quality",
                    "Momentum",
                ],
                key="discover_style",
            )

            risk = st.selectbox(
                "Risk tolerance",
                [
                    "Conservative",
                    "Moderate",
                    "Aggressive",
                ],
                index=1,
                key="discover_risk",
            )

        st.caption("Screening factors")

        f1, f2, f3, f4, f5 = st.columns(5)

        with f1:
            factor_valuation = st.checkbox(
                "Valuation",
                value=True,
                key="factor_valuation",
            )

        with f2:
            factor_growth = st.checkbox(
                "Growth",
                value=True,
                key="factor_growth",
            )

        with f3:
            factor_quality = st.checkbox(
                "Quality",
                value=True,
                key="factor_quality",
            )

        with f4:
            factor_momentum = st.checkbox(
                "Momentum",
                value=True,
                key="factor_momentum",
            )

        with f5:
            factor_risk = st.checkbox(
                "Risk",
                value=True,
                key="factor_risk",
            )

        run_discovery = st.form_submit_button(
            "Find opportunities",
            type="primary",
            width="stretch",
        )

    if run_discovery:
        if not any(
            (
                factor_valuation,
                factor_growth,
                factor_quality,
                factor_momentum,
                factor_risk,
            )
        ):
            st.warning(
                "Select at least one screening factor."
            )

        else:
            st.info(
                "The discovery engine will be connected "
                "after single-stock analysis works."
            )


# =========================================================
# COMPARE
# =========================================================
with tab_compare:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                Compare Companies
            </div>
            <div class="section-desc">
                Compare multiple stocks under the same
                research framework.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "compare_form",
        clear_on_submit=False,
    ):
        compare_tickers = st.text_input(
            "Tickers",
            value="MSFT, GOOGL, AMZN",
            help="Separate tickers with commas.",
            key="compare_tickers",
        )

        st.caption(
            "Example: MSFT, GOOGL, AMZN"
        )

        run_compare = st.form_submit_button(
            "Compare stocks",
            type="primary",
            width="stretch",
        )

    if run_compare:
        tickers = [
            ticker.strip().upper()
            for ticker in compare_tickers.split(",")
            if ticker.strip()
        ]

        if len(tickers) < 2:
            st.warning(
                "Enter at least two tickers to compare."
            )

        else:
            st.info(
                f"Comparison UI is ready for: "
                f"{', '.join(tickers)}. "
                "TradingAgents comparison logic "
                "will be added later."
            )


# =========================================================
# PORTFOLIO
# =========================================================
with tab_portfolio:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                Portfolio Fit
            </div>
            <div class="section-desc">
                Evaluate whether a new company complements
                or concentrates your existing holdings.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "portfolio_form",
        clear_on_submit=False,
    ):
        portfolio = st.text_area(
            "Current portfolio",
            value=(
                "MSFT 25%\n"
                "GOOGL 25%\n"
                "AMZN 25%\n"
                "V 25%"
            ),
            height=150,
            key="portfolio_holdings",
        )

        candidate = (
            st.text_input(
                "Candidate ticker",
                value="",
                placeholder="e.g. COST",
                key="portfolio_candidate",
            )
            .strip()
            .upper()
        )

        run_portfolio = st.form_submit_button(
            "Evaluate portfolio fit",
            type="primary",
            width="stretch",
        )

    if run_portfolio:
        if not portfolio.strip():
            st.warning(
                "Enter at least one current holding."
            )

        elif not candidate:
            st.warning(
                "Enter a candidate ticker."
            )

        else:
            st.info(
                f"Portfolio-fit UI is ready for "
                f"{candidate}. "
                "Portfolio-aware TradingAgents analysis "
                "will be connected later."
            )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.write("")
st.divider()

st.caption(
    "EquityLab · Research support only · "
    "Model-generated outputs should be independently verified."
)