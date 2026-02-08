import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN COMPLETA DE LA APP ---
st.set_page_config(
    page_title="GESTI Hogar PRO 5.9", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN REFORZADA A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    """Carga los datos frescos de la hoja de cálculo."""
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    """Sincroniza el DataFrame con Google Sheets y actualiza la sesión."""
    try:
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"❌ Error de conexión: No se pudo guardar en la nube. Detalles: {e}")

# Inicialización del estado de la sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- 3. GESTIÓN DE USUARIOS Y PERFILES ---
st.sidebar.title("👤 Panel de Acceso")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("Selecciona tu usuario:", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.sidebar.divider()
st.sidebar.info(f"Conectado como: **{user_name}**\n\nPerfil: **{perfil}**")

st.title("🏠 GESTI Hogar PRO 5.9 🚀")
st.markdown("---")

# --- 4. LÓGICA DE DATOS Y ESTADÍSTICAS ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Filtrado para cálculos de progreso
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']
mis_tareas_all = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas_all[mis_tareas_all['Estado'] == 'Pendiente']
mis_hechas = mis_tareas_all[mis_tareas_all['Estado'] == 'Hecho']

# --- 5. MENSAJES DE LOGRO Y MOTIVACIÓN ---
if not tareas_grupo.empty and pendientes_grupo.empty:
    st.balloons()
    st.success("🌟 **¡ENHORABUENA EQUIPO!** Todas las tareas del grupo han sido completadas. ¡Excelente coordinación!")
elif not mis_tareas_all.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **¡BUEN TRABAJO, {user_name.upper()}!** Has terminado todas tus tareas pendientes. ¡Disfruta de tu tiempo libre!")

# --- 6. SECCIÓN: TAREAS DISPONIBLES (MOTOR DE ASIGNACIÓN DIRECTO) ---
libres = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]

