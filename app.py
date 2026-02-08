import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠", layout="wide")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Inicialización
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- USUARIOS ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# --- LÓGICA DE CONTADORES Y MENSAJES ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Tareas para mi grupo
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_asignar = tareas_grupo[tareas_grupo['Responsable'] == 'Sin asignar']
pendientes_hacer_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']

# Tareas para mí específicamente
mis_tareas = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
mis_hechas = mis_tareas[mis_tareas['Estado'] == 'Hecho']

# --- MENSAJES DE ENHORABUENA ---
if not tareas_grupo.empty and pendientes_hacer_grupo.empty:
    st.balloons()
    st.success("🌟 **ENHORABUENA, todas las tareas realizadas, ¡BUEN TRABAJO EQUIPO!**")
elif not mis_tareas.empty and mis_pendientes.empty:
    st.success(f"👏 **ENHORABUENA {user_name}, todas tus tareas han sido realizadas, ¡BUEN TRABAJO {user_name}!**")

# --- 1. TAREAS LIBRES ---
st.header(f"📌 Tareas Libres ({len(pendientes_asignar)} pendientes de asignar para tu grupo)")

if not pendientes_asignar.empty:
    for i, row in pendientes_asignar.iterrows():
        with st.container():
            col_t, col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1, 1])
            col_t.write(f"**{row['Tarea']}**")
            franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
            for idx, f in enumerate(franjas):
                if st.columns(4)[idx if idx < 4 else 0].button(f, key=f"btn_{f}_{i}"): # Ajuste layout botones
                    st.session_state.df.at[i, 'Responsable'] = user_name
                    st.session_state.df.at[i, 'Franja'] = f
                    guardar_datos(st.session_state.df)
                    st.rerun()
else:
    st.info("No hay tareas libres para tu grupo.")

st.divider()

# --- 2. MI PANEL PERSONAL ---
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes de hacer)")
if not mis_tareas.empty:
    if not mis_pendientes.empty:
        for i, row in mis_pendientes.iterrows():
            c1, c2 = st.columns([4, 1])
            if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"d_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(st.session_state.df)
                st.rerun()
            if c2.button("🔓", key=f"f_{i}"):
                st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
                st.session_state.df.at[i, 'Franja'] = '-'
                guardar_datos(st.session_state.df)
                st.rerun()
    
    if not mis_hechas.empty:
        with st.expander("Ver mis tareas completadas"):
            for i, row in mis_hechas.iterrows():
                if st.button(f"🔄 Deshacer: {row['Tarea']}", key=f"und_{i}"):
                    st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                    guardar_datos(st.session_state.df)
                    st.rerun()

# --- 3. RUTINA ---
st.divider()
st.markdown("### ✨ Rutina Diaria")
st.caption("🌬️ Ventila | 🧺 Recoge | 🍎 Alimentación | 🧼 Higiene")

# --- 4. ADMINISTRACIÓN ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN"):
        # HISTÓRICO
        st.subheader("📜 Histórico Actual")
        st.dataframe(st.session_state.df)

        # NUEVA TAREA
        st.subheader("➕ Añadir Tarea")
        c_n1, c_n2, c_n3 = st.columns(3)
        nt = c_n1.text_input("Tarea")
        np = c_n2.selectbox("Para", ["Hijos", "Padres", "Todos"])
        nf = c_n3.selectbox("Frecuencia", ["Persistente", "Puntual"])
        if st.button("Añadir"):
            new_id = int(df['ID'].max() + 1) if not df.empty else 1
            new_row = pd.DataFrame([[new_id, nt, nf, np, 'Sin asignar', 'Pendiente', '-']], columns=df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success("Añadida. Dale a Reiniciar para guardar.")

        # RESETEOS
        st.subheader("🔄 Reseteos")
        if st.button("🔌 Reseteo de PRUEBA"):
            st.session_state.df = cargar_datos()
            st.rerun()

        if st.button("💾 REINICIO PRÓXIMO DÍA"):
            # IMPORTANTE: Aquí corregimos que no se quede vacío
            # Si en tu excel la columna Frecuencia está vacía o tiene otros nombres, esto fallaba.
            # Vamos a mantener TODO lo que no sea explícitamente "Puntual"
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            
            # Liberamos todo
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            
            st.session_state.df = df_next
            guardar_datos(df_next)
            st.success("Día reiniciado. Lista liberada.")
            st.rerun()
