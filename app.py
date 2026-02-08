import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Inicialización de la sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- SIDEBAR: USUARIOS ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 5.5 🚀")

# --- LÓGICA DE DATOS Y ESTADÍSTICAS ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Filtrado para cálculos
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_hacer_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']
mis_tareas = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
mis_hechas = mis_tareas[mis_tareas['Estado'] == 'Hecho']

# --- MENSAJES DE MOTIVACIÓN ---
if not tareas_grupo.empty and pendientes_hacer_grupo.empty:
    st.balloons()
    st.success("🌟 **ENHORABUENA, todas las tareas realizadas, ¡BUEN TRABAJO EQUIPO!**")
elif not mis_tareas.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **ENHORABUENA {user_name.upper()}, ¡has terminado todo lo tuyo!**")

# --- FUNCIÓN DE ASIGNACIÓN (REFORZADA CON CALLBACK) ---
def click_asignar(idx, franja):
    # Esta función se ejecuta ANTES de que Streamlit refresque la página
    df_temp = st.session_state.df.copy()
    row = df_temp.loc[idx]
    
    if row['Tipo'] in ['Contador', 'Multi-Franja']:
        cant = int(row['Cantidad'])
        if cant > 0:
            df_temp.at[idx, 'Cantidad'] = cant - 1
            if row['Tipo'] == 'Multi-Franja' and df_temp.at[idx, 'Cantidad'] == 0:
                df_temp.at[idx, 'Responsable'] = 'Ocupado'
            
            nueva_id = int(df_temp['ID'].max() + 1)
            nueva_fila = pd.DataFrame([{
                'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_name,
                'Estado': 'Pendiente', 'Franja': franja, 'Cantidad': 1
            }])
            df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
    else:
        df_temp.at[idx, 'Responsable'] = user_name
        df_temp.at[idx, 'Franja'] = franja
        df_temp.at[idx, 'Estado'] = 'Pendiente'

    guardar_datos(df_temp)
    # Streamlit refrescará automáticamente al terminar la función

# --- 1. SECCIÓN: TAREAS LIBRES ---
libres_grupo = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
simples = len(libres_grupo[~libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])])
acumuladas = int(libres_grupo[libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum())
total_pendientes = simples + acumuladas

st.header(f"📌 Tareas Libres ({total_pendientes} pendientes de asignar)")

if total_pendientes > 0:
    for i, row in libres_grupo.iterrows():
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_t, col_b = st.columns([1, 2])
        label = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            label += f" (Quedan: {int(row['Cantidad'])})"
        
        col_t.write(label)
        f_cols = col_b.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Noche"]
        for idx_f, f_name in enumerate(franjas):
            # Usamos on_click para máxima fiabilidad
            f_cols[idx_f].button(f_name, key=f"f_{f_name}_{i}", on_click=click_asignar, args=(i, f_name))
else:
    st.info("No hay tareas libres para tu grupo ahora mismo. ¡Descansa!")

# --- 2. SECCIÓN: MI PANEL PERSONAL ---
st.divider()
st.header(f"📋 Mi Panel: {user_name} ({len(mis_pendientes)} pendientes)")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c1, c2 = st.columns([4, 1])
        if c1.button(f"✅ Finalizar: {row['Tarea']} [{row['Franja']}]", key=f"do_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df); st.rerun()
        if c2.button("🔓", key=f"rel_{i}", help="Soltar tarea"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df); st.rerun()

# Historial para deshacer
if not mis_hechas.empty:
    with st.expander("Ver mis tareas completadas hoy"):
        for i, row in mis_hechas.iterrows():
            if st.button(f"🔄 Deshacer: {row['Tarea']}", key=f"un_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df); st.rerun()

# --- 3. SECCIÓN: ESTADO GLOBAL DE LA CASA ---
st.divider()
st.subheader("🏠 Vista General de la Familia")
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True)

# --- 4. SECCIÓN: CONSEJOS Y RUTINAS ---
st.divider()
st.subheader("✨ Rutinas para un Hogar Feliz")
r1, r2, r3, r4 = st.columns(4)
with r1: st.info("**🌬️ Aire Fresco**\n\nVentila tu habitación al menos 10 minutos. Es clave para tu salud y concentración.")
with r2: st.info("**🧺 Orden Visual**\n\nRecoge la ropa y haz la cama. Un espacio ordenado es una mente ordenada.")
with r3: st.info("**🍎 Energía**\n\nBebe agua constantemente y prioriza la fruta. Tu cuerpo te lo agradecerá.")
with r4: st.info("**🧼 Autocuidado**\n\nHigiene personal diaria y cepillado de dientes. ¡Siéntete bien contigo mismo!")

# --- 5. SECCIÓN: ADMINISTRACIÓN (SÓLO PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRADOR"):
        st.subheader("📊 Datos Maestros (Excel)")
        st.dataframe(st.session_state.df)

        st.subheader("➕ Añadir Nueva Tarea")
        ad1, ad2, ad3, ad4 = st.columns(4)
        nt = ad1.text_input("Nombre de la Tarea")
        nf = ad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = ad3.selectbox("Tipo de Tarea", ["Simple", "Contador", "Multi-Franja"])
        np = ad4.selectbox("Dirigido a", ["Hijos", "Padres", "Todos"])
        if st.button("Registrar en la lista"):
            if nt:
                nid = int(st.session_state.df['ID'].max() + 1)
                nueva = pd.DataFrame([{
                    'ID': nid, 'Tarea': nt, 'Frecuencia': nf, 'Tipo': ntp, 
                    'Para': np, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 
                    'Franja': '-', 'Cantidad': 1
                }])
                st.session_state.df = pd.concat([st.session_state.df, nueva], ignore_index=True)
                guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste de Cantidades Hoy")
        for i, row in st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])].iterrows():
            ca, cb, cc = st.columns([2, 1, 1])
            ca.write(f"**{row['Tarea']}**: {int(row['Cantidad'])} pendientes")
            if cb.button("➕", key=f"i_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if cc.button("➖", key=f"d_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reseteo de Jornada")
        col_r1, col_r2 = st.columns(2)
        if col_r1.button("🔌 Reseteo Visual (Sin Guardar)"):
            st.session_state.df = cargar_datos(); st.rerun()
        if col_r2.button("💾 GUARDAR Y REINICIAR DÍA"):
            # Lógica según tu instrucción del 08/02/2026
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            guardar_datos(df_next); st.success("Día reiniciado correctamente"); st.rerun()
