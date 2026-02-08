import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Conexión usando el Secret
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Al llamar a read() sin especificar worksheet, 
    # Streamlit cargará la primera pestaña que encuentre (tu nueva pestaña 'Datos')
    return conn.read(ttl=0)

def guardar_datos(df_nuevo):
    # Aquí sí especificamos el nuevo nombre limpio
    conn.update(worksheet="Datos", data=df_nuevo)

# --- PRUEBA ---
try:
    df = cargar_datos()
    st.success("🚀 ¡CONECTADO! GESTI Hogar PRO está en línea.")
    st.dataframe(df)
except Exception as e:
    st.error(f"Error 400 resuelto, pero surgió esto: {e}")
