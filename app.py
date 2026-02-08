import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="GESTI Hogar PRO 6.0", page_icon="🏠", layout="wide")

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    try:
        conn.update(data=df_nuevo)
        st.session_state.df = df_nuevo
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")

if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

# --- 3. USUARIO ---
st.sidebar.title("👤 Panel de Acceso")
usuarios = ["Papá", "Mamá", "Jesús", "Cris", "María"]
user_name = st.sidebar.selectbox("Selecciona tu usuario:", usuarios)
perfil = "Padre" if user_name in ["Papá", "Mamá"] else "Hijo"

st.title("🏠 GESTI Hogar PRO 6.0 🚀")

# --- 4. LÓGICA DE DATOS ---
df = st.session_state.df
filtro_grupo = ['Padres', 'Todos'] if perfil == "Padre" else ['Hijos', 'Todos']
tareas_grupo = df[df['Para'].isin(filtro_grupo)]
pendientes_grupo = tareas_grupo[tareas_grupo['Estado'] == 'Pendiente']
mis_tareas_all = df[df['Responsable'] == user_name]
mis_pendientes = mis_tareas_all[mis_tareas_all['Estado'] == 'Pendiente']
mis_hechas = mis_tareas_all[mis_tareas_all['Estado'] == 'Hecho']

# --- 5. SECCIÓN: TAREAS LIBRES (CON VENTANA DE AVISO) ---
libres = df[(df['Responsable'] == 'Sin asignar') & (df['Para'].isin(filtro_grupo))]
num_simples = len(libres[~libres['Tipo'].isin(['Contador', 'Multi-Franja'])])
num_unidades = int(libres[libres['Tipo'].isin(['Contador', 'Multi-Franja'])]['Cantidad'].sum()) if not libres.empty else 0
total_p = num_simples + num_unidades

st.header(f"📌 Tareas Libres ({total_p} pendientes)")

if total_p > 0:
    for i, row in libres.iterrows():
        if row['Tipo'] in ['Contador', 'Multi-Franja'] and row['Cantidad'] <= 0:
            continue
            
        col_info, col_btn = st.columns([1.5, 2])
        label = f"**{row['Tarea']}**"
        if row['Tipo'] in ['Contador', 'Multi-Franja']:
            label += f" *(Quedan: {int(row['Cantidad'])} unidades)*"
        col_info.write(label)
        
        f1, f2, f3, f4 = col_btn.columns(4)
        for f_nombre, f_col in [("Mañana", f1), ("Mediodía", f2), ("Tarde", f3), ("Noche", f4)]:
            if f_col.button(f_nombre, key=f"btn_{f_nombre}_{i}"):
                # 🔔 AVISO INMEDIATO DE REACCIÓN
                st.toast(f"⏳ Procesando asignación de '{row['Tarea']}' para {f_nombre}...", icon="⚡")
                
                with st.spinner("Sincronizando con la nube..."):
                    df_temp = st.session_state.df.copy()
                    
                    if row['Tipo'] in ['Contador', 'Multi-Franja']:
                        df_temp.at[i, 'Cantidad'] = int(row['Cantidad']) - 1
                        if row['Tipo'] == 'Multi-Franja' and df_temp.at[i, 'Cantidad'] == 0:
                            df_temp.at[i, 'Responsable'] = 'Ocupado'
                        
                        nueva_id = int(df_temp['ID'].max() + 1)
                        nueva_fila = pd.DataFrame([{
                            'ID': nueva_id, 'Tarea': row['Tarea'], 'Frecuencia': 'Puntual',
                            'Tipo': 'Simple', 'Para': row['Para'], 'Responsable': user_name,
                            'Estado': 'Pendiente', 'Franja': f_nombre, 'Cantidad': 1
                        }])
                        df_temp = pd.concat([df_temp, nueva_fila], ignore_index=True)
                    else:
                        df_temp.at[i, 'Responsable'] = user_name
                        df_temp.at[i, 'Franja'] = f_nombre
                        df_temp.at[i, 'Estado'] = 'Pendiente'
                    
                    guardar_datos(df_temp)
                    st.toast(f"✅ ¡{row['Tarea']} asignada correctamente!", icon="🎉")
                    time.sleep(1) # Pequeña pausa para que veas el mensaje
                    st.rerun()
