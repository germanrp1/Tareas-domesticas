import streamlit as st
import pandas as pd
from fpdf import FPDF

# ##############################
# Version V1k - REVISIÓN TOTAL VISIBILIDAD
# ##############################

# 1. Configuración de página y Entorno
st.set_page_config(page_title="JV Analizador Pro", layout="wide")
entorno = st.secrets.get("ENTORNO", "PRODUCCION")

if entorno == "DESARROLLO":
    st.sidebar.warning("🛠️ Modo Desarrollo (Rama Dev)")
else:
    st.sidebar.info("🚀 Modo Producción (Rama Main)")

# 2. Función PDF con Bloques de Parámetros
def create_pdf(df, p_glob, p_gast, p_repr, notas):
    pdf = FPDF()
    pdf.add_page()
    euro = chr(128)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "INFORME DETALLADO DE INVERSION JV".encode('windows-1252', 'ignore').decode('latin-1'), ln=True, align="C")
    
    for title, params in [("A. AJUSTES DEL ESCENARIO", p_glob), 
                          ("B. COSTES Y DIMENSIONAMIENTO", p_gast), 
                          ("C. ACUERDOS DE REPARTO", p_repr)]:
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
        pdf.cell(190, 8, "NOTAS:", ln=True)
        pdf.multi_cell(190, 6, notas.encode('windows-1252', 'ignore').decode('latin-1'))
    
    return pdf.output(dest="S").encode('latin-1')

# --- VALORES POR DEFECTO SOLICITADOS ---
#
with st.sidebar:
    st.header("⚙️ Ajustes Globales")
    modo = st.radio("Calcular por:", ["Precio Venta/Ud", "Precio Compra", "Ben. Objetivo"], index=0)
    meses = st.number_input("Duración Inversión (meses):", value=8) # Valor: 8
    num_gestores = st.number_input("Nº de Gestores:", value=2)
    
    st.divider()
    compra_fija = st.number_input("P. Compra Fijo (€):", value=750000.0) # Valor: 750.000
    e1 = st.number_input("Venta/Ud (€) 1:", value=200000.0) # Valor: 200.000
    e2 = st.number_input("Venta/Ud (€) 2:", value=215000.0) # Valor: 215.000
    e3 = st.number_input("Venta/Ud (€) 3:", value=228000.0) # Valor: 228.000

# --- INTERRUPTOR DESTACADO ---
st.title("🏢 JV Analizador Pro - V1k")
col_int, _ = st.columns([1, 1])
with col_int:
    # Este es el interruptor que no veías. Ahora está fuera de cualquier bloque.
    aplazado_on = st.toggle("🚀 ACTIVAR PAGO APLAZADO", value=False)

# --- BLOQUE GASTOS ---
with st.expander("🏠 Bloque Gastos", expanded=True):
    c1, c2 = st.columns(2)
    num_viviendas = c1.number_input("Nº de Viviendas:", value=7) # Valor: 7
    itp_pct = c2.number_input("ITP/IVA (%):", value=7.0) # Valor: 7%
    notaria = c1.number_input("Notaria (€):", value=1500.0)
    otros_g = c2.number_input("Otros gastos (€):", value=74000.0) # Valor: 74.000
    reforma = c1.number_input("Reforma (€):", value=300000.0) # Valor: 300.000
    desv = c2.number_input("Desviación (€):", value=30000.0)
    
    if aplazado_on:
        st.success("✅ MODO APLAZADO: El capital inicial se reduce a Arras + Gastos.")
        arras_pct = st.slider("% Arras (Gestor):", 0, 20, 10)
    else:
        arras_pct = 0

# --- BLOQUE REPARTOS ---
with st.expander("🤝 Bloque Repartos", expanded=True):
    c3, c4 = st.columns(2)
    ap_inv_pct = c3.number_input("% Aportación Inversor:", value=94.0) / 100 # Valor: 94%
    pct_is = c3.slider("% Sociedades:", 0, 30, 0)
    metodo_rent = c4.selectbox("Método:", ["% ROI fijo sobre Aportación", "% sobre Beneficio Proyecto"], index=0)
    r1_val = c4.number_input("Rentabilidad Pactada (%):", value=15.0) # Valor: 15%
    r1_inv = r1_val / 100

# --- CÁLCULOS ---
escenarios = [e1, e2, e3]
res = {}
for val in escenarios:
    v_total = val * num_viviendas
    itp_euro = compra_fija * (itp_pct / 100)
    gastos_tot = itp_euro + notaria + otros_g + reforma + desv
    
    if aplazado_on:
        arras_euro = compra_fija * (arras_pct / 100)
        c_inicial = arras_euro + gastos_tot
        deuda = compra_fija - arras_euro
        c_inv = gastos_tot * ap_inv_pct
        c_ges = c_inicial - c_inv
    else:
        c_inicial = compra_fija + gastos_tot
        deuda = 0
        c_inv = c_inicial * ap_inv_pct
        c_ges = c_inicial * (1 - ap_inv_pct)

    ben_neto = (v_total - c_inicial - deuda) * (1 - (pct_is/100))
    g_inv = c_inv * r1_inv if metodo_rent == "% ROI fijo sobre Aportación" else ben_neto * r1_inv
    g_ges = ben_neto - g_inv
    
    col_name = f"Venta:\n{v_total:,.0f}€"
    res[col_name] = [f"{c_inicial:,.0f}€", f"{deuda:,.0f}€", f"{ben_neto:,.0f}€", "---",
                     f"{c_inv:,.0f}€", f"{g_inv:,.0f}€", f"{(g_inv/c_inv)*100:.1f}%", "---",
                     f"{c_ges:,.0f}€", f"{g_ges:,.0f}€", f"{(g_ges/(c_ges if c_ges>0 else 1))*100:.1f}%"]

indices = ["Capital Inicial", "Pago Aplazado", "Beneficio Neto", "---", 
           "INV: Aportación", "INV: Ganancia", "INV: ROI", "---",
           "GES: Aportación", "GES: Ganancia", "GES: ROI"]

st.table(pd.DataFrame(res, index=indices))

# 4. Generación PDF
notas = st.text_area("Notas:")
if st.button("🚀 Generar PDF"):
    try:
        p_g = {"Modo": modo, "Meses": meses, "Viviendas": num_viviendas}
        p_gs = {"Compra": compra_fija, "ITP": itp_pct, "Reforma": reforma}
        p_r = {"Aport. Inv": f"{ap_inv_pct*100}%", "ROI Pactado": f"{r1_val}%"}
        pdf_out = create_pdf(pd.DataFrame(res, index=indices), p_g, p_gs, p_r, notas)
        st.download_button("⬇️ Descargar", pdf_out, "informe.pdf", "application/pdf")
    except Exception as e:
        st.error(f"Error: {e}")
