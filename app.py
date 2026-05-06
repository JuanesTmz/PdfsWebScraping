import streamlit as st
import os
import shutil
from pathlib import Path
import time
import zipfile
from urllib.parse import urlparse

# Importar la clase modificada de tu script original
from scraper import ScraperEstandar, OUTPUT_DIR

st.set_page_config(page_title="Scraper Web de PDFs - Escuela Inteligente", layout="wide", page_icon="📝")

st.title("📝 Scraper de Documentos y PDFs")
st.markdown("Extrae documentos de URLs directas, crawling de sitios institucionales o a través de APIs de investigación.")

# Pestañas de configuración
tab_direct, tab_crawl, tab_api = st.tabs(["📄 PDFs Directos", "🕸️ Crawling Web", "🤖 APIs Educativas"])

direct_pdfs = []
crawl_sources = []
api_sources = []

with tab_direct:
    st.header("Descarga Directa de PDFs")
    st.write("Ingresa los enlaces directos a descargar (un PDF por línea):")
    urls_input = st.text_area("URLs de PDFs", placeholder="https://ejemplo.com/doc1.pdf\nhttps://ejemplo.com/doc2.pdf")
    category_direct = st.text_input("Categoría para PDFs directos", value="manuales_directos")
    if urls_input:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        for idx, url in enumerate(urls):
            direct_pdfs.append({"url": url, "name": f"Direct_Doc_{idx}", "category": category_direct})

with tab_crawl:
    st.header("Rastreo Web (Crawling)")
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

with tab_api:
    st.header("Búsqueda en APIs")
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

st.divider()

col_btn, col_opt = st.columns([1, 2])
with col_opt:
    descargar_fisico = st.checkbox("⬇️ Descargar archivos físicamente al servidor para permitir su descarga en ZIP (puede demorar más)", value=False)

if st.button("🚀 Iniciar Extracción", type="primary"):
    if not direct_pdfs and not crawl_sources and not api_sources:
        st.warning("Debe configurar al menos un método de scraping.")
    else:
        with st.spinner('Procesando... Por favor espere.'):
            scraper = ScraperEstandar()
            # Si el usuario elige físico, skip_download=False; si no, True.
            results_queue = scraper.run(direct_pdfs=direct_pdfs, crawl_sources=crawl_sources, api_sources=api_sources, skip_download=not descargar_fisico)
            
            st.session_state['scraping_results'] = results_queue
            st.session_state['descargado'] = descargar_fisico

if 'scraping_results' in st.session_state and st.session_state['scraping_results']:
    results_queue = st.session_state['scraping_results']
    descargado = st.session_state.get('descargado', False)
    
    st.success(f"✅ ¡Se han encontrado {len(results_queue)} archivos!")
    st.subheader("Resultados de la Búsqueda")
    
    # --- BOTONES SUPERIORES Y FILTROS ---
    col_tools1, col_tools2, col_tools3 = st.columns([2, 1, 1])
    
    # Extraer categorías únicas para el filtro
    categorias_unicas = sorted(list(set([t[1] for t in results_queue])))
    with col_tools1:
        filtro_cat = st.multiselect("🔍 Filtrar por Categoría:", options=categorias_unicas, default=categorias_unicas)
    
    # Filtrar cola según categoría seleccionada
    filtered_results = [item for item in results_queue if item[1] in filtro_cat]
    
    with col_tools2:
        # Botón CSV siempre disponible
        import pandas as pd
        df_csv = pd.DataFrame([{ "Categoría": c, "Nombre": n, "URL": u } for u, c, n, _ in filtered_results])
        csv = df_csv.to_csv(index=False).encode('utf-8')
        st.download_button(label="💾 Descargar Enlaces (CSV)", data=csv, file_name="resultados_links.csv", mime="text/csv", use_container_width=True)

    with col_tools3:
        if descargado:
            # Comprimir resultados en ZIP para descarga
            downloaded_files = []
            if OUTPUT_DIR.exists():
                for root, _, files in os.walk(OUTPUT_DIR):
                    for file in files:
                        fpath = os.path.join(root, file)
                        # Validar si corresponde a categorías filtradas (aproximado por nombre de carpeta)
                        if Path(fpath).parent.name in filtro_cat:
                            downloaded_files.append(fpath)

            if downloaded_files:
                zip_path = "scraping_results.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for fpath in downloaded_files:
                        zipf.write(fpath, os.path.relpath(fpath, OUTPUT_DIR))
                
                with open(zip_path, "rb") as fp:
                    st.download_button(label="📦 Descargar Archivos (ZIP)", data=fp, file_name="archivos_procesados.zip", mime="application/zip", use_container_width=True)
            else:
                st.button("📦 Descargar Archivos (ZIP)", disabled=True, help="No hay archivos físicos descargados para el filtro actual.", use_container_width=True)
        else:
            st.button("📦 Descargar Archivos (ZIP)", disabled=True, help="Debes habilitar la descarga física antes de iniciar para usar esta opción.", use_container_width=True)
    
    st.write("---")

    # --- VISTAS ---
    # La vista principal ahora es "Vista de Tabla"
    tab_table, tab_grid = st.tabs(["📋 Vista de Tabla", "🗂️ Vista de Cuadrícula"])
    
    with tab_table:
        display_data = []
        for url, category, name, _ in filtered_results:
            display_data.append({
                "Categoría": category,
                "Nombre / Título": name,
                "Dominio Origen": urlparse(url).netloc,
                "Enlace Directo": url
            })
        st.dataframe(display_data, use_container_width=True, column_config={
            "Enlace Directo": st.column_config.LinkColumn("Enlace Directo")
        })

    with tab_grid:
        st.write("Explora los documentos de manera visual. Haz clic en 'Abrir Documento' para previsualizar o descargar desde su origen:")
        categories = {}
        for url, category, name, _ in filtered_results:
            if category not in categories:
                categories[category] = []
            categories[category].append((url, name))

        for cat, items in categories.items():
            st.markdown(f"#### 📁 {cat}")
            cols = st.columns(3)
            for idx, (url, name) in enumerate(items):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"#### 📄 {name[:40]}{'...' if len(name) > 40 else ''}")
                        st.caption(f"**Origen:** {urlparse(url).netloc}")
                        st.markdown(f"[**Abrir Documento 🔗**]({url})")
                        st.write("")
elif 'scraping_results' not in st.session_state:
    pass # Aún no se ha realizado ninguna búsqueda
