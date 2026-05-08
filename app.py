import streamlit as st

st.set_page_config(
    page_title="Escuela Inteligente — Recolector de Documentos",
    page_icon="🏫",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/inicio.py", title="Inicio", icon="🏠"),
    st.Page("pages/herramienta.py", title="Recolector de Documentos", icon="📄"),
])
pg.run()
