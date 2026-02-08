import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Leemos la primera hoja disponible (Datos)
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    """Intenta guardar y captura si falta el permiso de escritura"""
    try:
        # Intentamos el guardado directo
        conn.update(data=df_nuevo)
        st.success("☁️ Guardado en Google Sheets")
    except Exception as e:
        st.error(f"⚠️ Error de escritura: {e}")
        st.info("Para poder guardar, la hoja debe estar compartida con permisos de EDITOR para cualquier persona con el enlace, o configurar una Service Account.")

if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- LÓGICA DE USUARIOS ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# 1. ASIGNACIÓN
st.header("📌 Tareas Libres")
df = st.session_state.df
filtro = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']
visibles = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        if st.button(f"📍 {row['Tarea']}", key=f"t_{i}"):
            st.session_state.df.at[i, 'Responsable'] = user_name
            st.session_state.df.at[i, 'Estado'] = 'Pendiente'
            guardar_datos(st.session_state.df)
            st.rerun()

# 2. PANEL PERSONAL
st.header(f"📋 Panel de {user_name}")
mis_tareas = st.session_state.df[st.session_state.df['Responsable'] == user_name]
pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

for i, row in pendientes.iterrows():
    if st.button(f"✅ Hecho: {row['Tarea']}", key=f"done_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        guardar_datos(st.session_state.df)
        st.rerun()

# 3. CONTROL DE PADRES (LOS 2 RESETEOS)
if perfil == "Padre":
    with st.expander("⚙️ Administración"):
        # RESETEO 1: PRUEBA
        if st.button("🔄 Reseteo de PRUEBA (Sin guardar)"):
            st.session_state.df = cargar_datos() # Solo recarga, no modifica el excel
            st.warning("Datos de la lista reiniciados localmente (sin cambios en Drive).")
            st.rerun()

        # RESETEO 2: REAL
        if st.button("💾 Reinicio PRÓXIMO DÍA (Guardar todo)"):
            st.session_state.df['Responsable'] = 'Sin asignar'
            st.session_state.df['Estado'] = 'Pendiente'
            st.session_state.df['Franja'] = '-'
            # Aquí sí intentamos actualizar el Excel con las nuevas tareas si las hay
            guardar_datos(st.session_state.df)
            st.success("¡Día reiniciado y guardado!")
            st.rerun()

st.divider()
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Estado']])
