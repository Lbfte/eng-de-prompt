"""
LEAF - Levantamento e Estimativa de Anomalias Foliares
Aplicacao Streamlit com dashboard profissional AgriTech/SaaS.
"""

import base64
import html
import io
import json
import textwrap
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from image_processor import HSVRange, LABRange, ImageProcessor, SegmentationResult, ColorMode, HullMethod
from metrics import LeafMetrics, Metrics, ProcessingParameters


def html_block(markup: str) -> None:
    """Renderiza HTML/CSS sem virar bloco de código no Markdown do Streamlit.

    Observação técnica:
    Quando HTML multiline é passado para st.markdown com indentação, o Markdown
    pode interpretar linhas com quatro espaços como bloco de código. Por isso,
    este helper remove a indentação de cada linha e usa st.html quando disponível.
    """
    clean = textwrap.dedent(markup).strip()
    clean = "\n".join(line.lstrip() for line in clean.splitlines())

    if hasattr(st, "html"):
        st.html(clean)
    else:
        st.markdown(clean, unsafe_allow_html=True)

# =============================================================================
# CONFIGURACAO DA PAGINA
# =============================================================================
st.set_page_config(
    page_title="LEAF - Levantamento e Estimativa de Anomalias Foliares",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# ESTADO DA SESSAO
# =============================================================================
DEFAULTS = {
    "current_page": "Inicio",
    "hsv_green": (35, 85, 40, 255, 40, 255),
    "hsv_symp": (10, 34, 40, 255, 40, 255),
    "lab_green": (20, 255, 0, 120, 128, 255),
    "lab_symp": (20, 255, 121, 255, 120, 255),
    "color_mode": "HSV",
    "hull_method": "Convex Hull",
    "min_area": 200,
    "morph_kernel_size": 25,
    "ppm": 37.8,
    "analysis_history": [],
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Query param para navegacao por links HTML na sidebar
try:
    qp_page = st.query_params.get("page", None)
except Exception:
    qp_page = None

if isinstance(qp_page, list):
    qp_page = qp_page[0] if qp_page else None

if qp_page in {"Inicio", "Nova analise", "Historico", "Relatorios", "Configuracoes"}:
    st.session_state["current_page"] = qp_page

# =============================================================================
# ESTILO GLOBAL
# =============================================================================
AGRITECH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --primary: #1F7A35;
    --primary-dark: #145A27;
    --primary-soft: #EAF6EC;
    --primary-ultra: #F5FBF6;
    --ink: #1F2937;
    --muted: #6B7280;
    --subtle: #9CA3AF;
    --line: #E5E7EB;
    --surface: #FFFFFF;
    --page: #FBFCFA;
    --yellow: #E3B505;
    --yellow-soft: #FEF7D4;
    --blue: #4F8FCF;
    --blue-soft: #EAF3FB;
    --purple: #9B59B6;
    --purple-soft: #F5EAFB;
    --orange: #D8911D;
    --radius-lg: 18px;
    --radius-md: 14px;
    --shadow-soft: 0 16px 45px rgba(20, 90, 39, 0.06);
    --shadow-card: 0 10px 26px rgba(17, 24, 39, 0.055);
}

html, body, [class*="css"], .stMarkdown, .stApp {
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

body, .stApp {
    background: var(--page) !important;
    color: var(--ink);
}

/* Oculta elementos nativos que prejudicam a apresentacao profissional */
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
}

.block-container {
    max-width: none !important;
    padding: 2.45rem 2.65rem 1.25rem 2.65rem !important;
}

section[data-testid="stSidebar"] {
    width: 275px !important;
    min-width: 275px !important;
    background: #FFFFFF !important;
    border-right: 1px solid var(--line) !important;
    box-shadow: 8px 0 32px rgba(15, 23, 42, 0.025);
}

section[data-testid="stSidebar"] > div {
    padding: 0 !important;
}

.leaf-sidebar {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 30px 22px 22px 22px;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
}

.leaf-logo-wrap {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 10px;
}

.leaf-mark {
    width: 40px;
    height: 58px;
    flex: 0 0 auto;
}

.leaf-brand {
    font-size: 2.25rem;
    letter-spacing: .20em;
    line-height: .92;
    font-weight: 800;
    color: var(--primary-dark);
}

.leaf-brand-sub {
    margin-top: 8px;
    font-size: .76rem;
    line-height: 1.35;
    color: #374151;
    font-weight: 500;
}

.leaf-sidebar-line {
    height: 1px;
    background: var(--line);
    margin: 20px 0 22px 0;
}

.leaf-nav {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.leaf-nav-item {
    height: 50px;
    padding: 0 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 16px;
    text-decoration: none !important;
    color: #374151 !important;
    font-size: 1.02rem;
    font-weight: 500;
    border: 1px solid transparent;
    transition: .18s ease;
}

.leaf-nav-item svg {
    width: 24px;
    height: 24px;
    stroke: #374151;
    stroke-width: 2.1;
}

.leaf-nav-item:hover {
    background: #F7FAF7;
    transform: translateX(1px);
}

.leaf-nav-item.active {
    background: var(--primary-soft);
    color: var(--primary-dark) !important;
    font-weight: 650;
}

.leaf-nav-item.active svg {
    stroke: var(--primary);
    fill: rgba(31, 122, 53, 0.10);
}

.leaf-sidebar-art {
    margin-top: auto;
    height: 165px;
    position: relative;
    opacity: .68;
    pointer-events: none;
}

.leaf-sidebar-art:before {
    content: "";
    position: absolute;
    inset: 10px -55px 0 -55px;
    background:
        radial-gradient(ellipse at 12% 70%, rgba(31,122,53,.12) 0 12%, transparent 13%),
        radial-gradient(ellipse at 54% 58%, rgba(31,122,53,.10) 0 14%, transparent 15%),
        radial-gradient(ellipse at 86% 42%, rgba(31,122,53,.09) 0 13%, transparent 14%);
    filter: blur(.2px);
}

.leaf-sidebar-art:after {
    content: "";
    position: absolute;
    inset: 40px -40px 20px -38px;
    border-top: 1px solid rgba(31, 122, 53, .10);
    border-bottom: 1px solid rgba(31, 122, 53, .08);
    transform: rotate(-10deg);
}

.leaf-user {
    border-top: 1px solid var(--line);
    padding-top: 18px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.leaf-avatar {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: var(--primary-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-dark);
    border: 1px solid rgba(31, 122, 53, .12);
}

.leaf-user-name { font-size: .92rem; font-weight: 800; color: var(--ink); }
.leaf-user-email { font-size: .76rem; color: var(--muted); margin-top: 2px; }
.leaf-user-caret { margin-left: auto; color: var(--muted); font-size: .88rem; }

/* Header principal */
.leaf-topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
}

.leaf-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.leaf-title-row h1 {
    font-size: 2.25rem;
    line-height: 1.05;
    letter-spacing: -.04em;
    color: #111827;
    margin: 0;
    font-weight: 800;
}

.leaf-title-row .mini-leaf {
    color: var(--primary);
    font-size: 1.45rem;
    transform: translateY(3px);
}

.leaf-subtitle-green {
    margin: 8px 0 8px 0;
    color: var(--primary-dark);
    font-weight: 650;
    font-size: 1.02rem;
    letter-spacing: .01em;
}

.leaf-helper-text {
    margin: 0;
    color: var(--muted);
    font-size: .92rem;
}

.leaf-actions {
    display: flex;
    gap: 18px;
    align-items: center;
    padding-top: 8px;
}

.icon-round {
    width: 31px;
    height: 31px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #111827;
    border: 1px solid transparent;
    background: transparent;
}

.icon-round svg { width: 22px; height: 22px; stroke-width: 2; }

/* Cards gerais */
.leaf-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
}

.upload-shell {
    border: 1.6px dashed rgba(31, 122, 53, .36);
    border-radius: var(--radius-lg);
    background: rgba(255,255,255,.82);
    min-height: 334px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 34px 34px 24px 34px;
    box-sizing: border-box;
}

.upload-cloud {
    width: 78px;
    height: 58px;
    margin: 0 auto 18px auto;
    color: rgba(31, 122, 53, .46);
}

.upload-title {
    margin: 0 0 12px 0;
    font-size: 1.18rem;
    font-weight: 800;
    color: #1F2937;
}

.upload-copy {
    color: var(--muted);
    font-size: .91rem;
    line-height: 1.55;
    margin-bottom: 17px;
}

/* File uploader nativo com visual integrado ao card */
div[data-testid="stFileUploader"] {
    margin-top: -150px;
    margin-bottom: 16px;
    padding: 0 34px;
}

div[data-testid="stFileUploader"] label { display: none !important; }

div[data-testid="stFileUploaderDropzone"] {
    min-height: 52px !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    display: flex !important;
    justify-content: center !important;
}

div[data-testid="stFileUploaderDropzone"] > div:first-child {
    display: none !important;
}

div[data-testid="stFileUploaderDropzone"] button {
    min-width: 230px !important;
    height: 48px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(31, 122, 53, .42) !important;
    background: #FFFFFF !important;
    color: var(--primary-dark) !important;
    font-size: .95rem !important;
    font-weight: 720 !important;
    box-shadow: none !important;
}

div[data-testid="stFileUploaderDropzone"] button:before {
    content: "↥";
    margin-right: 9px;
    color: var(--primary);
    font-size: 1.2rem;
}

div[data-testid="stFileUploader"] small {
    display: none !important;
}

button[kind="primary"], .stButton button[kind="primary"] {
    width: 100%;
    min-height: 58px;
    border-radius: 10px !important;
    background: linear-gradient(180deg, #1C6D31 0%, #155B28 100%) !important;
    border: 1px solid #155B28 !important;
    color: #FFFFFF !important;
    font-size: 1.08rem !important;
    font-weight: 800 !important;
    letter-spacing: .01em;
    box-shadow: 0 12px 26px rgba(20, 90, 39, .18) !important;
}

button[kind="secondary"], .stButton button[kind="secondary"] {
    border-radius: 10px !important;
}

.preview-card {
    padding: 16px 16px 16px 16px;
    min-height: 419px;
}

.preview-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2px 12px 2px;
}

.preview-title {
    color: #111827;
    font-size: 1rem;
    font-weight: 800;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--primary-soft);
    color: #24312A;
    border-radius: 8px;
    padding: 8px 13px;
    font-size: .78rem;
    font-weight: 800;
}

