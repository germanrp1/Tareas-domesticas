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
        # Clasificación inicial: 'Padres', 'Hijos', 'Todos'
        data = {
            'ID': range(1, 11),
            'Tarea': [
                'Poner/Vaciar Lavavajillas', 'Lavadora y Tender', 'Cocinar Comida/Cena',
                'Limpiar Cocina', 'Bajar Basura/Reciclaje', 'Aspirar/Fregar Suelos',
                'Limpiar Baños', 'Planchar Ropa', 'Compra Semanal', 'Cristales y Polvo'
            ],
            'Frecuencia': ['Diario', 'Diario', 'Diario', 'Diario', 'Diario', 'Semanal', 'Semanal', 'Semanal', 'Semanal', 'Quincenal'],
            'Para': ['Hijos', 'Padres', 'Padres', 'Todos', 'Hijos', 'Todos', 'Todos', 'Padres', 'Padres', 'Todos'],
            'Responsable': ['Sin asignar'] * 10,
            'Estado': ['Pendiente'] * 10,
            'Franja': ['-'] * 10
        }
        df_inicial = pd.DataFrame(data)
        df_inicial.to_csv(CSV_FILE, index=False)
        return df_inicial

def guardar_datos(df):
    df.to_csv(CSV_FILE, index=False)

# --- INICIO DE LA APP ---
st.set_page_config(page_title="GESTI Hogar Pro", page_icon="🏠")
df = cargar_datos()

# Asegurar columnas necesarias
if 'Para' not in df.columns: df['Para'] = 'Todos'
if 'Franja' not in df.columns: df['Franja'] = '-'

# Sidebar con tu familia
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

# --- CABECERA ---
if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350)
st.title("🏠 GESTI Hogar PRO 🚀")
st.markdown("### *Gestión Inteligente del Hogar*")

# --- MODO PRESENTACIÓN ---
st.info("📢 EVENTO ESPECIAL HOY A LAS 17:00")

# --- SECCIÓN 1: ASIGNACIÓN FILTRADA ---
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
    st.success("¡No hay tareas libres para asignar!")

# --- SECCIÓN 2: MI PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = df[df['Responsable'] == user_name]

if not mis_tareas.empty:
    pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
    if not pendientes.empty:
        st.subheader("⏳ Por hacer")
        for i, row in pendientes.iterrows():
            c1, c2 = st.columns([3, 1])
            if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
                df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(df)
                st.rerun()
            if c2.button("🔓", key=f"free_{i}", help="Liberar"):
                df.at[i, 'Responsable'] = 'Sin asignar'
                df.at[i, 'Franja'] = '-'
                guardar_datos(df)
                st.rerun()
    
    completadas = mis_tareas[mis_tareas['Estado'] == 'Hecho']
    if not completadas.empty:
        st.subheader("🎉 Completadas")
        for i, row in completadas.iterrows():
            col_txt, col_rev = st.columns([4, 1])
            col_txt.write(f"✔️ :gray[~~{row['Tarea']} ({row['Franja']})~~]")
            if col_rev.button("↩️", key=f"rev_{i}"):
                df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(df)
                st.rerun()
else:
    st.info("No tienes tareas asignadas.")

st.divider()

# --- NUEVA SECCIÓN: ESTADO GLOBAL (VISIBLE PARA TODOS) ---
st.header("🌍 Estado General de la Casa")
st.write("Aquí puedes ver lo que todos están haciendo hoy:")
# Mostramos una versión limpia de la tabla para que todos vean quién hace qué
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)

# --- SECCIÓN 3: CONTROL DE PADRES (SOLO GESTIÓN) ---
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Guardar Nueva Tarea"):
            if n_tarea:
                nueva_id = df['ID'].max() + 1 if not df.empty else 1
                nueva_fila = pd.DataFrame([{'ID': nueva_id, 'Tarea': n_tarea, 'Frecuencia': 'Diario', 'Para': n_para, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 'Franja': '-'}])
                df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_datos(df)
                st.rerun()
        
        st.divider()
        st.subheader("Finalizar Período / Reset")
        c_res1, c_res2 = st.columns(2)
        if c_res1.button("⚠️ Reset por error", use_container_width=True):
            df['Responsable'] = 'Sin asignar'
            df['Estado'] = 'Pendiente'
            df['Franja'] = '-'
            guardar_datos(df)
            st.rerun()
        if c_res2.button("💾 Finalizar y Guardar", use_container_width=True):
            realizadas = df[(df['Responsable'] != 'Sin asignar') & (df['Estado'] == 'Hecho')].copy()
            if not realizadas.empty:
                realizadas['Fecha'] = datetime.now().strftime("%Y-%m-%d")
                realizadas.to_csv(HISTORIAL_FILE, mode='a', header=not os.path.exists(HISTORIAL_FILE), index=False)
            df['Responsable'] = 'Sin asignar'
            df['Estado'] = 'Pendiente'
            df['Franja'] = '-'
            guardar_datos(df)
            st.rerun()

# --- SECCIÓN FINAL: RUTINA DIARIA (PARA TODOS) ---
st.divider()
st.header(f"✨ Rutina Diaria de {user_name}")
st.markdown(f"""
✅ **Higiene:** Lávate la cara y cepíllate los dientes.  
🛏️ **Orden:** Haz tu cama y recoge tu ropa.  
🌬️ **Salud:** Ventila tu cuarto al menos 10 minutos.  
🍎 **Alimentación:** Cuida lo que comes y bebe suficiente agua.  
📚 **Mente:** Revisa tus tareas y prepárate para mañana.
""")

if os.path.exists(HISTORIAL_FILE) and perfil == "Padre":
    with st.expander("📜 Ver Historial Acumulado"):
        st.dataframe(pd.read_csv(HISTORIAL_FILE), use_container_width=True)
                
