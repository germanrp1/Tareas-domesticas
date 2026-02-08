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
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

# Inicialización
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- USUARIO Y PERFIL ---
st.sidebar.title("👤 Acceso Familiar")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("¿Quién eres?", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 5.3 (Full) 🚀")

# --- LÓGICA DE DATOS INICIAL ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']

# Tareas grupo
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_hacer_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']

# Tareas personales
mis_tareas = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas[mis_tareas['Estado'] == 'Pendiente']
mis_hechas = mis_tareas[mis_tareas['Estado'] == 'Hecho']

# --- MENSAJES DE ENHORABUENA ---
# 1. Mensaje de Equipo (Si el grupo ha terminado todo)
if not tareas_grupo.empty and pendientes_hacer_grupo.empty:
    st.balloons()
    st.success("🌟 **ENHORABUENA, todas las tareas realizadas, ¡BUEN TRABAJO EQUIPO!**")
# 2. Mensaje Individual (Si tú has terminado lo tuyo)
elif not mis_tareas.empty and mis_pendientes.empty:
    st.balloons()
    st.success(f"👏 **ENHORABUENA {user_name.upper()}, todas tus tareas han sido realizadas, ¡BUEN TRABAJO {user_name}!**")

# --- FUNCIÓN DE ASIGNACIÓN (REFORZADA) ---
def ejecutar_asignacion(idx, franja):
    df_actual = st.session_state.df.copy()
    row = df_actual.loc[idx]
    
    # Caso para Contadores o Multi-Franja
    if row['Tipo'] in ['Contador', 'Multi-Franja']:
        cant = int(row['Cantidad'])
        if cant > 0:
            # Restamos a la tarea base
            df_actual.at[idx, 'Cantidad'] = cant - 1
            
            # Si es multi-franja y se agota, marcamos como ocupada para quitar de la lista
            if row['Tipo'] == 'Multi-Franja' and df_actual.at[idx, 'Cantidad'] == 0:
                df_actual.at[idx, 'Responsable'] = 'Ocupado'
            
            # Creamos la tarea individual
            nueva_id = int(df_actual['ID'].max() + 1)
            nueva_fila = pd.DataFrame([{
                'ID': nueva_id,
                'Tarea': row['Tarea'],
                'Frecuencia': 'Puntual',
                'Tipo': 'Simple',
                'Para': row['Para'],
                'Responsable': user_name,
                'Estado': 'Pendiente',
                'Franja': franja,
                'Cantidad': 1
            }])
            df_actual = pd.concat([df_actual, nueva_fila], ignore_index=True)
        else:
            st.warning("No quedan unidades/turnos disponibles.")
            return
    else:
        # Caso Simple
        df_actual.at[idx, 'Responsable'] = user_name
        df_actual.at[idx, 'Franja'] = franja
        df_actual.at[idx, 'Estado'] = 'Pendiente'

    guardar_datos(df_actual)
    st.rerun()

# --- 1. TAREAS LIBRES ---
libres_grupo = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
# Cálculo total turnos: Simples + Suma de cantidades en Contador/Multi
total_libres = len(libres_grupo[~libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])])
total_libres += int(libres_grupo[libres_grupo['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum())

st.header(f"📌 Tareas Libres ({total_libres} tareas pendientes de asignar para tu grupo)")

if total_libres > 0:
    for i, row in libres_grupo.iterrows():
        # Saltamos las que son contadores pero ya están a cero
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_t, col_b = st.columns([1, 2])
        label = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            label += f" (Quedan: {int(row['Cantidad'])} turnos)"
        
        col_t.write(label)
        f_cols = col_b.columns(4)
        franjas = ["Mañana", "Mediodía", "Tarde", "Tarde/Noche"]
        for idx_f, f_name in enumerate(franjas):
            if f_cols[idx_f].button(f_name, key=f"btn_{f_name}_{i}"):
                ejecutar_asignacion(i, f_name)
else:
    st.info("No hay tareas libres para tu grupo.")

# --- 2. MI PANEL PERSONAL ---
st.header(f"📋 Mis Tareas ({len(mis_pendientes)} pendientes de hacer)")
if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c1, c2 = st.columns([4, 1])
        if c1.button(f"✅ Hecho: {row['Tarea']} ({row['Franja']})", key=f"do_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df); st.rerun()
        if c2.button("🔓", key=f"rel_{i}", help="Liberar tarea"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df); st.rerun()

# Deshacer hechas
if not mis_hechas.empty:
    with st.expander("Ver mis tareas finalizadas hoy (Deshacer)"):
        for i, row in mis_hechas.iterrows():
            if st.button(f"🔄 Volver a pendiente: {row['Tarea']}", key=f"un_{i}"):
                st.session_state.df.at[i, 'Estado'] = 'Pendiente'
                guardar_datos(st.session_state.df); st.rerun()

# --- 3. VISTA GENERAL DE LA CASA ---
st.divider()
st.subheader("🏠 Vista General de la Casa (Estado actual)")
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True)

# --- 4. RUTINAS DETALLADAS ---
st.divider()
st.subheader("✨ Consejos de Rutina para un día genial")
rt1, rt2, rt3, rt4 = st.columns(4)
with rt1: st.info("**🌬️ Habitación**\n\nVentila tu cuarto al menos 10 min. Deja que entre aire fresco y luz natural.")
with rt2: st.info("**🧺 Orden**\n\nRecoge la ropa del suelo, haz la cama y mantén tu zona de estudio despejada.")
with rt3: st.info("**🍎 Alimentación**\n\nBebe mucha agua, come fruta y respeta los horarios de las comidas.")
with rt4: st.info("**🧼 Higiene**\n\nDucha diaria, cepillado de dientes tras cada comida y ropa limpia.")

# --- 5. ADMINISTRACIÓN (SÓLO PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE ADMINISTRACIÓN Y HISTÓRICO"):
        st.subheader("📜 Lista Completa (Histórico Actual)")
        st.dataframe(st.session_state.df)

        st.subheader("➕ Añadir Nueva Tarea")
        cad1, cad2, cad3, cad4 = st.columns(4)
        nt = cad1.text_input("Nombre Tarea")
        nf = cad2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = cad3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        np = cad4.selectbox("Para", ["Hijos", "Padres", "Todos"])
        if st.button("Registrar Tarea"):
            if nt:
                new_id = int(st.session_state.df['ID'].max() + 1)
                new_row = pd.DataFrame([{
                    'ID': new_id, 'Tarea': nt, 'Frecuencia': nf, 'Tipo': ntp, 
                    'Para': np, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 
                    'Franja': '-', 'Cantidad': 1
                }])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔢 Ajuste Rápido de Contadores (Lavadoras, etc.)")
        for i, row in st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])].iterrows():
            c_a, c_b, c_c = st.columns([2, 1, 1])
            c_a.write(f"**{row['Tarea']}** (Actual: {int(row['Cantidad'])})")
            if c_b.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if c_c.button("➖", key=f"dec_{i}"):
                if st.session_state.df.at[i, 'Cantidad'] > 0:
                    st.session_state.df.at[i, 'Cantidad'] -= 1
                    guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        st.subheader("🔄 Gestión de Reseteo")
        r_col1, r_col2 = st.columns(2)
        if r_col1.button("🔌 Reseteo de PRUEBA (Sin guardar)"):
            st.session_state.df = cargar_datos(); st.rerun()
        if r_col2.button("💾 REINICIO PARA PRÓXIMO DÍA (Guardar)"):
            # Mantenemos las persistentes y limpiamos estados
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'] = 'Sin asignar'
            df_next['Estado'] = 'Pendiente'
            df_next['Franja'] = '-'
            guardar_datos(df_next); st.success("¡Día reiniciado!"); st.rerun()
