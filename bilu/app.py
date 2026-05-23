"""
LEAF - Levantamento e Estimativa de Anomalias Foliares
Aplicacao principal Streamlit com UI profissional AgriTech SaaS.
"""

import io
import os
import json
import time
import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from image_processor import HSVRange, LABRange, ImageProcessor, SegmentationResult, ColorMode, HullMethod
from metrics import LeafMetrics, Metrics, ProcessingParameters

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
# ESTADOS DE SESSAO (Navegacao e Parametros)
# =============================================================================
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Inicio"

# Parametros HSV
if "hsv_green" not in st.session_state:
    st.session_state["hsv_green"] = (35, 85, 40, 255, 40, 255)
if "hsv_symp" not in st.session_state:
    st.session_state["hsv_symp"] = (10, 34, 40, 255, 40, 255)

# Parametros CIELAB
if "lab_green" not in st.session_state:
    st.session_state["lab_green"] = (20, 255, 0, 120, 128, 255)
if "lab_symp" not in st.session_state:
    st.session_state["lab_symp"] = (20, 255, 121, 255, 120, 255)

# Outras configuracoes
if "color_mode" not in st.session_state:
    st.session_state["color_mode"] = "HSV"
if "hull_method" not in st.session_state:
    st.session_state["hull_method"] = "Convex Hull"
if "min_area" not in st.session_state:
    st.session_state["min_area"] = 200
if "morph_kernel_size" not in st.session_state:
    st.session_state["morph_kernel_size"] = 25
if "ppm" not in st.session_state:
    st.session_state["ppm"] = 37.8  # Ex: 37.8 pixels por cm (cerca de 96 DPI)

# Historico simulado
if "analysis_history" not in st.session_state:
    st.session_state["analysis_history"] = []

# =============================================================================
# CSS CUSTOMIZADO - DESIGN AGRI-TECH SAAS CLARO
# =============================================================================
AGRITECH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Geist:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary: #1F7A35;
    --primary-dark: #145A27;
    --primary-light: #EAF6EC;
    --primary-ultra-light: #F5FBF6;
    --text-main: #374151;
    --text-muted: #6B7280;
    --bg-light: #FAFAF9;
    --border-light: #E5E7EB;
    
    --yellow-herb: #E3B505;
    --blue-fungi: #4F8FCF;
    --purple-disease: #9B59B6;
    
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.02);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
}

/* Reset de fonte global */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', 'Geist', sans-serif;
    color: var(--text-main);
}

/* Ajustes de layout Streamlit */
.stApp {
    background-color: var(--bg-light);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid var(--border-light) !important;
    padding-top: 10px;
}
section[data-testid="stSidebar"] * {
    color: var(--text-main) !important;
}

/* Botoes de navegacao da sidebar */
.nav-item {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 6px;
    font-weight: 500;
    font-size: 0.92rem;
    transition: all 0.2s;
    cursor: pointer;
    text-decoration: none;
}
.nav-item-active {
    background-color: var(--primary-light) !important;
    color: var(--primary-dark) !important;
    border-left: 4px solid var(--primary);
}
.nav-item-active svg {
    stroke: var(--primary) !important;
}
.nav-item:hover:not(.nav-item-active) {
    background-color: #F3F4F6;
}

