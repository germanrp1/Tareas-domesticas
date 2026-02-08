import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# ==========================================
# 1. CONFIGURACIÓN E INTERFAZ DE USUARIO
# ==========================================
st.set_page_config(
    page_title="GESTI Hogar PRO 6.5 Premium", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado para mejorar la visibilidad de las alertas
st.markdown("""
    <style>
    .stAlert { border-radius: 10px; border: 1px solid #ff4b4b; }
    .main { background-color: #fafafa; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE CONEXIÓN A LA NUBE
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_maestros():
    """Llamada a la base de datos de Google Sheets sin caché."""
    return conn.read(ttl=0)

def sincronizar_nube(df_actualizado):
    """
    Envía los cambios a la hoja de cálculo. 
    Incluye limpieza de datos para evitar errores de tipo en celdas públicas.
    """
    try:
        # Aseguramos integridad de tipos antes de subir
        df_actualizado['ID'] = pd.to_numeric(df_actualizado['ID']).astype(int)
        if 'Cantidad' in df_actualizado.columns:
            df_actualizado['Cantidad'] = pd.to_numeric(df_actualizado['Cantidad']).fillna(1).astype(int)
        
        # Eliminamos valores nulos que corrompen la escritura en modo público
        df_final = df_actualizado.fillna("-")
        
        # Ejecución del comando de actualización
        conn.update(data=df_final)
        st.session_state.df = df_final
        return True
    except Exception as error_msg:
        # Captura el error de 'Public Spreadsheet' que vimos en la imagen
        st.error(f"⚠️ ERROR DE SINCRONIZACIÓN: {error_msg}")
        st.warning("👉 SOLUCIÓN: Si el error persiste, abre tu Excel y BORRA al usuario 'streamlit-app@...' de la lista de compartir. Deja solo 'Cualquier persona con el enlace'.")
        return False

# Carga inicial de datos
if 'df' not in st.session_state:
    with st.spinner("Conectando con la base de datos familiar..."):
        st.session_state.df = cargar_datos_maestros()

# ==========================================
# 3. IDENTIFICACIÓN Y PERFILES FAMILIARES
# ==========================================
st.sidebar.title("👤 Panel de Control de Usuario")
lista_familia = ["Papá", "Mamá", "Jesús", "Cris", "María"]
nombre_seleccionado = st.sidebar.selectbox("¿Quién está usando la App?", lista_familia)
es_padre = nombre_seleccionado in ["Papá", "Mamá"]
perfil_tipo = "Padre/Administrador" if es_padre else "Hijo/Usuario"

st.sidebar.divider()
st.sidebar.markdown(f"**Usuario Activo:** {nombre_seleccionado}")
st.sidebar.markdown(f"**Rango:** {perfil_tipo}")
st.sidebar.write("---")
st.sidebar.caption("v6.5 - Versión de alta capacidad")

st.title("🏠 GESTI Hogar PRO 6.5 🚀")
st.write(f"¡Hola **{nombre_seleccionado}**! Gestiona las tareas de casa de forma eficiente y colaborativa.")

# ==========================================
# 4. LÓGICA DE FILTRADO Y PROGRESO
# ==========================================
df_main = st.session_state.df
filtro_rol = ['Padres', 'Todos'] if es_padre else ['Hijos', 'Todos']

# Extracción de subconjuntos de datos para las vistas
tareas_libres_raw = df_main[(df_main['Responsable'] == 'Sin asignar') & (df_main['Para'].isin(filtro_rol))]
mis_tareas_pendientes = df_main[(df_main['Responsable'] == nombre_seleccionado) & (df_main['Estado'] == 'Pendiente')]
mis_tareas_hechas = df_main[(df_main['Responsable'] == nombre_seleccionado) & (df_main['Estado'] == 'Hecho')]

# Comprobación de fin de jornada
if not tareas_libres_raw.empty == False and not mis_tareas_pendientes.empty == True:
    st.balloons()
    st.success(f"🎊 **¡FANTÁSTICO {nombre_seleccionado.upper()}!** No tienes tareas pendientes y el panel está despejado.")

# ==========================================
# 5. PANEL DE ASIGNACIÓN (TAREAS LIBRES)
# ==========================================
st.header("📌 Tareas Disponibles para Asignar")

# Cálculo de pendientes reales (Simples + Unidades de contadores)
total_libres = len(tareas_libres_raw[~tareas_libres_raw['Tipo'].isin(['Contador', 'Multi-Franja'])])
unidades_disponibles = int(tareas_libres_raw[tareas_libres_raw['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum() if not tareas_libres_raw.empty else 0)

if (total_libres + unidades_disponibles) > 0:
    for idx_row, fila in tareas_libres_raw.iterrows():
        # Ignorar contadores vacíos
        if fila['Tipo'] in ['Contador', 'Multi-Franja'] and int(fila['Cantidad']) <= 0:
            continue
            
        c_label, c_btns = st.columns([1.5, 2])
        
        texto_display = f"**{fila['Tarea']}**"
        if fila['Tipo'] in ['Contador', 'Multi-Franja']:
            texto_display += f" *(Quedan: {int(fila['Cantidad'])} unidades)*"
        
        c_label.write(texto_display)
        
        # Botones de selección de turno
        col_m, col_md, col_t, col_n = c_btns.columns(4)
        mapeo_franjas = [("Mañana", col_m), ("Mediodía", col_md), ("Tarde", col_t), ("Noche", col_n)]
        
        for nombre_f, columna_f in mapeo_franjas:
            if columna_f.button(nombre_f, key=f"btn_{nombre_f}_{idx_row}"):
                st.toast(f"⚡ Procesando: {fila['Tarea']}...", icon="⏳")
                
                df_proceso = st.session_state.df.copy()
                
                if fila['Tipo'] in ['Contador', 'Multi-Franja']:
                    # Lógica de reducción de stock
                    df_proceso.at[idx_row, 'Cantidad'] = int(fila['Cantidad']) - 1
                    # Si es multifranja y llegamos a 0, lo ocultamos
                    if fila['Tipo'] == 'Multi-Franja' and df_proceso.at[idx_row, 'Cantidad'] == 0:
                        df_proceso.at[idx_row, 'Responsable'] = 'Asignado'
                    
                    # Inserción de la tarea individualizada
                    id_max = int(df_proceso['ID'].max() + 1)
                    nueva_fila_personal = pd.DataFrame([{
                        'ID': id_max, 'Tarea': fila['Tarea'], 'Frecuencia': 'Puntual',
                        'Tipo': 'Simple', 'Para': fila['Para'], 'Responsable': nombre_seleccionado,
                        'Estado': 'Pendiente', 'Franja': nombre_f, 'Cantidad': 1
                    }])
                    df_proceso = pd.concat([df_proceso, nueva_fila_personal], ignore_index=True)
                else:
                    # Lógica de asignación de tarea única
                    df_proceso.at[idx_row, 'Responsable'] = nombre_seleccionado
                    df_proceso.at[idx_row, 'Franja'] = nombre_f
                    df_proceso.at[idx_row, 'Estado'] = 'Pendiente'
                
                if sincronizar_nube(df_proceso):
                    st.toast("✅ Tarea guardada con éxito", icon="🎉")
                    st.rerun()
else:
    st.info("🌈 No hay tareas libres. ¡Buen momento para un descanso!")

# ==========================================
# 6. MI PANEL PERSONAL (TAREAS ASIGNADAS)
# ==========================================
st.divider()
st.header(f"📋 Mis Tareas: {nombre_seleccionado}")

if not mis_tareas_pendientes.empty:
    for i, r in mis_tareas_pendientes.iterrows():
        c_p1, c_p2 = st.columns([4, 1])
        if c_p1.button(f"✅ Finalizar: {r['Tarea']} ({r['Franja']})", key=f"fin_user_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            sincronizar_nube(st.session_state.df)
            st.rerun()
        if c_p2.button("🔓", key=f"rel_user_{i}", help="Liberar tarea"):
            if r['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            sincronizar_nube(st.session_state.df)
            st.rerun()
else:
    st.write("Aún no te has asignado ninguna tarea para hoy.")

# Historial de corrección
if not mis_tareas_hechas.empty:
    with st.expander("📂 Tareas que ya he terminado hoy (Haga clic para deshacer)"):
        for i, r in mis_tareas_hechas.iterrows():
            if st.button(f"🔄 Reabrir: {r['Tarea']}", key=f"undo_user_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                sincronizar_nube(st.session_state.df)
                st.rerun()

# ==========================================
# 7. VISTA GENERAL Y ESTADÍSTICAS
# ==========================================
st.divider()
st.subheader("🏠 Resumen de Actividad en el Hogar")
st.dataframe(
    df_main[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], 
    use_container_width=True, 
    hide_index=True
)

# ==========================================
# 8. RUTINAS DE SALUD Y BIENESTAR
# ==========================================
st.divider()
st.subheader("✨ Rutinas Diarias para un Hogar Saludable")
col_r1, col_r2, col_r3, col_r4 = st.columns(4)

with col_r1:
    st.info("**🌬️ Aire Puro**\n\nVentila tu habitación al menos 15 minutos al despertar. Elimina el CO2 acumulado y mejora tu capacidad de concentración.")
with col_r2:
    st.info("**🧺 Orden Visual**\n\nHaz la cama y despeja superficies. Un entorno libre de desorden reduce los niveles de cortisol y el estrés mental.")
with col_r3:
    st.info("**🍎 Hidratación**\n\nBebe al menos 2 litros de agua y prioriza la fruta fresca. Tu energía depende directamente de la calidad de tu hidratación.")
with col_r4:
    st.info("**🧼 Higiene y Salud**\n\nDucha diaria y cepillado tras cada comida. El autocuidado personal refuerza la autoestima y la disciplina diaria.")

# ==========================================
# 9. PANEL DE ADMINISTRACIÓN (SOLO PADRES)
# ==========================================
if es_padre:
    st.divider()
    with st.expander("⚙️ CONFIGURACIÓN AVANZADA (MODO ADMINISTRADOR)"):
        st.subheader("🛠️ Gestión de la Base de Datos")
        st.write("Datos maestros actuales en la nube:")
        st.dataframe(st.session_state.df)

        st.divider()
        st.subheader("➕ Añadir Nueva Tarea al Sistema")
        ca1, ca2, ca3, ca4 = st.columns(4)
        nombre_t = ca1.text_input("Nombre de la Tarea")
        freq_t = ca2.selectbox("Frecuencia", ["Persistente", "Puntual"], help="Las persistentes se reinician, las puntuales se borran.")
        tipo_t = ca3.selectbox("Tipo de Tarea", ["Simple", "Contador", "Multi-Franja"])
        para_t = ca4.selectbox("Dirigido a", ["Hijos", "Padres", "Todos"])
        
        if st.button("🚀 Registrar Tarea en Google Sheets"):
            if nombre_t:
                nuevo_id = int(st.session_state.df['ID'].max() + 1)
                nueva_entrada = pd.DataFrame([{
                    'ID': nuevo_id, 'Tarea': nombre_t, 'Frecuencia': freq_t, 
                    'Tipo': tipo_t, 'Para': para_t, 'Responsable': 'Sin asignar', 
                    'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1
                }])
                sincronizar_nube(pd.concat([st.session_state.df, nueva_entrada], ignore_index=True))
                st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste de Unidades (Lavadoras, Comidas, etc.)")
        df_unidades = st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])]
        for i, fila_u in df_unidades.iterrows():
            ua, ub, uc = st.columns([3, 1, 1])
            ua.write(f"**{fila_u['Tarea']}**: {int(fila_u['Cantidad'])} unidades restantes")
            if ub.button("➕", key=f"add_unit_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                sincronizar_nube(st.session_state.df); st.rerun()
            if uc.button("➖", key=f"rem_unit_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    sincronizar_nube(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Reinicio de Ciclo Diario")
        if st.button("💾 FINALIZAR DÍA Y RESETEAR PANEL"):
            # Regla del 08/02/2026:
            # 1. Se eliminan las tareas marcadas como 'Puntual'
            df_final = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            # 2. Se limpian responsables y estados de las persistentes
            df_final['Responsable'] = 'Sin asignar'
            df_final['Estado'] = 'Pendiente'
            df_final['Franja'] = '-'
            # 3. Guardado final
            sincronizar_nube(df_final)
            st.success("Día reiniciado correctamente. Tareas puntuales eliminadas.")
            st.rerun()

# FIN DEL CÓDIGO
