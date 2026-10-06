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
      st.warning("⚠️ Sube tu imagen 'logo_coopi.jpg' al repositorio.")

st.markdown('---')

# METAS Y DICCIONARIOS
META_BENEFICIARIOS_PROYECTO = 32000
META_5_PORCIENTO = META_BENEFICIARIOS_PROYECTO * 0.05  # 1,600 personas

MESES_ES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}

MAPA_ESTADOS = {
    'VE01': 'Distrito Capital',
    'VE07': 'Bolívar',
    'VE10': 'Delta Amacuro',
    'VE15': 'Miranda',
    'VE19': 'Sucre',
    'VE24': 'La Guaira',
    'Distrito Capital': 'Distrito Capital',
    'Bolívar': 'Bolívar',
    'Delta Amacuro': 'Delta Amacuro',
    'Miranda': 'Miranda',
    'Sucre': 'Sucre',
    'La Guaira': 'La Guaira',
}

font_layout = dict(family='Quicksand', size=13)


# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES DE LIMPIEZA Y ESTANDARIZACIÓN
# -----------------------------------------------------------------------------
def extraer_valor_booleano(diccionario_beneficiario, lista_posibles_claves):
  val_afirmativos = ['sí', 'si', 'yes', '1', 's', 'true']
  for clave in lista_posibles_claves:
    for k_item, v_item in diccionario_beneficiario.items():
      if clave.lower() in str(k_item).lower():
        val_str = str(v_item).lower().strip()
        if val_str in val_afirmativos or v_item == 1 or v_item is True:
          return 1
  return 0


def extraer_campo_dinamico(row_dict, palabras_clave, valor_defecto='Buzón'):
  for key, value in row_dict.items():
    if value is None or str(value).strip() == '':
      continue
    key_lower = str(key).lower()
    if any(pc.lower() in key_lower for pc in palabras_clave):
      val_str = str(value).strip()
      if val_str.lower() not in ['none', 'null', '']:
        return val_str
  return valor_defecto


def limpiar_canal(texto):
  if not texto or str(texto).lower() in ['none', 'null', '', 'nan']:
    return 'Buzón'
  t = str(texto).strip().lower()
  if 'buzon' in t or 'buz' in t:
    return 'Buzón'
  elif 'telefon' in t or 'llamada' in t:
    return 'Línea Telefónica'
  elif 'whatsapp' in t or 'mensaje' in t or 'text' in t:
    return 'Mensaje de Texto / WhatsApp'
  elif 'cara' in t:
    return 'Cara a Cara'
  elif 'correo' in t or 'email' in t:
    return 'Correo Electrónico'
  return str(texto).strip().title()


def mapear_categoria_segundo_formulario(cat_raw):
  if not cat_raw or str(cat_raw).lower() in ['none', 'null', '', 'nan']:
    return '3. Demanda de información de Asistencia Humanitaria', 1
  c = str(cat_raw).strip().lower()
  if 'positiv' in c:
    return '1. Retroalimentación Positiva (Felicitaciones)', 1
  elif 'solicitud de asistencia' in c or 'sugerencia' in c:
    return '2. Solicitud de Asistencia Humanitaria', 1
  elif 'solicitud de informaci' in c:
    return '3. Demanda de información de Asistencia Humanitaria', 1
  elif 'reclamo' in c:
    return '4. Reclamos Relacionadas a la Asistencia Humanitaria', 1
  elif 'queja' in c:
    return (
        '5. Quejas (Explotación y Abuso Sexual / Código de Conducta / Fraude'
        ' y Corrupción)',
        1,
    )
  return '3. Demanda de información de Asistencia Humanitaria', 1


def obtener_peso_fila(row_dict):
  cat_form2 = row_dict.get('Categoría de la retroalimentación') or row_dict.get(
