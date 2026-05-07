import streamlit as st
import os
import io
from pathlib import Path
import zipfile
from urllib.parse import urlparse
import pandas as pd

from scraper import ScraperEstandar, OUTPUT_DIR

st.set_page_config(page_title="Scraper Web de PDFs - Escuela Inteligente", layout="wide", page_icon="📝")

# ── CABECERA ─────────────────────────────────────────────────────────────────
st.title("📝 Scraper de Documentos y PDFs")
st.markdown("Extrae documentos de URLs directas, crawling de sitios institucionales o a través de APIs de investigación.")

tab_direct, tab_crawl, tab_api = st.tabs(["📄 PDFs Directos", "🕸️ Crawling Web", "🤖 APIs Educativas"])

direct_pdfs = []
crawl_sources = []
api_sources = []

# ── TAB: PDFS DIRECTOS ───────────────────────────────────────────────────────
with tab_direct:
    col_header, col_guide = st.columns([5, 1])
    with col_header:
        st.header("Descarga Directa de PDFs")
    with col_guide:
        st.write("")
        with st.popover("ℹ️ Guía", use_container_width=True):
            st.markdown("### 📄 PDFs Directos — Guía de uso")
            st.markdown("""
**¿Cuándo usarlo?**
Cuando ya tienes los enlaces exactos a los archivos PDF que quieres descargar.

**Pasos:**
1. Pega las URLs de los PDFs en el cuadro de texto, **una por línea**.
2. Asigna una **categoría** (carpeta de destino) para organizar los archivos.
3. Elige el modo de extracción con el selector al final de la página.

**Ejemplo de URL válida:**
```
https://universidad.edu.co/doc/informe2024.pdf
https://mineduc.gov.co/reglamento.pdf
```

**Modos de descarga:**
- **Solo enlaces** → Rápido, exporta un CSV con las URLs.
- **Descargar + ZIP** → Descarga los archivos al servidor y los empaqueta.
            """)
    st.write("Ingresa los enlaces directos a descargar (un PDF por línea):")
    urls_input = st.text_area("URLs de PDFs", placeholder="https://ejemplo.com/doc1.pdf\nhttps://ejemplo.com/doc2.pdf")
    category_direct = st.text_input("Categoría para PDFs directos", value="manuales_directos")
    if urls_input:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        for idx, url in enumerate(urls):
            direct_pdfs.append({"url": url, "name": f"doc_{idx}", "category": category_direct})

# ── TAB: CRAWLING ────────────────────────────────────────────────────────────
with tab_crawl:
    col_header, col_guide = st.columns([5, 1])
    with col_header:
        st.header("Rastreo Web (Crawling)")
    with col_guide:
        st.write("")
        with st.popover("ℹ️ Guía", use_container_width=True):
            st.markdown("### 🕸️ Crawling Web — Guía de uso")
            st.markdown("""
**¿Cuándo usarlo?**
Cuando quieres explorar automáticamente un sitio web institucional y recolectar todos los PDFs que encuentre, sin tener que copiar cada enlace manualmente.

**Pasos:**
1. Activa la casilla **"Habilitar Crawling"**.
2. Escribe el **nombre de la fuente** (para identificarla en resultados).
3. Ingresa la **URL base** del dominio (ej. `https://universidad.edu.co`).
4. Agrega las **URLs de inicio**: páginas desde donde el bot empezará a buscar.
5. Define **palabras clave** en los links para filtrar solo los relevantes (ej. `pdf, descargar, informe`).
6. Asigna una **categoría** y elige el modo de extracción al final.

**Cómo funciona el bot:**
El crawler visita cada URL de inicio, encuentra todos los enlaces de la página, filtra los que contengan tus palabras clave o terminen en `.pdf`, y los recopila. Luego repite el proceso en las páginas encontradas (hasta cierta profundidad).

**Consejo:** Usa palabras clave específicas para evitar recopilar archivos irrelevantes.
            """)
    st.write("Agrega una web institucional para extraer PDFs iterativamente.")
    crawl_enabled = st.checkbox("Habilitar Crawling", value=False)

    if crawl_enabled:
        crawl_site_name = st.text_input("Nombre de la Fuente", value="Universidad X")
        crawl_base_url = st.text_input("URL Base (dominio principal)", value="https://ejemplo.edu.co")
        crawl_start_urls = st.text_area("URLs de inicio (una por línea)", value="https://ejemplo.edu.co/publicaciones")
        crawl_keywords = st.text_input("Palabras clave en los links (separadas por coma)", value="pdf, descargar, informe")
        crawl_category = st.text_input("Categoría para Crawling", value="documentos_crawling")

        starts = [url.strip() for url in crawl_start_urls.split('\n') if url.strip()]
        kws = [kw.strip() for kw in crawl_keywords.split(',') if kw.strip()]

        crawl_sources.append({
            "name": crawl_site_name,
            "base_url": crawl_base_url,
            "start_urls": starts,
            "category": crawl_category,
            "link_keywords": kws,
            "verify_ssl": True
        })

