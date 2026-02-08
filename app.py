import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN DE LA APP ---
st.set_page_config(
    page_title="GESTI Hogar PRO", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # ttl=0 para forzar lectura de la nube siempre
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"❌ Error crítico de sincronización con la nube: {e}")

# Inicialización de la sesión de datos
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- 3. GESTIÓN DE USUARIOS Y PERFILES ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres hoy?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 5.8 🚀")

# --- 4. LÓGICA DE PROCESAMIENTO DE ASIGNACIÓN (SIN ERRORES) ---
def procesar_asignacion_segura():
    """
    Esta función procesa la tarea guardada en el estado temporal.
    Evita los errores de 'callback' de Streamlit al no usar on_click.
    """
    idx = st.session_state.pendiente_idx
    franja = st.session_state.pendiente_franja
    
    # Trabajamos sobre una copia fresca del estado
    df_actual = st.session_state.df.copy()
    row = df_actual.loc[idx]
    
    # CASO A: Tareas con Contador o Multi-Franja
    if row['Tipo'] in ['Contador', 'Multi-Franja']:
        cant_actual = int(row['Cantidad'])
        if cant_actual > 0:
            # Descontamos una unidad de la tarea 'almacén'
            df_actual.at[idx, 'Cantidad'] = cant_actual - 1
            
            # Si es Multi-Franja y se agotan los turnos, la ocultamos de libres
            if row['Tipo'] == 'Multi-Franja' and df_actual.at[idx, 'Cantidad'] == 0:
                df_actual.at[idx, 'Responsable'] = 'Ocupado (Sistema)'
            
            # Creamos la tarea individual para el responsable
            nueva_id = int(df_actual['ID'].max() + 1) if not df_actual.empty else 1
            nueva_fila = pd.DataFrame([{
                'ID': nueva_id,
                'Tarea': row['Tarea'],
                'Frecuencia': 'Puntual', # Se borrará al reiniciar el día
                'Tipo': 'Simple',
                'Para': row['Para'],
                'Responsable': user_name,
                'Estado': 'Pendiente',
                'Franja': franja,
                'Cantidad': 1
            }])
            df_actual = pd.concat([df_actual, nueva_fila], ignore_index=True)
        else:
            st.warning("⚠️ Ya no quedan unidades disponibles para esta tarea.")
            return
    
    # CASO B: Tarea Simple (Asignación directa)
    else:
        df_actual.at[idx, 'Responsable'] = user_name
        df_actual.at[idx, 'Franja'] = franja
        df_actual.at[idx, 'Estado'] = 'Pendiente'

    # Persistimos cambios
    guardar_datos(df_actual)
    # Limpieza de temporales
    del st.session_state.pendiente_idx
    del st.session_state.pendiente_franja

# --- 5. CÁLCULOS DE ESTADO Y MOTIVACIÓN ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Tareas del grupo y personales
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']
mis_tareas_total = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas_total[mis_tareas_total['Estado'] == 'Pendiente']
mis_hechas = mis_tareas_total[mis_tareas_total['Estado'] == 'Hecho']

# Mensajes de Enhorabuena
if not tareas_grupo.empty and pendientes_grupo.empty:
    st.balloons()
    st.success("🌟 **¡IMPRESIONANTE! El equipo ha completado todas las tareas asignadas. ¡Gran coordinación!**")
elif not mis_tareas_total.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **¡BRAVO {user_name.upper()}! Has terminado todas tus responsabilidades. ¡A disfrutar!**")

# --- 6. SECCIÓN: TAREAS DISPONIBLES ---
libres = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]

