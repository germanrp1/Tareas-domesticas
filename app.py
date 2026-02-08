import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# --- CONEXIÓN CON GOOGLE SHEETS ---
try:
    url_gsheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection, spreadsheet=url_gsheet)
except Exception:
    st.error("Error al leer la configuración de Secrets.")
    st.stop()

# Usamos st.session_state para manejar el "Modo Prueba" (sin guardado)
if 'df' not in st.session_state:
    try:
        st.session_state.df = conn.read(worksheet="Datos", ttl=0)
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.stop()

def guardar_en_nube():
    """Función para persistir los datos del estado actual al Excel"""
    conn.update(worksheet="Datos", data=st.session_state.df)

# --- SIDEBAR Y USUARIOS ---
st.sidebar.title("👤 Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

# --- CABECERA ---
if os.path.exists("GestiPro.png"):
    st.image("GestiPro.png", width=350)
st.title("🏠 GESTI Hogar PRO 🚀")

# --- SECCIÓN 1: ASIGNACIÓN ---
st.header("📌 Tareas Libres")
df = st.session_state.df # Usamos la copia de la sesión

visibles = df[(df['Responsable'] == 'Sin asignar') & 
              (df['Para'].isin(['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        st.write(f"**{row['Tarea']}**")
        cols = st.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        for idx, f in enumerate(franjas):
            if cols[idx].button(f, key=f"btn_{f}_{i}"):
                st.session_state.df.at[i, 'Responsable'] = user_name
                st.session_state.df.at[i, 'Franja'] = f
                guardar_en_nube() # Guardado automático al asignar
                st.rerun()
else:
    st.success("¡No hay tareas libres!")

# --- SECCIÓN 2: MI PANEL PERSONAL ---
st.header(f"📋 Panel de {user_name}")
mis_tareas = df[df['Responsable'] == user_name]
pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

for i, row in pendientes.iterrows():
    c1, c2 = st.columns([3, 1])
    if c1.button(f"✅ {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        guardar_en_nube()
        st.rerun()
    if c2.button("🔓", key=f"free_{i}"):
        st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
        st.session_state.df.at[i, 'Franja'] = '-'
        guardar_en_nube()
        st.rerun()

# --- SECCIÓN 4: CONTROL DE PADRES (ADMIN) ---
if perfil == "Padre":
    with st.expander("⚙️ Herramientas de Administración"):
        # Añadir tarea (se guarda o no según el botón de reset posterior)
        st.subheader("Añadir Nueva Tarea")
        n_tarea = st.text_input("Nombre de la tarea")
        n_para = st.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        if st.button("Añadir a la lista actual"):
            nueva_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
            nueva_fila = pd.DataFrame([[nueva_id, n_tarea, 'Diario', n_para, 'Sin asignar', 'Pendiente', '-']], 
                                      columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
            st.info("Tarea añadida temporalmente. Usa 'Reinicio Próximo Día' para guardarla en el Excel.")

        st.divider()
        
        # OPCIÓN 1: Reseteo sin guardar (Modo Prueba)
        if st.button("🔄 Reseteo de PRUEBA (Sin guardar en Excel)"):
            # Recargamos los datos originales del Excel a la sesión, descartando cambios actuales
            st.session_state.df = conn.read(worksheet="Datos", ttl=0)
            st.warning("Se han descartado los cambios. La hoja de cálculo no ha sido modificada.")
            st.rerun()

        # OPCIÓN 2: Reseteo guardando (Reinicio Próximo Día)
        if st.button("💾 Reinicio PRÓXIMO DÍA (Guardar y limpiar)"):
            # Limpiamos estados pero mantenemos la estructura para el día siguiente
            st.session_state.df['Responsable'] = 'Sin asignar'
            st.session_state.df['Estado'] = 'Pendiente'
            st.session_state.df['Franja'] = '-'
            guardar_en_nube() # Guardado definitivo incluyendo nuevas tareas
            st.success("Histórico actualizado y estados reiniciados en el Excel.")
            st.rerun()

# --- ESTADO GLOBAL ---
st.divider()
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)
