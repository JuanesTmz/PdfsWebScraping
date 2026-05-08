import streamlit as st

# ── HÉROE ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:2.6rem; margin-bottom:0;'>🏫 Escuela Inteligente</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='font-size:1.2rem; color:#e6e6e6; margin-top:0.3rem;'>"
    "Recolector automático de documentos educativos"
    "</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── QUÉ ES ───────────────────────────────────────────────────────────────────
col_texto, col_imagen = st.columns([3, 2], gap="large")

with col_texto:
    st.markdown("## ¿De qué se trata esto?")
    st.markdown("""
Imagina que quieres construir un asistente inteligente para tu colegio o universidad —
uno que pueda responder preguntas sobre pedagogía, políticas educativas, investigaciones o
cualquier tema académico.

Para que ese asistente sea útil, necesita haber **"leído" miles de documentos**: artículos de
investigación, guías del Ministerio de Educación, publicaciones de universidades, informes
de organismos internacionales...

**El problema:** buscar y descargar esos documentos uno por uno tomaría semanas.

**La solución:** esta herramienta lo hace sola. Tú le dices qué temas te interesan, y ella
sale a buscar los documentos en internet, los organiza y te los entrega listos para usar.
    """)

with col_imagen:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(
        "**En pocas palabras:**\n\n"
        "Es como tener un asistente de biblioteca que recorre el internet entero, "
        "encuentra todos los libros y artículos sobre los temas que necesitas, "
        "y te los trae organizados en carpetas.",
        icon="💡",
    )
    st.success(
        "**¿Para quién es?**\n\n"
        "Investigadores, docentes y equipos de innovación educativa que quieren "
        "construir bases de conocimiento sin perder tiempo en búsquedas manuales.",
        icon="🎯",
    )

st.divider()

# ── CÓMO FUNCIONA ────────────────────────────────────────────────────────────
st.markdown("## ¿Cómo funciona? — 3 pasos simples")
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container(border=True):
        st.markdown("### 1️⃣ Define qué buscar")
        st.markdown(
            "Escribe los temas que te interesan, por ejemplo: "
            "*\"inteligencia artificial en educación\"* o "
            "*\"competencias digitales docentes\"*. "
            "También puedes apuntar la herramienta a sitios web institucionales específicos."
        )

with col2:
    with st.container(border=True):
        st.markdown("### 2️⃣ Presiona el botón")
        st.markdown(
            "La herramienta sale a buscar automáticamente en repositorios académicos "
            "como OpenAlex, Zenodo, ERIC y Semantic Scholar — "
            "bases de datos con millones de artículos de acceso libre."
        )

with col3:
    with st.container(border=True):
        st.markdown("### 3️⃣ Descarga los resultados")
        st.markdown(
            "Obtén un archivo CSV con todos los enlaces encontrados, "
            "o descarga los PDFs directamente empaquetados en un ZIP, "
            "listos para alimentar tu sistema de inteligencia artificial."
        )

st.divider()

# ── FUENTES ──────────────────────────────────────────────────────────────────
st.markdown("## ¿De dónde saca los documentos?")
st.markdown("<br>", unsafe_allow_html=True)

fuentes = [
    ("🔬", "OpenAlex", "Más de 250 millones de artículos científicos de acceso abierto. La fuente más grande del mundo."),
    ("🎓", "ERIC", "Especializada en investigación educativa. Miles de estudios sobre pedagogía, currículo y aprendizaje."),
    ("🌐", "Zenodo", "Repositorio de la Unión Europea con publicaciones de ciencia abierta de todo el mundo."),
    ("🤖", "Semantic Scholar", "Enfocada en IA, ciencias de la computación y disciplinas STEM."),
    ("📚", "CORE", "Agrega millones de artículos de repositorios universitarios de todo el planeta."),
    ("🏛️", "Sitios web", "También puede rastrear portales institucionales como el Ministerio de Educación o universidades."),
]

cols = st.columns(3)
for idx, (icon, nombre, desc) in enumerate(fuentes):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"**{icon} {nombre}**")
            st.caption(desc)

st.divider()

# ── CTA ──────────────────────────────────────────────────────────────────────
st.markdown("## ¿Listo para empezar?")
st.markdown("Usa el menú de la izquierda o el botón de abajo para ir a la herramienta.")
st.markdown("<br>", unsafe_allow_html=True)

col_btn, col_space = st.columns([1, 3])
with col_btn:
    if st.button("Ir al Recolector →", type="primary", use_container_width=True):
        st.switch_page("pages/herramienta.py")
