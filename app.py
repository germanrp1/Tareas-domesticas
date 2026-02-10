
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

# --- SIDEBAR ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# --- LÓGICA DE CONTADORES Y MOTIVACIÓN ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']

mis_tareas = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

# 1. Mensajes de Motivación (Prioridad arriba)
if not tareas_grupo.empty and pendientes_grupo.empty:
    st.balloons()
    st.success("🌟 **ENHORABUENA, todas las tareas realizadas, ¡BUEN TRABAJO EQUIPO!**")
elif not mis_tareas.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **ENHORABUENA {user_name}, todas tus tareas han sido realizadas, ¡BUEN TRABAJO {user_name}!**")

# --- SECCIÓN 1: TAREAS LIBRES ---
num_libres = len(df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))])
st.header(f"📌 Tareas Libres ({num_libres} pendientes de asignar para tu grupo)")

libres_grupo = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]

for i, row in libres_grupo.iterrows():
    col_t, col_b = st.columns([1, 2])
    col_t.write(f"**{row['Tarea']}**")
    # Los 4 botones en una sola fila
    f1, f2, f3, f4 = col_b.columns(4)
    if f1.button("Mañana", key=f"m_{i}"):
        st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = user_name, "Mañana"
        guardar_datos(st.session_state.df); st.rerun()
    if f2.button("Mediodía", key=f"md_{i}"):
        st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = user_name, "Mediodía"
        guardar_datos(st.session_state.df); st.rerun()
    if f3.button("Tarde", key=f"t_{i}"):
        st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = user_name, "Tarde"
        guardar_datos(st.session_state.df); st.rerun()
    if f4.button("Noche", key=f"n_{i}"):
        st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = user_name, "Tarde/Noche"
        guardar_datos(st.session_state.df); st.rerun()

# --- SECCIÓN 2: MI PANEL ---
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes)")
for i, row in mis_tareas[mis_tareas['Estado'] == 'Pendiente'].iterrows():
    c1, c2 = st.columns([4, 1])
    if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"check_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        guardar_datos(st.session_state.df); st.rerun()
    if c2.button("🔓", key=f"rel_{i}", help="Liberar tarea"):
        st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
        guardar_datos(st.session_state.df); st.rerun()

# Botón para desmarcar hechas por error
with st.expander("Ver mis tareas finalizadas (corregir errores)"):
    for i, row in mis_tareas[mis_tareas['Estado'] == 'Hecho'].iterrows():
        if st.button(f"🔄 Volver a pendiente: {row['Tarea']}", key=f"rev_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Pendiente'
            guardar_datos(st.session_state.df); st.rerun()

# --- SECCIÓN 3: VISTA GENERAL DE LA CASA (Para todos) ---
st.divider()
st.subheader("🏠 Vista General de la Casa (Estado actual)")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado']], use_container_width=True)

# --- SECCIÓN 4: RUTINAS DETALLADAS ---
st.divider()
st.subheader("✨ Consejos de Rutina para un día genial")
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.info("**🌬️ Habitación**\n\nVentila tu cuarto al menos 10 min. Deja que entre aire fresco y luz natural.")
with r2:
    st.info("**🧺 Orden**\n\nRecoge la ropa del suelo, haz la cama y mantén tu zona de estudio despejada.")
with r3:
    st.info("**🍎 Alimentación**\n\nBebe mucha agua, come fruta y respeta los horarios de las comidas.")
with r4:
    st.info("**🧼 Higiene**\n\nDucha diaria, cepillado de dientes tras cada comida y ropa limpia.")

# --- SECCIÓN 5: HISTÓRICO Y ADMIN (SOLO PADRES) ---
if perfil == "Padre":
    st.divider()
    st.subheader("📜 Histórico de Tareas (Para Estadísticas)")
    st.write("Datos acumulados para análisis posterior:")
    st.dataframe(st.session_state.df) # Aquí se ve todo, incluyendo IDs y Frecuencias

    with st.expander("⚙️ Herramientas de Administración"):
        # Añadir Tarea
        st.markdown("### ➕ Añadir Tarea")
        col_ad1, col_ad2, col_ad3 = st.columns(3)
        nt = col_ad1.text_input("Nombre de la Tarea")
        np = col_ad2.selectbox("Destinatario", ["Hijos", "Padres", "Todos"])
        nf = col_ad3.selectbox("Frecuencia", ["Persistente", "Puntual"])
        if st.button("Registrar Tarea"):
            if nt:
                new_id = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
                new_row = pd.DataFrame([[new_id, nt, nf, np, 'Sin asignar', 'Pendiente', '-']], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                st.toast("Añadida. Se guardará al reiniciar el día.")

        st.divider()
        # Reseteos
        st.markdown("### 🔄 Gestión de Reseteo")
        c_res1, c_res2 = st.columns(2)
        if c_res1.button("🔌 Reseteo de PRUEBA (Sin guardar)"):
            st.session_state.df = cargar_datos()
            st.rerun()
        if c_res2.button("💾 REINICIO PARA PRÓXIMO DÍA"):
            # Filtrar: Mantener persistentes y borrar puntuales
            df_reinicio = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_reinicio['Responsable'] = 'Sin asignar'
            df_reinicio['Estado'] = 'Pendiente'
            df_reinicio['Franja'] = '-'
            st.session_state.df = df_reinicio
            guardar_datos(df_reinicio)
            st.success("¡Día reiniciado! Todo listo para mañana.")
            st.rerun()