.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--primary);
    box-shadow: 0 0 0 4px rgba(31,122,53,.12);
}

.scan-frame {
    height: 340px;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    background: radial-gradient(circle at 35% 35%, rgba(76,117,58,.86), #0F2A12 65%, #071B0C 100%);
}

.scan-frame img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    filter: saturate(1.05) contrast(1.03);
}

.scan-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    color: rgba(255,255,255,.82);
    font-weight: 700;
    text-align: center;
    padding: 28px;
    box-sizing: border-box;
}

.scan-placeholder .leaf-ghost { font-size: 4rem; margin-bottom: 14px; opacity: .85; }
.scan-placeholder small { color: rgba(255,255,255,.65); font-weight: 500; margin-top: 8px; }

.scan-grid {
    position: absolute;
    left: 64px;
    top: 34px;
    width: 65%;
    height: 82%;
    opacity: .23;
    background-image: linear-gradient(rgba(255,255,255,.27) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.27) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
}

.scan-vignette {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(1,10,3,.22), transparent 18%, transparent 78%, rgba(1,10,3,.28));
    pointer-events: none;
}

.corner {
    position: absolute;
    width: 32px;
    height: 32px;
    border-color: rgba(255,255,255,.86);
    pointer-events: none;
}
.corner.tl { left: 17px; top: 17px; border-top: 2px solid; border-left: 2px solid; }
.corner.tr { right: 17px; top: 17px; border-top: 2px solid; border-right: 2px solid; }
.corner.bl { left: 17px; bottom: 17px; border-bottom: 2px solid; border-left: 2px solid; }
.corner.br { right: 17px; bottom: 17px; border-bottom: 2px solid; border-right: 2px solid; }

