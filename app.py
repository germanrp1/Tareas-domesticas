import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import random

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================
st.set_page_config(
    page_title="GESTI Hogar PRO 6.8",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y GESTIÓN DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    """Carga los datos frescos de la hoja de cálculo."""
    try:
        return conn.read(ttl=0)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

def guardar_datos(df_nuevo):
    """Sincroniza el DataFrame actual con Google Sheets."""
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
    with st.spinner('Conectando con la central de tareas...'):
        st.session_state.df = cargar_datos()

# ==========================================
# 3. SEGURIDAD, PERFILES Y RUTINAS
# ==========================================
st.sidebar.title("🎮 Control de Acceso")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_actual = st.sidebar.selectbox("¿Quién está usando la App?", usuarios)

es_admin = user_actual in ["Papá", "Mamá"]
filtro_grupo = ['Padres', 'Todos'] if es_admin else ['Hijos', 'Todos']

st.sidebar.divider()

# --- FUNCIONALIDAD RECUPERADA: RUTINAS Y CONSEJOS ---
st.sidebar.subheader("💡 Rutina del Día")
categorias_rutina = {
    "🧼 Higiene": ["Limpia el móvil con alcohol", "Cambia las toallas de mano", "Ventilar 10 min la habitación"],
    "🍎 Alimentación": ["Bebe un vaso de agua ahora", "Fruta antes de las 18:00", "Prepara el menú de mañana"],
    "🧠 Mentalidad": ["5 min de silencio total", "Escribe 3 cosas agradecidas", "Planifica 1 hora sin pantallas"]
}
cat_elegida = random.choice(list(categorias_rutina.keys()))
consejo = random.choice(categorias_rutina[cat_elegida])
st.sidebar.info(f"**{cat_elegida}**\n\n{consejo}")

st.sidebar.divider()
st.sidebar.info(f"Conectado como: **{user_actual}**")
if es_admin:
    st.sidebar.success("Modo Administrador Activo")

# ==========================================
# 4. LÓGICA DE NEGOCIO
# ==========================================
df = st.session_state.df
libres_total = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
mis_pendientes = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Pendiente')]
mis_finalizadas = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Hecho')]

# ==========================================
# 5. INTERFAZ PRINCIPAL
# ==========================================
st.title("🏠 GESTI Hogar PRO 6.8")
st.caption("Gestión inteligente sincronizada en tiempo real.")

# --- SECCIÓN A: TAREAS DISPONIBLES ---
st.header(f"📌 Tareas Libres ({len(libres_total)})")

if libres_total.empty:
    st.success("🎉 ¡No hay tareas libres!")
else:
    for i, row in libres_total.iterrows():
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            try:
                cantidad_disponible = int(row.get('Cantidad', 0))
            except:
                cantidad_disponible = 0
            if cantidad_disponible <= 0:
                continue
        
        with st.container():
            c_info, c_btns = st.columns([2, 3])
            with c_info:
                badge = "🔢" if row['Tipo'] in ['Contador', 'Multi-Franja'] else "📋"
                txt = f"{badge} **{row['Tarea']}**"
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    txt += f"  \n*(Disponibles: {int(row['Cantidad'])} unidades)*"
                st.write(txt)
            
            with c_btns:
                f1, f2, f3, f4 = st.columns(4)
                franjas = [("Mañana", f1), ("Mediodía", f2), ("Tarde", f3), ("Noche", f4)]
                for f_nombre, col_bt in franjas:
                    if col_bt.button(f_nombre, key=f"asig_{i}_{f_nombre}"):
                        df_temp = st.session_state.df.copy()
                        if row['Tipo'] in ['Contador', 'Multi-Franja']:
                            df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                            nueva_tarea = pd.DataFrame([{
                                'ID': df_temp['ID'].max() + 1, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                                'Tipo': row['Tipo'], 'Para': row['Para'], 'Responsable': user_actual,
                                'Estado': 'Pendiente', 'Franja': f_nombre, 'Cantidad': 1
                            }])
                            df_temp = pd.concat([df_temp, nueva_tarea], ignore_index=True)
                        else:
                            df_temp.at[i, 'Responsable'], df_temp.at[i, 'Franja'] = user_actual, f_nombre
                        
                        if guardar_datos(df_temp):
                            st.toast(f"Asignada: {row['Tarea']}")
                            time.sleep(0.5)
                            st.rerun()

# --- SECCIÓN B: MI ACTIVIDAD ---
st.divider()
col_pend, col_fin = st.columns(2)

with col_pend:
    st.header(f"📋 Mis Tareas Pendientes ({len(mis_pendientes)})")
    if mis_pendientes.empty:
        st.write("☕ Nada pendiente.")
    else:
        for i, row in mis_pendientes.iterrows():
            with st.expander(f"🔹 {row['Tarea']} - {row['Franja']}", expanded=True):
                c_h, c_l = st.columns(2)
                if c_h.button("✅ Marcar Hecho", key=f"h_{i}"):
                    df_temp = st.session_state.df.copy()
                    df_temp.at[i, 'Estado'] = 'Hecho'
                    if guardar_datos(df_temp): st.rerun()
                if c_l.button("🔓 Liberar", key=f"l_{i}"):
                    df_temp = st.session_state.df.copy()
                    if row['Frecuencia'] == 'Puntual':
                        mask = (df_temp['Tarea'] == row['Tarea']) & (df_temp['Frecuencia'] != 'Puntual')
                        idx_orig = df_temp[mask].index
                        if not idx_orig.empty:
                            df_temp.at[idx_orig[0], 'Cantidad'] = int(df_temp.at[idx_orig[0], 'Cantidad']) + 1
                        df_temp = df_temp.drop(i)
                    else:
                        df_temp.at[i, 'Responsable'], df_temp.at[i, 'Franja'] = 'Sin asignar', '-'
                    if guardar_datos(df_temp): st.rerun()

with col_fin:
    st.header(f"✨ Mis Tareas Finalizadas ({len(mis_finalizadas)})")
    for i, row in mis_finalizadas.iterrows():
        c_txt, c_undo = st.columns([3, 1])
        c_txt.write(f"🟢 **{row['Tarea']}**")
        if c_undo.button("🔄 Deshacer", key=f"u_{i}"):
            df_temp = st.session_state.df.copy()
            df_temp.at[i, 'Estado'] = 'Pendiente'
            if guardar_datos(df_temp): st.rerun()

# --- SECCIÓN C: PANEL DE CONTROL (ADMIN AVANZADO RECUPERADO) ---
if es_admin:
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN AVANZADO"):
        tab1, tab2, tab3 = st.tabs(["🔄 Reseteos", "➕ Nueva Tarea", "🔢 Ajustar Contadores"])
        
        with tab1:
            c1, c2 = st.columns(2)
            if c1.button("🔄 MODO 1: Recarga Forzada"):
                st.session_state.df = cargar_datos()
                st.rerun()
            if c2.button("💾 MODO 2: Reinicio Próximo Día"):
                df_reset = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
                df_reset['Responsable'], df_reset['Estado'], df_reset['Franja'] = 'Sin asignar', 'Pendiente', '-'
                if guardar_datos(df_reset): st.balloons(); st.rerun()

        with tab2:
            st.subheader("Añadir Tarea Permanente")
            with st.form("new_task"):
                nt_nombre = st.text_input("Nombre de la Tarea")
                nt_para = st.selectbox("Para", ["Todos", "Padres", "Hijos"])
                nt_tipo = st.selectbox("Tipo", ["Normal", "Contador", "Multi-Franja"])
                nt_frec = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual"])
                nt_cant = st.number_input("Cantidad inicial (si es Contador)", value=1)
                if st.form_submit_button("Guardar Tarea"):
                    df_new = st.session_state.df.copy()
                    nueva_fila = pd.DataFrame([{
                        'ID': df_new['ID'].max() + 1, 'Tarea': nt_nombre, 'Frecuencia': nt_frec,
                        'Tipo': nt_tipo, 'Para': nt_para, 'Responsable': 'Sin asignar',
                        'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': nt_cant
                    }])
                    if guardar_datos(pd.concat([df_new, nueva_fila])): st.success("Tarea guardada!"); st.rerun()

        with tab3:
            st.subheader("Ajustar Repeticiones del Día")
            contadores = df[df['Tipo'].isin(['Contador', 'Multi-Franja']) & (df['Frecuencia'] != 'Puntual')]
            for idx, row in contadores.iterrows():
                col_n, col_v, col_btns = st.columns([2, 1, 2])
                col_n.write(f"**{row['Tarea']}**")
                nueva_val = col_v.number_input("Stock", value=int(row['Cantidad']), key=f"adj_{idx}")
                if nueva_val != int(row['Cantidad']):
                    df_temp = st.session_state.df.copy()
                    df_temp.at[idx, 'Cantidad'] = nueva_val
                    if guardar_datos(df_temp): st.rerun()

# ==========================================
# 6. RESUMEN Y ESTADÍSTICAS
# ==========================================
st.divider()
st.subheader("📊 Resumen General")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True, hide_index=True)

tareas_totales = len(df[df['Responsable'] != 'Sin asignar'])
tareas_hechas = len(df[df['Estado'] == 'Hecho'])
if tareas_totales > 0:
    porcentaje = tareas_hechas / tareas_totales
    st.progress(porcentaje, text=f"{tareas_hechas} de {tareas_totales} tareas completadas ({int(porcentaje*100)}%)")
