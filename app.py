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
  URL_LOGO_COOPI = 'https://raw.githubusercontent.com/integrasven2026/tablero-aap-coopi/main/coopi.jpg'
  posibles_nombres = ['coopi.jpg', 'Coopi.jpg', 'coopi_logo.jpg']
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
      st.warning("⚠️ Sube tu imagen 'coopi.jpg' al repositorio.")

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
}

font_layout = dict(family='Quicksand', size=13)


# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES DE LIMPIEZA Y CATEGORIZACIÓN
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


def extraer_campo_dinamico(
    row_dict, palabras_clave, valor_defecto='Buzón'
):
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
  elif 'mensaje' in t or 'text' in t or 'whatsapp' in t:
    return 'Mensaje de Texto / WhatsApp'
  elif 'cara' in t:
    return 'Cara a Cara'
  elif 'correo' in t or 'email' in t:
    return 'Correo Electrónico'
  return str(texto).strip().title()


def limpiar_tipo_pqrs(texto):
  if not texto or str(texto).lower() in ['none', 'null', '', 'nan']:
    return '3. Demanda de información de Asistencia Humanitaria'
  t = str(texto).strip()
  t_lower = t.lower()
  if t == '5_' or 'retroalimentaci' in t_lower or 'felicitacion' in t_lower:
    return '1. Retroalimentación Positiva (Felicitaciones)'
  elif t == '2' or 'solicitud' in t_lower:
    return '2. Solicitud de Asistencia Humanitaria'
  elif 'informacion' in t_lower or 'demanda' in t_lower or '3.' in t:
    return '3. Demanda de información de Asistencia Humanitaria'
  elif 'reclamo' in t_lower or '4.' in t:
    return '4. Reclamos Relacionadas a la Asistencia Humanitaria'
  elif 'queja' in t_lower or '5.' in t:
    return '5. Quejas (Explotación y Abuso Sexual / Código de Conducta / Fraude y Corrupción)'
  return t


def limpiar_estatus_caso(texto):
  if not texto or str(texto).lower() in ['none', 'null', '', 'nan']:
    return 'En Proceso'
  t = str(texto).strip().title()
  if 'abiert' in t.lower() or 'proceso' in t.lower() or 'pend' in t.lower():
    return 'En Proceso'
  if 'cerrad' in t.lower() or 'atendid' in t.lower() or 'resuelt' in t.lower():
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
  return 'En Proceso'


def extraer_fecha_aap(row_dict):
  claves_fecha = ['fecha', 'today', 'date', '_submission_time']
  for cf in claves_fecha:
    for key, value in row_dict.items():
      if value and cf in str(key).lower():
        v_str = str(value).strip()
        if len(v_str) >= 8:
          return v_str
  return None


