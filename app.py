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
  cat_form2 = row_dict.get('Categoría de la retroalimentación') or row_dict.get('categoria_retroalimentacion')
  if cat_form2:
    return mapear_categoria_segundo_formulario(cat_form2)

  tipo_detectado = None
  for k, v in row_dict.items():
    k_low = str(k).lower()
    if (
        ('retroalimentaci' in k_low and 'positiva' in k_low)
        or ('_1_retroalimentaci' in k_low)
        or ('carga_1' in k_low)
    ):
      if v is not None and str(v).strip() not in ['', 'none', 'null', 'nan']:
        try:
          num_val = int(float(v))
          if num_val > 0:
            return '1. Retroalimentación Positiva (Felicitaciones)', num_val
        except ValueError:
          pass

  for k, v in row_dict.items():
    k_low = str(k).lower()
    v_str = str(v).strip()
    v_low = v_str.lower()
    if 'tipopqrs' in k_low or 'tipo' in k_low or 'pqrs' in k_low:
      if (
          v_str == '5_'
          or 'retroalimentaci' in v_low
          or 'felicitacion' in v_low
      ):
        return '1. Retroalimentación Positiva (Felicitaciones)', 1

    if 'reclamo' in k_low and v_low not in ['', 'none', 'null', 'nan']:
      return '4. Reclamos Relacionadas a la Asistencia Humanitaria', 1
    if 'queja' in k_low and v_low not in ['', 'none', 'null', 'nan']:
      return (
          '5. Quejas (Explotación y Abuso Sexual / Código de Conducta / Fraude'
          ' y Corrupción)',
          1,
      )
    if (
        '_2_solicitudes_de_asistencia' in k_low
        and v_low not in ['', 'none', 'null', 'nan']
    ):
      return '2. Solicitud de Asistencia Humanitaria', 1
    if 'petici_n_pregunta' in k_low and v_low not in ['', 'none', 'null', 'nan']:
      return '3. Demanda de información de Asistencia Humanitaria', 1

    if v_str == '2' or 'solicitud' in v_low:
      tipo_detectado = '2. Solicitud de Asistencia Humanitaria'
    elif 'informacion' in v_low or 'demanda' in v_low or '3.' in v_str:
      tipo_detectado = '3. Demanda de información de Asistencia Humanitaria'

  if tipo_detectado:
    return tipo_detectado, 1
  return '3. Demanda de información de Asistencia Humanitaria', 1


def limpiar_colaborador(texto):
  if not texto or str(texto).lower() in ['none', 'null', '', 'nan']:
    return 'Carlos Mesa'
  t = str(texto).strip().lower()
  if 'daisy' in t:
    return 'Daisy Benites'
  elif 'carlos' in t:
    return 'Carlos Mesa'
  return str(texto).strip().title()


def limpiar_estatus_caso(texto):
  if not texto or str(texto).lower() in ['none', 'null', '', 'nan']:
    return 'Sin Especificar'
  t = str(texto).strip().title()
  if 'abiert' in t.lower():
    return 'Abierto'
  elif 'proceso' in t.lower() or 'pend' in t.lower():
    return 'En Proceso'
  elif 'cerrad' in t.lower() or 'atendid' in t.lower() or 'resuelt' in t.lower():
    return 'Cerrado'
  return t


def extraer_estatus_caso_especifico(row_dict):
  prioridades = ['estatus', 'seguimiento', 'resolucion', 'estado_caso']
  for p in prioridades:
    for key, value in row_dict.items():
      if (
          value is not None
          and str(value).strip() != ''
          and p in str(key).lower()
      ):
        return limpiar_estatus_caso(str(value))
  return 'Sin Especificar'


def extraer_fecha_aap(row_dict):
  claves_fecha = [
      'fecha de la retroalimentación',
      'fecha',
      'today',
      'date',
      '_submission_time',
  ]
  for cf in claves_fecha:
    for key, value in row_dict.items():
      if value and cf in str(key).lower():
        v_str = str(value).strip()
        if len(v_str) >= 8:
          return v_str
  return None


# -----------------------------------------------------------------------------
# CARGA DE DATOS DESDE KOBOTOOLBOX (AMBOS FORMULARIOS)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_kobo(
    asset_id, token_aap, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token_aap}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'
  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      return []
    return response.json().get('results', [])
  except Exception:
    return []


