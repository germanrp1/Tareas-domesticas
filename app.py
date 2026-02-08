import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # ttl=0 para asegurar que siempre traiga los datos más frescos
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"Error crítico al guardar en la nube: {e}")

# Inicialización de la sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- SIDEBAR: SELECCIÓN DE USUARIO ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 🚀")

# --- LÓGICA DE CONTADORES Y MOTIVACIÓN ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Filtrar tareas del grupo
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_hacer_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']

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

# --- FUNCIÓN DE ASIGNACIÓN UNIFICADA (v5.3) ---
def ejecutar_asignacion(index, franja_elegida):
    df_temp = st.session_state.df.copy()
    row = df_temp.loc[index]
    
    # Lógica para Contador y Multi-Franja (ambas usan la columna Cantidad)
    if row['Tipo'] in ['Contador', 'Multi-Franja']:
        if row['Cantidad'] > 0:
            # 1. Descontamos 1 de la cantidad global
            df_temp.at[index, 'Cantidad'] = int(row['Cantidad']) - 1
            
            # 2. Creamos copia personal (Puntual para que se borre al resetear)
            nueva_id = int(df_temp['ID'].max() + 1) if not df_temp.empty else 1
            nueva_fila = pd.DataFrame([{
                'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_name,
                'Estado': 'Pendiente', 'Franja': franja_elegida, 'Cantidad': 1
            }])
            df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
            
            # Si es Multi-Franja y se agotan los turnos, marcamos responsable sistema para ocultar
            if row['Tipo'] == 'Multi-Franja' and df_temp.at[index, 'Cantidad'] == 0:
                df_temp.at[index, 'Responsable'] = 'Sistema'
        else:
            st.warning("No quedan más turnos disponibles para esta tarea.")
            return
    else:
        # Caso Simple
        df_temp.at[index, 'Responsable'] = user_name
        df_temp.at[index, 'Franja'] = franja_elegida
    
    guardar_datos(df_temp)
    st.rerun()

# --- 1. SECCIÓN: TAREAS LIBRES ---
libres_grupo = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
# Cálculo de total real (tareas simples + suma de contadores/turnos)
simples = len(libres_grupo[~libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])])
acumuladas = int(libres_grupo[libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum())
num_tot = simples + acumuladas

st.header(f"📌 Tareas Libres ({num_tot} turnos/tareas por asignar)")

if num_tot > 0:
    for i, row in libres_grupo.iterrows():
        # Ocultar si es contador/multi y llegó a 0
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_t, col_b = st.columns([1, 2])
        label = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            label += f" (Quedan: {int(row['Cantidad'])} turnos)"
        
        col_t.write(label)
        f1, f2, f3, f4 = col_b.columns(4)
        if f1.button("Mañana", key=f"m_{i}"): ejecutar_asignacion(i, "Mañana")
        if f2.button("Mediodía", key=f"md_{i}"): ejecutar_asignacion(i, "Mediodía")
        if f3.button("Tarde", key=f"t_{i}"): ejecutar_asignacion(i, "Tarde")
        if f4.button("Noche", key=f"n_{i}"): ejecutar_asignacion(i, "Tarde/Noche")
else:
    st.info("¡Genial! No hay tareas pendientes de asignar para tu grupo.")

# --- 2. SECCIÓN: MI PANEL PERSONAL ---
st.divider()
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes)")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c1, c2 = st.columns([4, 1])
        if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"do_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df); st.rerun()
        if c2.button("🔓", key=f"rel_{i}", help="Liberar"):
            # Si es puntual (copia de contador), se borra. Si es base, se libera.
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df); st.rerun()

# Deshacer errores
if not mis_tareas[mis_tareas['Estado'] == 'Hecho'].empty:
    with st.expander("Ver mis tareas finalizadas hoy (Deshacer)"):
        for i, row in mis_tareas[mis_tareas['Estado'] == 'Hecho'].iterrows():
            if st.button(f"🔄 Error: Volver a pendiente: {row['Tarea']}", key=f"un_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df); st.rerun()

# --- 3. SECCIÓN: VISTA GENERAL ---
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

# --- 5. SECCIÓN: ADMINISTRACIÓN (PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN"):
        st.subheader("📜 Histórico / Lista Completa")
        st.dataframe(st.session_state.df)

        st.subheader("➕ Añadir Nueva Tarea")
        ca1, ca2, ca3, ca4 = st.columns(4)
        nt = ca1.text_input("Nombre")
        nf = ca2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = ca3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        np = ca4.selectbox("Para", ["Hijos", "Padres", "Todos"])
        if st.button("Registrar Tarea"):
            if nt:
                nid = int(st.session_state.df['ID'].max() + 1) if not st.session_state.df.empty else 1
                nueva = pd.DataFrame([{'ID': nid, 'Tarea': nt, 'Frecuencia': nf, 'Tipo': ntp, 'Para': np, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1}])
                st.session_state.df = pd.concat([st.session_state.df, nueva], ignore_index=True)
                guardar_datos(st.session_state.df); st.success("Añadida"); st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste de Contadores para Hoy")
        for i, row in st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])].iterrows():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{row['Tarea']}** (Quedan: {int(row['Cantidad'])})")
            if c2.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if c3.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Gestión de Reseteo")
        res1, res2 = st.columns(2)
        if res1.button("🔌 Reseteo de PRUEBA (Sin guardar)"):
            st.session_state.df = cargar_datos(); st.rerun()
        if res2.button("💾 REINICIO PRÓXIMO DÍA"):
            # Según tus instrucciones del 08/02/2026
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'], df_next['Estado'], df_next['Franja'] = 'Sin asignar', 'Pendiente', '-'
            # Las cantidades se mantienen según el valor que tengan en ese momento
            guardar_datos(df_next); st.success("¡Día reiniciado!"); st.rerun()
