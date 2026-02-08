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
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Inicialización de sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- SIDEBAR Y PERFILES ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# --- LÓGICA DE CONTADORES Y MOTIVACIÓN ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Tareas para el grupo del usuario
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
# Calculamos pendientes reales (considerando la columna Cantidad para los contadores)
pendientes_hacer_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']
pendientes_asignar_grupo = tareas_grupo[(tareas_grupo['Responsable'] == 'Sin asignar') & 
                                        ((tareas_grupo['Tipo'] != 'Contador') | (tareas_grupo['Cantidad'] > 0))]

# Tareas personales
mis_tareas = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']

# --- MENSAJES DE ENHORABUENA ---
if not tareas_grupo.empty and pendientes_hacer_grupo.empty:
    st.balloons()
    st.success("🌟 **ENHORABUENA, todas las tareas realizadas, ¡BUEN TRABAJO EQUIPO!**")
elif not mis_tareas.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **ENHORABUENA {user_name}, todas tus tareas han sido realizadas, ¡BUEN TRABAJO {user_name}!**")

# --- FUNCIÓN DE ASIGNACIÓN CORREGIDA ---
def ejecutar_asignacion(index, franja):
    # Cargamos copia fresca para evitar conflictos de sesión
    df_temp = st.session_state.df.copy()
    row = df_temp.loc[index]
    
    if row['Tipo'] == 'Contador':
        if row['Cantidad'] > 0:
            # 1. Descontamos de la tarea original
            df_temp.at[index, 'Cantidad'] = int(row['Cantidad']) - 1
            # 2. Creamos la tarea personal (copia)
            nueva_id = int(df_temp['ID'].max() + 1)
            nueva_fila = {
                'ID': nueva_id,
                'Tarea': row['Tarea'],
                'Frecuencia': 'Puntual', # Para que desaparezca al resetear el día
                'Tipo': 'Simple',
                'Para': row['Para'],
                'Responsable': user_name,
                'Estado': 'Pendiente',
                'Franja': franja,
                'Cantidad': 1
            }
            df_temp = pd.concat([df_temp, pd.DataFrame([nueva_fila])], ignore_index=True)
            st.success(f"Asignada 1 unidad de {row['Tarea']}")
        else:
            st.warning("Ya no quedan repeticiones de esta tarea.")
            return

    elif row['Tipo'] == 'Multi-Franja':
        nueva_id = int(df_temp['ID'].max() + 1)
        nueva_fila = {
            'ID': nueva_id,
            'Tarea': row['Tarea'],
            'Frecuencia': 'Puntual',
            'Tipo': 'Simple',
            'Para': row['Para'],
            'Responsable': user_name,
            'Estado': 'Pendiente',
            'Franja': franja,
            'Cantidad': 1
        }
        df_temp = pd.concat([df_temp, pd.DataFrame([nueva_fila])], ignore_index=True)
        st.success(f"Te has asignado {row['Tarea']} para la {franja}")
        
    else: # Caso Simple
        df_temp.at[index, 'Responsable'] = user_name
        df_temp.at[index, 'Franja'] = franja

    # Actualizar estado y persistir en Google Sheets
    st.session_state.df = df_temp
    guardar_datos(df_temp)
    st.rerun()

# --- 1. SECCIÓN: TAREAS LIBRES ---
num_pend_asig = len(pendientes_asignar_grupo[pendientes_asignar_grupo['Tipo'] != 'Contador']) + int(pendientes_asignar_grupo[pendientes_asignar_grupo['Tipo'] == 'Contador']['Cantidad'].sum())
st.header(f"📌 Tareas Libres ({num_pend_asig} pendientes de asignar para tu grupo)")

