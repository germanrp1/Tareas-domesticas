import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="GESTI Hogar PRO", page_icon="🏠")

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # ttl=0 para que los cambios en el Excel se vean al recargar la app
    # Cambia "Hoja 1" si en tu Drive la pestaña tiene otro nombre
    return conn.read(worksheet="Hoja 1", ttl=0)

def guardar_datos(df):
    conn.update(worksheet="Hoja 1", data=df)

# Carga de datos desde la nube
try:
    df = cargar_datos()
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()
