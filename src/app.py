"""
Apex — RVGT Marketing Intelligence & Operations Platform

Entry point for the Streamlit multi-page application.
Run with: streamlit run src/app.py
"""
import streamlit as st
from src.config.brand import COLORS, GRADIENTS, TYPOGRAPHY, BORDER_RADIUS, MOTION
from src.config import settings
from src.components.page_chrome import page_chrome

st.set_page_config(
    page_title=f"{settings.APP_NAME} | RVGT Marketing Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

page_chrome(title="Home", show_header=False)

ff = TYPOGRAPHY["font_family"]

st.markdown(
    f"""
    <div style="margin-bottom: 1.75rem;">
        <h1 style="background:{GRADIENTS['blue_cyan']}; -webkit-background-clip:text;
                   -webkit-text-fill-color:transparent; background-clip:text;
                   font-family:{ff}; font-size:1.75rem;
                   font-weight:700; margin-bottom:0.15rem; line-height:1.2;
                   display:inline-block;">
            Welcome back, Tyler
        </h1>
        <p style="color:{COLORS['text_secondary']}; font-family:{ff};
                  font-size:0.8125rem; margin:0;">
            Select a module from the sidebar to get started.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

modules = [
    ("📊", "Executive Scorecard", "Top-line KPIs, alerts, and financial summary"),
    ("💰", "Spend Allocation", "Channel mix optimization and DMA performance"),
    ("📺", "Brand Media", "Brand awareness campaigns: reach, frequency, BEI, and life events"),
    ("📢", "Performance Media", "Paid search, social, and programmatic with CPL and ROAS"),
    ("🔎", "SEO", "Organic rankings, keyword performance, and content gap analysis"),
    ("🤖", "AEO", "AI Engine Optimisation: LLM visibility score and competitive benchmarking"),
    ("🔻", "Acquisition Funnel", "Full funnel from Brand UOI to Active accounts"),
    ("🚀", "Product & Experience", "Digital product metrics, feature adoption, and UX signals"),
    ("⚙️", "Operations Command", "Launch calendar, capacity, and system health"),
    ("🧪", "Simulator", "Full-funnel acquisition modeling and scenario analysis"),
]

st.markdown(
    f"""
    <style>
    .apex-module-card {{
        background: {COLORS['glass_bg']};
        border: 1px solid {COLORS['glass_border']};
        border-radius: {BORDER_RADIUS['xl']};
        padding: 20px;
        margin-bottom: 16px;
        min-height: 120px;
        cursor: pointer;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: box-shadow {MOTION['duration_normal']} {MOTION['ease_out']},
                    transform {MOTION['duration_fast']} {MOTION['ease_out']},
                    border-color {MOTION['duration_normal']} {MOTION['ease_out']};
        position: relative;
    }}
    .apex-module-card:hover {{
        box-shadow: 0 8px 32px rgba(0, 117, 255, 0.18);
        transform: translateY(-3px);
        border-color: rgba(0, 117, 255, 0.3);
    }}
    .apex-module-card:hover .apex-module-arrow {{
        opacity: 1;
        transform: translateX(0);
    }}
    .apex-module-arrow {{
        opacity: 0;
        transform: translateX(-4px);
        transition: opacity {MOTION['duration_fast']} {MOTION['ease_out']},
                    transform {MOTION['duration_fast']} {MOTION['ease_out']};
        position: absolute;
        top: 20px;
        right: 16px;
        color: {COLORS['accent']};
        font-size: 1rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(3)
for i, (icon, name, desc) in enumerate(modules):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="apex-module-card">
                <span class="apex-module-arrow">→</span>
                <div style="font-size: 32px; margin-bottom: 10px; line-height: 1;">{icon}</div>
                <div style="font-weight: 600; font-size: 0.9375rem; color: {COLORS['text_primary']};
                            font-family: {ff}; margin-bottom: 4px;">{name}</div>
                <div style="font-size: 0.8125rem; color: {COLORS['text_secondary']};
                            font-family: {ff};">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