# ── TAB: APIS ────────────────────────────────────────────────────────────────
with tab_api:
    col_header, col_guide = st.columns([5, 1])
    with col_header:
        st.header("Búsqueda en APIs")
    with col_guide:
        st.write("")
        with st.popover("ℹ️ Guía", use_container_width=True):
            st.markdown("### 🤖 APIs Educativas — Guía de uso")
            st.markdown("""
**¿Cuándo usarlo?**
Cuando quieres buscar artículos académicos o documentos de investigación usando términos de búsqueda, sin conocer las URLs de antemano.

**APIs disponibles:**

| API | Especialidad |
|-----|-------------|
| **OpenAlex** | Artículos académicos de acceso abierto (recomendada) |
| **ERIC** | Investigación en educación (EE.UU.) |
| **Zenodo** | Repositorio multidisciplinar de ciencia abierta |
| **Semantic Scholar** | Papers de IA, ciencias y más |
| **CORE** | Millones de artículos en acceso abierto |
| **Custom** | Tu propia API con soporte para respuestas JSON |

**Pasos:**
1. Activa **"Habilitar Búsquedas por API"**.
2. Selecciona la **API** de tu preferencia.
3. Escribe tus **consultas de búsqueda**, una por línea (en español o inglés).
4. Define el **máximo de documentos** por consulta.
5. Asigna una **categoría** y elige el modo de extracción al final.

**Ejemplo de consultas:**
```
inteligencia artificial en educación
aprendizaje basado en proyectos Colombia
competencias digitales docentes
```

**API personalizada:** Si usas *Custom*, el bot enviará los términos a tu URL y extraerá cualquier enlace que termine en `.pdf` de la respuesta JSON.
            """)
    st.write("Utiliza repositorios como OpenAlex, ERIC o Zenodo para descargar artículos.")
    api_enabled = st.checkbox("Habilitar Búsquedas por API", value=False)

    if api_enabled:
        api_type = st.selectbox("Selecciona la API", ["core", "openalex", "eric", "zenodo", "semantic_scholar", "custom"], index=1)

        custom_api_url = ""
        if api_type == "custom":
            custom_api_url = st.text_input("URL de API personalizada", placeholder="https://api.mipropia-biblioteca.com/search")
            st.caption("El bot enviará los términos de búsqueda a la API y extraerá cualquier URL que finalice en '.pdf' de la respuesta.")

        api_queries = st.text_area("Consultas (una por línea)", value="educacion virtual colombia\ninteligencia artificial pedagogia")
        api_max_docs = st.number_input("Máximo de documentos por query", min_value=1, max_value=500, value=15)
        api_category = st.text_input("Categoría para APIs", value="papers_investigacion")

        queries = [q.strip() for q in api_queries.split('\n') if q.strip()]

        api_sources.append({
            "name": f"Búsqueda_APIs_{api_type}",
            "type": api_type,
            "category": api_category,
            "queries": queries,
            "custom_url": custom_api_url,
            "max_per_query": api_max_docs
        })

# ── MODO DE EXTRACCIÓN + BOTÓN ────────────────────────────────────────────────
st.divider()

col_modo, col_accion = st.columns([3, 1])

with col_modo:
    modo = st.radio(
        "¿Cómo quieres obtener los resultados?",
        options=[
            "🔗 Solo recopilar enlaces (exportar CSV)",
            "📦 Descargar archivos físicamente (exportar CSV + ZIP)",
        ],
        captions=[
            "Rápido — recorre las fuentes y guarda las URLs sin bajar ningún archivo.",
            "Completo — descarga cada PDF al servidor y los empaqueta en un ZIP descargable.",
        ],
    )

