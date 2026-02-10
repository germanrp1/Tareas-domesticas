import streamlit as st
import pandas as pd
from fpdf import FPDF

# ##############################
# Version V1k - VALORES POR DEFECTO
# ##############################

entorno = st.secrets.get("ENTORNO", "PRODUCCION")
st.set_page_config(page_title="JV Analizador Pro", layout="wide")

if entorno == "DESARROLLO":
    st.sidebar.warning("🛠️ Modo Desarrollo (Rama Dev)")
else:
    st.sidebar.info("🚀 Modo Producción (Rama Main)")

# Función PDF Blindada
def create_pdf(df, p_globales, p_gastos, p_repartos, notas):
    pdf = FPDF()
    pdf.add_page()
    euro = chr(128)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "INFORME DETALLADO DE INVERSION JV".encode('windows-1252', 'ignore').decode('latin-1'), ln=True, align="C")
    
    # Bloques de Parámetros
    for title, params in [("A. AJUSTES DEL ESCENARIO", p_globales), 
                          ("B. COSTES Y DIMENSIONAMIENTO", p_gastos), 
                          ("C. ACUERDOS DE REPARTO", p_repartos)]:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 8, title, ln=True)
        pdf.set_font("Arial", "", 10)
        for k, v in params.items():
            txt = f"{k}: {v}".replace("€", euro)
            pdf.cell(190, 6, txt.encode('windows-1252', 'ignore').decode('latin-1'), ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(50, 10, "Concepto", 1)
    for col in df.columns:
        pdf.cell(46, 10, col.replace('\n', ' ').replace("€", euro).encode('windows-1252', 'ignore').decode('latin-1'), 1, 0, 'C')
    pdf.ln()
    
    pdf.set_font("Arial", "", 8)
    for i in range(len(df)):
        idx_txt = str(df.index[i]).replace("ó", "o").replace("í", "i").replace("€", euro)
        pdf.cell(50, 8, idx_txt.encode('windows-1252', 'ignore').decode('latin-1'), 1)
        for val in df.iloc[i]:
            pdf.cell(46, 8, str(val).replace("€", euro).encode('windows-1252', 'ignore').decode('latin-1'), 1, 0, 'C')
        pdf.ln()

    if notas:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(190, 8, "NOTAS ADICIONALES:", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(190, 6, notas.encode('windows-1252', 'ignore').decode('latin-1'))
    
    return pdf.output(dest="S").encode('latin-1')

# --- SIDEBAR (Valores por defecto solicitados) ---
with st.sidebar:
    st.header("⚙️ Ajustes Globales")
    # Configurado por defecto: Precio Venta/Ud
    modo = st.radio("Calcular por:", ["Precio Venta/Ud", "Precio Compra", "Ben. Objetivo"], index=0)
    # 8 meses por defecto
    meses = st.number_input("Duración Inversión (meses):", value=8, min_value=1)
    num_gestores = st.number_input("Nº de Gestores:", value=2, min_value=1)
    
    # Valores por defecto solicitados: 750k compra, ventas 200k, 215k, 228k
    compra_fija = st.number_input("P. Compra Fijo (€):", value=750000.0)
    e1 = st.number_input("Venta/Ud (€) 1:", value=200000.0)
    e2 = st.number_input("Venta/Ud (€) 2:", value=215000.0)
    e3 = st.number_input("Venta/Ud (€) 3:", value=228000.0)

# --- CUERPO PRINCIPAL ---
st.title("🏢 JV Analizador Pro - V1k")

# INTERRUPTOR DE PAGO APLAZADO (En la parte superior para máxima visibilidad)
aplazado_on = st.toggle("🚀 ACTIVAR MODO PAGO APLAZADO", value=False)

with st.expander("🏠 Bloque Gastos y Unidades", expanded=True):
    c1, c2 = st.columns(2)
    # 7 viviendas por defecto
    num_viviendas = c1.number_input("Nº de Viviendas:", value=7, min_value=1)
    # ITP 7% por defecto
    itp_pct = c2.number_input("ITP/IVA (%):", value=7.0)
    notaria = c1.number_input("Notaria/Tasación (€):", value=1500.0)
    # Otros gastos 74k por defecto
    otros_g = c2.number_input("Otros gastos (€):", value=74000.0)
    # Reforma 300k por defecto
    reforma_total = c1.number_input("Reforma (€):", value=300000.0)
    desviacion = c2.number_input("Desviación (€):", value=30000.0)
    
    if aplazado_on:
        st.warning("⚠️ MODO PAGO APLAZADO ACTIVADO")
        arras_pct = st.slider("% Arras (Aporta Gestor):", 0, 20, 10)
    else:
        arras_pct = 0

with st.expander("🤝 Bloque % Repartos", expanded=True):
    c3, c4 = st.columns(2)
    # Aportación inversor 94% por defecto
    ap_inv_pct = c3.number_input("% Aportación Inversor (s/Inversión):", value=94.0) / 100
    pct_is = c3.slider("% Impuesto Sociedades:", 0, 30, 0) / 100
    # Método ROI sobre aportación por defecto
    metodo_rent = c4.selectbox("Método Rentabilidad Inversor:", 
                             ["% ROI fijo sobre Aportación", "% sobre Beneficio Proyecto"], index=0)
    # 15% beneficio por defecto
    r1_val = c4.number_input("Porcentaje Pactado (%):", value=15.0)
    r1_inv = r1_val / 100

notas_input = st.text_area("📝 Notas Adicionales:")

# --- LÓGICA DE CÁLCULO ---
escenarios = [e1, e2, e3]
res = {}

for val in escenarios:
    compra = compra_fija
    v_total = val * num_viviendas
    itp_euro = compra * (itp_pct / 100)
    gastos_totales = itp_euro + notaria + otros_g + reforma_total + desviacion
    
    if aplazado_on:
        arras_euro = compra * (arras_pct / 100)
        deuda_aplazada = compra - arras_euro
        inv_total_inicial = arras_euro + gastos_totales
        c_total_inversor = gastos_totales * ap_inv_pct
        c_total_gestor = arras_euro + (gastos_totales * (1 - ap_inv_pct))
    else:
        deuda_aplazada = 0
        inv_total_inicial = compra + gastos_totales
        c_total_inversor = inv_total_inicial * ap_inv_pct
        c_total_gestor = inv_total_inicial * (1 - ap_inv_pct)

    beneficio_bruto = v_total - inv_total_inicial - deuda_aplazada
    neto_proyecto = beneficio_bruto * (1 - pct_is)
    
    if metodo_rent == "% sobre Beneficio Proyecto":
        g_inv = neto_proyecto * r1_inv
    else:
        g_inv = c_total_inversor * r1_inv 
    
    g_ges = neto_proyecto - g_inv
    recup_iva = (reforma_total + otros_g + desviacion) * 0.21

    col_head = f"Venta:\n{v_total:,.0f} €"
    res[col_head] = [
        f"{inv_total_inicial:,.0f}€", f"{deuda_aplazada:,.0f}€", f"{neto_proyecto:,.0f}€", "---",
        f"{c_total_inversor:,.0f}€", f"{g_inv:,.0f}€", f"{(g_inv/c_total_inversor)*100:.1f}%", f"{(g_inv/c_total_inversor)*(12/meses)*100:.1f}%", "---",
        f"{c_total_gestor:,.0f}€", f"{g_ges:,.0f}€", f"{(g_ges/c_total_gestor)*100:.1f}%", f"{(g_ges/c_total_gestor)*(12/meses)*100:.1f}%",
        f"{c_total_gestor/num_gestores:,.0f}€", f"{g_ges/num_gestores:,.0f}€", f"{(g_ges/(c_total_gestor if c_total_gestor > 0 else 1))*100:.1f}%", "---",
        f"{recup_iva:,.0f}€", f"{inv_total_inicial + neto_proyecto + recup_iva:,.0f}€"
    ]

indices = [
    "PROYECTO: Capital Inicial", "PROYECTO: Pago Aplazado", "PROYECTO: Ben. Neto", "--- ",
    "INVERSOR: Aportación", "INVERSOR: Beneficio", "INVERSOR: ROI (Proy)", "INVERSOR: ROI (Anual)", "---  ",
    "GESTOR: Aportación Total", "GESTOR: Beneficio", "GESTOR: ROI (Proy)", "GESTOR: ROI (Anual)",
    "CADA GESTOR: Aport.", "CADA GESTOR: Benef.", "CADA GESTOR: ROI (Total)", "---   ",
    "LIQUIDEZ: IVA Recup.", "LIQUIDEZ: Caja Final Total"
]

st.table(pd.DataFrame(res, index=indices))

# Parámetros PDF
p_glob = {"Modo": modo, "Duración": f"{meses} meses", "Ventas Unit": f"{e1}, {e2}, {e3}"}
p_gast = {"Unidades": num_viviendas, "P. Compra": f"{compra:,.0f}€", "ITP": f"{itp_pct}%", "Aplazado": "SI" if aplazado_on else "NO"}
p_repr = {"Aport. Inv": f"{ap_inv_pct*100}%", "Aport. Ges": f"{(1-ap_inv_pct)*100}%", "Rentabilidad": f"{r1_val}% s/Aportación"}

if st.button("🚀 Generar Informe PDF"):
    try:
        pdf_bytes = create_pdf(pd.DataFrame(res, index=indices), p_glob, p_gast, p_repr, notas_input)
        st.download_button("⬇️ Descargar PDF", pdf_bytes, "informe_v1k.pdf", "application/pdf")
    except Exception as e:
        st.error(f"Error PDF: {e}")
