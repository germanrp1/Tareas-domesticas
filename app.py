import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# --- CONEXIÓN CON GOOGLE SHEETS ---
# Usamos la conexión estándar que lee tus Secrets automáticamente
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Buscamos la pestaña exacta "Datos"
    return conn.read(worksheet="Datos", ttl=0)

def guardar_datos(df_a_guardar):
    # Guardamos en la pestaña exacta "Datos"
    conn.update(worksheet="Datos", data=df_a_guardar)

# --- CARGA INICIAL A LA SESIÓN ---
# Usamos session_state para permitir el Modo Prueba (reseteo sin guardar)
if 'df' not in st.session_state:
    try:
        st.session_state.df = cargar_datos()
    except Exception as e:
        st.error(f"Error al cargar la hoja 'Datos': {e}")
        st.info("Asegúrate de que la pestaña en el Excel se llama exactamente 'Datos' (sin espacios).")
        st.stop()

# --- SIDEBAR Y USUARIOS ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

# --- CABECERA ---
if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350)
st.title("🏠 GESTI Hogar PRO 🚀")

# --- SECCIÓN 1: ASIGNACIÓN DE TAREAS ---
st.header("📌 Tareas Libres")
# Trabajamos sobre la copia de la sesión para permitir pruebas
df_sesion = st.session_state.df

if perfil == "Padre":
    visibles = df_sesion[(df_sesion['Responsable'] == 'Sin asignar') & (df_sesion['Para'].isin(['Padres', 'Todos']))]
else:
    visibles = df_sesion[(df_sesion['Responsable'] == 'Sin asignar') & (df_sesion['Para'].isin(['Hijos', 'Todos']))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        st.write(f"**{row['Tarea']}**")
        c1, c2, c3, c4 = st.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        cols = [c1, c2, c3, c4]
        for idx, f in enumerate(franjas):
            if cols[idx].button(f, key=f"btn_{f}_{i}"):
                st.session_state.df.at[i, 'Responsable'] = user_name
                st.session_state.df.at[i, 'Franja'] = f
                guardar_datos(st.session_state.df) # Guardado real tras asignar
                st.rerun()
else:
    st.success("¡No hay tareas libres!")

# --- SECCIÓN 2: PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = st.session_state.df[st.session_state.df['Responsable'] == user_name]
pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

if not pendientes.empty:
    for i, row in pendientes.iterrows():
        c1, c2 = st.columns([3, 1])
        if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df)
            st.rerun()
        if c2.button("🔓", key=f"free_{i}"):
            st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
            st.session_state.df.at[i, 'Franja'] = '-'
            guardar_datos(st.session_state.df)
            st.rerun()

# --- SECCIÓN 3: CONTROL DE PADRES (LOS 2 RESETEOS) ---
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        # Añadir Nueva Tarea
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Añadir a la lista actual"):
            if n_tarea:
                nueva_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
                nueva_fila = pd.DataFrame([[nueva_id, n_tarea, 'Diario', n_para, 'Sin asignar', 'Pendiente', '-']], 
                                          columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
                st.info("Tarea añadida a la sesión. Se guardará permanentemente si usas el reset de 'Próximo Día'.")

        st.divider()
        st.subheader("Modos de Reseteo")

        # OPCIÓN 1: RESETEO DE PRUEBA (Sin guardar)
        if st.button("🔄 Reseteo de PRUEBA (NO guarda en Excel)"):
            # Recargamos los datos originales del Excel descartando lo que haya en la app
            st.session_state.df = cargar_datos()
            st.warning("⚠️ Datos restaurados desde la nube. No se ha modificado el Excel.")
            st.rerun()

        # OPCIÓN 2: RESETEO REAL (Próximo día, con guardado)
        if st.button("💾 Reinicio PRÓXIMO DÍA (SÍ guarda en Excel)"):
            # Limpiamos los estados de las tareas actuales para empezar de cero
            st.session_state.df['Responsable'] = 'Sin asignar'
            st.session_state.df['Estado'] = 'Pendiente'
            st.session_state.df['Franja'] = '-'
            # Al guardar, si se crearon tareas nuevas, se subirán al Excel
            guardar_datos(st.session_state.df)
            st.success("✅ Excel actualizado: Histórico guardado y tareas reiniciadas.")
            st.rerun()

# --- VISTA GENERAL ---
st.divider()
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)
