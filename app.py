import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración de archivos
CSV_FILE = 'tareas.csv'
HISTORIAL_FILE = 'historial.csv'

def cargar_datos():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        data = {
            'ID': range(1, 11),
            'Tarea': [
                'Poner/Vaciar Lavavajillas', 'Lavadora y Tender', 'Cocinar Comida/Cena',
                'Limpiar Cocina', 'Bajar Basura/Reciclaje', 'Aspirar/Fregar Suelos',
                'Limpiar Baños', 'Planchar Ropa', 'Compra Semanal', 'Cristales y Polvo'
            ],
            'Frecuencia': ['Diario', 'Diario', 'Diario', 'Diario', 'Diario', 'Semanal', 'Semanal', 'Semanal', 'Semanal', 'Quincenal'],
            'Responsable': ['Sin asignar'] * 10,
            'Estado': ['Pendiente'] * 10
        }
        df_inicial = pd.DataFrame(data)
        df_inicial.to_csv(CSV_FILE, index=False)
        return df_inicial

def guardar_datos(df):
    df.to_csv(CSV_FILE, index=False)

# --- INICIO DE LA APP ---
st.set_page_config(page_title="GESTI Hogar Pro", page_icon="🏠")
df = cargar_datos()

# Sidebar con tu familia
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

# --- CABECERA CON LOGO Y TÍTULO ---
# Mostramos el logo que subiste a GitHub
if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350) # Puedes ajustar el tamaño cambiando el 150
st.title("🏠 GESTI Hogar PRO 🚀")
st.markdown("### *Gestión Inteligente del Hogar*") # Una pequeña descripción elegante debajo

# --- SECCIÓN 1: ASIGNACIÓN ---
st.header("📌 Tareas Libres")
disponibles = df[df['Responsable'] == 'Sin asignar']

if not disponibles.empty:
    for i, row in disponibles.iterrows():
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"**{row['Tarea']}**")
        col2.caption(f"⏱ {row['Frecuencia']}")
        if col3.button("Yo la hago", key=f"asig_{i}"):
            df.at[i, 'Responsable'] = user_name
            guardar_datos(df)
            st.rerun()
else:
    st.success("¡No hay tareas libres!")

st.divider()

# --- SECCIÓN 2: MI PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = df[df['Responsable'] == user_name]

if not mis_tareas.empty:
    # 1. Tareas Pendientes
    pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
    if not pendientes.empty:
        st.subheader("⏳ Por hacer")
        for i, row in pendientes.iterrows():
            c1, c2 = st.columns([3, 1])
            if c1.button(f"✅ Hecha: {row['Tarea']}", key=f"done_{i}"):
                df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(df)
                st.rerun()
            if c2.button("🔓", key=f"free_{i}", help="Liberar tarea"):
                df.at[i, 'Responsable'] = 'Sin asignar'
                guardar_datos(df)
                st.rerun()
    
    # 2. Tareas Completadas (Con botón para desmarcar)
    completadas = mis_tareas[mis_tareas['Estado'] == 'Hecho']
    if not completadas.empty:
        st.subheader("🎉 Completadas")
        for i, row in completadas.iterrows():
            col_txt, col_rev = st.columns([4, 1])
            col_txt.write(f"✔️ :gray[~~{row['Tarea']}~~]")
            if col_rev.button("↩️", key=f"rev_{i}", help="Volver a poner como pendiente"):
                df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(df)
                st.rerun()
else:
    st.info("No tienes tareas asignadas.")

# --- SECCIÓN 3: CONTROL DE PADRES ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ Herramientas de Administración"):
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_freq = st.selectbox("Frecuencia", ["Diario", "Semanal", "Quincenal"])
        if st.button("Guardar Nueva Tarea"):
            if n_tarea:
                nueva_id = df['ID'].max() + 1 if not df.empty else 1
                nueva_fila = pd.DataFrame([{'ID': nueva_id, 'Tarea': n_tarea, 'Frecuencia': n_freq, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente'}])
                df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_datos(df)
                st.rerun()
        
        st.divider()
        st.subheader("Finalizar Período / Reset")
        c_res1, c_res2 = st.columns(2)
        
        with c_res1:
            if st.button("⚠️ Reset por error", use_container_width=True):
                df['Responsable'] = 'Sin asignar'
                df['Estado'] = 'Pendiente'
                guardar_datos(df)
                st.rerun()

        with c_res2:
            if st.button("💾 Finalizar y Guardar", use_container_width=True):
                realizadas = df[(df['Responsable'] != 'Sin asignar') & (df['Estado'] == 'Hecho')].copy()
                if not realizadas.empty:
                    realizadas['Fecha'] = datetime.now().strftime("%Y-%m-%d")
                    if os.path.exists(HISTORIAL_FILE):
                        realizadas.to_csv(HISTORIAL_FILE, mode='a', header=False, index=False)
                    else:
                        realizadas.to_csv(HISTORIAL_FILE, index=False)
                df['Responsable'] = 'Sin asignar'
                df['Estado'] = 'Pendiente'
                guardar_datos(df)
                st.rerun()

    # Mostrar siempre la tabla general para los padres (para que no "desaparezca")
    st.subheader("📊 Estado General de la Casa")
    st.dataframe(df, use_container_width=True)

    if os.path.exists(HISTORIAL_FILE):
        with st.expander("📜 Ver Historial Acumulado"):
            st.dataframe(pd.read_csv(HISTORIAL_FILE), use_container_width=True)
        
