import os
import html
from datetime import date

import streamlit as st
from analysis_service import run_stock_analysis
from valuation_service import analyze_valuation
from screener_service import discover_stocks
from discovery_analysis_service import analyze_discovery_candidates, discovery_summary_frame
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
# ANALYSIS RESULT · EQUITYLAB RESEARCH VIEW
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
        analyzed_ticker = analysis_result["ticker"]

        # -------------------------------------------------
        # VALUATION ENGINE
        # -------------------------------------------------

        cached_valuation = st.session_state.get(
            "valuation_result"
        )

        cached_valuation_ticker = st.session_state.get(
            "valuation_ticker"
        )

        if (
            cached_valuation is None
            or cached_valuation_ticker
            != analyzed_ticker
        ):
            try:
                with st.spinner(
                    f"Building live price map for "
                    f"{analyzed_ticker}..."
                ):
                    cached_valuation = (
                        analyze_valuation(
                            analyzed_ticker
                        )
                    )

                st.session_state[
                    "valuation_result"
                ] = cached_valuation

                st.session_state[
                    "valuation_ticker"
                ] = analyzed_ticker

                st.session_state[
                    "valuation_error"
                ] = None

            except Exception as exc:
                st.session_state[
                    "valuation_result"
                ] = None

                st.session_state[
                    "valuation_ticker"
                ] = analyzed_ticker

                st.session_state[
                    "valuation_error"
                ] = str(exc)

        valuation = st.session_state.get(
            "valuation_result"
        )

        valuation_error = st.session_state.get(
            "valuation_error"
        )


        # -------------------------------------------------
        # DISPLAY HELPERS
        # -------------------------------------------------

        def _money(value):
            if value is None:
                return "—"

            return (
                f"${float(value):,.2f}"
            )


        def _pct(value):
            if value is None:
                return "—"

            return (
                f"{float(value):+.1f}%"
            )


        def _range(low, high):
            if (
                low is None
                or high is None
            ):
                return "—"

            low_value = float(low)
            high_value = float(high)

            lower = min(
                low_value,
                high_value,
            )

            upper = max(
                low_value,
                high_value,
            )

            return (
                f"{_money(lower)} – "
                f"{_money(upper)}"
            )


        def _plain_ai_text(value):
            if not value:
                return "No report returned."

            text_value = str(value)

            for token in (
                "###",
                "##",
                "#",
                "**",
                "__",
                "`",
            ):
                text_value = (
                    text_value.replace(
                        token,
                        "",
                    )
                )

            lines = [
                line.strip()
                for line
                in text_value.splitlines()
            ]

            return "\n".join(
                line
                for line in lines
                if line
            )


        def _fixed_text(value):
            clean = _plain_ai_text(
                value
            )

            safe = (
                html.escape(clean)
                .replace(
                    "\n",
                    "<br>",
                )
            )

            st.markdown(
                (
                    '<div class="research-body">'
                    f'{safe}'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )


        def _summary_card(
            column,
            label,
            value,
            note="",
        ):
            with column:
                st.markdown(
                    (
                        '<div class="research-card">'
                        '<div class="research-card-label">'
                        f'{html.escape(str(label))}'
                        '</div>'
                        '<div class="research-card-value">'
                        f'{html.escape(str(value))}'
                        '</div>'
                        '<div class="research-card-note">'
                        f'{html.escape(str(note))}'
                        '</div>'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )


        # -------------------------------------------------
        # RESEARCH UI STYLE
        # -------------------------------------------------

        st.markdown(
            """
            <style>

            .research-card {
                border:
                    1px solid
                    rgba(255,255,255,0.09);

                background:
                    rgba(255,255,255,0.028);

                border-radius: 16px;
                padding: 16px 18px;
                min-height: 108px;
            }

            .research-card-label {
                color: #8b93a7;
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 8px;
            }

            .research-card-value {
                color: #f4f4f5;
                font-size: 22px;
                font-weight: 700;
                line-height: 1.15;
            }

            .research-card-note {
                color: #71717a;
                font-size: 12px;
                line-height: 1.4;
                margin-top: 7px;
            }

            .research-body {
                color: #d4d4d8;
                font-size: 14px;
                line-height: 1.72;
                font-weight: 400;
            }

            .zone-title {
                color: #f4f4f5;
                font-size: 14px;
                font-weight: 650;
                margin-bottom: 10px;
            }

            .zone-row {
                display: flex;
                justify-content:
                    space-between;
                gap: 16px;

                border-bottom:
                    1px solid
                    rgba(255,255,255,0.06);

                padding: 9px 0;
                font-size: 13px;
            }

            .zone-name {
                color: #9ca3af;
            }

            .zone-value {
                color: #f4f4f5;
                font-weight: 650;
                text-align: right;
            }

            </style>
            """,
            unsafe_allow_html=True,
        )


        # -------------------------------------------------
        # TOP SUMMARY
        # -------------------------------------------------

        st.success(
            f"{analyzed_ticker} research completed."
        )

        if valuation:

            current_price = valuation.get(
                "current_price"
            )

            fair_value = valuation.get(
                "fair_value"
            )

            fair_low = valuation.get(
                "fair_value_low"
            )

            fair_high = valuation.get(
                "fair_value_high"
            )

            top_cards = st.columns(4)

            _summary_card(
                top_cards[0],
                "Current Price",
                _money(current_price),
                valuation.get(
                    "quote_source",
                    "",
                ),
            )

            _summary_card(
                top_cards[1],
                "Base Fair Value",
                _money(fair_value),
                (
                    "Confidence: "
                    f"{valuation.get('valuation_confidence', '—')}"
                ),
            )

            _summary_card(
                top_cards[2],
                "Fair Value Range",
                _range(
                    fair_low,
                    fair_high,
                ),
                (
                    "Status: "
                    f"{valuation.get('valuation_status', '—')}"
                ),
            )

            _summary_card(
                top_cards[3],
                "Model Upside / Downside",
                _pct(
                    valuation.get(
                        "upside_downside_pct"
                    )
                ),
                (
                    "TradingAgents: "
                    f"{analysis_result.get('rating', '—')}"
                ),
            )

            st.write("")

            second_cards = st.columns(4)

            _summary_card(
                second_cards[0],
                "TradingAgents",
                analysis_result.get(
                    "rating",
                    "—",
                ),
                "Multi-agent research signal",
            )

            _summary_card(
                second_cards[1],
                "Valuation",
                valuation.get(
                    "valuation_status",
                    "—",
                ),
                (
                    "Relative to model "
                    "fair-value range"
                ),
            )

            dispersion = valuation.get(
                "model_dispersion_pct"
            )

            dispersion_note = (
                (
                    "DCF vs consensus dispersion "
                    f"{dispersion:.1f}%"
                )
                if dispersion is not None
                else
                "Model dispersion unavailable"
            )

            _summary_card(
                second_cards[2],
                "Model Confidence",
                valuation.get(
                    "valuation_confidence",
                    "—",
                ),
                dispersion_note,
            )

            _summary_card(
                second_cards[3],
                "Research Depth",
                analysis_result.get(
                    "research_depth",
                    "—",
                ),
                (
                    "Analysis date: "
                    f"{analysis_result.get('analysis_date', '—')}"
                ),
            )


            # -------------------------------------------------
            # PRICE MAP
            # -------------------------------------------------

            st.divider()
            st.markdown(
                "### Price Map"
            )

            price_left, price_right = (
                st.columns(2)
            )

            with price_left:

                st.markdown(
                    (
                        '<div class="zone-title">'
                        'Valuation Bands'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )

                valuation_rows = [
                    (
                        "Deep Value",
                        (
                            "≤ "
                            + _money(
                                valuation.get(
                                    "deep_value_max"
                                )
                            )
                            if valuation.get(
                                "deep_value_max"
                            ) is not None
                            else "—"
                        ),
                    ),

                    (
                        "Undervalued",
                        _range(
                            valuation.get(
                                "undervalued_min"
                            ),
                            valuation.get(
                                "undervalued_max"
                            ),
                        ),
                    ),

                    (
                        "Fair Value",
                        _range(
                            valuation.get(
                                "fair_value_min"
                            ),
                            valuation.get(
                                "fair_value_max"
                            ),
                        ),
                    ),

                    (
                        "Expensive",
                        _range(
                            valuation.get(
                                "expensive_min"
                            ),
                            valuation.get(
                                "expensive_max"
                            ),
                        ),
                    ),

                    (
                        "Rich",
                        (
                            "≥ "
                            + _money(
                                valuation.get(
                                    "rich_min"
                                )
                            )
                            if valuation.get(
                                "rich_min"
                            ) is not None
                            else "—"
                        ),
                    ),
                ]

                for (
                    label,
                    value,
                ) in valuation_rows:

                    st.markdown(
                        (
                            '<div class="zone-row">'
                            '<span class="zone-name">'
                            f'{html.escape(label)}'
                            '</span>'
                            '<span class="zone-value">'
                            f'{html.escape(value)}'
                            '</span>'
                            '</div>'
                        ),
                        unsafe_allow_html=True,
                    )


            with price_right:

                st.markdown(
                    (
                        '<div class="zone-title">'
                        'Execution Research Bands'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )

                execution_rows = [
                    (
                        "Valuation Entry",
                        _range(
                            valuation.get(
                                "valuation_entry_zone_low"
                            ),
                            valuation.get(
                                "valuation_entry_zone_high"
                            ),
                        ),
                    ),

                    (
                        "Technical Support",
                        _range(
                            valuation.get(
                                "technical_entry_zone_low"
                            ),
                            valuation.get(
                                "technical_entry_zone_high"
                            ),
                        ),
                    ),

                    (
                        "Convergent Entry",
                        (
                            _range(
                                valuation.get(
                                    "entry_zone_low"
                                ),
                                valuation.get(
                                    "entry_zone_high"
                                ),
                            )
                            if valuation.get(
                                "entry_zone_status"
                            )
                            == "CONVERGENT"
                            else
                            "No convergence"
                        ),
                    ),

                    (
                        "Valuation Trim / Reassess",
                        _range(
                            valuation.get(
                                "valuation_trim_zone_low"
                            ),
                            valuation.get(
                                "valuation_trim_zone_high"
                            ),
                        ),
                    ),

                    (
                        "Technical Resistance",
                        _range(
                            valuation.get(
                                "technical_trim_zone_low"
                            ),
                            valuation.get(
                                "technical_trim_zone_high"
                            ),
                        ),
                    ),

                    (
                        "Convergent Trim / Reassess",
                        (
                            _range(
                                valuation.get(
                                    "trim_zone_low"
                                ),
                                valuation.get(
                                    "trim_zone_high"
                                ),
                            )
                            if valuation.get(
                                "trim_zone_status"
                            )
                            == "CONVERGENT"
                            else
                            "No convergence"
                        ),
                    ),
                ]

                for (
                    label,
                    value,
                ) in execution_rows:

                    st.markdown(
                        (
                            '<div class="zone-row">'
                            '<span class="zone-name">'
                            f'{html.escape(label)}'
                            '</span>'
                            '<span class="zone-value">'
                            f'{html.escape(value)}'
                            '</span>'
                            '</div>'
                        ),
                        unsafe_allow_html=True,
                    )


            if (
                valuation.get(
                    "entry_zone_status"
                )
                != "CONVERGENT"
            ):
                st.warning(
                    "Valuation and technical support "
                    "do not currently overlap. "
                    "EquityLab therefore does not "
                    "assign one precise entry band."
                )


            if (
                valuation.get(
                    "trim_zone_status"
                )
                != "CONVERGENT"
            ):
                st.info(
                    "Valuation and technical resistance "
                    "do not currently overlap for a "
                    "single Trim / Reassess band."
                )


            st.caption(
                "Price bands are model-based research "
                "ranges, not automatic buy/sell "
                "instructions. Yahoo Finance data "
                "may be delayed."
            )


            # -------------------------------------------------
            # TECHNICAL LEVELS
            # -------------------------------------------------

            st.divider()
            st.markdown(
                "### Technical Levels"
            )

            technical_cards = (
                st.columns(4)
            )

            _summary_card(
                technical_cards[0],
                "MA 120",
                _money(
                    valuation.get(
                        "ma120"
                    )
                ),
                "Medium-term trend reference",
            )

            _summary_card(
                technical_cards[1],
                "MA 200",
                _money(
                    valuation.get(
                        "ma200"
                    )
                ),
                "Long-term trend reference",
            )

            _summary_card(
                technical_cards[2],
                "Support",
                _range(
                    valuation.get(
                        "support_2"
                    ),
                    valuation.get(
                        "support_1"
                    ),
                ),
                "Recent price-distribution support",
            )

            _summary_card(
                technical_cards[3],
                "Resistance",
                _range(
                    valuation.get(
                        "resistance_1"
                    ),
                    valuation.get(
                        "resistance_2"
                    ),
                ),
                "Recent price-distribution resistance",
            )


            # -------------------------------------------------
            # MODEL DETAILS
            # -------------------------------------------------

            with st.expander(
                "Valuation model details"
            ):

                model_cards = (
                    st.columns(3)
                )

                discount_rate = (
                    valuation.get(
                        "discount_rate"
                    )
                )

                _summary_card(
                    model_cards[0],
                    "DCF",
                    _money(
                        valuation.get(
                            "dcf_fair_value"
                        )
                    ),
                    (
                        f"Discount rate "
                        f"{discount_rate * 100:.1f}%"
                        if discount_rate
                        is not None
                        else
                        "Discount rate unavailable"
                    ),
                )

                _summary_card(
                    model_cards[1],
                    "Analyst Consensus",
                    _money(
                        valuation.get(
                            "analyst_target"
                        )
                    ),
                    (
                        "Yahoo Finance "
                        "consensus field"
                    ),
                )

                _summary_card(
                    model_cards[2],
                    "Fair Value Range",
                    _range(
                        valuation.get(
                            "fair_value_low"
                        ),
                        valuation.get(
                            "fair_value_high"
                        ),
                    ),
                    (
                        "Confidence: "
                        f"{valuation.get('valuation_confidence', '—')}"
                    ),
                )

                notes = (
                    valuation.get(
                        "notes"
                    )
                    or []
                )

                if notes:
                    st.markdown(
                        "##### Model notes"
                    )

                    for note in notes:
                        st.caption(
                            f"• {note}"
                        )


            st.caption(
                (
                    "Valuation generated: "
                    f"{valuation.get('timestamp_utc', '—')} UTC"
                )
            )


        elif valuation_error:

            st.warning(
                "TradingAgents completed, but "
                "the valuation engine could not "
                "build the live price map."
            )

            with st.expander(
                "Valuation error details"
            ):
                st.code(
                    valuation_error
                )


        # -------------------------------------------------
        # FIXED-SIZE AI RESEARCH VIEW
        # -------------------------------------------------

        st.divider()

        st.markdown(
            "### Research View"
        )

        final_view = (
            analysis_result.get(
                "final_decision"
            )
            or analysis_result.get(
                "investment_plan"
            )
            or analysis_result.get(
                "trader_plan"
            )
            or
            "No final research view returned."
        )

        _fixed_text(
            final_view
        )


        # -------------------------------------------------
        # DETAILED RESEARCH
        # -------------------------------------------------

        st.write("")

        st.markdown(
            "### Detailed Research"
        )

        detail_tabs = st.tabs(
            [
                "Fundamentals",
                "Market",
                "News",
                "Sentiment",
                "Bull / Bear",
                "Risk",
            ]
        )


        with detail_tabs[0]:
            _fixed_text(
                analysis_result.get(
                    "fundamentals_report"
                )
            )


        with detail_tabs[1]:
            _fixed_text(
                analysis_result.get(
                    "market_report"
                )
            )


        with detail_tabs[2]:
            _fixed_text(
                analysis_result.get(
                    "news_report"
                )
            )


        with detail_tabs[3]:
            _fixed_text(
                analysis_result.get(
                    "sentiment_report"
                )
            )


        with detail_tabs[4]:

            bull_col, bear_col = (
                st.columns(2)
            )

            with bull_col:
                st.markdown(
                    "##### Bull Case"
                )

                _fixed_text(
                    analysis_result.get(
                        "bull_case"
                    )
                )

            with bear_col:
                st.markdown(
                    "##### Bear Case"
                )

                _fixed_text(
                    analysis_result.get(
                        "bear_case"
                    )
                )


        with detail_tabs[5]:

            st.markdown(
                "##### Risk Manager"
            )

            _fixed_text(
                analysis_result.get(
                    "risk_manager"
                )
            )

            with st.expander(
                "Research Manager"
            ):
                _fixed_text(
                    analysis_result.get(
                        "research_manager"
                    )
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

        elif universe == "Custom watchlist":
            st.warning(
                "Custom watchlists will be added in a later step. "
                "For now, select S&P 500, NASDAQ 100, or Dow Jones."
            )

        else:
            try:
                with st.spinner(
                    f"Screening {universe} across valuation, growth, "
                    "quality, momentum and risk..."
                ):
                    discovery_result = discover_stocks(
                        universe=universe,
                        horizon=horizon,
                        style=style,
                        risk_tolerance=risk,
                        enabled_factors={
                            "valuation": factor_valuation,
                            "growth": factor_growth,
                            "quality": factor_quality,
                            "momentum": factor_momentum,
                            "risk": factor_risk,
                        },
                        top_n=10,
                    )

                st.session_state["discovery_result"] = discovery_result
                st.session_state["discovery_error"] = None

            except Exception as exc:
                st.session_state["discovery_result"] = None
                st.session_state["discovery_error"] = str(exc)


    # ---------------------------------------------------------
    # DISCOVERY RESULTS
    # ---------------------------------------------------------

    discovery_error = st.session_state.get(
        "discovery_error"
    )

    discovery_result = st.session_state.get(
        "discovery_result"
    )

    if discovery_error:
        st.error(
            "The stock screener could not complete the search."
        )

        with st.expander("Show error details"):
            st.code(discovery_error)

    if (
        discovery_result is not None
        and not discovery_result.empty
    ):
        st.success(
            f"Found {len(discovery_result)} research candidates."
        )

        st.markdown("### Leading Candidates")

        top_candidates = discovery_result.head(3)
        candidate_columns = st.columns(len(top_candidates))

        for column, (_, row) in zip(
            candidate_columns,
            top_candidates.iterrows(),
        ):
            sector_value = row.get("sector", "")
            sector_text = (
                sector_value
                if isinstance(sector_value, str) and sector_value.strip()
                else "Sector unavailable"
            )

            name_value = row.get("name", "")
            company_name = (
                name_value
                if isinstance(name_value, str) and name_value.strip()
                else row["symbol"]
            )

            with column:
                card_html = (
                    f'<div class="metric-card">'
                    f'<div class="metric-label">'
                    f'#{int(row["rank"])} · {sector_text}'
                    f'</div>'
                    f'<div class="metric-value">'
                    f'{row["symbol"]}'
                    f'</div>'
                    f'<div style="color:#a1a1aa;'
                    f'font-size:0.82rem;'
                    f'margin-top:4px;'
                    f'min-height:38px;">'
                    f'{company_name}'
                    f'</div>'
                    f'<div style="margin-top:12px;'
                    f'font-size:1.15rem;'
                    f'font-weight:650;">'
                    f'{row["quant_score"]:.1f}'
                    f'<span style="color:#71717a;'
                    f'font-size:0.72rem;'
                    f'font-weight:400;">'
                    f' / 100'
                    f'</span>'
                    f'</div>'
                    f'</div>'
                )

                st.markdown(
                    card_html,
                    unsafe_allow_html=True,
                )

        st.write("")
        st.markdown("### Factor Breakdown")

        display_frame = discovery_result[
            [
                "rank",
                "symbol",
                "name",
                "quant_score",
                "valuation_score",
                "growth_score",
                "quality_score",
                "momentum_score",
                "risk_score",
            ]
        ].copy()

        score_columns = [
            "quant_score",
            "valuation_score",
            "growth_score",
            "quality_score",
            "momentum_score",
            "risk_score",
        ]

        display_frame[score_columns] = (
            display_frame[score_columns].round(1)
        )

        display_frame = display_frame.rename(
            columns={
                "rank": "Rank",
                "symbol": "Ticker",
                "name": "Company",
                "quant_score": "Overall",
                "valuation_score": "Valuation",
                "growth_score": "Growth",
                "quality_score": "Quality",
                "momentum_score": "Momentum",
                "risk_score": "Risk",
            }
        )

        st.dataframe(
            display_frame,
            hide_index=True,
            width="stretch",
            column_config={
                "Rank": st.column_config.NumberColumn(
                    width="small",
                    format="%d",
                ),
                "Ticker": st.column_config.TextColumn(
                    width="small",
                ),
                "Company": st.column_config.TextColumn(
                    width="large",
                ),
                "Overall": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Valuation": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Growth": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Quality": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Momentum": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Risk": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
            },
        )

        st.caption(
            "Quant scores are screening signals, not investment recommendations. "
            "The next stage will run TradingAgents on selected candidates."
        )


        st.write("")
        st.divider()

        st.markdown("### TradingAgents Deep Research")

        st.caption(
            "The Quant Screener narrows the universe first. "
            "TradingAgents can now perform multi-agent research "
            "on the highest-ranked candidates."
        )

        deep_col1, deep_col2 = st.columns(2)

        with deep_col1:
            deep_top_k = st.selectbox(
                "Candidates to analyze",
                [1, 2, 3],
                index=0,
                format_func=lambda value: f"Top {value}",
                key="discovery_deep_top_k",
            )

        with deep_col2:
            deep_analysis_date = st.date_input(
                "Deep analysis date",
                value=date.today(),
                key="discovery_deep_date",
            )

        run_deep_discovery = st.button(
            "Run TradingAgents deep research",
            type="primary",
            width="stretch",
            key="run_deep_discovery",
        )

        if run_deep_discovery:
            try:
                with st.spinner(
                    f"TradingAgents is researching the top "
                    f"{deep_top_k} candidate(s)..."
                ):
                    deep_results = analyze_discovery_candidates(
                        discovery_result=discovery_result,
                        analysis_date=deep_analysis_date,
                        top_k=deep_top_k,
                        research_depth="Shallow",
                    )

                st.session_state[
                    "discovery_deep_results"
                ] = deep_results

                st.session_state[
                    "discovery_deep_error"
                ] = None

            except Exception as exc:
                st.session_state[
                    "discovery_deep_results"
                ] = None

                st.session_state[
                    "discovery_deep_error"
                ] = str(exc)

        deep_error = st.session_state.get(
            "discovery_deep_error"
        )

        deep_results = st.session_state.get(
            "discovery_deep_results"
        )

        if deep_error:
            st.error(
                "TradingAgents deep research could not be completed."
            )

            with st.expander("Show error details"):
                st.code(deep_error)

        if deep_results:
            completed_count = sum(
                1
                for item in deep_results
                if item.get("status") == "completed"
            )

            st.success(
                f"Deep research completed for "
                f"{completed_count} candidate(s)."
            )

            summary_frame = discovery_summary_frame(
                deep_results
            )

            if not summary_frame.empty:
                summary_frame[
                    "Quant Score"
                ] = summary_frame[
                    "Quant Score"
                ].round(1)

                st.markdown(
                    "#### Quant + TradingAgents Summary"
                )

                st.dataframe(
                    summary_frame,
                    hide_index=True,
                    width="stretch",
                )

            st.markdown(
                "#### Candidate Research"
            )

            for item in deep_results:
                ticker = item.get(
                    "ticker",
                    "Unknown",
                )

                company = item.get(
                    "company",
                    ticker,
                )

                quant_score = item.get(
                    "quant_score"
                )

                rating = (
                    item.get("rating")
                    or "No rating"
                )

                status = item.get(
                    "status"
                )

                if status == "failed":
                    with st.expander(
                        f"{ticker} · Analysis failed"
                    ):
                        st.error(
                            item.get("error")
                            or "Unknown error."
                        )

                    continue

                label = (
                    f"{ticker} · {company} · "
                    f"Quant {quant_score:.1f} · "
                    f"{rating}"
                )

                with st.expander(
                    label,
                    expanded=False,
                ):
                    st.markdown(
                        "##### Final Investment View"
                    )

                    final_view = (
                        item.get(
                            "final_decision"
                        )
                        or item.get(
                            "investment_plan"
                        )
                        or "No final view returned."
                    )

                    st.markdown(
                        final_view
                    )

                    research_manager = item.get(
                        "research_manager"
                    )

                    if research_manager:
                        st.markdown(
                            "##### Research Manager"
                        )
                        st.markdown(
                            research_manager
                        )

                    bull_col, bear_col = st.columns(
                        2
                    )

                    with bull_col:
                        st.markdown(
                            "##### Bull Case"
                        )
                        st.markdown(
                            item.get(
                                "bull_case"
                            )
                            or "No bull case returned."
                        )

                    with bear_col:
                        st.markdown(
                            "##### Bear Case"
                        )
                        st.markdown(
                            item.get(
                                "bear_case"
                            )
                            or "No bear case returned."
                        )

                    risk_manager = item.get(
                        "risk_manager"
                    )

                    if risk_manager:
                        st.markdown(
                            "##### Risk Manager"
                        )
                        st.markdown(
                            risk_manager
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