else:
    st.info("✨ Todo limpio por ahora.")

# --- 6. MI PANEL PERSONAL ---
st.divider()
st.header(f"📋 Mis Tareas ({len(mis_pendientes)})")
if not mis_pendientes.empty:
    for i, row in mis_pendientes.iterrows():
        c_p1, c_p2 = st.columns([4, 1])
        if c_p1.button(f"✅ Finalizar: {row['Tarea']} ({row['Franja']})", key=f"done_{i}"):
            st.session_state.df.at[i, 'Estado'] = 'Hecho'
            guardar_datos(st.session_state.df)
            st.rerun()
        if c_p2.button("🔓", key=f"undo_asig_{i}"):
            if row['Frecuencia'] == 'Puntual':
                st.session_state.df = st.session_state.df.drop(i)
            else:
                st.session_state.df.at[i, 'Responsable'], st.session_state.df.at[i, 'Franja'] = 'Sin asignar', '-'
            guardar_datos(st.session_state.df)
            st.rerun()

# --- 7. VISTA GENERAL ---
st.divider()
st.subheader("🏠 Resumen General")
st.dataframe(df[['Tarea', 'Responsable', 'Franja', 'Estado', 'Cantidad']], use_container_width=True, hide_index=True)

# --- 8. RUTINAS ---
st.divider()
st.subheader("✨ Rutinas")
r1, r2, r3, r4 = st.columns(4)
with r1: st.info("**🌬️ Habitación**\n\nVentila 10-15 min. Aire limpio, mejor descanso.")
with r2: st.info("**🧺 Orden**\n\nHaz la cama y recoge ropa. Mente despejada.")
with r3: st.info("**🍎 Hidratación**\n\nAgua y fruta. Cuida tu energía.")
with r4: st.info("**🧼 Higiene**\n\nDucha y dientes. Autocuidado diario.")

# --- 9. ADMIN (SÓLO PADRES) ---
if perfil == "Padre":
    st.divider()
    with st.expander("⚙️ PANEL DE CONTROL"):
        st.subheader("➕ Añadir Tarea")
        ca1, ca2, ca3, ca4 = st.columns(4)
        nt = ca1.text_input("Tarea")
        nf = ca2.selectbox("Frecuencia", ["Persistente", "Puntual"])
        ntp = ca3.selectbox("Tipo", ["Simple", "Contador", "Multi-Franja"])
        np = ca4.selectbox("Para", ["Hijos", "Padres", "Todos"])
        if st.button("🚀 Registrar"):
            nid = int(st.session_state.df['ID'].max() + 1)
            nueva = pd.DataFrame([{'ID': nid, 'Tarea': nt, 'Frecuencia': nf, 'Tipo': ntp, 'Para': np, 'Responsable': 'Sin asignar', 'Estado': 'Pendiente', 'Franja': '-', 'Cantidad': 1}])
            guardar_datos(pd.concat([st.session_state.df, nueva], ignore_index=True))
            st.rerun()

        st.subheader("🔢 Ajuste Contadores")
        for i, row in st.session_state.df[st.session_state.df['Tipo'].isin(['Contador', 'Multi-Franja'])].iterrows():
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{row['Tarea']}**: {int(row['Cantidad'])} unidades")
            if col_b.button("➕", key=f"inc_{i}"):
                st.session_state.df.at[i, 'Cantidad'] += 1
                guardar_datos(st.session_state.df); st.rerun()
            if col_c.button("➖", key=f"dec_{i}"):
                st.session_state.df.at[i, 'Cantidad'] -= 1
                guardar_datos(st.session_state.df); st.rerun()

        st.divider()
        if st.button("💾 REINICIAR DÍA (Regla 08/02)"):
            df_next = st.session_state.df[st.session_state.df['Frecuencia'] != 'Puntual'].copy()
            df_next['Responsable'], df_next['Estado'], df_next['Franja'] = 'Sin asignar', 'Pendiente', '-'
            guardar_datos(df_next); st.rerun()
