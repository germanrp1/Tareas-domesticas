import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# --- CONEXIÓN SIMPLE ---
# Al no poner argumentos, Streamlit busca directamente [connections.gsheets] en tus secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# Usamos session_state para que el "Modo Prueba" sea posible
if 'df' not in st.session_state:
    try:
        # Cargamos los datos de la pestaña "Datos" (asegúrate que se llama así en el Excel)
        st.session_state.df = conn.read(worksheet="Datos", ttl=0)
    except Exception as e:
        st.error("Error al conectar con la hoja 'Datos'. Revisa el nombre de la pestaña.")
        st.stop()

def actualizar_excel():
    """Guarda el estado actual de la sesión en Google Sheets"""
    conn.update(worksheet="Datos", data=st.session_state.df)

# --- INTERFAZ ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350)
st.title("🏠 GESTI Hogar PRO 🚀")

# --- 1. ASIGNACIÓN ---
st.header("📌 Tareas Libres")
df_actual = st.session_state.df
visibles = df_actual[(df_actual['Responsable'] == 'Sin asignar') & 
                     (df_actual['Para'].isin(['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        st.write(f"**{row['Tarea']}**")
        cols = st.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        for idx, f in enumerate(franjas):
            if cols[idx].button(f, key=f"btn_{f}_{i}"):
                st.session_state.df.at[i, 'Responsable'] = user_name
                st.session_state.df.at[i, 'Franja'] = f
                actualizar_excel() # Guardado normal de asignación
                st.rerun()
else:
    st.success("¡No hay tareas libres!")

# --- 2. PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = st.session_state.df[st.session_state.df['Responsable'] == user_name]
pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

for i, row in pendientes.iterrows():
    c1, c2 = st.columns([3, 1])
    if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        actualizar_excel()
        st.rerun()
    if c2.button("🔓", key=f"free_{i}"):
        st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
        st.session_state.df.at[i, 'Franja'] = '-'
        actualizar_excel()
        st.rerun()

# --- 3. CONTROL DE PADRES (LOS DOS RESETEOS) ---
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        # Añadir Tarea
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Añadir a la lista"):
            nueva_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
            nueva_fila = pd.DataFrame([[nueva_id, n_tarea, 'Diario', n_para, 'Sin asignar', 'Pendiente', '-']], 
                                      columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
            st.toast("Tarea añadida a la sesión actual.")

        st.divider()
        st.subheader("Opciones de Reseteo")
        
        # RESETEO 1: MODO PRUEBA
        if st.button("🔄 Reseteo de PRUEBA (NO guarda en Excel)"):
            # Recargamos los datos limpios del Excel borrando lo que hay en memoria
            st.session_state.df = conn.read(worksheet="Datos", ttl=0)
            st.warning("⚠️ Reseteo local completado. No se han modificado los datos en la nube ni las tareas nuevas.")
            st.rerun()

        # RESETEO 2: REINICIO REAL (SIGUIENTE DÍA)
        if st.button("💾 Reinicio PRÓXIMO DÍA (SÍ guarda en Excel)"):
            # Reiniciamos estados pero mantenemos las tareas (incluyendo las nuevas)
            st.session_state.df['Responsable'] = 'Sin asignar'
            st.session_state.df['Estado'] = 'Pendiente'
            st.session_state.df['Franja'] = '-'
            actualizar_excel() # Aquí sí enviamos todo al Excel
            st.success("✅ Reinicio diario completado. Datos actualizados en el histórico de la nube.")
            st.rerun()

# --- VISTA GLOBAL ---
st.divider()
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)
