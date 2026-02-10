import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="GESTI Hogar PRO 6.6", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo para que los avisos de error y éxito sean más legibles
st.markdown("""
    <style>
    .stAlert { border-radius: 12px; }
    .stButton>button { border-radius: 8px; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.05); }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. MOTOR DE CONEXIÓN (FORZADO A MODO PÚBLICO)
# ==============================================================================
# Creamos la conexión. Importante: Al no pasarle credenciales, usará el enlace público.
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_frescos():
    """Carga los datos ignorando cualquier caché previa del navegador."""
    try:
        # ttl=0 asegura que no use datos guardados antiguos
        return conn.read(ttl=0)
    except Exception as e:
        st.error(f"Error al conectar con la hoja: {e}")
        return pd.DataFrame()

def guardar_cambios_nube(df_nuevo):
    """
    Sincroniza el DataFrame con la hoja de cálculo.
    Si da el error de 'Service Account', intentamos limpiar la sesión.
    """
    try:
        # Limpieza de tipos de datos para que Google Sheets no se queje
        df_nuevo['ID'] = pd.to_numeric(df_nuevo['ID'], errors='coerce').fillna(0).astype(int)
        if 'Cantidad' in df_nuevo.columns:
            df_nuevo['Cantidad'] = pd.to_numeric(df_nuevo['Cantidad'], errors='coerce').fillna(1).astype(int)
        
        # Reseteamos el índice para que la tabla en el Excel sea continua
        df_final = df_nuevo.reset_index(drop=True).fillna("-")
        
        # Ejecución de la actualización
        conn.update(data=df_final)
        st.session_state.df = df_final
        return True
    except Exception as e:
        st.error(f"❌ Error de persistencia: {e}")
        st.info("💡 Si acabas de quitar al usuario de Google, pulsa 'R' en tu teclado o reinicia la pestaña para limpiar la caché del navegador.")
        return False

# Inicialización del estado global de la aplicación
if 'df' not in st.session_state or st.sidebar.button("🔄 Forzar Recarga"):
    st.session_state.df = cargar_datos_frescos()

# ==============================================================================
# 3. GESTIÓN DE PERFILES DE USUARIO
# ==============================================================================
st.sidebar.title("👥 Acceso Familiar")
usuarios_disponibles = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_actual = st.sidebar.selectbox("Selecciona tu nombre:", usuarios_disponibles)
es_admin = user_actual in ["Papá", "Mamá"]
rango_texto = "Administrador" if es_admin else "Usuario Estándar"

st.sidebar.divider()
st.sidebar.markdown(f"**Usuario:** {user_actual}")
st.sidebar.markdown(f"**Rol:** {rango_texto}")
st.sidebar.caption("Sincronización: Activa (Modo Público)")

st.title("🏠 GESTI Hogar PRO 6.6 🚀")
st.markdown(f"Bienvenido de nuevo, **{user_actual}**. Aquí tienes el estado de las tareas.")

# ==============================================================================
# 4. PROCESAMIENTO DE TAREAS Y FILTROS
# ==============================================================================
df = st.session_state.df
# Determinamos qué tareas puede ver/asignarse según su grupo
filtro_grupo = ['Padres', 'Todos'] if es_admin else ['Hijos', 'Todos']

# Filtramos tareas para las diferentes secciones
libres_total = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
mis_pendientes = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Pendiente')]
mis_hechas = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Hecho')]

# Comprobación de éxito total
if libres_total.empty and not mis_pendientes.empty:
    st.success("✨ ¡Genial! No quedan tareas libres para tu grupo.")

# ==============================================================================
# 5. SECCIÓN DE ASIGNACIÓN (TAREAS DISPONIBLES)
# ==============================================================================
st.header("📌 Tareas Libres")

# Conteo de tareas individuales y turnos de contadores
conteo_simples = len(libres_total[~libres_total['Tipo'].isin(['Contador', 'Multi-Franja'])])
conteo_unidades = int(libres_total[libres_total['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum() if not libres_total.empty else 0)

if (conteo_simples + conteo_unidades) > 0:
    for i, row in libres_total.iterrows():
        # Saltamos contadores agotados
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and int(row['Cantidad']) <= 0:
            continue
            
        c_desc, c_btn_group = st.columns([1.5, 2])
        
        txt_tarea = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            txt_tarea += f" *(Disponibles: {int(row['Cantidad'])} unidades)*"
        
        c_desc.write(txt_tarea)
        
        # Botones de franja horaria
        f_cols = c_btn_group.columns(4)
        franjas_nombres = ["Mañana", "Mediodía", "Tarde", "Noche"]
        
        for idx_f, nombre_f in enumerate(franjas_nombres):
            if f_cols[idx_f].button(nombre_f, key=f"asig_{nombre_f}_{i}"):
                st.toast(f"⏳ Asignando '{row['Tarea']}'...", icon="⚡")
                
                df_temp = st.session_state.df.copy()
                
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    # Reducimos una unidad del contador original
                    df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                    # Si es multifranja y se acaba, marcamos como ocupado el original
                    if row['Tipo'] == 'Multi-Franja' and df_temp.at[i, 'Cantidad'] == 0:
                        df_temp.at[i, 'Responsable'] = 'Asignado'
                    
                    # Creamos la tarea individual para el usuario actual
                    nueva_id = int(df_temp['ID'].max() + 1)
                    nueva_fila = pd.DataFrame([{
                        'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                        'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_actual,
                        'Estado': 'Pendiente', 'Franja': nombre_f, 'Cantidad': 1
                    }])
                    df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
                else:
                    # Asignación de tarea normal
                    df_temp.at[i, 'Responsable'] = user_actual
                    df_temp.at[i, 'Franja'] = nombre_f
                    df_temp.at[i, 'Estado'] = 'Pendiente'
                
                if guardar_cambios_nube(df_temp):
                    st.rerun()
else:
    st.info("🌈 No hay tareas pendientes ahora mismo. ¡Disfruta el día!")

# ==============================================================================
# 6. PANEL PERSONAL Y SEGUIMIENTO
# ==============================================================================
st.divider()
st.header(f"📋 Mi Lista Personal ({len(mis_pendientes)})")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        cp1, cp2 = st.columns([4, 1])
        if cp1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"check_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_cambios_nube(st.session_state.df)
            st.rerun()
        if cp2.button("🔓", key=f"liberar_{i}", help="Devolver tarea al grupo"):
            if row['Frecuencia'] == 'Puntual':
                # Si es una copia de contador, se borra
                st.session_state.df = st.session_state.df.drop(i)
            else:
                # Si es fija, vuelve a estar libre
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_cambios_nube(st.session_state.df)
            st.rerun()

# ==============================================================================
# 7. VISTA GENERAL DE LA CASA
# ==============================================================================
st.divider()
st.subheader("🏠 Resumen de Actividad General")
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
             use_container_width=True, hide_index=True)

# ==============================================================================
# 8. RECOMENDACIONES DE RUTINA (EXTENDIDAS)
# ==============================================================================
st.divider()
st.subheader("✨ Consejos de Convivencia y Salud")
r_col1, r_col2, r_col3, r_col4 = st.columns(4)

with r_col1:
    st.info("**🌬️ Ventilación**\n\nAbre las ventanas 15 minutos al levantarte. Renovar el aire oxigena el cerebro y mejora tu ánimo matutino.")
with r_col2:
    st.info("**🧺 Orden Personal**\n\nHaz la cama y recoge tu ropa. Un entorno despejado ayuda a mantener una mente enfocada y reduce el estrés.")
with r_col3:
    st.info("**🍎 Hidratación**\n\nBebe agua a menudo y prioriza la fruta. Tu cuerpo y mente funcionan mucho mejor con combustible natural.")
with r_col4:
    st.info("**🧼 Higiene**\n\nDucha diaria y limpieza dental. El autocuidado es fundamental para mantener la disciplina y el bienestar.")

# ==============================================================================
# 9. PANEL DE ADMINISTRACIÓN (SOLO PADRES)
# ==============================================================================
if es_admin:
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRADOR"):
        st.subheader("➕ Añadir Nueva Tarea")
        ad1, ad2, ad3, ad4 = st.columns(4)
        n_tarea = ad1.text_input("Nombre de la Tarea")
        n_freq = ad2.selectbox("Periodicidad", ["Persistente", "Puntual"])
        n_tipo = ad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        n_para = ad4.selectbox("Dirigido a", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Tarea"):
            if n_tarea:
                n_id = int(st.session_state.df['ID'].max() + 1)
                nueva = pd.DataFrame([{
                    'ID': n_id, 'Tarea': n_tarea, 'Frecuencia': n_freq, 
                    'Tipo': n_tipo, 'Para': n_para, 'Responsable': 'Sin asignar', 
                    'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1
                }])
                guardar_cambios_nube(pd.concat([st.session_state.df, nueva], ignore_index=True))
                st.rerun()

        st.divider()
        st.subheader("🔄 Reinicio de Ciclo (Regla 08/02/2026)")
        if st.button("💾 FINALIZAR DÍA Y REINICIAR"):
            # Filtrar: Mantener persistentes, eliminar puntuales.
            df_reset = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_reset['Responsable'], df_reset['Estado'], df_reset['Franja'] = 'Sin asignar', 'Pendiente', '-'
            guardar_cambios_nube(df_reset)
            st.success("Panel reiniciado. ¡Listos para mañana!")
            st.rerun()
