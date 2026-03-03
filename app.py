import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================
st.set_page_config(
    page_title="GESTI Hogar PRO 6.7",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y GESTIÓN DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    """Carga los datos frescos de la hoja de cálculo."""
    try:
        return conn.read(ttl=0)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

def guardar_datos(df_nuevo):
    """Sincroniza el DataFrame actual con Google Sheets."""
    try:
        # Normalización para evitar errores de envío
        df_final = df_nuevo.copy().reset_index(drop=True)
        df_final = df_final.fillna("-")
        conn.update(data=df_final)
        st.session_state.df = df_final
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")
        return False

# Inicialización de la sesión
if 'df' not in st.session_state:
    with st.spinner('Conectando con la central de tareas...'):
        st.session_state.df = cargar_datos()

# ==========================================
# 3. SEGURIDAD Y PERFILES
# ==========================================
st.sidebar.title("🎮 Control de Acceso")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_actual = st.sidebar.selectbox("¿Quién está usando la App?", usuarios)

# Lógica de permisos
es_admin = user_actual in ["Papá", "Mamá"]
filtro_grupo = ['Padres', 'Todos'] if es_admin else ['Hijos', 'Todos']

st.sidebar.divider()
st.sidebar.info(f"Conectado como: **{user_actual}**")
if es_admin:
    st.sidebar.success("Modo Administrador Activo")

# ==========================================
# 4. LÓGICA DE NEGOCIO (PROCESAMIENTO)
# ==========================================
df = st.session_state.df

# Filtrar listas para la interfaz
libres_total = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
mis_pendientes = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Pendiente')]
mis_finalizadas = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Hecho')]

# ==========================================
# 5. INTERFAZ PRINCIPAL
# ==========================================
st.title("🏠 GESTI Hogar PRO 6.7")
st.caption("Gestión inteligente de tareas domésticas sincronizada en tiempo real.")

# --- SECCIÓN A: TAREAS DISPONIBLES ---
st.header(f"📌 Tareas Libres ({len(libres_total)})")

if libres_total.empty:
    st.success("🎉 ¡No hay tareas libres! Todo está bajo control.")
else:
    for i, row in libres_total.iterrows():
        # Validar si hay stock en contadores
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            try:
                cantidad_disponible = int(row.get('Cantidad', 0))
            except:
                cantidad_disponible = 0
            if cantidad_disponible <= 0:
                continue
        
        with st.container():
            c_info, c_btns = st.columns([2, 3])
            
            with c_info:
                badge = "🔢" if row['Tipo'] in ['Contador', 'Multi-Franja'] else "📋"
                txt = f"{badge} **{row['Tarea']}**"
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    txt += f"  \n*(Disponibles: {int(row['Cantidad'])} unidades)*"
                st.write(txt)
            
            with c_btns:
                f1, f2, f3, f4 = st.columns(4)
                franjas = [("Mañana", f1), ("Mediodía", f2), ("Tarde", f3), ("Noche", f4)]
                
                for f_nombre, col_bt in franjas:
                    if col_bt.button(f_nombre, key=f"asig_{i}_{f_nombre}"):
                        df_temp = st.session_state.df.copy()
                        
                        if row['Tipo'] in ['Contador', 'Multi-Franja']:
                            # Restar del stock principal
                            df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                            # Crear nueva entrada puntual para el usuario
                            nueva_tarea = pd.DataFrame([{
                                'ID': df_temp['ID'].max() + 1,
                                'Tarea': row['Tarea'],
                                'Frecuencia': 'Puntual',
                                'Tipo': row['Tipo'],
                                'Para': row['Para'],
                                'Responsable': user_actual,
                                'Estado': 'Pendiente',
                                'Franja': f_nombre,
                                'Cantidad': 1
                            }])
                            df_temp = pd.concat([df_temp, nueva_tarea], ignore_index=True)
                        else:
                            # Tarea simple: asignar directamente
                            df_temp.at[i, 'Responsable'] = user_actual
                            df_temp.at[i, 'Franja'] = f_nombre
                        
                        if guardar_datos(df_temp):
                            st.toast(f"Asignada: {row['Tarea']}")
                            time.sleep(0.5)
                            st.rerun()

# --- SECCIÓN B: MI ACTIVIDAD ---
st.divider()
col_pend, col_fin = st.columns(2)

with col_pend:
    st.header(f"📋 Mis Tareas Pendientes ({len(mis_pendientes)})")
    if mis_pendientes.empty:
        st.write("☕ Tómate un respiro, no tienes nada pendiente.")
    else:
        for i, row in mis_pendientes.iterrows():
            with st.expander(f"🔹 {row['Tarea']} - {row['Franja']}", expanded=True):
                c_h, c_l = st.columns(2)
                if c_h.button("✅ Marcar Hecho", key=f"h_{i}"):
                    df_temp = st.session_state.df.copy()
                    df_temp.at[i, 'Estado'] = 'Hecho'
                    if guardar_datos(df_temp): st.rerun()
                
                if c_l.button("🔓 Liberar / Error", key=f"l_{i}"):
                    df_temp = st.session_state.df.copy()
                    if row['Frecuencia'] == 'Puntual':
                        # Devolver stock al contador original buscando por nombre y que no sea puntual
                        mask = (df_temp['Tarea'] == row['Tarea']) & (df_temp['Frecuencia'] != 'Puntual')
                        idx_orig = df_temp[mask].index
                        if not idx_orig.empty:
                            df_temp.at[idx_orig[0], 'Cantidad'] = int(df_temp.at[idx_orig[0], 'Cantidad']) + 1
                        df_temp = df_temp.drop(i)
                    else:
                        df_temp.at[i, 'Responsable'] = 'Sin asignar'
                        df_temp.at[i, 'Franja'] = '-'
                    if guardar_datos(df_temp): st.rerun()

with col_fin:
    st.header(f"✨ Mis Tareas Finalizadas ({len(mis_finalizadas)})")
    if mis_finalizadas.empty:
        st.caption("Las tareas que completes aparecerán aquí.")
    else:
        for i, row in mis_finalizadas.iterrows():
            c_txt, c_undo = st.columns([3, 1])
            c_txt.write(f"🟢 **{row['Tarea']}**")
            if c_undo.button("🔄 Deshacer", key=f"u_{i}"):
                df_temp = st.session_state.df.copy()
                df_temp.at[i, 'Estado'] = 'Pendiente'
                if guardar_datos(df_temp): st.rerun()

# --- SECCIÓN C: PANEL DE CONTROL (ADMIN) ---
if es_admin:
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN AVANZADO"):
        st.warning("Atención: Estas acciones modifican la base de datos global.")
        
        c1, c2 = st.columns(2)
        
        if c1.button("🔄 MODO 1: Recarga Forzada (Pruebas)"):
            st.session_state.df = cargar_datos()
            st.info("Sincronización completada desde la nube.")
            st.rerun()
            
        if c2.button("💾 MODO 2: Reinicio Próximo Día"):
            df_actual = st.session_state.df.copy()
            # 1. Eliminar tareas puntuales (clones de contadores)
            # 2. Resetear fijos
            df_reset = df_actual[df_actual['Frecuencia'] != 'Puntual'].copy()
            df_reset['Responsable'] = 'Sin asignar'
            df_reset['Estado'] = 'Pendiente'
            df_reset['Franja'] = '-'
            # Aquí se pueden resetear contadores a valores por defecto si se desea
            if guardar_datos(df_reset):
                st.balloons()
                st.rerun()

# ==========================================
# 6. RESUMEN Y ESTADÍSTICAS (FOOTER)
# ==========================================
st.divider()
with st.container():
    st.subheader("📊 Resumen de Actividad General")
    st.dataframe(
        st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']],
        use_container_width=True,
        hide_index=True
    )
    
    # Barra de progreso real
    tareas_totales = len(df[df['Responsable'] != 'Sin asignar'])
    tareas_hechas = len(df[df['Estado'] == 'Hecho'])
    if tareas_totales > 0:
        porcentaje = tareas_hechas / tareas_totales
        st.progress(porcentaje, text=f"Objetivo diario: {tareas_hechas} de {tareas_totales} tareas completadas ({int(porcentaje*100)}%)")