@st.cache_data(ttl=3600)
def cargar_todos_datos_aap(asset_id_aap, asset_id_seg, token_aap):
  data1 = cargar_datos_kobo(asset_id_aap, token_aap)
  data2 = cargar_datos_kobo(asset_id_seg, token_aap)

  all_raw_data = []
  for r in data1:
    r['_form_source'] = 'form1'
    all_raw_data.append(r)
  for r in data2:
    r['_form_source'] = 'form2'
    all_raw_data.append(r)

  if not all_raw_data:
    return pd.DataFrame()

  aap_rows = []
  for r in all_raw_data:
    canal_raw = r.get(
        'Mecanismo por el cual se recogió la retroalimentación'
    ) or extraer_campo_dinamico(r, ['canal', 'medio'], 'Buzón')
    tipo_pqrs, peso = obtener_peso_fila(r)

    colab_raw = (
        r.get('Nombre_y_apellido_de_r_que_recibe_el_PQRS')
        or r.get('Nombre de la persona que recibe la retroalimentación')
        or r.get('colaborador')
        or 'carlos_mesa'
    )
    colab = limpiar_colaborador(colab_raw)

    estado_caso = extraer_estatus_caso_especifico(r)
    fecha_aap = extraer_fecha_aap(r)

    proyecto_val = (
        r.get('proyectoa')
        or r.get('Proyecto')
        or r.get('ong')
        or r.get('socio')
        or r.get('group_pqrs/socio')
        or 'COOPI'
    )
    proyecto_val = str(proyecto_val).strip()
    if proyecto_val.lower() in ['', 'none', 'null', 'nan']:
      proyecto_val = 'COOPI'

    discapacidad = extraer_valor_booleano(r, ['discapacidad', 'pcd'])
    indigena = extraer_valor_booleano(r, ['indigena', 'etnia'])
    lgbtiq = extraer_valor_booleano(r, ['lgbtiq', 'lgbt'])
    embarazada = extraer_valor_booleano(r, ['embarazada', 'lactante'])

    sexo_raw = str(
        r.get('sexo')
        or r.get('Sexo')
        or r.get('group_pqrs/sexo')
        or ''
    ).lower().strip()
    try:
      edad = float(
          r.get('edad') or r.get('Edad') or r.get('group_pqrs/edad') or 0
      )
    except (ValueError, TypeError):
      edad = 0

    es_nina = 1 if (edad < 18 and sexo_raw in ['femenino', 'f', 'mujer']) else 0
    es_nino = 1 if (edad < 18 and sexo_raw in ['masculino', 'm', 'hombre']) else 0

    estado_geo_val = r.get('Estado') or extraer_campo_dinamico(
        r, ['estado_geo', 'Estado'], 'General'
    )

    aap_rows.append({
        '_id': r.get('_id'),
        'Canal': limpiar_canal(canal_raw),
        'Tipo_PQRS': tipo_pqrs,
        'Colaborador': colab,
        'Estado_Caso': estado_caso,
        'Fecha': fecha_aap,
        'Discapacidad': discapacidad,
        'Indigena': indigena,
        'LGBTIQ': lgbtiq,
        'Embarazada': embarazada,
        'Es_Nina': es_nina,
        'Es_Nino': es_nino,
        'Proyecto': proyecto_val,
        'Estado_Geo': MAPA_ESTADOS.get(estado_geo_val, estado_geo_val),
    })

    for _ in range(peso - 1):
      aap_rows.append({
          '_id': r.get('_id'),
          'Canal': limpiar_canal(canal_raw),
          'Tipo_PQRS': tipo_pqrs,
          'Colaborador': colab,
          'Estado_Caso': 'Sin Especificar',
          'Fecha': fecha_aap,
          'Discapacidad': discapacidad,
          'Indigena': indigena,
          'LGBTIQ': lgbtiq,
          'Embarazada': embarazada,
          'Es_Nina': es_nina,
          'Es_Nino': es_nino,
          'Proyecto': proyecto_val,
          'Estado_Geo': MAPA_ESTADOS.get(estado_geo_val, estado_geo_val),
      })

  df_aap = pd.DataFrame(aap_rows)
  if not df_aap.empty and 'Fecha' in df_aap.columns:
    df_aap['Fecha_DT'] = pd.to_datetime(df_aap['Fecha'], errors='coerce')
    df_aap = df_aap.sort_values(by='Fecha_DT')
    df_aap['Mes_Reporte'] = df_aap['Fecha_DT'].apply(
        lambda x: (
            f'{x.year} - {MESES_ES.get(x.month, "")}'
            if pd.notnull(x)
            else 'Sin Fecha'
        )
    )
  else:
    df_aap['Mes_Reporte'] = 'Sin Fecha'
  return df_aap


@st.cache_data(ttl=3600)
def cargar_datos_indicadores_aap(
    asset_id_ind, token_ind, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token_ind}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id_ind}/data.json'
  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      return pd.DataFrame()
    data = response.json().get('results', [])
    if not data:
      return pd.DataFrame()
    return pd.
