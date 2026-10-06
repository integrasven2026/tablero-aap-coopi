import io
import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# PALETA DE COLORES OFICIAL COOPI
# -----------------------------------------------------------------------------
COLOR_AZUL_COOPI = '#0072CE'
COLOR_VERDE_COOPI = '#009639'
COLOR_AZUL_OSCURO = '#08327D'
COLOR_NARANJA_ABIERTO = '#E67E22'

PALETA_COOPI = [
    COLOR_AZUL_COOPI,
    COLOR_VERDE_COOPI,
    COLOR_AZUL_OSCURO,
    '#17C3B2',
    '#D89FE3',
]

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='PQRS COOPI Venezuela | Rendición de Cuentas',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Quicksand:wght@600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, p, div, span, label, input, button {
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
    }

    h1, h2, h3, h4, h5, h6, .stSubheader {
        font-family: 'Now', 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }

    .titulo-principal {
        font-family: 'Now', 'Montserrat', sans-serif !important;
        color: #0072CE !important;
        margin-bottom: 5px !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# ENCABEZADO Y LOGO DE COOPI
# -----------------------------------------------------------------------------
col_header_title, col_header_logo = st.columns([3, 1])

with col_header_title:
  st.markdown(
      "<h1 class='titulo-principal'>PQRS COOPI Venezuela</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      '**Organización:** COOPI (Cooperazione Internazionale) | **Módulo:'
      ' Rendición de Cuentas y AAP**'
  )

with col_header_logo:
  URL_LOGO_COOPI = 'https://raw.githubusercontent.com/integrasven2026/tablero-aap-coopi/main/logo_coopi.jpg'
  posibles_nombres = [
      'logo_coopi.jpg',
      'coopi.jpg',
      'Coopi.jpg',
      'coopi_logo.jpg',
  ]
  logo_path = None
  for nombre in posibles_nombres:
    if os.path.exists(nombre):
      logo_path = nombre
      break

  if logo_path:
    try:
      st.image(logo_path, width=200)
    except Exception:
      pass
  else:
    try:
      st.image(URL_LOGO_COOPI, width=200)
    except Exception:
      st.warning("⚠️ Sube tu imagen 'logo_
