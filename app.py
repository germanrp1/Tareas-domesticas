import streamlit as st
import pandas as pd
import os

# Configuración de archivos
CSV_FILE = 'tareas_hogar.py' # Podrías usar .csv, pero algunos hostings prefieren archivos de texto

# 1. Función para cargar datos
def cargar_datos():
    if os.path.exists('tareas.csv'):
        return pd.read_csv('tareas.csv')
    else:
        # Datos iniciales si el archivo no existe
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
        df_inicial.to_csv('tareas.csv', index=False)
        return df_inicial

# 2. Función para guardar datos
def guardar_datos(df):
    df.to_csv('tareas.csv', index=False)

# --- INICIO DE LA APP ---
st.set_page_config(page_title="Hogar Pro 2026", page_icon="🏠")
df = cargar_datos()

# Sidebar para identificación
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"
st.sidebar.info(f"Conectado como: **{perfil}**")

st.title("🏠 Gestión de Tareas Domésticas")

# --- SECCIÓN 1: ASIGNACIÓN ---
st.header("📌 Tareas Libres")
disponibles = df[df['Responsable'] == 'Sin asignar']

if not disponibles.empty:
    for i, row in disponibles.iterrows():
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"**{row['Tarea']}**")
        col2.caption(f"⏱ {row['Frecuencia']}")
        if col3.button("Yo me encargo", key=f"asig_{i}"):
            df.at[i, 'Responsable'] = user_name
            guardar_datos(df)
            st.rerun()
else:
    st.success("¡No hay tareas pendientes de asignación!")

st.divider()

# --- SECCIÓN 2: MI PANEL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = df[df['Responsable'] == user_name]

if not mis_tareas.empty:
    pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
    if not pendientes.empty:
        st.subheader("⏳ Por hacer")
        for i, row in pendientes.iterrows():
            col_a, col_b = st.columns([3, 1])
            if col_a.button(f"✅ Hecha: {row['Tarea']}", key=f"done_{i}"):
                df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(df)
                st.rerun()
            
            # BOTÓN PARA DESASIGNAR
            if col_b.button("🔓 Liberar", key=f"free_{i}", help="Devolver a la lista común"):
                df.at[i, 'Responsable'] = 'Sin asignar'
                guardar_datos(df)
                st.rerun()

    
    # Subsección Hechas (Diferenciadas visualmente)
    completadas = mis_tareas[mis_tareas['Estado'] == 'Hecho']
    if not completadas.empty:
        st.subheader("🎉 Completadas")
        for i, row in completadas.iterrows():
            st.write(f"✔️ :gray[~~{row['Tarea']}~~]") # Texto tachado y gris
else:
    st.info("Aún no tienes tareas asignadas para hoy.")

# --- SECCIÓN 3: CONTROL DE PADRES ---
if perfil == "Padre":
    with st.expander("⚙️ Administrar (Solo Padres)"):
        st.write("Vista general de la casa:")
        st.dataframe(df[['Tarea', 'Responsable', 'Estado']])
        if st.button("🔄 Reiniciar todas las tareas (Nuevo día)"):
            df['Responsable'] = 'Sin asignar'
            df['Estado'] = 'Pendiente'
            guardar_datos(df)
            st.rerun()
