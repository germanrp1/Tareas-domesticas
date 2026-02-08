import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_seguro():
    """Carga los datos como en el test de prueba que funcionó"""
    return conn.read(ttl=0)

def guardar_datos_en_nube(df_nuevo):
    """Guarda especificando la pestaña 'Datos'"""
    conn.update(worksheet="Datos", data=df_nuevo)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'df' not in st.session_state:
    try:
        st.session_state.df = cargar_datos_seguro()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

# --- INTERFAZ ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")
st.success("✅ ¡CONECTADO! GESTI Hogar PRO está en línea.")

# 1. SECCIÓN DE ASIGNACIÓN
st.header("📌 Tareas Libres")
df_actual = st.session_state.df
filtro_para = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Filtramos las tareas que no tienen responsable
visibles = df_actual[(df_actual['Responsable'] == 'Sin asignar') & (df_actual['Para'].isin(filtro_para))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        st.write(f"**{row['Tarea']}**")
        cols = st.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        for idx, f in enumerate(franjas):
            if cols[idx].button(f, key=f"btn_{f}_{i}"):
                st.session_state.df.at[i, 'Responsable'] = user_name
                st.session_state.df.at[i, 'Franja'] = f
                guardar_datos_en_nube(st.session_state.df)
                st.rerun()
else:
    st.info("No hay tareas libres para asignar.")

# 2. PANEL PERSONAL
st.header(f"📋 Panel de {user_name}")
mis_tareas = st.session_state.df[st.session_state.df['Responsable'] == user_name]
pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

for i, row in pendientes.iterrows():
    c1, c2 = st.columns([3, 1])
    if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        guardar_datos_en_nube(st.session_state.df)
        st.rerun()
    if c2.button("🔓", key=f"free_{i}"):
        st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
        st.session_state.df.at[i, 'Franja'] = '-'
        guardar_datos_en_nube(st.session_state.df)
        st.rerun()

# 3. CONTROL DE PADRES (ADMIN)
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        # Nueva Tarea
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Añadir a la lista"):
            if n_tarea:
                nueva_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
                nueva_fila = pd.DataFrame([[nueva_id, n_tarea, 'Diario', n_para, 'Sin asignar', 'Pendiente', '-']], 
                                          columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
                st.toast("Tarea añadida localmente.")

        st.divider()
        st.subheader("Opciones de Reseteo")

        # --- MODO 1: RESETEO DE PRUEBA (Sin guardar) ---
        if st.button("🔄 Reseteo de PRUEBA (NO guarda en Excel)"):
            # Recargamos la sesión desde el Excel original (descartamos tareas nuevas y cambios)
            st.session_state.df = cargar_datos_seguro()
            st.warning("⚠️ Datos restaurados. Se han perdido las tareas nuevas no guardadas.")
            st.rerun()

        # --- MODO 2: REINICIO PRÓXIMO DÍA (Guardando todo) ---
        if st.button("💾 Reinicio PRÓXIMO DÍA (SÍ guarda en Excel)"):
            # Reiniciamos estados pero mantenemos las tareas (incluidas las nuevas creadas)
            st.session_state.df['Responsable'] = 'Sin asignar'
            st.session_state.df['Estado'] = 'Pendiente'
            st.session_state.df['Franja'] = '-'
            # Guardamos la tabla completa en el Excel
            guardar_datos_en_nube(st.session_state.df)
            st.success("✅ Reinicio completado. Nuevas tareas y estados guardados en Drive.")
            st.rerun()

# --- VISTA GLOBAL ---
st.divider()
st.subheader("📊 Estado Global de la Casa")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)

