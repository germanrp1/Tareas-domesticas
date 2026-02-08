import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠", layout="wide")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Carga la hoja principal (Datos)
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
    except Exception as e:
        st.error(f"Error al guardar en la nube: {e}")

# Inicialización de sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- SIDEBAR: SELECCIÓN DE USUARIO ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# --- 1. TAREAS LIBRES (CLASIFICADAS POR PERFIL Y CON FRANJAS) ---
st.header("📌 Tareas Libres")
df_actual = st.session_state.df
# Filtro según el perfil del usuario
filtro_para = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']
visibles = df_actual[(df_actual['Responsable'] == 'Sin asignar') & (df_actual['Para'].isin(filtro_para))]

if not visibles.empty:
    for i, row in visibles.iterrows():
        with st.container():
            col_t, col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1, 1])
            col_t.write(f"**{row['Tarea']}**")
            franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
            botones = [col_f1, col_f2, col_f3, col_f4]
            
            for idx, f in enumerate(franjas):
                if botones[idx].button(f, key=f"btn_{f}_{i}"):
                    st.session_state.df.at[i, 'Responsable'] = user_name
                    st.session_state.df.at[i, 'Franja'] = f
                    guardar_datos(st.session_state.df)
                    st.rerun()
else:
    st.success("🎉 ¡No hay tareas pendientes de asignación!")

st.divider()

# --- 2. PANEL PERSONAL (MARCAR/DESMARCAR Y LIBERAR) ---
st.header(f"📋 Tareas de {user_name}")
mis_tareas = st.session_state.df[st.session_state.df['Responsable'] == user_name]

if not mis_tareas.empty:
    # Dividimos en Pendientes y Hechas para permitir "desmarcar"
    pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
    hechas = mis_tareas[mis_tareas['Estado'] == 'Hecho']

    if not pendientes.empty:
        st.subheader("Pendientes")
        for i, row in pendientes.iterrows():
            c1, c2 = st.columns([4, 1])
            if c1.button(f"✅ Marcar Hecho: {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Hecho'
                guardar_datos(st.session_state.df)
                st.rerun()
            if c2.button("🔓 Liberar", key=f"free_{i}", help="Devolver a la lista común"):
                st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
                st.session_state.df.at[i, 'Franja'] = '-'
                guardar_datos(st.session_state.df)
                st.rerun()

    if not hechas.empty:
        st.subheader("Completadas hoy")
        for i, row in hechas.iterrows():
            if st.button(f"🔄 Error: Volver a pendiente: {row['Tarea']}", key=f"undo_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df)
                st.rerun()
else:
    st.info("No tienes tareas asignadas por ahora.")

# --- 3. CONSEJOS DE RUTINA (REPRODUCIDOS POR USUARIO) ---
st.divider()
with st.expander("✨ Consejos de Rutina Diaria"):
    cols = st.columns(4)
    with cols[0]:
        st.markdown("**🌬️ Aire:** Ventila tu habitación.")
    with cols[1]:
        st.markdown("**🧺 Orden:** Recoge la ropa y trastos.")
    with cols[2]:
        st.markdown("**🍎 Salud:** Come sano y bebe agua.")
    with cols[3]:
        st.markdown("**🧼 Higiene:** Ducha y cepillado.")

# --- 4. ADMINISTRACIÓN AVANZADA (PARA PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN"):
        # A) NUEVA TAREA
        st.subheader("➕ Añadir Nueva Tarea")
        col_n1, col_n2, col_n3 = st.columns([2, 1, 1])
        nueva_t = col_n1.text_input("Nombre de la Tarea")
        nueva_p = col_n2.selectbox("¿Para quién?", ["Todos", "Hijos", "Padres"])
        tipo_t = col_n3.selectbox("Tipo", ["Persistente", "Puntual"])
        
        if st.button("Añadir Tarea"):
            if nueva_t:
                nueva_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
                nueva_fila = pd.DataFrame([[
                    nueva_id, nueva_t, tipo_t, nueva_p, 'Sin asignar', 'Pendiente', '-'
                ]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
                st.toast("Tarea añadida. Recuerda 'Reiniciar Día' para que sea oficial.")

        st.divider()
        st.subheader("🔄 Gestión de Reseteo")
        
        # MODO 1: RESETEO DE PRUEBA (Según tus instrucciones del 2026-02-08)
        if st.button("🔌 Reseteo de PRUEBA (Sin guardar en Excel)"):
            st.session_state.df = cargar_datos()
            st.warning("⚠️ Se han descartado los cambios locales. Las tareas nuevas NO se guardaron.")
            st.rerun()

        # MODO 2: REINICIO REAL (Según tus instrucciones del 2026-02-08)
        if st.button("💾 REINICIO PARA PRÓXIMO DÍA (Guardar todo)"):
            # 1. Mantenemos las persistentes y las nuevas que hayamos creado en esta sesión
            # (Si son puntuales, se irán; si son persistentes, se quedan)
            df_reinicio = st.session_state.df[st.session_state.df['Frecuencia'] == 'Persistente'].copy()
            
            # 2. LIBERAMOS LA LISTA COMPLETAMENTE
            # Esto hace que las tareas vuelvan a aparecer en "Tareas Libres"
            df_reinicio['Responsable'] = 'Sin asignar'
            df_reinicio['Estado'] = 'Pendiente'
            df_reinicio['Franja'] = '-'
            
            # 3. Actualizamos la sesión y el Excel
            st.session_state.df = df_reinicio
            guardar_datos(st.session_state.df)
            st.success("✅ ¡Día reiniciado! Toda la lista se ha liberado y está disponible de nuevo.")
            st.rerun()

# --- VISTA GLOBAL ---
st.divider()
st.subheader("📊 Vista General de la Casa")
st.dataframe(st.session_state.df, use_container_width=True)