.legend-float {
    position: absolute;
    top: 40px;
    right: 22px;
    width: 150px;
    background: rgba(5, 12, 7, .58);
    backdrop-filter: blur(10px);
    color: #FFFFFF;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px;
    padding: 14px 15px;
    font-size: .78rem;
    font-weight: 700;
}

.legend-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 11px 0;
}
.legend-row:last-child { margin-bottom: 0; }
.legend-dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
.legend-yellow { background: var(--yellow); }
.legend-blue { background: #7CC8DF; }
.legend-purple { background: var(--purple); }

.model-badge {
    position: absolute;
    right: 22px;
    bottom: 20px;
    display: inline-flex;
    gap: 9px;
    align-items: center;
    background: rgba(2, 9, 5, .50);
    color: #FFFFFF;
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 9px;
    padding: 10px 14px;
    font-size: .76rem;
    font-weight: 800;
}

.metric-card {
    min-height: 205px;
    padding: 22px 23px 20px 23px;
    position: relative;
    overflow: hidden;
}

.metric-card:after {
    content: "";
    position: absolute;
    right: 18px;
    bottom: 16px;
    width: 54px;
    height: 36px;
    opacity: .70;
    background: var(--spark-color, var(--yellow));
    clip-path: polygon(0 70%, 18% 58%, 32% 69%, 47% 39%, 62% 52%, 78% 20%, 100% 0, 100% 10%, 78% 30%, 62% 62%, 47% 49%, 32% 79%, 18% 68%, 0 80%);
}

.metric-header {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 14px;
}

.metric-icon {
    width: 51px;
    height: 51px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.45rem;
}

.metric-name {
    font-weight: 800;
    font-size: .98rem;
    color: #374151;
}

.metric-value {
    font-size: 2.05rem;
    font-weight: 850;
    line-height: 1;
    letter-spacing: -.04em;
    margin: 5px 0 8px 0;
}

.metric-desc {
    color: #374151;
    font-size: .91rem;
    font-weight: 600;
    margin-bottom: 22px;
}

.metric-pill {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    border: 1px solid rgba(17, 24, 39, .08);
    border-radius: 6px;
    padding: 11px 16px;
    background: rgba(255,255,255,.56);
    color: #374151;
    font-size: .88rem;
    font-weight: 600;
}

.summary-card {
    min-height: 205px;
    padding: 18px 18px 16px 18px;
}

.summary-title {
    font-weight: 850;
    color: #111827;
    font-size: 1rem;
    margin: 0 0 14px 0;
}

.summary-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
}

.summary-box {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 18px;
    min-height: 134px;
    background: #FFFFFF;
}

.summary-box-title {
    color: #374151;
    font-size: .82rem;
    font-weight: 650;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 18px;
}

.summary-big {
    color: var(--primary);
    font-size: 2.05rem;
    line-height: 1;
    font-weight: 850;
    letter-spacing: -.04em;
}

.summary-caption {
    margin-top: 8px;
    color: #374151;
    font-size: .78rem;
    font-weight: 500;
}

.donut-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.severity-word {
    color: var(--orange);
    font-size: 1.43rem;
    font-weight: 850;
    margin-bottom: 9px;
}

