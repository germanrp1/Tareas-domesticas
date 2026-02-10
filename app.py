import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==============================================================================
st.set_page_config(page_title="GESTI Hogar PRO 6.6", page_icon="🏠", layout="wide")

st.markdown("""
    <style>
    .stAlert { border-radius: 12px; }
    .stButton>button { border-radius: 8px; transition: 0.3s; width: 100%; }
    .stButton>button:hover { transform: scale(1.05); background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. CONEXIÓN Y PERSISTENCIA
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        # Limpieza técnica antes de subir para evitar errores de tipo
        df_final = df_nuevo.copy().reset_index(drop=True).fillna("-")
        if 'ID' in df_final.columns:
            df_final['ID'] = pd.to_numeric(df_final['ID'], errors='coerce').fillna(0).astype(int)
        if 'Cantidad' in df_final.columns:
            df_final['Cantidad'] = pd.to_numeric(df_final['Cantidad'], errors='coerce').fillna(1).astype(int)
        
        conn.update(data=df_final)
        st.session_state.df = df_final
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar en la nube: {e}")
        return False

# Inicialización del estado
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# ==============================================================================
# 3. PERFILES Y FILTROS
# ==============================================================================
usuarios_disponibles = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_actual = st.sidebar.selectbox("👤 ¿Quién eres?", usuarios_disponibles)
es_admin = user_actual in ["Papá", "Mamá"]
filtro_grupo = ['Padres', 'Todos'] if es_admin else ['Hijos', 'Todos']

st.title("🏠 GESTI Hogar PRO 6.6 🚀")
st.markdown(f"Bienvenido, **{user_actual}**. {'(Modo Administrador)' if es_admin else ''}")

# Procesamiento de datos actuales
df = st.session_state.df
libres_total = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
mis_pendientes = df[(df['Responsable'] == user_actual) & (df['Estado'] == 'Pendiente')]

# Motivación
if not libres_total.empty and len(mis_pendientes) == 0:
    st.info("💡 Tienes tareas disponibles para asignar. ¡Ayuda a la familia!")
elif libres_total.empty and not mis_pendientes.empty:
    st.success("✨ ¡Buen trabajo! Ya no quedan tareas libres para tu grupo.")
elif libres_total.empty and mis_pendientes.empty:
    st.balloons()
    st.success("🌟 ¡TODO LISTO! Disfruta del descanso.")

# ==============================================================================
# 4. SECCIÓN: ASIGNACIÓN POR FRANJAS (LÓGICA MEJORADA)
# ==============================================================================
st.header("📌 Tareas Libres")

if not libres_total.empty:
    for i, row in libres_total.iterrows():
        # Saltamos contadores agotados
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and int(row.get('Cantidad', 1)) <= 0:
            continue
            
        c_desc, c_btn_group = st.columns([1.5, 2.5])
        
        txt_tarea = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            txt_tarea += f" *(Disponibles: {int(row['Cantidad'])} unidades)*"
        c_desc.write(txt_tarea)
        
        # Los 4 botones de franja
        f_cols = c_btn_group.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Noche"]
        
        for idx, f_nombre in enumerate(franjas):
            if f_cols[idx].button(f_nombre, key=f"asig_{f_nombre}_{i}"):
                df_temp = st.session_state.df.copy()
                
                # Caso A: Tareas con stock (Contador/Multi-Franja)
                if row['Tipo'] in ['Contador', 'Multi-Franja']:
                    df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                    if row['Tipo'] == 'Multi-Franja' and df_temp.at[i, 'Cantidad'] == 0:
                        df_temp.at[i, 'Responsable'] = 'Asignado'
                    
                    # Creamos la tarea individual para el usuario
                    nueva_id = int(df_temp['ID'].max() + 1)
                    nueva_fila = pd.DataFrame([{
                        'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                        'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_actual,
                        'Estado': 'Pendiente', 'Franja': f_nombre, 'Cantidad': 1
                    }])
                    df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
                
                # Caso B: Tarea normal
                else:
                    df_temp.at[i, 'Responsable'] = user_actual
                    df_temp.at[i, 'Franja'] = f_nombre
                    df_temp.at[i, 'Estado'] = 'Pendiente'
                
                if guardar_datos(df_temp):
                    st.rerun()
else:
    st.info("🌈 No hay tareas pendientes de asignar.")

# ==============================================================================
# 5. PANEL PERSONAL Y SEGUIMIENTO
# ==============================================================================
st.divider()
st.header(f"📋 Mi Lista Personal ({len(mis_pendientes)})")

if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        cp1, cp2 = st.columns([4, 1])
        if cp1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"check_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df)
            st.rerun()
        if cp2.button("🔓", key=f"liberar_{i}", help="Devolver al grupo"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df)
            st.rerun()

# ==============================================================================
# 6. VISTA GENERAL Y CONSEJOS
# ==============================================================================
st.divider()
with st.expander("🏠 Resumen de Actividad General (Toda la casa)"):
    st.dataframe(st.session_state.df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
                 use_container_width=True, hide_index=True)

st.subheader("✨ Consejos de Convivencia")
r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.info("**🌬️ Ventilación**\n\n15 min de aire fresco al despertar.")
r_col2.info("**🧺 Orden**\n\nHaz la cama y recoge tu ropa.")
r_col3.info("**🍎 Hidratación**\n\nBebe agua y prioriza la fruta.")
r_col4.info("**🧼 Higiene**\n\nDucha diaria y cepillado dental.")

# ==============================================================================
# 7. PANEL DE ADMIN (REGLA 08/02/2026)
# ==============================================================================
if es_admin:
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRADOR"):
        # Añadir Nueva Tarea
        st.subheader("➕ Añadir Nueva Tarea")
        ad1, ad2, ad3, ad4 = st.columns(4)
        n_tarea = ad1.text_input("Nombre")
        n_freq = ad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        n_tipo = ad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        n_para = ad4.selectbox("Para", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Tarea"):
            if n_tarea:
                n_id = int(st.session_state.df['ID'].max() + 1)
                nueva = pd.DataFrame([{
                    'ID': n_id, 'Tarea': n_tarea, 'Frecuencia': n_freq, 
                    'Tipo': n_tipo, 'Para': n_para, 'Responsable': 'Sin asignar', 
                    'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1
                }])
                guardar_datos(pd.concat([st.session_state.df, nueva], ignore_index=True))
                st.rerun()

        st.divider()
        st.subheader("🔄 Modos de Reseteo (Instrucción 08/02/26)")
        c_res1, c_res2 = st.columns(2)
        
        # MODO 1: Sin guardar (Pruebas)
        if c_res1.button("🔄 Modo 1: Reset Interfaz (Sin guardar)"):
            st.session_state.df = cargar_datos()
            st.toast("Interfaz restaurada. No se han modificado datos en la nube.")
            st.rerun()
            
        # MODO 2: Con guardado (Reinicio real)
        if c_res2.button("💾 Modo 2: Reinicio Diario (Guardar Cambios)"):
            # Mantenemos solo tareas persistentes
            df_reset = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_reset['Responsable'], df_reset['Estado'], df_reset['Franja'] = 'Sin asignar', 'Pendiente', '-'
            if guardar_datos(df_reset):
                st.success("Día finalizado y sincronizado. ¡Todo listo para mañana!")
                st.rerun()