# Cálculo avanzado de pendientes (Simples + Suma de Contadores)
num_simples = len(libres[~libres['Tipo'].isin(['Contador', 'Multi-Franja'])])
num_unidades = int(libres[libres['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum())
total_ver = num_simples + num_unidades

st.header(f"📌 Tareas Libres ({total_ver} por asignar)")

if total_ver > 0:
    for i, row in libres.iterrows():
        # Filtro de seguridad para contadores agotados
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_txt, col_btns = st.columns([1, 2])
        
        # Etiqueta de tarea
        texto_tarea = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            texto_tarea += f" (Quedan: {int(row['Cantidad'])} unidades)"
        col_txt.write(texto_tarea)
        
        # Botones de Franja
        b1, b2, b3, b4 = col_btns.columns(4)
        franjas_list = [("Mañana", b1), ("Mediodía", b2), ("Tarde", b3), ("Noche", b4)]
        
        for f_nombre, f_col in franjas_list:
            if f_col.button(f_nombre, key=f"btn_{f_nombre}_{i}"):
                st.session_state.pendiente_idx = i
                st.session_state.pendiente_franja = f_nombre
                procesar_asignacion_segura()
                st.rerun()
else:
    st.info("🌈 No hay tareas pendientes para tu grupo ahora mismo. ¡Buen trabajo!")

# --- 7. SECCIÓN: MI PANEL DE CONTROL PERSONAL ---
st.divider()
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes)")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c_p1, c_p2 = st.columns([4, 1])
        # Botón de finalizar
        if c_p1.button(f"✅ Finalizar: {row['Tarea']} [{row['Franja']}]", key=f"hecho_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df)
            st.rerun()
        # Botón de liberar
        if c_p2.button("🔓", key=f"lib_{i}", help="Liberar tarea para que otro la haga"):
            if row['Frecuencia'] == 'Puntual':
                # Si era una copia de contador, se elimina
                st.session_state.df = st.session_state.df.drop(i)
            else:
                # Si era base, se resetea
                st.session_state.df.at[i, 'Responsable'] = 'Sin asignar'
                st.session_state.df.at[i, 'Franja'] = '-'
            guardar_datos(st.session_state.df)
            st.rerun()

# Historial para corregir errores
if not mis_hechas.empty:
    with st.expander("📂 Historial de tareas completadas hoy (Deshacer)"):
        for i, row in mis_hechas.iterrows():
            if st.button(f"🔄 Error: Marcar como pendiente: {row['Tarea']}", key=f"undo_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df)
                st.rerun()

# --- 8. SECCIÓN: VISTA GENERAL DE LA CASA ---
st.divider()
st.subheader("🏠 Resumen de Actividad de la Familia")
st.dataframe(
    df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
    use_container_width=True,
    hide_index=True
)

# --- 9. SECCIÓN: RUTINAS Y CONSEJOS DETALLADOS ---
st.divider()
st.subheader("✨ Rutinas para un Hogar Saludable")
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.info("**🌬️ Habitación Fresca**\n\nVentila tu cuarto al menos 10-15 minutos cada mañana. Renovar el aire mejora tu descanso y concentración.")
with r2:
    st.info("**🧺 Orden es Paz**\n\nRecoge la ropa del suelo, haz la cama y mantén tu mesa despejada. Un entorno ordenado reduce el estrés.")
with r3:
    st.info("**🍎 Energía Saludable**\n\nBebe al menos 2 litros de agua al día y prioriza la fruta fresca. ¡Tu cuerpo necesita combustible del bueno!")
with r4:
    st.info("**🧼 Higiene y Salud**\n\nDucha diaria, cepillado de dientes tras cada comida y ropa limpia. Sentirte limpio te hace sentir mejor.")

# --- 10. SECCIÓN: PANEL DE ADMINISTRACIÓN (PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL AVANZADO DE ADMINISTRACIÓN"):
        st.subheader("📜 Histórico Maestro de Datos")
        st.write("Datos brutos de la hoja de cálculo:")
        st.dataframe(st.session_state.df)

        st.divider()
        st.subheader("➕ Añadir Nueva Tarea al Sistema")
        ad1, ad2, ad3, ad4 = st.columns(4)
        new_t = ad1.text_input("Nombre de la Tarea")
        new_f = ad2.selectbox("Frecuencia", ["Persistente", "Puntual"], help="Las persistentes no se borran al reiniciar.")
        new_tp = ad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        new_p = ad4.selectbox("Para quién", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Tarea en la Nube"):
            if new_t:
                new_id = int(st.session_state.df['ID'].max() + 1)
                new_fila = pd.DataFrame([{
                    'ID': new_id, 'Tarea': new_t, 'Frecuencia': new_f, 'Tipo': new_tp, 
                    'Para': new_p, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 
                    'Franja': '-', 'Cantidad': 1
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_fila], ignore_index=True)
                guardar_datos(st.session_state.df)
                st.success("✅ Tarea añadida con éxito"); st.rerun()

        st.divider()
        st.subheader("🔢 Gestión de Contadores y Turnos")
        # Mostrar solo tareas con unidades
        df_cont = st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])]
        for i, row in df_cont.iterrows():
            ca, cb, cc = st.columns([3, 1, 1])
            ca.write(f"**{row['Tarea']}**: Actualmente {int(row['Cantidad'])} unidades")
            if cb.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if cc.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reinicio de Ciclo")
        res1, res2 = st.columns(2)
        if res1.button("🔌 Reseteo Visual (Cargar de nube)"):
            st.session_state.df = cargar_datos()
            st.rerun()
        if res2.button("💾 FINALIZAR DÍA Y REINICIAR"):
            # Lógica según tu instrucción del 08/02/2026:
            # 1. Mantenemos solo tareas persistentes
            # 2. Reseteamos estados y responsables
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            # Las cantidades se quedan como estén en el histórico
            guardar_datos(df_next)
            st.success("✅ El día se ha reiniciado. Se han borrado las tareas puntuales.")
            st.rerun()