# -----------------------------------------------------------------------------
# CARGA DE DATOS DESDE KOBOTOOLBOX
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_aap(
    asset_id_aap, token_aap, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token_aap}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id_aap}/data.json'
  try:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
      return pd.DataFrame()
    data = response.json().get('results', [])
    if not data:
      return pd.DataFrame()
  except Exception:
    return pd.DataFrame()

  aap_rows = []
  for r in data:
    canal_raw = extraer_campo_dinamico(r, ['canal', 'medio'], 'Buzón')
    tipo_pqrs_raw = extraer_campo_dinamico(
        r, ['tipo', 'retroalimentacion', 'pqrs'], '3. Demanda de información de Asistencia Humanitaria'
    )
    estado_caso = extraer_estatus_caso_especifico(r)
    fecha_aap = extraer_fecha_aap(r)
    socio_val = str(
        r.get('ong') or r.get('socio') or r.get('group_pqrs/socio') or 'COOPI'
    ).upper().strip()

    discapacidad = extraer_valor_booleano(r, ['discapacidad', 'pcd'])
    indigena = extraer_valor_booleano(r, ['indigena', 'etnia'])
    lgbtiq = extraer_valor_booleano(r, ['lgbtiq', 'lgbt'])
    embarazada = extraer_valor_booleano(r, ['embarazada', 'lactante'])

    sexo_raw = str(
        r.get('sexo') or r.get('group_pqrs/sexo') or ''
    ).lower().strip()
    try:
      edad = float(r.get('edad') or r.get('group_pqrs/edad') or 0)
    except (ValueError, TypeError):
      edad = 0

    es_nina = 1 if (edad < 18 and sexo_raw in ['femenino', 'f', 'mujer']) else 0
    es_nino = 1 if (edad < 18 and sexo_raw in ['masculino', 'm', 'hombre']) else 0
    estado_geo_val = extraer_campo_dinamico(
        r, ['estado_geo', 'Estado'], 'General'
    )

    aap_rows.append({
        '_id': r.get('_id'),
        'Canal': limpiar_canal(canal_raw),
        'Tipo_PQRS': limpiar_tipo_pqrs(tipo_pqrs_raw),
        'Estado_Caso': estado_caso,
        'Fecha': fecha_aap,
        'Discapacidad': discapacidad,
        'Indigena': indigena,
        'LGBTIQ': lgbtiq,
        'Embarazada': embarazada,
        'Es_Nina': es_nina,
        'Es_Nino': es_nino,
        'Socio': socio_val,
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
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


# Credenciales y IDs de KoboToolbox
try:
  KOBO_TOKEN = st.secrets.get(
      'KOBO_TOKEN', 'a18c017a2e697f4ea1272375dae261ccec6b19d7'
  )
except Exception:
  KOBO_TOKEN = 'a18c017a2e697f4ea1272375dae261ccec6b19d7'

ASSET_ID_AAP = 'aRbFg8ig22Ts5JFFvsWNaE'
ASSET_ID_IND_AAP = 'aMYumvwLQ4rQeq5iFDSboS'

df_aap_raw = cargar_datos_aap(ASSET_ID_AAP, KOBO_TOKEN)
df_eval_aap = cargar_datos_indicadores_aap(ASSET_ID_IND_AAP, KOBO_TOKEN)

# -----------------------------------------------------------------------------
# FILTROS EN LA BARRA LATERAL
# -----------------------------------------------------------------------------
st.sidebar.header('Filtros AAP - COOPI')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
  st.cache_data.clear()
  st.rerun()

st.sidebar.markdown('---')

socios_disp = ['COOPI'] + sorted(
    [x for x in df_aap_raw['Socio'].unique() if x and x != 'COOPI']
)
socio_aap_sel = st.sidebar.selectbox('Organización / Socio:', socios_disp, index=0)

meses_ordenados = sorted(
    [m for m in df_aap_raw['Mes_Reporte'].unique() if m != 'Sin Fecha']
)
if 'Sin Fecha' in df_aap_raw['Mes_Reporte'].values:
  meses_ordenados.append('Sin Fecha')
meses_disp = ['Todos'] + meses_ordenados
mes_sel = st.sidebar.selectbox('Mes del Reporte:', meses_disp)

estados_disp = ['Todos'] + sorted(
    [x for x in df_aap_raw['Estado_Geo'].dropna().unique() if x]
)
estado_sel = st.sidebar.selectbox('Estado Geográfico:', estados_disp)

lista_poblacion_interes = [
    'TODOS',
    'Personas con Discapacidad',
    'Niñas',
    'Niños',
    'Comunidad Indígena',
    'LGBTIQ+',
    'Embarazadas / Lactantes',
]
poblacion_sel = st.sidebar.selectbox('Población de Interés:', lista_poblacion_interes)

# APLICAR FILTROS AAP (PQRS)
df_aap_filtered = df_aap_raw.copy()
if socio_aap_sel != 'TODOS':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Socio'] == socio_aap_sel]
if mes_sel != 'Todos':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Mes_Reporte'] == mes_sel]
if estado_sel != 'Todos':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Estado_Geo'] == estado_sel]

if poblacion_sel == 'Personas con Discapacidad':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Discapacidad'] == 1]
elif poblacion_sel == 'Niñas':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Es_Nina'] == 1]
elif poblacion_sel == 'Niños':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Es_Nino'] == 1]
elif poblacion_sel == 'Comunidad Indígena':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Indigena'] == 1]
elif poblacion_sel == 'LGBTIQ+':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['LGBTIQ'] == 1]
elif poblacion_sel == 'Embarazadas / Lactantes':
  df_aap_filtered = df_aap_filtered[df_aap_filtered['Embarazada'] == 1]

total_pqrs = len(df_aap_filtered)
pct_meta_pqrs = (total_pqrs / META_5_PORCIENTO) * 100

# -----------------------------------------------------------------------------
# SECCIÓN 1: MÉTRICAS GENERALES DE PQRS
# -----------------------------------------------------------------------------
st.subheader(f'Resumen de Rendición de Cuentas - {socio_aap_sel}')

m_c1, m_c2, m_c3 = st.columns(3)
m_c1.metric('Total PQRS Registradas', f'{total_pqrs:,}')
m_c2.metric('Meta 5% (Beneficiarios)', f'{int(META_5_PORCIENTO):,}')
m_c3.metric('% Cumplimiento Meta PQRS', f'{pct_meta_pqrs:.2f}%')

st.markdown('---')

# -----------------------------------------------------------------------------
# SECCIÓN 2: GRÁFICOS DE PQRS
# -----------------------------------------------------------------------------
aap_c1, aap_c2 = st.columns(2)

with aap_c1:
  st.markdown('### Canal más utilizado por los participantes')
  if total_pqrs > 0 and 'Canal' in df_aap_filtered.columns:
    df_canal = df_aap_filtered['Canal'].value_counts().reset_index()
    df_canal.columns = ['Canal', 'Cantidad']
    df_canal = df_canal.sort_values(by='Cantidad', ascending=True)
    df_canal['Porcentaje'] = (df_canal['Cantidad'] / total_pqrs) * 100
    df_canal['Etiqueta'] = df_canal.apply(
        lambda r: f"{r['Cantidad']} ({r['Porcentaje']:.0f}%)", axis=1
    )

    fig_canal = px.bar(
        df_canal,
        y='Canal',
        x='Cantidad',
        orientation='h',
        text='Etiqueta',
        color_discrete_sequence=[COLOR_AZUL_COOPI],
    )
    fig_canal.update_traces(textposition='outside')
    fig_canal.update_layout(
        xaxis_title='Número de PQRS', yaxis_title='', font=font_layout, height=320
    )
    st.plotly_chart(fig_canal, width='stretch')
  else:
    st.info('No hay datos de canales registrados.')

with aap_c2:
  st.markdown('### Tipos de PQRS Recibidos')
  if total_pqrs > 0 and 'Tipo_PQRS' in df_aap_filtered.columns:
    df_tipo = df_aap_filtered['Tipo_PQRS'].value_counts().reset_index()
    df_tipo.columns = ['Tipo', 'Cantidad']

    fig_tipo = px.pie(
        df_tipo,
        names='Tipo',
        values='Cantidad',
        hole=0.4,
        color_discrete_sequence=PALETA_COOPI,
    )
    fig_tipo.update_traces(textinfo='label+value+percent')
    fig_tipo.update_layout(showlegend=True, font=font_layout, height=320)
    st.plotly_chart(fig_tipo, width='stretch')
  else:
    st.info('No hay datos de tipos de PQRS.')

st.markdown('<br>', unsafe_allow_html=True)

aap_c3, aap_c4 = st.columns(2)

with aap_c3:
  st.markdown('### Participantes Atendidos por Mes')
  if total_pqrs > 0 and 'Mes_Reporte' in df_aap_filtered.columns:
    df_mes_aap = (
        df_aap_filtered.groupby('Mes_Reporte', sort=False)
        .size()
        .reset_index(name='Atendidos')
    )
    df_mes_aap['Porcentaje'] = (df_mes_aap['Atendidos'] / total_pqrs) * 100
    df_mes_aap['Etiqueta'] = df_mes_aap.apply(
        lambda r: f"{r['Atendidos']} ({r['Porcentaje']:.0f}%)", axis=1
    )

    fig_mes_aap = px.area(
        df_mes_aap,
        x='Mes_Reporte',
        y='Atendidos',
        text='Etiqueta',
        color_discrete_sequence=[COLOR_VERDE_COOPI],
    )
    fig_mes_aap.update_traces(textposition='top center')
    fig_mes_aap.update_layout(
        xaxis_title='Mes', yaxis_title='PQRS Recibidos', font=font_layout, height=320
    )
    st.plotly_chart(fig_mes_aap, width='stretch')
  else:
    st.info('No hay datos de temporalidad.')

with aap_c4:
  st.markdown('### Seguimiento a los Casos')
  if total_pqrs > 0 and 'Estado_Caso' in df_aap_filtered.columns:
    df_est_aap = df_aap_filtered['Estado_Caso'].value_counts().reset_index()
    df_est_aap.columns = ['Estado', 'Cantidad']
    df_est_aap['Porcentaje'] = (df_est_aap['Cantidad'] / total_pqrs) * 100
    df_est_aap['Etiqueta'] = df_est_aap.apply(
        lambda r: f"{r['Cantidad']} ({r['Porcentaje']:.0f}%)", axis=1
    )

    MAPA_COLORES_ESTADO = {
        'En Proceso': COLOR_VERDE_COOPI,
        'Cerrado': COLOR_AZUL_COOPI,
    }

    fig_est_aap = px.bar(
        df_est_aap,
        x='Estado',
        y='Cantidad',
        text='Etiqueta',
        color='Estado',
        color_discrete_map=MAPA_COLORES_ESTADO,
    )
    fig_est_aap.update_traces(textposition='outside')
    fig_est_aap.update_layout(
        xaxis_title='Estado de Resolución',
        yaxis_title='Casos',
        showlegend=False,
        font=font_layout,
        height=320,
    )
    st.plotly_chart(fig_est_aap, width='stretch')
  else:
    st.info('No hay datos de seguimiento de casos.')

st.markdown('---')

# -----------------------------------------------------------------------------
# SECCIÓN 3: INDICADORES AAP (EVALUACIÓN DE SATISFACCIÓN)
# -----------------------------------------------------------------------------
st.markdown(
    "<h2 style='color: #0072CE;'>Indicadores de Satisfacción y Conocimiento"
    ' AAP</h2>',
    unsafe_allow_html=True,
)
st.caption('Resultados de encuestas de retroalimentación y satisfacción')

if not df_eval_aap.empty:
  df_eval_filtered = df_eval_aap.copy()
  tot_part_eval = len(df_eval_filtered)
  pct_meta_eval = (tot_part_eval / META_5_PORCIENTO) * 100

  col_ind_tot, col_ind_meta = st.columns([1, 1])
  col_ind_tot.metric('Total Evaluaciones AAP', f'{tot_part_eval:,}')
  col_ind_meta.metric(
      '% Meta Evaluaciones (5% de 32 mil)', f'{pct_meta_eval:.2f}%'
  )

  st.markdown('<br>', unsafe_allow_html=True)

  row1_c1, row1_c2 = st.columns(2)

  # 1. Satisfacción
  with row1_c1:
    st.markdown('### Satisfacción de los participantes')
    sat_col = [c for c in df_eval_filtered.columns if 'satisfac' in c.lower()]
    if sat_col:
      df_sat = df_eval_filtered[sat_col[0]].value_counts().reset_index()
      df_sat.columns = ['Nivel', 'Cantidad']
    else:
      df_sat = pd.DataFrame()

    if not df_sat.empty and df_sat['Cantidad'].sum() > 0:
      fig_sat = px.pie(
          df_sat,
          names='Nivel',
          values='Cantidad',
          hole=0.4,
          color_discrete_sequence=PALETA_COOPI,
      )
      fig_sat.update_traces(textinfo='label+value+percent')
      fig_sat.update_layout(showlegend=False, font=font_layout, height=360)
      st.plotly_chart(fig_sat, width='stretch')
    else:
      st.info('No hay registros de satisfacción disponibles.')

  # 2. Conocimiento del comportamiento esperado
  with row1_c2:
    st.markdown('### Conocimiento del comportamiento esperado')
    comp_col = [
        c
        for c in df_eval_filtered.columns
        if 'comportamiento' in c.lower() or 'esperado' in c.lower()
    ]
    if comp_col:
      df_comp = df_eval_filtered[comp_col[0]].value_counts().reset_index()
      df_comp.columns = ['Respuesta', 'Cantidad']
    else:
      df_comp = pd.DataFrame()

    if not df_comp.empty and df_comp['Cantidad'].sum() > 0:
      total_comp = df_comp['Cantidad'].sum()
      df_comp['Etiqueta'] = df_comp['Cantidad'].apply(
          lambda x: (
              f'{x} ({(x / total_comp * 100):.1f}%)'
              if total_comp > 0
              else f'{x}'
          )
      )
      fig_comp = px.bar(
          df_comp,
          x='Respuesta',
          y='Cantidad',
          text='Etiqueta',
          color='Respuesta',
          color_discrete_map={
              'Sí': COLOR_VERDE_COOPI,
              'Si': COLOR_VERDE_COOPI,
              'No': COLOR_AZUL_COOPI,
          },
      )
      fig_comp.update_traces(textposition='outside')
      fig_comp.update_layout(showlegend=False, font=font_layout, height=360)
      st.plotly_chart(fig_comp, width='stretch')
    else:
      st.info('No hay registros de comportamiento disponibles.')
else:
  st.info('Esperando registros del formulario de Indicadores AAP.')
