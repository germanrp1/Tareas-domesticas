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

# Inicialización de sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- USUARIOS ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 5.0 🚀")

# --- LÓGICA DE ASIGNACIÓN ESPECIAL ---
def asignar_tarea(index, nombre_persona, franja_elegida):
    df = st.session_state.df
    tarea_row = df.loc[index]
    
    if tarea_row['Tipo'] == 'Contador':
        if tarea_row['Cantidad'] > 0:
            # 1. Restamos 1 a la cantidad global
            st.session_state.df.at[index, 'Cantidad'] -= 1
            # 2. Creamos una copia personal para el usuario
            nueva_id = int(df['ID'].max() + 1)
            nueva_fila = pd.DataFrame([[
                nueva_id, tarea_row['Tarea'], 'Puntual', 'Simple', tarea_row['Para'], 
                nombre_persona, 'Pendiente', franja_elegida, 1
            ]], columns=df.columns)
            st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
            
    elif tarea_row['Tipo'] == 'Multi-Franja':
        # Creamos una sub-tarea para esa franja específica
        nueva_id = int(df['ID'].max() + 1)
        nueva_fila = pd.DataFrame([[
            nueva_id, tarea_row['Tarea'], 'Puntual', 'Simple', tarea_row['Para'], 
            nombre_persona, 'Pendiente', franja_elegida, 1
        ]], columns=df.columns)
        st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)
        # La tarea original se queda "Sin asignar" para que otros cojan otras franjas
        
    else: # Tipo Simple
        st.session_state.df.at[index, 'Responsable'] = nombre_persona
        st.session_state.df.at[index, 'Franja'] = franja_elegida

    guardar_datos(st.session_state.df)
    st.rerun()

# --- 1. SECCIÓN DE TAREAS LIBRES ---
st.header("📌 Tareas Libres")
df = st.session_state.df
filtro_p = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Solo mostramos tareas base (Sin asignar)
libres = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_p))]

for i, row in libres.iterrows():
    # Si es contador y llegó a 0, no la mostramos como libre
    if row['Tipo'] == 'Contador' and row['Cantidad'] <= 0:
        continue
        
    col_t, col_b = st.columns([1, 2])
    texto_tarea = f"**{row['Tarea']}**"
    if row['Tipo'] == 'Contador':
        texto_tarea += f" (Quedan: {int(row['Cantidad'])})"
    
    col_t.write(texto_tarea)
    f1, f2, f3, f4 = col_b.columns(4)
    if f1.button("Mañana", key=f"m_{i}"): asignar_tarea(i, user_name, "Mañana")
    if f2.button("Mediodía", key=f"md_{i}"): asignar_tarea(i, user_name, "Mediodía")
    if f3.button("Tarde", key=f"t_{i}"): asignar_tarea(i, user_name, "Tarde")
    if f4.button("Noche", key=f"n_{i}"): asignar_tarea(i, user_name, "Tarde/Noche")

# --- 2. MI PANEL PERSONAL ---
st.header(f"📋 Mis Tareas")
mis_pendientes = df[(df['Responsable'] == user_name) & (df['Estado'] == 'Pendiente')]
for i, row in mis_pendientes.iterrows():
    c1, c2 = st.columns([4, 1])
    if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"chk_{i}"):
        st.session_state.df.at[i, 'Estado'] = 'Hecho'
        guardar_datos(st.session_state.df); st.rerun()
    if c2.button("🔓", key=f"rel_{i}"):
        # Si la libero, ¿qué pasa? Si era de un contador, deberíamos devolverla... 
        # Por simplicidad ahora solo la borramos si era copia
        if row['Frecuencia'] == 'Puntual':
            st.session_state.df = st.session_state.df.drop(i)
        else:
            st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
        guardar_datos(st.session_state.df); st.rerun()

# --- 3. ADMINISTRACIÓN (GESTIÓN DE CANTIDADES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE CONTROL (Padres)"):
        st.subheader("🔢 Ajuste de Lavadoras y Contadores para HOY")
        contadores = df[df['Tipo'] == 'Contador']
        for i, row in contadores.iterrows():
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"**{row['Tarea']}** (Actual: {int(row['Cantidad'])})")
            if c2.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if c3.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        if st.button("💾 REINICIO PRÓXIMO DÍA"):
            # 1. Filtramos: Solo nos quedamos con las que NO son Puntuales
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            # 2. Reseteamos estados
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            # Nota: La 'Cantidad' se queda como esté en el Excel (valor por defecto)
            st.session_state.df = df_next
            guardar_datos(df_next)
            st.success("¡Día reiniciado!")
            st.rerun()

# --- VISTA GENERAL Y RUTINAS (Mantenemos lo anterior) ---
st.divider()
st.subheader("🏠 Estado de la Casa")
st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']])