# Cálculo detallado de lo que falta (Simples + Unidades de Contadores)
num_simples = len(libres[~libres['Tipo'].isin(['Contador', 'Multi-Franja'])])
num_unidades = int(libres[libres['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum())
total_pendientes_libres = num_simples + num_unidades

st.header(f"📌 Tareas Libres ({total_pendientes_libres} pendientes de asignar)")

if total_pendientes_libres > 0:
    for i, row in libres.iterrows():
        # Saltamos si es un contador vacío
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_info, col_btn = st.columns([1.5, 2])
        
        # Etiqueta descriptiva
        txt_label = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            txt_label += f" *(Quedan: {int(row['Cantidad'])} unidades)*"
        col_info.write(txt_label)
        
        # Botones de Franja Horaria
        f1, f2, f3, f4 = col_btn.columns(4)
        config_franjas = [("Mañana", f1), ("Mediodía", f2), ("Tarde", f3), ("Noche", f4)]
        
        for f_nombre, f_col in config_franjas:
            if f_col.button(f_nombre, key=f"btn_{f_nombre}_{i}"):
                df_temp = df.copy()
                
                # LÓGICA DE ASIGNACIÓN
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    # Descontamos del almacén principal
                    df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                    # Si es multifranja y se agota, marcamos como ocupado para que desaparezca
                    if row['Tipo'] == 'Multi-Franja' and df_temp.at[i, 'Cantidad'] == 0:
                        df_temp.at[i, 'Responsable'] = 'Ocupado'
                    
                    # Creamos la tarea individual para el usuario
                    nueva_id = int(df_temp['ID'].max() + 1)
                    nueva_fila = pd.DataFrame([{
                        'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                        'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_name,
                        'Estado': 'Pendiente', 'Franja': f_nombre, 'Cantidad': 1
                    }])
                    df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
                else:
                    # Tarea Simple: Asignación directa
                    df_temp.at[i, 'Responsable'] = user_name
                    df_temp.at[i, 'Franja'] = f_nombre
                    df_temp.at[i, 'Estado'] = 'Pendiente'
                
                guardar_datos(df_temp)
                st.rerun()
else:
    st.info("✨ No hay tareas pendientes para tu grupo ahora mismo. ¡Relájate!")

# --- 7. SECCIÓN: MI PANEL PERSONAL ---
st.divider()
st.header(f"📋 Mi Panel Personal ({len(mis_pendientes)} tareas)")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c_p1, c_p2 = st.columns([4, 1])
        if c_p1.button(f"✅ Marcar como HECHO: {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df)
            st.rerun()
        if c_p2.button("🔓", key=f"undo_asig_{i}", help="Liberar tarea"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df)
            st.rerun()

# Historial para deshacer fallos
if not mis_hechas.empty:
    with st.expander("📂 Ver mis tareas finalizadas hoy"):
        for i, row in mis_hechas.iterrows():
            if st.button(f"🔄 Devolver a pendiente: {row['Tarea']}", key=f"rev_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df)
                st.rerun()

# --- 8. SECCIÓN: VISTA GENERAL DE LA CASA ---
st.divider()
st.subheader("🏠 Resumen General de Actividades")
st.dataframe(
    df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
    use_container_width=True, 
    hide_index=True
)

# --- 9. SECCIÓN: RUTINAS Y SALUD (DETALLADO) ---
st.divider()
st.subheader("✨ Consejos para una mejor Convivencia")
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.info("**🌬️ Aire Fresco**\n\nVentila tu habitación al menos 10-15 min cada mañana. Renovar el aire mejora tu descanso y concentración notablemente.")
with r2:
    st.info("**🧺 Orden Visual**\n\nRecoge la ropa y haz la cama. Un espacio ordenado proyecta una mente ordenada. ¡Es el primer paso para un gran día!")
with r3:
    st.info("**🍎 Hidratación**\n\nBebe mucha agua y prioriza la fruta fresca entre horas. Tu cuerpo y tu cerebro necesitan combustible de calidad.")
with r4:
    st.info("**🧼 Higiene Personal**\n\nDucha diaria, cepillado de dientes y ropa limpia. Mantener el autocuidado sube el ánimo y la autoestima.")

# --- 10. SECCIÓN: ADMINISTRACIÓN Y CONTROL (SÓLO PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE CONTROL DE ADMINISTRADOR"):
        st.subheader("📊 Histórico Completo (Google Sheets)")
        st.dataframe(st.session_state.df)

        st.divider()
        st.subheader("➕ Añadir Nueva Tarea")
        cad1, cad2, cad3, cad4 = st.columns(4)
        nt = cad1.text_input("Nombre de la Tarea")
        nf = cad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = cad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        np = cad4.selectbox("Destinado a", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Tarea"):
            if nt:
                nid = int(st.session_state.df['ID'].max() + 1)
                nueva = pd.DataFrame([{
                    'ID': nid, 'Tarea': nt, 'Frecuencia': nf, 'Tipo': ntp, 
                    'Para': np, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 
                    'Franja': '-', 'Cantidad': 1
                }])
                st.session_state.df = pd.concat([st.session_state.df, nueva], ignore_index=True)
                guardar_datos(st.session_state.df)
                st.success("¡Tarea añadida!")
                st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste de Unidades (Lavadoras, Platos...)")
        df_cont = st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])]
        for i, row in df_cont.iterrows():
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{row['Tarea']}**: {int(row['Cantidad'])} pendientes hoy")
            if col_b.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if col_c.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reinicio de Jornada")
        c_re1, c_re2 = st.columns(2)
        if c_re1.button("🔌 Recargar datos de la nube"):
            st.session_state.df = cargar_datos(); st.rerun()
        if c_re2.button("💾 FINALIZAR DÍA Y REINICIAR"):
            # Lógica: Mantener persistentes, borrar puntuales, limpiar estados.
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            guardar_datos(df_next)
            st.success("¡Día reiniciado! Todo listo para mañana.")
            st.rerun()