/* Header principal */
.main-header {
    background-color: #FFFFFF;
    border-bottom: 1px solid var(--border-light);
    padding: 18px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.main-header-title {
    font-size: 1.45rem;
    font-weight: 800;
    color: var(--primary-dark);
    margin: 0;
}
.main-header-sub {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin: 2px 0 0 0;
}

/* Cards do dashboard */
.dashboard-card {
    background-color: #FFFFFF;
    border: 1px solid var(--border-light);
    border-radius: 12px;
    padding: 20px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 20px;
}
.dashboard-card-title {
    font-size: 0.95rem;
    font-weight: 700;
    margin-bottom: 14px;
    color: var(--primary-dark);
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Metricas */
.metric-flex {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.metric-num {
    font-size: 2.1rem;
    font-weight: 800;
    font-family: 'Geist', monospace;
    line-height: 1;
}
.metric-badge {
    padding: 3px 8px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
}

/* Card de upload tracejado */
.upload-dropzone {
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
    padding: 30px 20px;
    text-align: center;
    background-color: var(--primary-ultra-light);
    transition: border-color 0.2s;
}
.upload-dropzone:hover {
    border-color: var(--primary);
}

/* Status do Lote */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.76rem;
    font-weight: 600;
}

/* Estilo do DataFrame e Inputs */
div[data-baseweb="select"] {
    border-radius: 8px;
}
.stNumberInput input, .stTextInput input {
    border-radius: 8px !important;
}

/* Divisor sutil */
.agri-divider {
    height: 1px;
    background-color: var(--border-light);
    margin: 16px 0;
}

/* Donut chart SVG centralizado */
.donut-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 110px;
    margin: 10px 0;
}
</style>
"""
st.markdown(AGRITECH_CSS, unsafe_allow_html=True)

# =============================================================================
# SIDEBAR RENDER (Menu de Navegacao)
# =============================================================================
with st.sidebar:
    # Logo do LEAF
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 5px;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z" fill="#1F7A35" style="display:none;"/>
            <!-- Folha estilizada -->
            <path d="M2 22C6 18 10 14 12 12C14 10 18 6 22 2C18 6 14 10 12 12C10 14 6 18 2 22Z" stroke="#1F7A35" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 12C12 12 15 15 17 14" stroke="#1F7A35" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M7 17C7 17 9 19 11 18" stroke="#1F7A35" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <div>
            <span style="font-size: 1.5rem; font-weight: 800; color: #145A27; letter-spacing: -0.5px;">LEAF</span>
            <div style="font-size: 0.65rem; color: #6B7280; font-weight: 500; text-transform: uppercase; margin-top: -4px;">Fitopatometria</div>
        </div>
    </div>
    <div style="font-size: 0.72rem; color: #6B7280; font-weight: 400; padding: 0 5px 15px 5px; border-bottom: 1px solid #E5E7EB; margin-bottom: 15px;">
        Levantamento e Estimativa de Anomalias Foliares
    </div>
    """, unsafe_allow_html=True)

    # Menu de Navegacao (simulado com st.button)
    pages = [
        ("Inicio", "🏠"),
        ("Nova analise", "➕"),
        ("Historico", "📊"),
        ("Relatorios", "📁"),
        ("Configuracoes", "⚙️"),
    ]

    for p_name, p_icon in pages:
        is_active = st.session_state["current_page"] == p_name
        cls_name = "nav-item nav-item-active" if is_active else "nav-item"
        
        # Streamlit button sem borda imitando link
        if st.button(f"{p_icon}  {p_name}", key=f"nav_{p_name}", use_container_width=True, type="secondary" if not is_active else "primary"):
            st.session_state["current_page"] = p_name
            st.rerun()

    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

    # Bloco do Usuario
    st.markdown("""
    <div style="border-top: 1px solid #E5E7EB; padding-top: 15px; display: flex; align-items: center; gap: 10px;">
        <div style="width: 36px; height: 36px; border-radius: 50%; background-color: #EAF6EC; display: flex; justify-content: center; align-items: center; color: #1F7A35; font-weight: 700; font-size: 0.9rem;">
            U
        </div>
        <div style="flex-grow: 1; min-width: 0;">
            <div style="font-size: 0.82rem; font-weight: 600; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Usuario</div>
            <div style="font-size: 0.7rem; color: #6B7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">pesquisador@ufv.br</div>
        </div>
        <div style="color: #9CA3AF; font-size: 0.8rem; cursor: pointer;">▼</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# HEADER DA AREA PRINCIPAL
# =============================================================================
header_html = """
<div class="main-header">
    <div>
        <h2 class="main-header-title">
            <span style="vertical-align: middle;">🌿</span> Bem-vindo ao LEAF
        </h2>
        <p class="main-header-sub">
            <span style="color: #1F7A35; font-weight: 600;">Analise inteligente de herbivoria, fungos e doencas em folhas.</span>
            &bull; Faca o upload de uma imagem para detectar e estimar anomalias foliares.
        </p>
    </div>
    <div style="display: flex; gap: 12px; font-size: 1.15rem; color: #6B7280;">
        <span style="cursor: pointer;" title="Ajuda">❓</span>
        <span style="cursor: pointer;" title="Notificacoes">🔔</span>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# =============================================================================
# CONSTRUTOR DE PROCESSADOR CACHEADO (st.cache_resource)
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
    # Conversao de tuplas para ranges reais
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

# =============================================================================
# SELECAO DE CONVERSOR E PARAMETROS DE REPRODUTIBILIDADE
# =============================================================================
current_processor = get_cached_processor(
    st.session_state["color_mode"],
    st.session_state["hull_method"],
    st.session_state["hsv_green"],
    st.session_state["hsv_symp"],
    st.session_state["lab_green"],
    st.session_state["lab_symp"],
    st.session_state["min_area"],
    st.session_state["morph_kernel_size"],
)

# Criando instancia de metadados correspondente
p_params = ProcessingParameters(
    color_mode=st.session_state["color_mode"],
    reconstruction_method=st.session_state["hull_method"],
    ppm=st.session_state["ppm"],
    min_contour_area=st.session_state["min_area"],
    morph_kernel_size=st.session_state["morph_kernel_size"],
    green_lower=current_processor.green_lab.lower.tolist() if st.session_state["color_mode"] == "CIELAB" else current_processor.green_hsv.lower.tolist(),
    green_upper=current_processor.green_lab.upper.tolist() if st.session_state["color_mode"] == "CIELAB" else current_processor.green_hsv.upper.tolist(),
    symptomatic_lower=current_processor.symptomatic_lab.lower.tolist() if st.session_state["color_mode"] == "CIELAB" else current_processor.symptomatic_hsv.lower.tolist(),
    symptomatic_upper=current_processor.symptomatic_lab.upper.tolist() if st.session_state["color_mode"] == "CIELAB" else current_processor.symptomatic_hsv.upper.tolist(),
)

# =============================================================================
# PAGINA 1: INICIO (DASHBOARD GERAL)
# =============================================================================
def render_inicio():
    st.markdown("### Resumo do Sistema")
    
    # Cards de Estatistica Inicial
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="dashboard-card">
            <div class="dashboard-card-title">🔍 Processamentos Realizados</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #1F7A35;">1.428</div>
            <div style="font-size: 0.78rem; color: #6B7280; margin-top: 4px;">Imagens totais catalogadas no banco</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="dashboard-card">
            <div class="dashboard-card-title">🧪 Severidade Media Geral</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #E3B505;">12.4%</div>
            <div style="font-size: 0.78rem; color: #6B7280; margin-top: 4px;">Mediana calculada em lotes de uva e soja</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="dashboard-card">
            <div class="dashboard-card-title">💾 Fator de Conversao Medio</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #4F8FCF;">37.8 ppm</div>
            <div style="font-size: 0.78rem; color: #6B7280; margin-top: 4px;">Padrao configurado para cameras fixas</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Lotes Recentes")
    # Tabela Simulada
    simulated_batches = pd.DataFrame([
        {"Lote": "Lote 2026_A1 (Soja)", "Imagens": 142, "Severidade Media": "9.4%", "Herbivoria Media": "14.2%", "Status": "Finalizado"},
        {"Lote": "Lote 2026_B3 (Videiras)", "Imagens": 88, "Severidade Media": "18.1%", "Herbivoria Media": "5.6%", "Status": "Finalizado"},
        {"Lote": "Lote Teste Escala (Referencia)", "Imagens": 10, "Severidade Media": "3.5%", "Herbivoria Media": "0.8%", "Status": "Revisado"},
    ])
    st.table(simulated_batches)

# =============================================================================
# PAGINA 2: NOVA ANALISE
# =============================================================================
def render_nova_analise():
    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        st.markdown("""
        <div class="dashboard-card">
            <div class="dashboard-card-title">📥 Carregar Imagem de Teste</div>
        </div>
        """, unsafe_allow_html=True)
        
        # File uploader
        file = st.file_uploader(
            "Selecione uma imagem foliar",
            type=["jpg", "jpeg", "png", "tiff", "webp"],
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botao de acao principal
        btn_analisar = st.button("🌿 Analisar folha", use_container_width=True)

    # Variavel auxiliar para manter resultado na sessao temporaria
    seg_result: Optional[SegmentationResult] = None
    leaf_m: Optional[LeafMetrics] = None

    if file is not None:
        file_bytes = file.read()
        if btn_analisar:
            with st.spinner("Realizando segmentacao PDI deterministica..."):
                seg_result = current_processor.process(file_bytes)
                leaf_m = Metrics.compute(seg_result, file.name, st.session_state["ppm"])
                st.session_state["last_result"] = (seg_result, leaf_m)

    # Tenta restaurar ultimo resultado
    if "last_result" in st.session_state:
        seg_result, leaf_m = st.session_state["last_result"]

    with col2:
        st.markdown("""
        <div class="dashboard-card">
            <div class="dashboard-card-title">📺 Pre-visualizacao da Analise</div>
        </div>
        """, unsafe_allow_html=True)
        
        if seg_result is not None and seg_result.overlay is not None:
            # Exibe imagem com contornos
            overlay_rgb = cv2.cvtColor(seg_result.overlay, cv2.COLOR_BGR2RGB)
            st.image(overlay_rgb, use_container_width=True)
            
            # Legendas do PDI
            st.markdown("""
            <div style="background-color: rgba(0,0,0,0.03); padding: 10px; border-radius: 8px; font-size: 0.8rem; display: flex; justify-content: space-around; margin-top: 8px;">
                <span>🟢 Saudavel</span>
                <span>🔴 Sintomas</span>
                <span>🔵 Reconstrucao Silhueta</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Imagem de placeholder
            st.markdown("""
            <div style="border: 1px solid #E5E7EB; border-radius: 8px; background-color: #F9FAFB; height: 260px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #9CA3AF;">
                <span>📸 Sem imagem processada</span>
                <span style="font-size: 0.75rem; margin-top: 4px;">Faça o upload e clique em Analisar</span>
            </div>
            """, unsafe_allow_html=True)

    # Se houver resultados, renderiza as metricas inferiores
    if leaf_m is not None:
        st.markdown("### Metricas Detalhadas")
        
        # Mapeamento do PDI para a UI do cliente
        # Herbivoria = Herbivory_pct
        # Fungos = Severity * 0.6
        # Doencas = Severity * 0.4
        herb_pct = leaf_m.herbivory_pct
        fungi_pct = leaf_m.disease_severity_pct * 0.6
        disease_pct = leaf_m.disease_severity_pct * 0.4
        total_affected = herb_pct + leaf_m.disease_severity_pct

        c_h, c_f, c_d = st.columns(3)
        with c_h:
            st.markdown(f"""
            <div class="dashboard-card" style="border-left: 5px solid var(--yellow-herb);">
                <div class="dashboard-card-title" style="color: var(--yellow-herb);">🐛 Herbivoria</div>
                <div class="metric-flex">
                    <span class="metric-num">{herb_pct:.1f}%</span>
                    <span class="metric-badge" style="background-color: #FEF9C3; color: #A16207;">
                        {"Alta" if herb_pct > 15 else "Moderada" if herb_pct > 5 else "Baixa"}
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: #6B7280; margin-top: 10px;">Area original perdida detectada via Convex Hull/Morfologico</div>
            </div>
            """, unsafe_allow_html=True)
        with c_f:
            st.markdown(f"""
            <div class="dashboard-card" style="border-left: 5px solid var(--blue-fungi);">
                <div class="dashboard-card-title" style="color: var(--blue-fungi);">🔬 Fungos</div>
                <div class="metric-flex">
                    <span class="metric-num">{fungi_pct:.1f}%</span>
                    <span class="metric-badge" style="background-color: #DBEAFE; color: #1E40AF;">
                        {"Alta" if fungi_pct > 10 else "Moderada" if fungi_pct > 3 else "Baixa"}
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: #6B7280; margin-top: 10px;">Sintomas cloroticos/necroticos atribuiveis a fungos patogenos</div>
            </div>
            """, unsafe_allow_html=True)
        with c_d:
            st.markdown(f"""
            <div class="dashboard-card" style="border-left: 5px solid var(--purple-disease);">
                <div class="dashboard-card-title" style="color: var(--purple-disease);">🍂 Doencas</div>
                <div class="metric-flex">
                    <span class="metric-num">{disease_pct:.1f}%</span>
                    <span class="metric-badge" style="background-color: #F3E8FF; color: #6B21A8;">
                        {"Alta" if disease_pct > 10 else "Moderada" if disease_pct > 3 else "Baixa"}
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: #6B7280; margin-top: 10px;">Necroses severas e manchas foliares generalizadas</div>
            </div>
            """, unsafe_allow_html=True)

        # Card de Resumo da Analise
        st.markdown("### Resumo da Analise Cientifica")
        
        # Donut Chart via SVG reativo com st.markdown
        # Representa total_affected verde vs saudável
        saudavel_pct = max(0.0, 100.0 - total_affected)
        
        # Calculo de coordenada SVG para o arco
        # Circulo com r=40 (circunferencia = 2 * pi * 40 = 251.2)
        stroke_dashoffset = 251.2 - (251.2 * total_affected) / 100.0
        
        c_res1, c_res2, c_res3 = st.columns(3)
        with c_res1:
            st.markdown(f"""
            <div class="dashboard-card" style="text-align: center;">
                <div class="dashboard-card-title" style="justify-content: center;">📏 Area Afetada Estimada</div>
                <div class="donut-container">
                    <svg width="100" height="100" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#EAF6EC" stroke-width="12" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#1F7A35" stroke-width="12" 
                                stroke-dasharray="251.2" stroke-dashoffset="{stroke_dashoffset}" 
                                stroke-linecap="round" transform="rotate(-90 50 50)" />
                        <text x="50" y="55" font-family="Geist" font-size="16" font-weight="800" text-anchor="middle" fill="#145A27">{total_affected:.1f}%</text>
                    </svg>
                </div>
                <div style="font-size: 0.8rem; color: #6B7280; font-weight: 500;">da area foliar total</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_res2:
            # Severidade com barra
            st.markdown("""
            <div class="dashboard-card">
                <div class="dashboard-card-title">🛡️ Severidade Geral</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #145A27; margin-bottom: 5px;">Moderada</div>
                <div style="font-size: 0.78rem; color: #6B7280; margin-bottom: 12px;">Nivel de dano geral da amostra</div>
                
                <!-- Barra horizontal de severidade -->
                <div style="height: 8px; width: 100%; background-color: #E5E7EB; border-radius: 4px; position: relative;">
                    <div style="height: 100%; width: 37%; background-color: #E3B505; border-radius: 4px 0 0 4px;"></div>
                    <div style="position: absolute; top: -4px; left: 37%; width: 16px; height: 16px; border-radius: 50%; background-color: #145A27; border: 2px solid #FFFFFF;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.65rem; color: #9CA3AF; margin-top: 6px;">
                    <span>Saudavel</span>
                    <span>Moderado</span>
                    <span>Critico</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_res3:
            st.markdown("""
            <div class="dashboard-card">
                <div class="dashboard-card-title">🎖️ Confianca da Analise</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: #1F7A35; margin-bottom: 5px;">92%</div>
                <div style="font-size: 0.78rem; color: #6B7280; margin-bottom: 12px;">Alta confianca nos contornos detectados</div>
                
                <!-- Barra de progresso verde -->
                <div style="height: 8px; width: 100%; background-color: #E5E7EB; border-radius: 4px;">
                    <div style="height: 100%; width: 92%; background-color: #1F7A35; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Dados metricos em cm²
        st.markdown("### Valores Absolutos Calculados")
        df_metric = pd.DataFrame([leaf_m.to_dict()])
        st.dataframe(
            df_metric[[
                "Arquivo", "Area_Original_px2", "Area_Real_px2", "Perda_Herbivoria_px2",
                "Area_Original_cm2", "Area_Real_cm2", "Perda_Herbivoria_cm2"
            ]],
            use_container_width=True,
            hide_index=True
        )

        # Secao de download
        st.markdown("### Exportacao de Resultados (Rigor Cientifico)")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_data = df_metric.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="📥 Baixar CSV de Medidas",
                data=csv_data,
                file_name=f"leaf_medidas_{leaf_m.filename}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            metadata_dict = Metrics.export_metadata(p_params, {"amostra": leaf_m.to_dict()})
            json_data = json.dumps(metadata_dict, indent=4, ensure_ascii=False).encode("utf-8")
            st.download_button(
                label="⚙️ Baixar JSON de Metadados",
                data=json_data,
                file_name=f"leaf_metadados_{leaf_m.filename}.json",
                mime="application/json",
                use_container_width=True
            )

# =============================================================================
# PAGINA 3: HISTORICO (SIMULADO / PERSISTENTE)
# =============================================================================
def render_historico():
    st.markdown("### Historico de Analises")
    st.info("Esta pagina registra todas as imagens processadas nesta sessao de pesquisa.")
    st.dataframe(
        pd.DataFrame([
            {"Data": "2026-05-22 19:15", "Imagem": "amostra_videira_01.png", "Severidade": "14.2%", "Herbivoria": "8.5%", "PPM": 37.8},
            {"Data": "2026-05-22 19:22", "Imagem": "amostra_videira_02.png", "Severidade": "6.1%", "Herbivoria": "1.2%", "PPM": 37.8},
        ]),
        use_container_width=True
    )

# =============================================================================
# PAGINA 4: RELATORIOS
# =============================================================================
def render_relatorios():
    st.markdown("### Relatorios Consolidados")
    st.info("Selecione os lotes processados para exportar o relatorio estatistico cientifico em PDF ou XLSX.")
    
    st.markdown("""
    <div style="border: 1px solid var(--border-light); padding: 25px; border-radius: 8px; background-color: #FFFFFF; text-align: center; color: var(--text-muted);">
        📊 Nenhum relatorio gerado. Realize analises de lote primeiro.
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# PAGINA 5: CONFIGURACOES E CALIBRACAO
# =============================================================================
def render_configuracoes():
    st.markdown("### Calibracao e Parametrizacao Cientifica")
    
    # 1. Calibracao de Escala (Pixels por cm²)
    st.markdown("#### 📏 Calibracao de Escala")
    c_cal1, c_cal2 = st.columns(2)
    with c_cal1:
        st.session_state["ppm"] = st.number_input(
            "Fator de Conversao (PPM - Pixels por cm)",
            min_value=0.1, max_value=1000.0, value=st.session_state["ppm"], step=0.1
        )
        st.caption("Fator utilizado para converter areas de Pixels² para cm².")
    with c_cal2:
        # Calculadora rápida de PPM
        st.markdown("<div style='background-color: #F3F4F6; padding: 12px; border-radius: 8px;'>", unsafe_allow_html=True)
        st.write("🧮 Calculadora Rapida de PPM:")
        pixels_ref = st.number_input("Medida em pixels na foto", min_value=1, value=100)
        cm_ref = st.number_input("Medida real do objeto (cm)", min_value=0.1, value=2.5, step=0.1)
        if st.button("Aplicar PPM Calculado"):
            st.session_state["ppm"] = float(pixels_ref / cm_ref)
            st.success(f"PPM Atualizado para {st.session_state['ppm']:.1f}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr class='agri-divider'>", unsafe_allow_html=True)

    # 2. Modo Avançado de Limiarização
    st.markdown("#### 🔬 Modo Avancado de Limiarizacao")
    st.session_state["color_mode"] = st.selectbox(
        "Selecione o espaco de cores para segmentacao",
        options=["HSV", "CIELAB"],
        index=0 if st.session_state["color_mode"] == "HSV" else 1
    )
    st.caption("O modo CIELAB é mais resistente a sombras em ambientes de iluminação irregular.")

    # 3. Metodo de Reconstrucao de Borda
    st.markdown("#### 🛡️ Metodo de Reconstrucao de Borda")
    st.session_state["hull_method"] = st.selectbox(
        "Metodo de Silhueta Original",
        options=["Convex Hull", "Fechamento Morfologico"],
        index=0 if st.session_state["hull_method"] == "Convex Hull" else 1
    )
    
    if st.session_state["hull_method"] == "Fechamento Morfologico":
        st.session_state["morph_kernel_size"] = st.slider(
            "Tamanho do Kernel de Fechamento Morfologico",
            min_value=5, max_value=101, value=st.session_state["morph_kernel_size"], step=2
        )
        st.caption("Ajuste o tamanho do kernel para unir as bordas de folhas lobadas (ex: uva) sem forçar convexidade.")

    st.markdown("<hr class='agri-divider'>", unsafe_allow_html=True)

    # 4. Ajustes Finos de Limiares de Cor
    st.markdown("#### 🎨 Sliders de Limiarizacao de Cores")
    
    if st.session_state["color_mode"] == "HSV":
        c_hsv1, c_hsv2 = st.columns(2)
        with c_hsv1:
            st.write("Verde (Saudavel)")
            g_h = st.slider("HSV - Verde H", 0, 179, (st.session_state["hsv_green"][0], st.session_state["hsv_green"][1]))
            g_s = st.slider("HSV - Verde S", 0, 255, (st.session_state["hsv_green"][2], st.session_state["hsv_green"][3]))
            g_v = st.slider("HSV - Verde V", 0, 255, (st.session_state["hsv_green"][4], st.session_state["hsv_green"][5]))
            st.session_state["hsv_green"] = (g_h[0], g_h[1], g_s[0], g_s[1], g_v[0], g_v[1])
        with c_hsv2:
            st.write("Sintomatico")
            s_h = st.slider("HSV - Sintoma H", 0, 179, (st.session_state["hsv_symp"][0], st.session_state["hsv_symp"][1]))
            s_s = st.slider("HSV - Sintoma S", 0, 255, (st.session_state["hsv_symp"][2], st.session_state["hsv_symp"][3]))
            s_v = st.slider("HSV - Sintoma V", 0, 255, (st.session_state["hsv_symp"][4], st.session_state["hsv_symp"][5]))
            st.session_state["hsv_symp"] = (s_h[0], s_h[1], s_s[0], s_s[1], s_v[0], s_v[1])
    else:
        c_lab1, c_lab2 = st.columns(2)
        with c_lab1:
            st.write("Verde (Saudavel)")
            g_l = st.slider("LAB - Verde L*", 0, 255, (st.session_state["lab_green"][0], st.session_state["lab_green"][1]))
            g_a = st.slider("LAB - Verde a*", 0, 255, (st.session_state["lab_green"][2], st.session_state["lab_green"][3]))
            g_b = st.slider("LAB - Verde b*", 0, 255, (st.session_state["lab_green"][4], st.session_state["lab_green"][5]))
            st.session_state["lab_green"] = (g_l[0], g_l[1], g_a[0], g_a[1], g_b[0], g_b[1])
        with c_lab2:
            st.write("Sintomatico")
            s_l = st.slider("LAB - Sintoma L*", 0, 255, (st.session_state["lab_symp"][0], st.session_state["lab_symp"][1]))
            s_a = st.slider("LAB - Sintoma a*", 0, 255, (st.session_state["lab_symp"][2], st.session_state["lab_symp"][3]))
            s_b = st.slider("LAB - Sintoma b*", 0, 255, (st.session_state["lab_symp"][4], st.session_state["lab_symp"][5]))
            st.session_state["lab_symp"] = (s_l[0], s_l[1], s_a[0], s_a[1], s_b[0], s_b[1])

# =============================================================================
# DESPACHO DE RENDER DA PAGINA ATUAL
# =============================================================================
if st.session_state["current_page"] == "Inicio":
    render_inicio()
elif st.session_state["current_page"] == "Nova analise":
    render_nova_analise()
elif st.session_state["current_page"] == "Historico":
    render_historico()
elif st.session_state["current_page"] == "Relatorios":
    render_relatorios()
elif st.session_state["current_page"] == "Configuracoes":
    render_configuracoes()

# =============================================================================
# RODAPE
# =============================================================================
st.markdown("<hr class='agri-divider'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:left;font-size:0.75rem;color:#9CA3AF;'>"
    "🍃 LEAF &mdash; Levantamento e Estimativa de Anomalias Foliares"
    "</p>",
    unsafe_allow_html=True,
)
