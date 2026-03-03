import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================
st.set_page_config(
    page_title="GESTI Hogar PRO 6.9",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .advice-box { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y GESTIÓN DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        return conn.read(ttl=0)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

def guardar_datos(df_nuevo):
    try:
        df_final = df_nuevo.copy().reset_index(drop=True)
        df_final = df_final.fillna("-")
        conn.update(data=df_final)
        st.session_state.df = df_final
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")
        return False

if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# ==========================================
# 3. PERFILES Y SEGURIDAD
# ==========================================
st.sidebar.title("🎮 Control de Acceso")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_actual = st.sidebar.selectbox("¿Quién está usando la App?", usuarios)
es_admin = user_actual in ["Papá", "Mamá"]
filtro_grupo = ['Padres', 'Todos'] if es_admin else ['Hijos', 'Todos']

st.sidebar.divider()
st.sidebar.info(f"Conectado como: **{user_actual}**")
if es_admin:
    st.sidebar.success("Modo Administrador Activo")

# ==========================================
# 4. LÓGICA DE NEGOCIO (CONTADORES BLINDADOS)
# ==========================================
df = st.session_state.df

def obtener_stock_real(df_actual, nombre_tarea):
    """Calcula el stock restando las filas puntuales de la fila maestra."""
    maestra = df_actual[(df_actual['Tarea'] == nombre_tarea) & (df_actual['Frecuencia'] != 'Puntual')]
    if maestra.empty: return 0
    total_objetivo = int(maestra.iloc[0]['Cantidad'])
    asignadas = len(df_actual[(df_actual['Tarea'] == nombre_tarea) & (df_actual['Frecuencia'] == 'Puntual')])
    return max(0, total_objetivo - asignadas)

# Filtrado de tareas
libres_total = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
mis_pendientes = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Pendiente')]
mis_finalizadas = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Hecho')]

# ==========================================
# 5. INTERFAZ PRINCIPAL
# ==========================================
st.title("🏠 GESTI Hogar PRO 6.9")

# --- SECCIÓN A: TAREAS DISPONIBLES ---
st.header(f"📌 Tareas Libres")

if libres_total.empty:
    st.success("🎉 ¡Todo bajo control!")
else:
    # Solo mostramos tareas que tengan stock o sean normales
    for i, row in libres_total.iterrows():
        stock_disponible = 1 # Valor por defecto para tareas normales
        
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            # Solo procesamos la fila MAESTRA en esta sección
            if row['Frecuencia'] == 'Puntual': continue 
            stock_disponible = obtener_stock_real(df, row['Tarea'])
            if stock_disponible <= 0: continue

        with st.container():
            c_info, c_btns = st.columns([2, 3])
            with c_info:
                badge = "🔢" if row['Tipo'] in ['Contador', 'Multi-Franja'] else "📋"
                txt = f"{badge} **{row['Tarea']}**"
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    txt += f"  \n*(Disponibles: {stock_disponible})*"
                st.write(txt)
            
            with c_btns:
                f1, f2, f3, f4 = st.columns(4)
                franjas = [("Mañana", f1), ("Mediodía", f2), ("Tarde", f3), ("Noche", f4)]
                for f_nombre, col_bt in franjas:
                    if col_bt.button(f_nombre, key=f"asig_{i}_{f_nombre}"):
                        df_temp = st.session_state.df.copy()
                        nueva_tarea = pd.DataFrame([{
                            'ID': df_temp['ID'].max() + 1,
                            'Tarea': row['Tarea'],
                            'Frecuencia': 'Puntual',
                            'Tipo': row['Tipo'],
                            'Para': row['Para'],
                            'Responsable': user_actual,
                            'Estado': 'Pendiente',
                            'Franja': f_nombre,
                            'Cantidad': 1
                        }])
                        # Si es tarea normal, quitamos la original. Si es contador, la dejamos (ya que restamos por cálculo)
                        if row['Tipo'] not in ['Contador', 'Multi-Franja']:
                            df_temp = df_temp.drop(i)
                        
                        df_temp = pd.concat([df_temp, nueva_tarea], ignore_index=True)
                        if guardar_datos(df_temp): st.rerun()

# --- SECCIÓN B: MI ACTIVIDAD ---
st.divider()
col_pend, col_fin = st.columns(2)

with col_pend:
    st.header(f"📋 Mis Pendientes ({len(mis_pendientes)})")
    for i, row in mis_pendientes.iterrows():
        with st.expander(f"🔹 {row['Tarea']} ({row['Franja']})", expanded=True):
            c_h, c_l = st.columns(2)
            if c_h.button("✅ Hecho", key=f"h_{i}"):
                df_temp = st.session_state.df.copy()
                df_temp.at[i, 'Estado'] = 'Hecho'
                if guardar_datos(df_temp): st.rerun()
            if c_l.button("🔓 Liberar", key=f"l_{i}"):
                df_temp = st.session_state.df.copy()
                if row['Frecuencia'] == 'Puntual' and row['Tipo'] not in ['Contador', 'Multi-Franja']:
                    # Si era normal y la liberamos, vuelve a estar sin asignar (pero la fila ya se borró al asignar, hay que recrearla o marcarla)
                    df_temp.at[i, 'Responsable'], df_temp.at[i, 'Franja'] = 'Sin asignar', '-'
                else:
                    df_temp = df_temp.drop(i)
                if guardar_datos(df_temp): st.rerun()

with col_fin:
    st.header(f"✨ Mis Finalizadas ({len(mis_finalizadas)})")
    for i, row in mis_finalizadas.iterrows():
        c_txt, c_undo = st.columns([3, 1])
        c_txt.write(f"🟢 **{row['Tarea']}**")
        if c_undo.button("🔄 Undo", key=f"u_{i}"):
            df_temp = st.session_state.df.copy()
            df_temp.at[i, 'Estado'] = 'Pendiente'
            if guardar_datos(df_temp): st.rerun()

# --- SECCIÓN C: RECOMENDACIONES (SUEÑO, HIGIENE, ALIMENTACIÓN, MENTALIDAD) ---
st.divider()
st.header("💡 Recomendaciones para un Día Pro")
r1, r2, r3, r4 = st.columns(4)

with r1:
    st.subheader("💤 Sueño")
    st.markdown('<div class="advice-box"><b>Horario Fijo:</b> Acuéstate y levántate siempre a la misma hora para regular tu ciclo circadiano.</div>', unsafe_allow_html=True)
    st.markdown('<div class="advice-box"><b>Cero Pantallas:</b> Evita la luz azul (móvil/TV) 1 hora antes de dormir para generar melatonina.</div>', unsafe_allow_html=True)

with r2:
    st.subheader("🍎 Alimentación")
    st.markdown('<div class="advice-box"><b>Proteína y Fibra:</b> Prioriza verduras y proteínas para mantener la energía estable sin picos de azúcar.</div>', unsafe_allow_html=True)
    st.markdown('<div class="advice-box"><b>Hidratación:</b> Bebe un vaso de agua al despertar; tu cuerpo lleva 8 horas en ayunas.</div>', unsafe_allow_html=True)

with r3:
    st.subheader("🧼 Higiene")
    st.markdown('<div class="advice-box"><b>Ventilación:</b> Abre las ventanas 10 min al día; mejora la calidad del aire y elimina toxinas.</div>', unsafe_allow_html=True)
    st.markdown('<div class="advice-box"><b>Orden Visual:</b> Una encimera limpia reduce el cortisol (estrés) al cocinar.</div>', unsafe_allow_html=True)

with r4:
    st.subheader("🧠 Mentalidad")
    st.markdown('<div class="advice-box"><b>Regla de los 2 min:</b> Si una tarea lleva menos de 2 min (ej. fregar un plato), hazla ahora.</div>', unsafe_allow_html=True)
    st.markdown('<div class="advice-box"><b>Agradecimiento:</b> Anota 3 cosas buenas del día antes de dormir para entrenar el optimismo.</div>', unsafe_allow_html=True)

# --- SECCIÓN D: PANEL ADMIN ---
if es_admin:
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN AVANZADO"):
        t1, t2, t3 = st.tabs(["🔄 Reseteos", "➕ Nueva Tarea", "🔢 Ajustar Objetivos"])
        
        with t1:
            c1, c2 = st.columns(2)
            if c1.button("🔄 MODO 1: Recarga Forzada (Mantiene todo)"):
                st.session_state.df = cargar_datos()
                st.rerun()
            if c2.button("💾 MODO 2: Reinicio Próximo Día (Limpia y Sincroniza)"):
                df_reset = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
                df_reset['Responsable'], df_reset['Estado'], df_reset['Franja'] = 'Sin asignar', 'Pendiente', '-'
                if guardar_datos(df_reset): st.balloons(); st.rerun()

        with t2:
            with st.form("new_task"):
                n_t = st.text_input("Tarea")
                n_p = st.selectbox("Para", ["Todos", "Padres", "Hijos"])
                n_tp = st.selectbox("Tipo", ["Normal", "Contador", "Multi-Franja"])
                n_c = st.number_input("Cantidad Objetivo", value=1)
                if st.form_submit_button("Guardar"):
                    nueva_fila = pd.DataFrame([{'ID': df['ID'].max()+1, 'Tarea': n_t, 'Frecuencia': 'Diaria', 'Tipo': n_tp, 'Para': n_p, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': n_c}])
                    if guardar_datos(pd.concat([df, nueva_fila])): st.rerun()

        with t3:
            st.write("Ajusta cuántas veces hay que hacer cada tarea hoy:")
            contadores = df[df['Tipo'].isin(['Contador', 'Multi-Franja']) & (df['Frecuencia'] != 'Puntual')]
            for idx, row in contadores.iterrows():
                col_n, col_v = st.columns([3, 1])
                nuevo_val = col_v.number_input(f"{row['Tarea']}", value=int(row['Cantidad']), key=f"adj_{idx}")
                if nuevo_val != int(row['Cantidad']):
                    df_temp = st.session_state.df.copy()
                    df_temp.at[idx, 'Cantidad'] = nuevo_val
                    if guardar_datos(df_temp): st.rerun()

# --- RESUMEN ---
st.divider()
st.subheader("📊 Resumen General")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True, hide_index=True)
