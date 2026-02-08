import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- 1. CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(
    page_title="GESTI Hogar PRO 6.4", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTIÓN DE CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    """Obtiene la última versión de la lista de tareas."""
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    """
    Sincroniza los cambios con la nube. 
    Limpia índices y tipos de datos para evitar errores de permisos.
    """
    try:
        # Aseguramos tipos de datos numéricos para evitar errores de API
        df_nuevo['ID'] = pd.to_numeric(df_nuevo['ID']).astype(int)
        if 'Cantidad' in df_nuevo.columns:
            df_nuevo['Cantidad'] = pd.to_numeric(df_nuevo['Cantidad']).fillna(1).astype(int)
        
        # Limpieza de valores nulos para estabilidad en hojas públicas
        df_nuevo = df_nuevo.fillna("-")
        
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
        return True
    except Exception as e:
        st.error(f"❌ ERROR CRÍTICO AL GUARDAR: {e}")
        st.warning("⚠️ Detectado conflicto de permisos. Si el error persiste, elimina la cuenta de servicio (iam.gserviceaccount.com) de la lista de compartir de tu Excel.")
        return False

# Inicialización del DataFrame en la sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- 3. SELECCIÓN DE USUARIO Y PERFILES ---
st.sidebar.title("👤 Panel de Usuario")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("Identifícate para continuar:", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.sidebar.divider()
st.sidebar.info(f"**Usuario:** {user_name}\n\n**Acceso:** {perfil}")

st.title("🏠 GESTI Hogar PRO 6.4 🚀")
st.markdown("---")

# --- 4. CÁLCULOS DE PROGRESO Y ESTADOS ---
df = st.session_state.df
filtro_familia = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Tareas relevantes para el usuario actual
tareas_relevantes = df[df['Para'].isin(filtro_familia)]
pendientes_relevantes = tareas_relevantes[tareas_relevantes['Estado'] == 'Pendiente']
mis_pendientes = df[(df['Responsable'] == user_name) & (df['Estado'] == 'Pendiente')]
mis_completadas = df[(df['Responsable'] == user_name) & (df['Estado'] == 'Hecho')]

# Mensajes de celebración
if not tareas_relevantes.empty and pendientes_relevantes.empty:
    st.balloons()
    st.success("🌟 **¡MISIÓN CUMPLIDA!** No quedan tareas pendientes para tu grupo. ¡Buen trabajo en equipo!")
elif not mis_pendientes.empty == False and len(df[df['Responsable'] == user_name]) > 0:
    st.balloons()
    st.success(f"👏 **¡BRAVO, {user_name.upper()}!** Has terminado todas tus responsabilidades personales.")

# --- 5. PANEL DE TAREAS LIBRES (MOTOR DE ASIGNACIÓN) ---
libres = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_familia))]
total_p = len(libres[~libres['Tipo'].isin(['Contador', 'Multi-Franja'])])
unidades_p = int(libres[libres['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum() if not libres.empty else 0)

st.header(f"📌 Tareas Disponibles ({total_p + unidades_p} por asignar)")

if (total_p + unidades_p) > 0:
    for i, row in libres.iterrows():
        # Filtro para no mostrar contadores a cero
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and int(row['Cantidad']) <= 0:
            continue
            
        c_desc, c_ops = st.columns([1.5, 2])
        
        info_t = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            info_t += f" *(Disponibles: {int(row['Cantidad'])} unidades)*"
        c_desc.write(info_t)
        
        # Generación de botones por franja
        f_cols = c_ops.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Noche"]
        
        for idx, f_nom in enumerate(franjas):
            if f_cols[idx].button(f_nom, key=f"assign_{f_nom}_{i}"):
                st.toast(f"⚡ Procesando: {row['Tarea']}...", icon="⏳")
                
                df_work = st.session_state.df.copy()
                
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    # Reducir stock del almacén
                    df_work.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                    if row['Tipo'] == 'Multi-Franja' and df_work.at[i, 'Cantidad'] == 0:
                        df_work.at[i, 'Responsable'] = 'Ocupado'
                    
                    # Crear nueva tarea puntual para el usuario
                    nueva_fila = pd.DataFrame([{
                        'ID': int(df_work['ID'].max() + 1), 'Tarea': row['Tarea'], 
                        'Frecuencia': 'Puntual', 'Tipo': 'Simple', 'Para': row['Para'], 
                        'Responsable': user_name, 'Estado': 'Pendiente', 
                        'Franja': f_nom, 'Cantidad': 1
                    }])
                    df_work = pd.concat([df_work, nueva_fila], ignore_index=True)
                else:
                    # Asignación de tarea simple
                    df_work.at[i, 'Responsable'] = user_name
                    df_work.at[i, 'Franja'] = f_nom
                    df_work.at[i, 'Estado'] = 'Pendiente'
                
                if guardar_datos(df_work):
                    st.toast("✅ Asignada con éxito", icon="🎉")
                    st.rerun()
else:
    st.info("🌈 No hay tareas libres. ¡Es momento de descansar!")

# --- 6. MI PANEL DE CONTROL ---
st.divider()
st.header(f"📋 Mis Tareas Actuales ({len(mis_pendientes)})")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        cp1, cp2 = st.columns([4, 1])
        if cp1.button(f"✅ Finalizar: {row['Tarea']} ({row['Franja']})", key=f"fin_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df); st.rerun()
        if cp2.button("🔓", key=f"lib_{i}", help="Soltar tarea"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df); st.rerun()

# Deshacer tareas
if not mis_completadas.empty:
    with st.expander("📂 Historial de tareas hechas (Deshacer)"):
        for i, row in mis_completadas.iterrows():
            if st.button(f"🔄 Marcar como pendiente: {row['Tarea']}", key=f"undo_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df); st.rerun()

# --- 7. VISTA GENERAL DE LA CASA ---
st.divider()
st.subheader("🏠 Resumen de Actividad")
st.dataframe(
    df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
    use_container_width=True, 
    hide_index=True
)

# --- 8. RUTINAS DE SALUD Y ORDEN ---
st.divider()
st.subheader("✨ Rutinas Diarias Recomendadas")
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.info("**🌬️ Ventilación**\n\nVentila tu dormitorio al menos 15 minutos. El aire fresco mejora la calidad del sueño y la salud pulmonar.")
with r2:
    st.info("**🧺 Orden Personal**\n\nHaz la cama y despeja el escritorio. Un espacio ordenado reduce el ruido visual y aumenta la concentración.")
with r3:
    st.info("**🍎 Nutrición**\n\nBebe suficiente agua y toma una pieza de fruta. Mantener el cuerpo hidratado es clave para tener energía todo el día.")
with r4:
    st.info("**🧼 Autocuidado**\n\nHigiene diaria completa. Sentirse limpio y aseado influye positivamente en tu estado de ánimo y autoestima.")

# --- 9. ADMINISTRACIÓN (ACCESO RESTRINGIDO) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE CONTROL AVANZADO"):
        st.subheader("📊 Gestión de Datos Brutos")
        st.dataframe(st.session_state.df)

        st.divider()
        st.subheader("➕ Crear Nueva Tarea")
        ad1, ad2, ad3, ad4 = st.columns(4)
        new_name = ad1.text_input("Nombre Tarea")
        new_freq = ad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        new_type = ad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        new_target = ad4.selectbox("Destinado a", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Nueva Tarea"):
            if new_name:
                nid = int(st.session_state.df['ID'].max() + 1)
                nueva = pd.DataFrame([{
                    'ID': nid, 'Tarea': new_name, 'Frecuencia': new_freq, 
                    'Tipo': new_type, 'Para': new_target, 'Responsable': 'Sin asignar', 
                    'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1
                }])
                guardar_datos(pd.concat([st.session_state.df, nueva], ignore_index=True))
                st.rerun()

        st.divider()
        st.subheader("🔢 Control de Unidades (Contadores)")
        df_cont = st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])]
        for i, row in df_cont.iterrows():
            ca, cb, cc = st.columns([3, 1, 1])
            ca.write(f"**{row['Tarea']}**: {int(row['Cantidad'])} turnos")
            if cb.button("➕", key=f"plus_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if cc.button("➖", key=f"minus_{i}"):
                st.session_state.df.at[i, 'Cantidad'] -= 1
                guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reinicio de Ciclo")
        if st.button("💾 FINALIZAR DÍA (REGLA 08/02)"):
            # 1. Filtramos: Solo se quedan las tareas persistentes
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            # 2. Reseteamos estados y responsables para el nuevo día
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            # 3. Guardamos y reiniciamos
            guardar_datos(df_next)
            st.success("Día finalizado. Tareas puntuales eliminadas y persistentes reiniciadas.")
            st.rerun()