with col_accion:
    st.write("")
    st.write("")
    btn_run = st.button("🚀 Iniciar Extracción", type="primary", use_container_width=True)

# ── LÓGICA DE EXTRACCIÓN ─────────────────────────────────────────────────────
if btn_run:
    if not direct_pdfs and not crawl_sources and not api_sources:
        st.warning("Debe configurar al menos un método de scraping.")
    else:
        descargar_fisico = modo.startswith("📦")
        with st.spinner("Procesando... Por favor espere."):
            scraper = ScraperEstandar()
            results_queue = scraper.run(
                direct_pdfs=direct_pdfs,
                crawl_sources=crawl_sources,
                api_sources=api_sources,
                skip_download=not descargar_fisico,
            )
            st.session_state["scraping_results"] = results_queue
            st.session_state["descargado"] = descargar_fisico

# ── RESULTADOS ───────────────────────────────────────────────────────────────
if st.session_state.get("scraping_results"):
    results_queue = st.session_state["scraping_results"]
    descargado = st.session_state.get("descargado", False)

    st.success(f"✅ ¡Se han encontrado {len(results_queue)} archivos!")
    st.subheader("Resultados de la Búsqueda")

    col_filter, col_csv, col_zip_dl = st.columns([3, 1, 1])

    categorias_unicas = sorted({t[1] for t in results_queue})
    with col_filter:
        filtro_cat = st.multiselect("🔍 Filtrar por Categoría:", options=categorias_unicas, default=categorias_unicas)

    filtered_results = [item for item in results_queue if item[1] in filtro_cat]

    with col_csv:
        df_csv = pd.DataFrame([{"Categoría": c, "Nombre": n, "URL": u} for u, c, n, _ in filtered_results])
        st.download_button(
            label="💾 Exportar CSV",
            data=df_csv.to_csv(index=False).encode("utf-8"),
            file_name="resultados_links.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_zip_dl:
        if descargado:
            # ZIP construido en memoria — no escribe archivos temporales al disco,
            # compatible con Streamlit Cloud y cualquier entorno de despliegue
            zip_buffer = io.BytesIO()
            files_added = 0
            if OUTPUT_DIR.exists():
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(OUTPUT_DIR):
                        for file in files:
                            fpath = Path(root) / file
                            if fpath.parent.name in filtro_cat:
                                zipf.write(fpath, os.path.relpath(fpath, OUTPUT_DIR))
                                files_added += 1
            zip_buffer.seek(0)

            if files_added:
                st.download_button(
                    label="📦 Descargar ZIP",
                    data=zip_buffer,
                    file_name="archivos_procesados.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.button("📦 Descargar ZIP", disabled=True, help="No hay archivos físicos para el filtro actual.", use_container_width=True)
        else:
            st.button("📦 Descargar ZIP", disabled=True, help="Selecciona '📦 Descargar archivos' antes de iniciar.", use_container_width=True)

    st.write("---")

    tab_table, tab_grid = st.tabs(["📋 Vista de Tabla", "🗂️ Vista de Cuadrícula"])

    with tab_table:
        display_data = [
            {
                "Nombre del Archivo": name,
                "Categoría": category,
                "Dominio Origen": urlparse(url).netloc,
                "Enlace Directo": url,
            }
            for url, category, name, _ in filtered_results
        ]
        st.dataframe(display_data, use_container_width=True, column_config={
            "Enlace Directo": st.column_config.LinkColumn("Enlace Directo")
        })

    with tab_grid:
        categories: dict = {}
        for url, category, name, _ in filtered_results:
            categories.setdefault(category, []).append((url, name))

        for cat, items in categories.items():
            st.markdown(f"#### 📁 {cat}")
            cols = st.columns(3)
            for idx, (url, name) in enumerate(items):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(
                            "<p style='font-size:2rem; margin:0 0 0.25rem 0;'>📄</p>",
                            unsafe_allow_html=True,
                        )
                        display_name = name if len(name) <= 60 else name[:57] + "..."
                        st.markdown(f"**{display_name}**")
                        domain = urlparse(url).netloc
                        st.markdown(
                            f"<span style='background:#f0f2f6; padding:2px 8px; border-radius:99px;"
                            f" font-size:0.75rem; color:#555;'>🌐 {domain}</span>",
                            unsafe_allow_html=True,
                        )
                        st.write("")
                        st.link_button("Abrir documento →", url=url, use_container_width=True)