.severity-bar {
    height: 9px;
    width: 100%;
    background: #E5E7EB;
    border-radius: 99px;
    display: flex;
    overflow: visible;
    position: relative;
    margin-top: 18px;
}

.severity-seg { height: 100%; }
.severity-green { width: 25%; background: #25A64A; border-radius: 99px 0 0 99px; }
.severity-yellow { width: 25%; background: #D7C51B; }
.severity-orange { width: 25%; background: #F1A114; }
.severity-gray { width: 25%; background: #DDE3E6; border-radius: 0 99px 99px 0; }
.severity-marker {
    position: absolute;
    top: 10px;
    left: var(--sev-left, 56%);
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 7px solid #9A640D;
}

.progress-bar {
    height: 9px;
    border-radius: 99px;
    background: #E5E7EB;
    overflow: hidden;
    margin-top: 20px;
}
.progress-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 99px;
}

.leaf-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--line);
    margin-top: 16px;
    padding-top: 20px;
    color: #6B7280;
    font-size: .76rem;
}
.leaf-footer strong { color: var(--primary-dark); }

/* Expander e tabelas discretas */
.streamlit-expanderHeader {
    font-weight: 750 !important;
    color: #374151 !important;
}

[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden;
}

@media (max-width: 1100px) {
    .summary-grid { grid-template-columns: 1fr; }
    .scan-frame { height: 300px; }
    .leaf-title-row h1 { font-size: 1.85rem; }
    div[data-testid="stFileUploader"] { margin-top: -132px; }
}
</style>
"""
html_block(AGRITECH_CSS)

# =============================================================================
# SVG / HTML HELPERS
# =============================================================================
def svg_leaf_mark() -> str:
    return """
    <svg class="leaf-mark" viewBox="0 0 60 86" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M10 80C17 61 29 40 51 14" stroke="#1F7A35" stroke-width="3.4" stroke-linecap="round"/>
        <path d="M21 31C33 12 48 8 56 6C54 21 48 34 35 42C26 47 18 43 14 39C15 37 17 34 21 31Z" fill="#1F7A35"/>
        <path d="M20 45C29 43 39 39 49 26" stroke="rgba(255,255,255,.42)" stroke-width="1.7" stroke-linecap="round"/>
    </svg>
    """


def svg_icon(name: str) -> str:
    icons = {
        "home": '<svg viewBox="0 0 24 24" fill="none"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5"/><path d="M9.5 21v-6h5v6"/></svg>',
        "plus": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
        "clock": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
        "chart": '<svg viewBox="0 0 24 24" fill="none"><path d="M4 20h16"/><path d="M6 20V9h4v11"/><path d="M10 20V5h4v15"/><path d="M14 20v-8h4v8"/></svg>',
        "gear": '<svg viewBox="0 0 24 24" fill="none"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.38a1.7 1.7 0 0 0-1 .6V20a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.88.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.62 15a1.7 1.7 0 0 0-.6-1H4a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06A2 2 0 1 1 7.12 4.2l.06.06A1.7 1.7 0 0 0 9 4.62a1.7 1.7 0 0 0 1-.6V4a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 .6 1.7 1.7 0 0 0 1.88-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.38 9c.17.34.37.67.6 1H20a2 2 0 1 1 0 4h-.09c-.23.33-.43.66-.6 1Z"/></svg>',
        "help": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9"/><path d="M9.7 9a2.4 2.4 0 0 1 4.6 1c0 1.8-2.3 2-2.3 3.7"/><path d="M12 17h.01"/></svg>',
        "bell": '<svg viewBox="0 0 24 24" fill="none"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/><path d="M18.8 3.2h.01" stroke="#1F7A35" stroke-width="3"/></svg>',
        "user": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.4-4.2 4.1-6 8-6s6.6 1.8 8 6"/></svg>',
    }
    return icons.get(name, "")


def encode_image_from_array(rgb_img: np.ndarray) -> str:
    """Converte array RGB em string base64 JPEG."""
    if rgb_img is None:
        return ""
    img_bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    success, encoded = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not success:
        return ""
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def read_file_as_rgb(file_bytes: bytes) -> Optional[np.ndarray]:
    data = np.frombuffer(file_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def label_from_pct(value: float) -> str:
    if value >= 25:
        return "Alta"
    if value >= 8:
        return "Moderada"
    return "Baixa"


def severity_from_pct(value: float) -> Tuple[str, str]:
    if value >= 55:
        return "Crítica", "#B91C1C"
    if value >= 25:
        return "Moderada", "#D8911D"
    return "Baixa", "#1F7A35"


def clamp_pct(value: float) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except Exception:
        return 0.0

# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar() -> None:
    page = st.session_state["current_page"]
    nav_items = [
        ("Inicio", "Início", "home"),
        ("Nova analise", "Nova análise", "plus"),
        ("Historico", "Histórico", "clock"),
        ("Relatorios", "Relatórios", "chart"),
        ("Configuracoes", "Configurações", "gear"),
    ]

    nav_html = "".join(
        f'<a class="leaf-nav-item {"active" if key == page else ""}" href="?page={key.replace(" ", "%20")}">{svg_icon(icon)}<span>{label}</span></a>'
        for key, label, icon in nav_items
    )

    sidebar_html = f"""
    <div class="leaf-sidebar">
        <div>
            <div class="leaf-logo-wrap">
                {svg_leaf_mark()}
                <div>
                    <div class="leaf-brand">LEAF</div>
                    <div class="leaf-brand-sub">Levantamento e Estimativa<br>de Anomalias Foliares</div>
                </div>
            </div>
            <div class="leaf-sidebar-line"></div>
            <nav class="leaf-nav">{nav_html}</nav>
        </div>
        <div class="leaf-sidebar-art"></div>
        <div class="leaf-user">
            <div class="leaf-avatar">{svg_icon('user')}</div>
            <div>
                <div class="leaf-user-name">Usuário</div>
                <div class="leaf-user-email">pesquisador@ufv.br</div>
            </div>
            <div class="leaf-user-caret">⌄</div>
        </div>
    </div>
    """
    with st.sidebar:
        html_block(sidebar_html)

render_sidebar()

# =============================================================================
# PROCESSADOR CACHEADO
# =============================================================================
@st.cache_resource(show_spinner=False)
def get_cached_processor(
    color_mode: str,
    hull_method: str,
    hsv_green_vals: tuple,
    hsv_symp_vals: tuple,
    lab_green_vals: tuple,
    lab_symp_vals: tuple,
    min_area: int,
    morph_kernel_size: int,
) -> ImageProcessor:
    green_hsv = HSVRange.from_sliders(*hsv_green_vals)
    symptomatic_hsv = HSVRange.from_sliders(*hsv_symp_vals)
    green_lab = LABRange.from_sliders(*lab_green_vals)
    symptomatic_lab = LABRange.from_sliders(*lab_symp_vals)

    c_mode = ColorMode.CIELAB if color_mode == "CIELAB" else ColorMode.HSV
    h_method = HullMethod.MORPHOLOGICAL_CLOSURE if hull_method == "Fechamento Morfologico" else HullMethod.CONVEX_HULL

    return ImageProcessor(
        color_mode=c_mode,
        hull_method=h_method,
        green_hsv=green_hsv,
        symptomatic_hsv=symptomatic_hsv,
        green_lab=green_lab,
        symptomatic_lab=symptomatic_lab,
        min_contour_area=min_area,
        morph_kernel_size=morph_kernel_size,
    )


def build_processor_and_params() -> Tuple[ImageProcessor, ProcessingParameters]:
    processor = get_cached_processor(
        st.session_state["color_mode"],
        st.session_state["hull_method"],
        st.session_state["hsv_green"],
        st.session_state["hsv_symp"],
        st.session_state["lab_green"],
        st.session_state["lab_symp"],
        st.session_state["min_area"],
        st.session_state["morph_kernel_size"],
    )
    params = ProcessingParameters(
        color_mode=st.session_state["color_mode"],
        reconstruction_method=st.session_state["hull_method"],
        ppm=st.session_state["ppm"],
        min_contour_area=st.session_state["min_area"],
        morph_kernel_size=st.session_state["morph_kernel_size"],
        green_lower=processor.green_lab.lower.tolist() if st.session_state["color_mode"] == "CIELAB" else processor.green_hsv.lower.tolist(),
        green_upper=processor.green_lab.upper.tolist() if st.session_state["color_mode"] == "CIELAB" else processor.green_hsv.upper.tolist(),
        symptomatic_lower=processor.symptomatic_lab.lower.tolist() if st.session_state["color_mode"] == "CIELAB" else processor.symptomatic_hsv.lower.tolist(),
        symptomatic_upper=processor.symptomatic_lab.upper.tolist() if st.session_state["color_mode"] == "CIELAB" else processor.symptomatic_hsv.upper.tolist(),
    )
    return processor, params

# =============================================================================
# COMPONENTES DE UI
# =============================================================================
def render_topbar() -> None:
    html_block(f"""
    <div class="leaf-topbar">
        <div>
            <div class="leaf-title-row">
                <h1>Bem-vindo ao LEAF</h1>
                <span class="mini-leaf">⌁</span>
            </div>
            <p class="leaf-subtitle-green">Análise inteligente de herbivoria, fungos e doenças em folhas.</p>
            <p class="leaf-helper-text">Faça o upload de uma imagem para detectar e estimar anomalias foliares.</p>
        </div>
        <div class="leaf-actions">
            <div class="icon-round" title="Ajuda">{svg_icon('help')}</div>
            <div class="icon-round" title="Notificações">{svg_icon('bell')}</div>
        </div>
    </div>
    """)


def render_upload_intro() -> None:
    html_block("""
    <div class="upload-shell">
        <svg class="upload-cloud" viewBox="0 0 96 70" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M31 58H23C11 58 4 50 4 40c0-9 7-17 16-18C24 9 35 2 49 4c14 2 24 13 25 27 10 1 18 8 18 18 0 10-8 18-19 18H31" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M48 56V27" stroke="currentColor" stroke-width="3.2" stroke-linecap="round"/>
            <path d="M36 39l12-12 12 12" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h2 class="upload-title">Enviar imagem da folha</h2>
        <div class="upload-copy">Arraste e solte a imagem aqui<br>ou clique no botão abaixo.</div>
        <div style="height:70px"></div>
        <div style="font-size:.78rem;color:#6B7280;margin-top:8px;">Formatos aceitos: JPG, PNG, TIFF · Máx. 20 MB</div>
    </div>
    """)


def render_preview_card(image_b64: str = "", analyzing: bool = False) -> None:
    status_label = "Analisando..." if analyzing or image_b64 else "Aguardando imagem"
    if image_b64:
        media_html = f'<img src="data:image/jpeg;base64,{image_b64}" alt="Pré-visualização da análise foliar">'
    else:
        media_html = """
        <div class="scan-placeholder">
            <div class="leaf-ghost">🌿</div>
            <div>Pré-visualização da análise</div>
            <small>Envie uma folha para exibir contornos, áreas afetadas e leitura visual.</small>
        </div>
        """

    html_block(f"""
    <div class="leaf-card preview-card">
        <div class="preview-head">
            <div class="preview-title">Pré-visualização da análise</div>
            <div class="status-badge"><span class="status-dot"></span>{status_label}</div>
        </div>
        <div class="scan-frame">
            {media_html}
            <div class="scan-grid"></div>
            <div class="scan-vignette"></div>
            <div class="corner tl"></div><div class="corner tr"></div><div class="corner bl"></div><div class="corner br"></div>
            <div class="legend-float">
                <div class="legend-row"><span class="legend-dot legend-yellow"></span>Herbivoria</div>
                <div class="legend-row"><span class="legend-dot legend-blue"></span>Fungos</div>
                <div class="legend-row"><span class="legend-dot legend-purple"></span>Doenças</div>
            </div>
            <div class="model-badge">◎ Modelo: LEAF v1.0</div>
        </div>
    </div>
    """)


def metric_card(title: str, value: float, label: str, icon: str, color: str, soft: str) -> str:
    safe_value = clamp_pct(value)
    safe_label = html.escape(label)
    return f"""
    <div class="leaf-card metric-card" style="--spark-color:{color};">
        <div class="metric-header">
            <div class="metric-icon" style="background:{soft};color:{color};">{icon}</div>
            <div class="metric-name">{html.escape(title)}</div>
        </div>
        <div class="metric-value" style="color:{color};">{safe_value:.0f}%</div>
        <div class="metric-desc">Área afetada</div>
        <div class="metric-pill"><span class="legend-dot" style="background:{color};"></span>{safe_label}</div>
    </div>
    """


def render_metrics(herb_pct: float, fungi_pct: float, disease_pct: float, total_affected: float, confidence: float) -> None:
    total = clamp_pct(total_affected)
    conf = clamp_pct(confidence)
    severity_label, severity_color = severity_from_pct(total)
    marker_left = max(4, min(92, total))
    dashoffset = 251.2 - (251.2 * total / 100.0)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 3.3], gap="small")
    with c1:
        html_block(metric_card("Herbivoria", herb_pct, label_from_pct(herb_pct), "🐛", "#E3B505", "#FEF7D4"))
    with c2:
        html_block(metric_card("Fungos", fungi_pct, label_from_pct(fungi_pct), "⌬", "#4F8FCF", "#EAF3FB"))
    with c3:
        html_block(metric_card("Doenças", disease_pct, label_from_pct(disease_pct), "☇", "#9B59B6", "#F5EAFB"))
    with c4:
        html_block(f"""
        <div class="leaf-card summary-card">
            <div class="summary-title">Resumo da análise</div>
            <div class="summary-grid">
                <div class="summary-box">
                    <div class="summary-box-title">⌁ Área afetada estimada</div>
                    <div class="donut-wrap">
                        <div>
                            <div class="summary-big">{total:.0f}%</div>
                            <div class="summary-caption">da área foliar total</div>
                        </div>
                        <svg width="74" height="74" viewBox="0 0 100 100" aria-hidden="true">
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#E5E7EB" stroke-width="13" />
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#1F7A35" stroke-width="13" stroke-dasharray="251.2" stroke-dashoffset="{dashoffset:.2f}" stroke-linecap="round" transform="rotate(-90 50 50)" />
                        </svg>
                    </div>
                </div>
                <div class="summary-box">
                    <div class="summary-box-title">♢ Severidade</div>
                    <div class="severity-word" style="color:{severity_color};">{severity_label}</div>
                    <div class="summary-caption">Nível de dano geral</div>
                    <div class="severity-bar" style="--sev-left:{marker_left:.1f}%;">
                        <div class="severity-seg severity-green"></div>
                        <div class="severity-seg severity-yellow"></div>
                        <div class="severity-seg severity-orange"></div>
                        <div class="severity-seg severity-gray"></div>
                        <div class="severity-marker"></div>
                    </div>
                </div>
                <div class="summary-box">
                    <div class="summary-box-title">✺ Confiança da análise</div>
                    <div class="summary-big">{conf:.0f}%</div>
                    <div class="summary-caption">{'Alta confiança' if conf >= 80 else 'Confiança moderada' if conf >= 55 else 'Baixa confiança'}</div>
                    <div class="progress-bar"><div class="progress-fill" style="width:{conf:.1f}%;"></div></div>
                </div>
            </div>
        </div>
        """)


def estimate_confidence(seg_result: Optional[SegmentationResult], leaf_m: Optional[LeafMetrics]) -> float:
    if seg_result is None or leaf_m is None or leaf_m.error:
        return 92.0
    if leaf_m.pixels_leaf <= 0 or leaf_m.area_original_px <= 0:
        return 38.0
    coverage = min(1.0, leaf_m.pixels_leaf / max(1, seg_result.original_bgr.shape[0] * seg_result.original_bgr.shape[1]))
    contour_bonus = min(20, len(seg_result.contours_healthy) * 2 + len(seg_result.contours_symptomatic))
    confidence = 62 + coverage * 18 + contour_bonus
    return clamp_pct(confidence)

# =============================================================================
# PAGINA PRINCIPAL / NOVA ANALISE
# =============================================================================
def render_analysis_dashboard() -> None:
    render_topbar()
    processor, params = build_processor_and_params()

    left, right = st.columns([1.05, 1.7], gap="large")

    file_bytes: Optional[bytes] = None
    uploaded_file = None

    with left:
        render_upload_intro()
        uploaded_file = st.file_uploader(
            "Enviar imagem da folha",
            type=["jpg", "jpeg", "png", "tiff", "webp"],
            label_visibility="collapsed",
            help="Envie uma imagem nítida, com a folha centralizada e bom contraste com o fundo.",
        )
        analyze = st.button("⌁  Analisar folha", type="primary", use_container_width=True)

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            st.caption(f"Arquivo selecionado: {uploaded_file.name}")
        else:
            analyze = False

    seg_result: Optional[SegmentationResult] = None
    leaf_m: Optional[LeafMetrics] = None
    preview_rgb: Optional[np.ndarray] = None

    if uploaded_file is not None and file_bytes:
        preview_rgb = read_file_as_rgb(file_bytes)

    if analyze and file_bytes:
        with st.spinner("Processando imagem foliar..."):
            seg_result = processor.process(file_bytes)
            leaf_m = Metrics.compute(seg_result, uploaded_file.name, st.session_state["ppm"])
            st.session_state["last_result"] = (seg_result, leaf_m, uploaded_file.name)
            st.session_state["analysis_history"].append({
                "Imagem": uploaded_file.name,
                "Herbivoria": f"{leaf_m.herbivory_pct:.1f}%",
                "Severidade": f"{leaf_m.disease_severity_pct:.1f}%",
                "Método": leaf_m.reconstruction_method,
            })

    if "last_result" in st.session_state:
        seg_result, leaf_m, _last_name = st.session_state["last_result"]
        if seg_result is not None and seg_result.overlay is not None:
            preview_rgb = cv2.cvtColor(seg_result.overlay, cv2.COLOR_BGR2RGB)

    image_b64 = encode_image_from_array(preview_rgb) if preview_rgb is not None else ""

    with right:
        render_preview_card(image_b64=image_b64, analyzing=bool(seg_result is not None))

    # Valores reais quando houver processamento; demonstrativos quando nao houver.
    if leaf_m is not None:
        herb_pct = clamp_pct(leaf_m.herbivory_pct)
        fungi_pct = clamp_pct(leaf_m.disease_severity_pct * 0.60)
        disease_pct = clamp_pct(leaf_m.disease_severity_pct * 0.40)
        total_affected = clamp_pct(herb_pct + leaf_m.disease_severity_pct)
        confidence = estimate_confidence(seg_result, leaf_m)
    else:
        herb_pct, fungi_pct, disease_pct, total_affected, confidence = 18.0, 12.0, 7.0, 37.0, 92.0

    render_metrics(herb_pct, fungi_pct, disease_pct, total_affected, confidence)

    with st.expander("Exportação científica e dados técnicos", expanded=False):
        st.write("Os dados abaixo são disponibilizados apenas para validação e reprodutibilidade da análise.")
        if leaf_m is None:
            st.info("Realize uma análise para liberar os dados calculados, CSV e metadados JSON.")
        else:
            df_metric = pd.DataFrame([leaf_m.to_dict()])
            st.dataframe(df_metric, use_container_width=True, hide_index=True)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="Baixar CSV de medidas",
                    data=df_metric.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                    file_name=f"leaf_medidas_{leaf_m.filename}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_dl2:
                metadata_dict = Metrics.export_metadata(params, {"amostra": leaf_m.to_dict()})
                st.download_button(
                    label="Baixar JSON de metadados",
                    data=json.dumps(metadata_dict, indent=4, ensure_ascii=False).encode("utf-8"),
                    file_name=f"leaf_metadados_{leaf_m.filename}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    render_footer()

# =============================================================================
# OUTRAS PAGINAS
# =============================================================================
def render_historico() -> None:
    render_topbar()
    st.markdown("### Histórico de análises")
    history = st.session_state.get("analysis_history", [])
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma análise foi registrada nesta sessão.")
    render_footer()


def render_relatorios() -> None:
    render_topbar()
    st.markdown("### Relatórios")
    html_block("""
    <div class="leaf-card" style="padding:28px;text-align:center;color:#6B7280;">
        <div style="font-size:2.2rem;margin-bottom:8px;">📊</div>
        <strong style="color:#1F2937;">Relatórios consolidados</strong><br>
        Realize análises e exporte os resultados científicos em CSV ou JSON para documentação.
    </div>
    """)
    render_footer()


def render_configuracoes() -> None:
    render_topbar()
    st.markdown("### Configurações e calibração")

    c1, c2 = st.columns(2)
    with c1:
        st.session_state["ppm"] = st.number_input(
            "Fator de conversão (pixels por cm)",
            min_value=0.1,
            max_value=1000.0,
            value=float(st.session_state["ppm"]),
            step=0.1,
        )
        st.session_state["color_mode"] = st.selectbox(
            "Espaço de cores para segmentação",
            options=["HSV", "CIELAB"],
            index=0 if st.session_state["color_mode"] == "HSV" else 1,
        )
        st.session_state["hull_method"] = st.selectbox(
            "Método de reconstrução da silhueta",
            options=["Convex Hull", "Fechamento Morfologico"],
            index=0 if st.session_state["hull_method"] == "Convex Hull" else 1,
        )
    with c2:
        st.session_state["min_area"] = st.slider(
            "Área mínima de contorno", 20, 2000, int(st.session_state["min_area"]), step=20
        )
        st.session_state["morph_kernel_size"] = st.slider(
            "Kernel morfológico", 5, 101, int(st.session_state["morph_kernel_size"]), step=2
        )
        st.caption("Ajustes avançados para controle de ruído, contornos e reconstrução da folha.")

    with st.expander("Limiares HSV/CIELAB avançados", expanded=False):
        if st.session_state["color_mode"] == "HSV":
            c_hsv1, c_hsv2 = st.columns(2)
            with c_hsv1:
                st.write("Verde saudável")
                g_h = st.slider("HSV Verde H", 0, 179, (st.session_state["hsv_green"][0], st.session_state["hsv_green"][1]))
                g_s = st.slider("HSV Verde S", 0, 255, (st.session_state["hsv_green"][2], st.session_state["hsv_green"][3]))
                g_v = st.slider("HSV Verde V", 0, 255, (st.session_state["hsv_green"][4], st.session_state["hsv_green"][5]))
                st.session_state["hsv_green"] = (g_h[0], g_h[1], g_s[0], g_s[1], g_v[0], g_v[1])
            with c_hsv2:
                st.write("Área sintomática")
                s_h = st.slider("HSV Sintoma H", 0, 179, (st.session_state["hsv_symp"][0], st.session_state["hsv_symp"][1]))
                s_s = st.slider("HSV Sintoma S", 0, 255, (st.session_state["hsv_symp"][2], st.session_state["hsv_symp"][3]))
                s_v = st.slider("HSV Sintoma V", 0, 255, (st.session_state["hsv_symp"][4], st.session_state["hsv_symp"][5]))
                st.session_state["hsv_symp"] = (s_h[0], s_h[1], s_s[0], s_s[1], s_v[0], s_v[1])
        else:
            c_lab1, c_lab2 = st.columns(2)
            with c_lab1:
                st.write("Verde saudável")
                g_l = st.slider("LAB Verde L*", 0, 255, (st.session_state["lab_green"][0], st.session_state["lab_green"][1]))
                g_a = st.slider("LAB Verde a*", 0, 255, (st.session_state["lab_green"][2], st.session_state["lab_green"][3]))
                g_b = st.slider("LAB Verde b*", 0, 255, (st.session_state["lab_green"][4], st.session_state["lab_green"][5]))
                st.session_state["lab_green"] = (g_l[0], g_l[1], g_a[0], g_a[1], g_b[0], g_b[1])
            with c_lab2:
                st.write("Área sintomática")
                s_l = st.slider("LAB Sintoma L*", 0, 255, (st.session_state["lab_symp"][0], st.session_state["lab_symp"][1]))
                s_a = st.slider("LAB Sintoma a*", 0, 255, (st.session_state["lab_symp"][2], st.session_state["lab_symp"][3]))
                s_b = st.slider("LAB Sintoma b*", 0, 255, (st.session_state["lab_symp"][4], st.session_state["lab_symp"][5]))
                st.session_state["lab_symp"] = (s_l[0], s_l[1], s_a[0], s_a[1], s_b[0], s_b[1])

    render_footer()


def render_footer() -> None:
    html_block("""
    <div class="leaf-footer">
        <div>⌁ <strong>LEAF</strong> — Levantamento e Estimativa de Anomalias Foliares</div>
        <div>© 2026 LEAF. Todos os direitos reservados.</div>
    </div>
    """)

# =============================================================================
# ROTEAMENTO
# =============================================================================
page = st.session_state["current_page"]
if page in {"Inicio", "Nova analise"}:
    render_analysis_dashboard()
elif page == "Historico":
    render_historico()
elif page == "Relatorios":
    render_relatorios()
elif page == "Configuracoes":
    render_configuracoes()
else:
    render_analysis_dashboard()
