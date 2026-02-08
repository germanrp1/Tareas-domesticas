import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Lee la hoja de cálculo (ttl=0 para que no use caché y los cambios sean instantáneos)
    return conn.read(worksheet="Sheet1", ttl=0)

def guardar_datos(df):
    # Actualiza la hoja de cálculo en Drive
    conn.update(worksheet="Sheet1", data=df)

# Carga inicial
df = cargar_datos()

# --- SIDEBAR Y USUARIOS ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

# --- CABECERA ---
if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350)
st.title("🏠 GESTI Hogar PRO 🚀")
st.markdown("### *Gestión Inteligente del Hogar*")

# --- SECCIÓN 1: ASIGNACIÓN ---
st.header("📌 Tareas Libres")
if perfil == "Padre":
    visibles = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(['Padres', 'Todos']))]
else:
    visibles = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(['Hijos', 'Todos']))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        st.write(f"**{row['Tarea']}** (⏱ {row['Frecuencia']})")
        c1, c2, c3, c4 = st.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        cols = [c1, c2, c3, c4]
        for idx, f in enumerate(franjas):
            if cols[idx].button(f, key=f"btn_{f}_{i}"):
                df.at[i, 'Responsable'] = user_name
                df.at[i, 'Franja'] = f
                guardar_datos(df)
                st.rerun()
        st.divider()
else:
    st.success("¡No hay tareas libres!")

# --- SECCIÓN 2: MI PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = df[df['Responsable'] == user_name]

if not mis_tareas.empty:
    pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
    if not pendientes.empty:
        for i, row in pendientes.iterrows():
            c1, c2 = st.columns([3, 1])
            if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
                df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(df)
                st.rerun()
            if c2.button("🔓", key=f"free_{i}"):
                df.at[i, 'Responsable'] = 'Sin asignar'
                df.at[i, 'Franja'] = '-'
                guardar_datos(df)
                st.rerun()
    
    completadas = mis_tareas[mis_tareas['Estado'] == 'Hecho']
    if not completadas.empty:
        st.subheader("🎉 Completadas")
        for i, row in completadas.iterrows():
            st.write(f"✔️ :gray[~~{row['Tarea']} ({row['Franja']})~~]")
else:
    st.info("No tienes tareas asignadas.")

# --- SECCIÓN 3: ESTADO GLOBAL ---
st.divider()
st.header("🌍 Estado General de la Casa")
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)

# --- SECCIÓN 4: CONTROL DE PADRES (ADMIN) ---
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Guardar Nueva Tarea"):
            if n_tarea:
                # El ID se calcula automáticamente
                nueva_id = int(df['ID'].max() + 1) if not df.empty else 1
                # Crear nueva fila con el mismo formato que la hoja
                nueva_fila = pd.DataFrame([[nueva_id, n_tarea, 'Diario', n_para, 'Sin asignar', 'Pendiente', '-']], 
                                          columns=df.columns)
                df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_datos(df)
                st.rerun()
        
        st.divider()
        if st.button("⚠️ Resetear todas las asignaciones"):
            df['Responsable'] = 'Sin asignar'
            df['Estado'] = 'Pendiente'
            df['Franja'] = '-'
            guardar_datos(df)
            st.rerun()

# --- RUTINA FINAL ---
st.divider()
st.header(f"✨ Rutina Diaria de {user_name}")
st.markdown("✅ Higiene | 🛏️ Cama | 🌬️ Ventilar | 🍎 Alimentación")