if num_pend_asig > 0:
    for i, row in pendientes_asignar_grupo.iterrows():
        col_t, col_b = st.columns([1, 2])
        label = f"**{row['Tarea']}**" + (f" (Quedan: {int(row['Cantidad'])})" if row['Tipo'] == 'Contador' else "")
        col_t.write(label)
        
        f1, f2, f3, f4 = col_b.columns(4)
        if f1.button("Mañana", key=f"m_{i}"): ejecutar_asignacion(i, "Mañana")
        if f2.button("Mediodía", key=f"md_{i}"): ejecutar_asignacion(i, "Mediodía")
        if f3.button("Tarde", key=f"t_{i}"): ejecutar_asignacion(i, "Tarde")
        if f4.button("Noche", key=f"n_{i}"): ejecutar_asignacion(i, "Tarde/Noche")
else:
    st.info("No hay tareas libres para asignar ahora mismo.")

# --- 2. SECCIÓN: MI PANEL PERSONAL ---
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes de hacer)")
if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c1, c2 = st.columns([4, 1])
        if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"do_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df); st.rerun()
        if c2.button("🔓", key=f"rel_{i}", help="Liberar tarea"):
            if row['Frecuencia'] == 'Puntual': st.session_state.df = st.session_state.df.drop(i)
            else: 
                st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
                st.session_state.df.at[i, 'Franja'] = '-'
            guardar_datos(st.session_state.df); st.rerun()

# Deshacer hechas por error
hechas_recientes = mis_tareas[mis_tareas['Estado'] == 'Hecho']
if not hechas_recientes.empty:
    with st.expander("Ver mis tareas finalizadas hoy"):
        for i, row in hechas_recientes.iterrows():
            if st.button(f"🔄 Deshacer: {row['Tarea']}", key=f"und_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df); st.rerun()

# --- 3. SECCIÓN: VISTA GENERAL DE LA CASA ---
st.divider()
st.subheader("🏠 Vista General de la Casa")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True)

# --- 4. SECCIÓN: RUTINAS DETALLADAS ---
st.divider()
st.subheader("✨ Consejos de Rutina")
r1, r2, r3, r4 = st.columns(4)
with r1: st.info("**🌬️ Habitación**\n\nVentila tu cuarto al menos 10 min. Deja que entre aire fresco y luz natural.")
with r2: st.info("**🧺 Orden**\n\nRecoge la ropa del suelo, haz la cama y mantén tu zona despejada.")
with r3: st.info("**🍎 Alimentación**\n\nBebe mucha agua, come fruta y respeta los horarios.")
with r4: st.info("**🧼 Higiene**\n\nDucha diaria, cepillado de dientes y ropa limpia.")

# --- 5. SECCIÓN: ADMINISTRACIÓN Y HISTÓRICO (PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN Y HISTÓRICO"):
        st.subheader("📜 Histórico actual de la lista")
        st.dataframe(st.session_state.df)

        st.subheader("➕ Añadir Nueva Tarea")
        col_ad1, col_ad2, col_ad3, col_ad4 = st.columns(4)
        nt = col_ad1.text_input("Nombre Tarea")
        nf = col_ad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = col_ad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        np = col_ad4.selectbox("Para", ["Hijos", "Padres", "Todos"])
        
        if st.button("Registrar Nueva Tarea"):
            if nt:
                new_id = int(st.session_state.df['ID'].max() + 1)
                new_row = pd.DataFrame([[new_id, nt, nf, ntp, np, 'Sin asignar', 'Pendiente', '-', 1]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                guardar_datos(st.session_state.df); st.success("Tarea añadida"); st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste rápido de Contadores")
        for i, row in st.session_state.df[st.session_state.df['Tipo'] == 'Contador'].iterrows():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{row['Tarea']}** (Hoy: {int(row['Cantidad'])})")
            if c2.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if c3.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reseteos")
        c_res1, c_res2 = st.columns(2)
        if c_res1.button("🔌 Reseteo de PRUEBA (Sin guardar)"):
            st.session_state.df = cargar_datos(); st.rerun()
        if c_res2.button("💾 REINICIO PRÓXIMO DÍA"):
            # Limpiamos puntuales y reseteamos el resto
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'], df_next['Estado'], df_next['Franja'] = 'Sin asignar', 'Pendiente', '-'
            guardar_datos(df_next); st.success("¡Día reiniciado!"); st.rerun()
