import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(page_title="Dashboard de Ventas Retail", layout="wide")

RUTA_DATOS = '.'  # cambiar por tu ruta origen en local

# ==========================================================
# ESTILOS (tema oscuro + KPI cards estilo Polysure)
# ==========================================================
st.markdown("""
<style>
    .stApp { background-color: #0e0e10; }
    .kpi-title {
        font-size: 13px;
        font-weight: 600;
        color: #c9c9c9;
        line-height: 1.3;
        height: 38px;
        display: flex;
        align-items: flex-end;
        margin: 0 0 6px 2px;
    }
    .kpi-title-extra {
        font-weight: 400;
        color: #8a8a8a;
        font-size: 12px;
        margin-left: 6px;
    }
    .kpi-card {
        border-radius: 16px;
        padding: 18px 20px;
        height: 88px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: #111111;
    }
    .kpi-value { font-size: 26px; font-weight: 700; margin: 0; }
    .kpi-sub { font-size: 13px; font-weight: 600; margin: 4px 0 0 0; }
    .kpi-yellow { background-color: #F4C542; }
    .kpi-purple { background-color: #B9A7F0; }
    .kpi-green  { background-color: #B8E4C9; }
    .kpi-coral  { background-color: #F2B7A3; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = "plotly_dark"
COLOR_PRINCIPAL = "#7EC8F0"  # celeste consistente en todos los gráficos


def formato_k_mm(v):
    """15439 -> 15.43K | 4750000 -> 4.7MM"""
    if pd.isna(v):
        return "-"
    signo = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{signo}{v/1_000_000:.1f}MM"
    if v >= 1_000:
        return f"{signo}{v/1_000:.2f}K"
    return f"{signo}{v:,.0f}"


def kpi_card(col, titulo_en, clase, valor, sub=None, titulo_extra=None):
    extra_html = f'<span class="kpi-title-extra">— {titulo_extra}</span>' if titulo_extra else ''
    sub_html = f'<p class="kpi-sub">{sub}</p>' if sub else ''
    html = (
        f'<div class="kpi-title">{titulo_en}{extra_html}</div>'
        f'<div class="kpi-card {clase}">'
        f'<p class="kpi-value">{valor}</p>'
        f'{sub_html}'
        f'</div>'
    )
    col.markdown(html, unsafe_allow_html=True)


# ==========================================================
# CARGA DE DATOS
# ==========================================================
@st.cache_data
def cargar_datos():
    merge_v1 = pd.read_csv(f'{RUTA_DATOS}/merge_v1.csv', sep=None, engine='python', parse_dates=['Date'], dayfirst=True)
    calendario = pd.read_csv(f'{RUTA_DATOS}/calendario.csv', sep=None, engine='python', parse_dates=['Date'], dayfirst=True)
    stores = pd.read_csv(f'{RUTA_DATOS}/stores data-set.csv', sep=None, engine='python')
    return merge_v1, calendario, stores

merge_v1, calendario, stores = cargar_datos()

@st.cache_data
def armar_tabla_final(merge_v1, calendario, stores):
    df = merge_v1.merge(stores, on='Store', how='left')
    df = df.merge(calendario, on='Date', how='left')
    return df

df = armar_tabla_final(merge_v1, calendario, stores)

# ==========================================================
# SIDEBAR: FILTROS
# ==========================================================
st.sidebar.header("Filters")

anios_disponibles = sorted(df['Anio'].dropna().unique())
anio_sel = st.sidebar.multiselect("Year", anios_disponibles, default=anios_disponibles)

meses_disponibles = sorted(df['Mes'].dropna().unique())
mes_sel = st.sidebar.multiselect("Month", meses_disponibles, default=meses_disponibles)

tipo_tienda_sel = st.sidebar.multiselect(
    "Store type", sorted(df['Type'].dropna().unique()),
    default=sorted(df['Type'].dropna().unique())
)

tiendas_disponibles = sorted(df['Store'].unique())
tienda_sel = st.sidebar.multiselect("Store (optional)", tiendas_disponibles)

incluir_holiday = st.sidebar.checkbox("Include holiday weeks", value=True)
excluir_devoluciones = st.sidebar.checkbox("Exclude returns (negative sales)", value=False)

# ==========================================================
# APLICAR FILTROS
# ==========================================================
df_filtrado = df[
    df['Anio'].isin(anio_sel) &
    df['Mes'].isin(mes_sel) &
    df['Type'].isin(tipo_tienda_sel)
]

if tienda_sel:
    df_filtrado = df_filtrado[df_filtrado['Store'].isin(tienda_sel)]

if not incluir_holiday:
    df_filtrado = df_filtrado[df_filtrado['IsHoliday'] == False]

if excluir_devoluciones:
    df_filtrado = df_filtrado[df_filtrado['Es_Devolucion'] == False]

# ==========================================================
# TÍTULO
# ==========================================================
st.title("🛒 Retail Data Analytics")
st.caption("Weekly sales analysis by store, department and period")

# ==========================================================
# CÁLCULO DE KPIs
# ==========================================================
# 1. YTD (Year to Date): siempre anclado al año MÁS RECIENTE dentro de los años
#    filtrados. Corta en el último mes que tenga datos reales ese año (el menor
#    entre el mes máximo filtrado y el mes máximo con datos disponibles), para
#    no sumar meses sin información como si fueran cero.
MESES_EN = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
            7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}

anio_ytd = max(anio_sel) if anio_sel else None

df_ytd_base = df[df['Type'].isin(tipo_tienda_sel)]
if anio_ytd is not None:
    df_ytd_base = df_ytd_base[df_ytd_base['Anio'] == anio_ytd]
if tienda_sel:
    df_ytd_base = df_ytd_base[df_ytd_base['Store'].isin(tienda_sel)]
if not incluir_holiday:
    df_ytd_base = df_ytd_base[df_ytd_base['IsHoliday'] == False]
if excluir_devoluciones:
    df_ytd_base = df_ytd_base[df_ytd_base['Es_Devolucion'] == False]

if not df_ytd_base.empty and mes_sel:
    mes_corte = min(max(mes_sel), int(df_ytd_base['Mes'].max()))
    venta_ytd = df_ytd_base.loc[df_ytd_base['Mes'] <= mes_corte, 'Weekly_Sales'].sum()
    ytd_sub = f"Jan\u2013{MESES_EN.get(mes_corte, '')} {anio_ytd}"
else:
    venta_ytd = 0
    ytd_sub = "-"

# 2. Venta promedio SEMANAL (KPI ejecutivo): primero se suma la venta de TODAS
#    las tiendas y departamentos por cada semana, y luego se promedian esas
#    sumas semanales agrupando por Holiday / No-Holiday. Así el KPI responde:
#    "¿cuánto vende el negocio completo en una semana festiva promedio vs. una
#    semana regular promedio?" (no un promedio a nivel de fila individual).
venta_promedio_periodo = df_filtrado['Weekly_Sales'].mean() if len(df_filtrado) else 0

ventas_por_semana = df_filtrado.groupby(['Date', 'IsHoliday'], as_index=False)['Weekly_Sales'].sum()

promedio_no_holiday = ventas_por_semana.loc[ventas_por_semana['IsHoliday'] == False, 'Weekly_Sales'].mean()
promedio_holiday = ventas_por_semana.loc[ventas_por_semana['IsHoliday'] == True, 'Weekly_Sales'].mean()

promedio_no_holiday = promedio_no_holiday if pd.notna(promedio_no_holiday) else 0
promedio_holiday = promedio_holiday if pd.notna(promedio_holiday) else 0

delta_vs_holiday = (
    (promedio_holiday - promedio_no_holiday) / promedio_no_holiday * 100
) if promedio_no_holiday else 0

# 3. Tienda top del periodo
if not df_filtrado.empty:
    ventas_por_tienda = df_filtrado.groupby('Store')['Weekly_Sales'].sum()
    tienda_top = ventas_por_tienda.idxmax()
    venta_tienda_top = ventas_por_tienda.max()
else:
    tienda_top, venta_tienda_top = "-", 0

# 4. Crecimiento QoQ: se compara el PROMEDIO SEMANAL de cada trimestre (no la
#    suma total), porque el último trimestre disponible en el dataset suele
#    estar incompleto (menos semanas registradas). Comparar sumas totales en
#    ese caso mostraría una caída falsa, causada solo por faltar semanas de
#    datos, no por una baja real del negocio.
df_trimestres = df_filtrado.copy()
if not df_trimestres.empty:
    df_trimestres['Quarter'] = df_trimestres['Date'].dt.to_period('Q')
    ventas_semana_trim = df_trimestres.groupby(['Quarter', 'Date'], as_index=False)['Weekly_Sales'].sum()
    por_trimestre = ventas_semana_trim.groupby('Quarter')['Weekly_Sales'].mean().sort_index()
else:
    por_trimestre = pd.Series(dtype='float64')

if len(por_trimestre) >= 2:
    venta_trim_actual = por_trimestre.iloc[-1]
    venta_trim_anterior = por_trimestre.iloc[-2]
    qoq = (venta_trim_actual - venta_trim_anterior) / venta_trim_anterior * 100 if venta_trim_anterior else 0
    trim_label = str(por_trimestre.index[-1])
elif len(por_trimestre) == 1:
    venta_trim_actual = por_trimestre.iloc[-1]
    qoq = 0
    trim_label = str(por_trimestre.index[-1])
else:
    venta_trim_actual = 0
    qoq = 0
    trim_label = "-"

# ==========================================================
# KPIs (título en inglés arriba, valor numérico dentro de la card)
# ==========================================================
c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "YTD Sales", "kpi-yellow", f"${formato_k_mm(venta_ytd)}", ytd_sub)
kpi_card(c2, "Weekly Avg Sales: Holiday vs Regular", "kpi-purple",
          f"${formato_k_mm(promedio_holiday)}", f"{delta_vs_holiday:+.1f}% vs regular")
kpi_card(c3, "Top Store of Period", "kpi-green",
          f"Store {tienda_top}", f"${formato_k_mm(venta_tienda_top)}")
kpi_card(c4, "QoQ Sales Growth", "kpi-coral", f"{qoq:+.1f}%", titulo_extra=f"{trim_label} vs prior Q")

st.markdown("###")

# ==========================================================
# GRÁFICO 1: Tendencia de ventas — ventana móvil de los últimos 12 meses
# ==========================================================
# La tendencia siempre muestra los últimos 12 meses hacia atrás desde el mes
# más reciente disponible dentro de los Años/Tienda/Tipo filtrados, sin que el
# filtro de Mes recorte esta ventana (si no, el gráfico se vería fragmentado).
st.subheader("Sales trend (last 12 months)")

df_para_tendencia = df[
    df['Anio'].isin(anio_sel) &
    df['Type'].isin(tipo_tienda_sel)
]
if tienda_sel:
    df_para_tendencia = df_para_tendencia[df_para_tendencia['Store'].isin(tienda_sel)]
if not incluir_holiday:
    df_para_tendencia = df_para_tendencia[df_para_tendencia['IsHoliday'] == False]
if excluir_devoluciones:
    df_para_tendencia = df_para_tendencia[df_para_tendencia['Es_Devolucion'] == False]

if not df_para_tendencia.empty:
    fecha_max_tendencia = df_para_tendencia['Date'].max()
    # Anclamos por MES calendario (no por resta de días) para evitar que quede
    # un mes 13 parcial cuando fecha_max no cae justo en fin de mes.
    periodo_max = fecha_max_tendencia.to_period('M')
    periodo_min = periodo_max - 11  # 11 hacia atrás + el mes actual = 12 meses
    df_para_tendencia = df_para_tendencia.copy()
    df_para_tendencia['Mes_Periodo'] = df_para_tendencia['Date'].dt.to_period('M')
    df_para_tendencia = df_para_tendencia[df_para_tendencia['Mes_Periodo'] >= periodo_min]
else:
    df_para_tendencia = df_para_tendencia.copy()
    df_para_tendencia['Mes_Periodo'] = df_para_tendencia['Date']

# Agregamos por mes (no por semana): con data semanal, los picos de holiday
# dominan visualmente y no deja ver la tendencia general mes a mes.
tendencia = df_para_tendencia.groupby('Mes_Periodo', as_index=False)['Weekly_Sales'].sum()
tendencia['Mes_Periodo'] = tendencia['Mes_Periodo'].dt.to_timestamp()

fig1 = px.line(tendencia, x='Mes_Periodo', y='Weekly_Sales', template=PLOTLY_TEMPLATE, markers=True)
fig1.update_traces(line_color=COLOR_PRINCIPAL, line_width=2, marker=dict(size=7))
fig1.update_layout(
    xaxis_title="Month",
    yaxis_title="Monthly sales",
    xaxis=dict(dtick="M1", tickformat="%b %Y", tickangle=-45)
)
st.plotly_chart(fig1, width='stretch')

# ==========================================================
# GRÁFICO 2: Ventas por tipo de tienda
# ==========================================================
st.subheader("Sales by store type")
por_tipo = df_filtrado.groupby('Type', as_index=False)['Weekly_Sales'].sum()
fig2 = px.bar(por_tipo, x='Type', y='Weekly_Sales', template=PLOTLY_TEMPLATE)
fig2.update_traces(marker_color=COLOR_PRINCIPAL)
st.plotly_chart(fig2, width='stretch')

# ==========================================================
# GRÁFICO 3: Top 10 departamentos
# ==========================================================
st.subheader("Top 10 departments")
top_dept = (
    df_filtrado.groupby('Dept', as_index=False)['Weekly_Sales']
    .sum()
    .sort_values('Weekly_Sales', ascending=False)
    .head(10)
)
fig3 = px.bar(top_dept, x='Weekly_Sales', y='Dept', orientation='h', template=PLOTLY_TEMPLATE,
               text=top_dept['Weekly_Sales'].map(lambda v: f"${v:,.0f}"))
fig3.update_traces(marker_color=COLOR_PRINCIPAL, textposition='outside')
fig3.update_layout(yaxis=dict(type='category', categoryorder='total ascending'))
st.plotly_chart(fig3, width='stretch')

# ==========================================================
# GRÁFICO 4: Impacto de semanas festivas (lollipop)
# ==========================================================
st.subheader("Holiday weeks impact on sales")

holiday_comp = df_filtrado.groupby('IsHoliday', as_index=False)['Weekly_Sales'].mean()
holiday_comp['IsHoliday'] = holiday_comp['IsHoliday'].map({True: 'Holiday', False: 'Regular'})
holiday_comp = holiday_comp.set_index('IsHoliday').reindex(['Regular', 'Holiday']).reset_index()

val_regular = holiday_comp.loc[holiday_comp['IsHoliday'] == 'Regular', 'Weekly_Sales'].values
val_festivo = holiday_comp.loc[holiday_comp['IsHoliday'] == 'Holiday', 'Weekly_Sales'].values
val_regular = val_regular[0] if len(val_regular) else 0
val_festivo = val_festivo[0] if len(val_festivo) else 0
uplift = ((val_festivo - val_regular) / val_regular * 100) if val_regular else 0

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=['Regular', 'Holiday'], y=[val_regular, val_festivo],
    mode='lines', line=dict(color='rgba(255,255,255,0.3)', width=2), showlegend=False
))
fig4.add_trace(go.Scatter(
    x=['Regular', 'Holiday'], y=[val_regular, val_festivo],
    mode='markers+text', marker=dict(size=18, color=[COLOR_PRINCIPAL, "#F4C542"]),
    text=[f"${val_regular:,.0f}", f"${val_festivo:,.0f}"],
    textposition='top center', showlegend=False
))
fig4.update_layout(
    template=PLOTLY_TEMPLATE,
    yaxis_title="Weekly_Sales",
    annotations=[dict(
        x=0.5, y=max(val_regular, val_festivo) * 1.15, xref='paper', yref='y',
        text=f"{uplift:+.1f}%", showarrow=False,
        font=dict(size=14, color="#111111"),
        bgcolor="#B8E4C9", borderpad=6, bordercolor="#B8E4C9", borderwidth=1
    )]
)
st.plotly_chart(fig4, width='stretch')

st.divider()

# ==========================================================
# TABLA DE DETALLE
# ==========================================================
st.subheader("Filtered data detail")
st.dataframe(df_filtrado, width='stretch')
