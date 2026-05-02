"""
scraper.py — Web scraper ético v2 para base de conocimiento de Escuela Inteligente
-----------------------------------------------------------------------------------
Mejoras v2:
  - Bug corregido: robots.txt fallido → asumir permiso correctamente
  - Soporte verify_ssl por fuente (sitios .gov.co con certificados problemáticos)
  - API de ERIC (IES) para búsqueda de documentos STEM sin scraping HTML
  - API de CORE.ac.uk para artículos académicos open access
  - API de Zenodo (CERN) para OER y publicaciones abiertas
  - URLs actualizadas y verificadas
  - Extracción de PDFs más amplia (también busca en texto de los enlaces)
  - 3 fases: PDFs directos → Crawling → APIs
"""

import time
import json
import random
import hashlib
import logging
import requests
import urllib.robotparser
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional

from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("knowledge_base")
LOGS_DIR   = Path("logs")
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

MIN_DELAY            = 3.0
MAX_DELAY            = 7.0
MAX_DOCS_PER_SOURCE  = 20
MAX_PAGES_PER_SOURCE = 15
MAX_PDF_SIZE_BYTES   = 50 * 1024 * 1024  # 50 MB

USER_AGENT = (
    "EscuelaInteligente-ResearchBot/2.0 "
    "(Proyecto educativo Medellín; contacto: info@escuelainteligente.edu.co)"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# FASE 1 — PDFs directos con URLs verificadas
# ─────────────────────────────────────────────────────────────
# NOTA MEN: mineducacion.gov.co devuelve 500 Server Error a bots.
# Descarga estos manualmente desde el navegador y colócalos en:
#   knowledge_base/contexto_educativo_nacional/
# URLs de referencia (funcionan en el navegador):
#   https://www.mineducacion.gov.co/1621/articles-340021_recurso_1.pdf  (Estándares)
#   https://www.mineducacion.gov.co/1759/articles-379822_recurso_1.pdf  (DBA Matemáticas)
#   https://www.mineducacion.gov.co/1759/articles-379381_recurso_1.pdf  (DBA Lenguaje)
#   https://www.mineducacion.gov.co/1759/articles-379494_recurso_1.pdf  (DBA Ciencias Nat.)
#   https://www.mineducacion.gov.co/1759/articles-379739_recurso_1.pdf  (DBA Ciencias Soc.)
# ─────────────────────────────────────────────────────────────
DIRECT_PDFS = [
    # ── UNESCO — PDFs del repositorio UNESDOC ────────────────
    # Formato correcto: descarga directa desde el repositorio
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000373755.pdf/PDF/pf0000373755_spa.pdf.multi",
        "name": "UNESCO - Recomendación sobre REA 2019",
        "category": "REA",
        "tags": ["UNESCO", "OER", "REA", "recomendación internacional"],
        "verify_ssl": True,
    },
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000370294.pdf/PDF/pf0000370294_spa.pdf.multi",
        "name": "UNESCO - Marco de Competencias Docentes en TIC",
        "category": "teoria_educativa",
        "tags": ["UNESCO", "TIC", "competencias docentes", "tecnología"],
        "verify_ssl": True,
    },
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000232022.pdf/PDF/pf0000232022_spa.pdf.multi",
        "name": "UNESCO - Replantear la educación",
        "category": "teoria_educativa",
        "tags": ["UNESCO", "educación", "futuro", "teoría educativa"],
        "verify_ssl": True,
    },
    # ── CEPAL ─────────────────────────────────────────────────
    {
        "url": "https://repositorio.cepal.org/bitstream/handle/11362/47620/1/S2100655_es.pdf",
        "name": "CEPAL - Educación digital en América Latina",
        "category": "teoria_educativa",
        "tags": ["CEPAL", "educación digital", "América Latina", "TIC"],
        "verify_ssl": True,
    },
    {
        "url": "https://repositorio.cepal.org/bitstream/handle/11362/45037/S2000554_es.pdf",
        "name": "CEPAL - Educación en tiempos de pandemia COVID-19",
        "category": "teoria_educativa",
        "tags": ["CEPAL", "educación", "pandemia", "América Latina"],
        "verify_ssl": True,
    },
    {
        "url": "https://repositorio.cepal.org/bitstream/handle/11362/48099/S2200803_es.pdf",
        "name": "CEPAL - Habilidades del siglo XXI en América Latina",
        "category": "teoria_educativa",
        "tags": ["CEPAL", "habilidades", "siglo XXI", "América Latina"],
        "verify_ssl": True,
    },
    {
        "url": "https://repositorio.cepal.org/bitstream/handle/11362/44395/S1801141_es.pdf",
        "name": "CEPAL - Agenda educativa digital 2030",
        "category": "teoria_educativa",
        "tags": ["CEPAL", "agenda digital", "educación", "2030"],
        "verify_ssl": True,
    },
    # ── CONPES 3975 — URL alternativa vía DNP ────────────────
    {
        "url": "https://colaboracion.dnp.gov.co/CDT/Conpes/Econ%C3%B3micos/3975.pdf",
        "name": "CONPES 3975 - Política Nacional de Inteligencia Artificial Colombia",
        "category": "uso_etico_IA",
        "tags": ["IA", "política pública", "Colombia", "CONPES", "DNP"],
        "verify_ssl": True,
    },
]


# ─────────────────────────────────────────────────────────────
# FASE 2 — Crawling de sitios web institucionales
# ─────────────────────────────────────────────────────────────
CRAWL_SOURCES = [
    {
        "name": "Colombia Aprende - Portal principal",
        "base_url": "https://colombiaaprende.edu.co",
        "start_urls": ["https://colombiaaprende.edu.co/"],
        "category": "REA",
        "tags": ["REA", "Colombia Aprende", "MEN", "recursos educativos"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        "link_keywords": ["recurso", "guia", "cartilla", "orientacion", "documento", "pdf"],
        "verify_ssl": True,
    },
    {
        "name": "Alcaldía de Medellín - Secretaría de Educación",
        "base_url": "https://www.medellin.gov.co",
        "start_urls": [
            "https://www.medellin.gov.co/es/secretaria-de-educacion/",
        ],
        "category": "geografia_educativa_medellin",
        "tags": ["Medellín", "Secretaría de Educación", "política educativa local"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        "link_keywords": ["educacion", "plan", "programa", "docente", "pdf", "descarg"],
        "verify_ssl": True,
    },
    {
        "name": "Parque Explora - Recursos educadores",
        "base_url": "https://www.parqueexplora.org",
        "start_urls": [
            "https://www.parqueexplora.org/educadores/",
        ],
        "category": "geografia_educativa_medellin",
        "tags": ["Parque Explora", "ciencias", "Medellín", "STEM", "recursos docentes"],
        "allowed_extensions": [".pdf", ".html"],
        "follow_links": True,
        "link_keywords": ["recurso", "guia", "taller", "docente", "pdf", "actividad", "descarg"],
        "verify_ssl": True,
    },
    {
        "name": "Ruta N Medellín",
        "base_url": "https://www.rutanmedellin.org",
        "start_urls": ["https://www.rutanmedellin.org/"],
        "category": "geografia_educativa_medellin",
        "tags": ["Ruta N", "innovación", "Medellín", "ciencia y tecnología"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        "link_keywords": ["publicacion", "informe", "reporte", "pdf", "descarg", "documento"],
        "verify_ssl": True,
    },
    {
        "name": "MinCiencias - Inteligencia Artificial",
        "base_url": "https://minciencias.gov.co",
        "start_urls": [
            "https://minciencias.gov.co/politica-de-inteligencia-artificial",
        ],
        "category": "uso_etico_IA",
        "tags": ["MinCiencias", "IA", "ciencia", "tecnología", "Colombia"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        "link_keywords": ["pdf", "documento", "politica", "inteligencia"],
        "verify_ssl": True,
    },
    {
        "name": "ICFES - Marcos de referencia y guías",
        "base_url": "https://www.icfes.gov.co",
        "start_urls": [
            "https://www.icfes.gov.co/web/guest/referentes-y-estructuras",
            "https://www.icfes.gov.co/web/guest/guias-de-orientacion",
            "https://www.icfes.gov.co/web/guest/informes-de-resultados",
        ],
        "category": "contexto_educativo_nacional",
        "tags": ["ICFES", "evaluación", "SABER", "competencias", "Colombia", "marcos de referencia"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        # keywords más amplias para capturar marcos y guías, no solo calendarios
        "link_keywords": ["marco", "referencia", "estructura", "guia", "orientacion",
                          "saber", "competencia", "cuadernillo", "informe", "pdf"],
        "verify_ssl": False,
    },
    {
        "name": "Computadores para Educar",
        "base_url": "https://www.computadoresparaeducar.gov.co",
        "start_urls": ["https://www.computadoresparaeducar.gov.co/"],
        "category": "pensamiento_computacional",
        "tags": ["TIC", "educación digital", "Colombia", "CPE"],
        "allowed_extensions": [".pdf"],
        "follow_links": True,
        "link_keywords": ["recurso", "documento", "pdf", "cartilla", "guia"],
        "verify_ssl": False,
    },
]


# ─────────────────────────────────────────────────────────────
# FASE 3 — APIs documentales (sin scraping HTML)
# ─────────────────────────────────────────────────────────────
API_SOURCES = [
    {
        "name": "ERIC API - STEM y Pensamiento Computacional",
        "type": "eric",
        "category": "REA",
        "tags": ["ERIC", "STEM", "investigación educativa", "open access"],
        "queries": [
            "STEM education Latin America",
            "computational thinking K-12",
            "mathematics education primary school",
            "critical thinking teaching strategies elementary",
            "artificial intelligence education ethics",
            "cybersecurity education students",
            "project based learning STEM",
        ],
        "max_per_query": 5,
    },
    {
        "name": "CORE API - Pedagogía y Didáctica",
        "type": "core",
        "category": "teoria_educativa",
        "tags": ["CORE", "open access", "pedagogía", "investigación académica"],
        "queries": [
            "pedagogía constructivista aprendizaje",
            "aprendizaje basado en proyectos educación",
            "educación STEM Colombia",
            "pensamiento crítico educación básica",
            "inteligencia artificial educación ética",
            "ciberseguridad educación jóvenes",
            "lectura crítica comprensión lectora",
            "mediación pedagógica tecnología digital",
        ],
        "max_per_query": 5,
    },
    {
        "name": "Zenodo - OER y Recursos Educativos",
        "type": "zenodo",
        "category": "REA",
        "tags": ["Zenodo", "OER", "CERN", "recursos educativos abiertos"],
        "queries": [
            "open educational resources STEM mathematics",
            "teaching materials computational thinking",
            "Colombia education curriculum",
            "digital literacy education",
        ],
        "max_per_query": 5,
    },
]


# ─────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────
class EthicalScraper:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        # ↓ FIX CLAVE: dominios donde robots.txt no cargó → asumir permiso total
        self._robots_allow_all: set[str] = set()
        self._visited_urls: set[str] = set()
        self.stats = {"downloaded": 0, "skipped": 0, "errors": 0}

    # ── Delay cortés ─────────────────────────────────────────
    def _wait(self, label: str = ""):
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        log.info(f"  [{label}] Esperando {delay:.1f}s...")
        time.sleep(delay)

    # ── robots.txt via requests (no urllib interno) ───────────
    def _load_robots(self, base_url: str, verify: bool = True):
        if base_url in self._robots_cache:
            return
        rp  = urllib.robotparser.RobotFileParser()
        url = urljoin(base_url, "/robots.txt")
        loaded = False
        try:
            r = self.session.get(url, timeout=10, verify=verify)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                loaded = True
                log.info(f"  robots.txt OK: {url}")
            else:
                log.info(f"  robots.txt {r.status_code} en {base_url} → permiso asumido")
        except Exception as e:
            log.warning(f"  robots.txt inalcanzable en {base_url} ({type(e).__name__}) → permiso asumido")

        if not loaded:
            self._robots_allow_all.add(base_url)

        self._robots_cache[base_url] = rp

    def _is_allowed(self, base_url: str, url: str, verify: bool = True) -> bool:
        self._load_robots(base_url, verify)
        if base_url in self._robots_allow_all:
            return True
        return self._robots_cache[base_url].can_fetch(USER_AGENT, url)

    # ── GET seguro ───────────────────────────────────────────
    def _get(self, url: str, stream: bool = False,
             verify: bool = True) -> Optional[requests.Response]:
        try:
            r = self.session.get(url, timeout=25, stream=stream, verify=verify)
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError:
            # Reintento sin verificación si hay error SSL
            try:
                log.warning(f"  SSL error en {url}, reintentando sin verificación...")
                r = self.session.get(url, timeout=25, stream=stream, verify=False)
                r.raise_for_status()
                return r
            except Exception as e2:
                log.error(f"  Error GET (2do intento) {url}: {e2}")
                self.stats["errors"] += 1
                return None
        except requests.RequestException as e:
            log.error(f"  Error GET {url}: {e}")
            self.stats["errors"] += 1
            return None

    # ── Descarga de PDF ──────────────────────────────────────
    def _download_pdf(self, url: str, category: str, tags: list,
                      source_name: str, verify: bool = True) -> Optional[Path]:
        if url in self._visited_urls:
            self.stats["skipped"] += 1
            return None
        self._visited_urls.add(url)

        # HEAD para verificar tipo y tamaño antes de descargar
        try:
            head = self.session.head(url, timeout=10,
                                     allow_redirects=True, verify=verify)
            ct = head.headers.get("Content-Type", "")
            cl = int(head.headers.get("Content-Length", 0))
            if cl > MAX_PDF_SIZE_BYTES:
                log.warning(f"  PDF demasiado grande ({cl/1e6:.1f} MB): {url}")
                self.stats["skipped"] += 1
                return None
            if ct and "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
                log.info(f"  No es PDF ({ct}): {url}")
                return None
        except Exception:
            pass

        r = self._get(url, stream=True, verify=verify)
        if not r:
            return None

        ct = r.headers.get("Content-Type", "")
        if ct and "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
            log.info(f"  No es PDF ({ct}): {url}")
            return None

        # Nombre de archivo
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        raw_name = urlparse(url).path.rstrip("/").split("/")[-1] or "documento"
        if not raw_name.lower().endswith(".pdf"):
            raw_name += ".pdf"
        filename = f"{url_hash}_{raw_name[:80]}"

        dest_dir = OUTPUT_DIR / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        filepath = dest_dir / filename

        if filepath.exists():
            log.info(f"  Ya existe: {filename}")
            self.stats["skipped"] += 1
            return filepath

        total = 0
        try:
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total += len(chunk)
                    if total > MAX_PDF_SIZE_BYTES:
                        filepath.unlink(missing_ok=True)
                        log.warning(f"  Descarga abortada (excede límite): {url}")
                        return None
        except Exception as e:
            log.error(f"  Error al escribir {filename}: {e}")
            filepath.unlink(missing_ok=True)
            return None

        if total < 1024:
            log.warning(f"  Archivo sospechosamente pequeño ({total} B): {url}")
            filepath.unlink(missing_ok=True)
            return None

        log.info(f"  ✓ {filename} ({total/1024:.0f} KB)")
        self._save_meta(filepath, url, source_name, category, tags)
        self.stats["downloaded"] += 1
        return filepath

    def _save_meta(self, path: Path, url: str, source: str,
                   category: str, tags: list):
        meta = {
            "file": path.name,
            "source_name": source,
            "url": url,
            "category": category,
            "tags": tags,
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(path.with_suffix(".meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # ── Extraer PDFs de HTML ─────────────────────────────────
    def _extract_pdf_links(self, html: str, page_url: str,
                           base_url: str, keywords: list) -> list[str]:
        soup  = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href   = urljoin(page_url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc != urlparse(base_url).netloc:
                continue
            text   = a.get_text(strip=True).lower()
            is_pdf = href.lower().endswith(".pdf")
            kw_hit = any(kw in href.lower() or kw in text for kw in keywords)
            if is_pdf or kw_hit:
                links.append(href)
        return list(dict.fromkeys(links))

    def _extract_page_links(self, html: str, page_url: str,
                            base_url: str, keywords: list) -> list[str]:
        soup  = BeautifulSoup(html, "html.parser")
        links = []
        skip  = (".pdf", ".jpg", ".png", ".zip", ".mp4", ".doc", ".xls")
        for a in soup.find_all("a", href=True):
            href   = urljoin(page_url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc != urlparse(base_url).netloc:
                continue
            if any(href.lower().endswith(e) for e in skip):
                continue
            text   = a.get_text(strip=True).lower()
            kw_hit = any(kw in href.lower() or kw in text for kw in keywords)
            if kw_hit:
                links.append(href)
        return list(dict.fromkeys(links))

    # ─────────────────────────────────────────────────────────
    # FASE 1: PDFs directos
    # ─────────────────────────────────────────────────────────
    def run_direct_pdfs(self):
        log.info(f"\n{'='*60}")
        log.info(f"FASE 1 — PDFs directos ({len(DIRECT_PDFS)} documentos)")
        log.info(f"{'='*60}")
        for item in DIRECT_PDFS:
            self._wait(item["name"])
            self._download_pdf(
                url        = item["url"],
                category   = item["category"],
                tags       = item["tags"],
                source_name= item["name"],
                verify     = item.get("verify_ssl", True),
            )

    # ─────────────────────────────────────────────────────────
    # FASE 2: Crawling
    # ─────────────────────────────────────────────────────────
    def run_crawl_sources(self):
        for src in CRAWL_SOURCES:
            self._crawl(src)

    def _crawl(self, source: dict):
        log.info(f"\n{'='*60}")
        log.info(f"FASE 2 — Crawling: {source['name']}")
        log.info(f"{'='*60}")
        verify   = source.get("verify_ssl", True)
        keywords = source.get("link_keywords", [])
        base     = source["base_url"]
        docs_dl  = 0
        pages_v  = 0
        queue    = list(source["start_urls"])
        seen: set[str] = set()

        while queue and docs_dl < MAX_DOCS_PER_SOURCE:
            url = queue.pop(0)
            if url in seen or url in self._visited_urls:
                continue
            seen.add(url)

            if not self._is_allowed(base, url, verify):
                log.warning(f"  robots.txt prohíbe: {url}")
                continue

            self._wait(source["name"])

            if url.lower().endswith(".pdf"):
                r = self._download_pdf(url, source["category"],
                                       source["tags"], source["name"], verify)
                if r:
                    docs_dl += 1
                continue

            if pages_v >= MAX_PAGES_PER_SOURCE:
                log.info(f"  Límite de páginas alcanzado ({MAX_PAGES_PER_SOURCE})")
                break

            r = self._get(url, verify=verify)
            if not r:
                continue
            pages_v += 1

            pdf_links  = self._extract_pdf_links(r.text, url, base, keywords)
            page_links = self._extract_page_links(r.text, url, base, keywords)
            log.info(f"  Página: {url} → {len(pdf_links)} PDFs | {len(page_links)} páginas")

            for lnk in pdf_links:
                if docs_dl >= MAX_DOCS_PER_SOURCE:
                    break
                if lnk not in self._visited_urls:
                    self._wait(source["name"])
                    result = self._download_pdf(lnk, source["category"],
                                                source["tags"], source["name"], verify)
                    if result:
                        docs_dl += 1

            if source.get("follow_links", False):
                for lnk in page_links:
                    if lnk not in seen:
                        queue.append(lnk)

        log.info(f"  Crawling finalizado: {docs_dl} docs descargados.")

    # ─────────────────────────────────────────────────────────
    # FASE 3: APIs documentales
    # ─────────────────────────────────────────────────────────
    def run_api_sources(self):
        for src in API_SOURCES:
            if src["type"] == "eric":
                self._run_eric(src)
            elif src["type"] == "core":
                self._run_core(src)
            elif src["type"] == "zenodo":
                self._run_zenodo(src)

    # ── ERIC API ─────────────────────────────────────────────
    def _run_eric(self, src: dict):
        log.info(f"\n{'='*60}")
        log.info(f"FASE 3 — ERIC API: {src['name']}")
        log.info(f"{'='*60}")
        docs_dl = 0
        for query in src["queries"]:
            if docs_dl >= MAX_DOCS_PER_SOURCE:
                break
            self._wait("ERIC API")
            params = {
                "search": query, "format": "json",
                "fields": "id,title,pdfurl,url",
                "rows": src.get("max_per_query", 5), "start": 0,
            }
            try:
                r = self.session.get("https://api.ies.ed.gov/eric/",
                                     params=params, timeout=15)
                r.raise_for_status()
                docs = r.json().get("response", {}).get("docs", [])
                log.info(f"  ERIC '{query}': {len(docs)} resultados")
                for doc in docs:
                    pdf_url = doc.get("pdfurl", "")
                    if not pdf_url:
                        eid = doc.get("id", "")
                        if eid:
                            pdf_url = f"https://files.eric.ed.gov/fulltext/{eid}.pdf"
                    if not pdf_url or not pdf_url.startswith("http"):
                        continue
                    self._wait("ERIC download")
                    res = self._download_pdf(pdf_url, src["category"],
                                             src["tags"] + [query], src["name"])
                    if res:
                        docs_dl += 1
            except Exception as e:
                log.error(f"  ERIC error ({query}): {e}")
        log.info(f"  ERIC finalizado: {docs_dl} docs.")

    # ── CORE API ─────────────────────────────────────────────
    def _run_core(self, src: dict):
        log.info(f"\n{'='*60}")
        log.info(f"FASE 3 — CORE API: {src['name']}")
        log.info(f"{'='*60}")
        docs_dl = 0
        for query in src["queries"]:
            if docs_dl >= MAX_DOCS_PER_SOURCE:
                break
            self._wait("CORE API")
            params = {"q": query, "limit": src.get("max_per_query", 5),
                      "offset": 0, "fulltext": "true"}
            try:
                r = self.session.get("https://api.core.ac.uk/v3/search/works",
                                     params=params, timeout=20)
                r.raise_for_status()
                results = r.json().get("results", [])
                log.info(f"  CORE '{query}': {len(results)} resultados")
                for item in results:
                    pdf_url = item.get("downloadUrl") or item.get("fullTextUrl", "")
                    if not pdf_url:
                        for lnk in item.get("links", []):
                            if lnk.get("type") == "download":
                                pdf_url = lnk.get("url", "")
                                break
                    if not pdf_url or not pdf_url.startswith("http"):
                        continue
                    self._wait("CORE download")
                    res = self._download_pdf(pdf_url, src["category"],
                                             src["tags"] + [query], src["name"])
                    if res:
                        docs_dl += 1
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    backoff = 60  # esperar 1 minuto ante rate limit
                    log.warning(f"  CORE rate limit (429). Pausa de {backoff}s...")
                    time.sleep(backoff)
                else:
                    log.error(f"  CORE error ({query}): {e}")
            except Exception as e:
                log.error(f"  CORE error ({query}): {e}")
        log.info(f"  CORE finalizado: {docs_dl} docs.")

    # ── Zenodo API ───────────────────────────────────────────
    def _run_zenodo(self, src: dict):
        log.info(f"\n{'='*60}")
        log.info(f"FASE 3 — Zenodo API: {src['name']}")
        log.info(f"{'='*60}")
        docs_dl = 0
        for query in src["queries"]:
            if docs_dl >= MAX_DOCS_PER_SOURCE:
                break
            self._wait("Zenodo API")
            params = {"q": query, "type": "publication",
                      "size": src.get("max_per_query", 5), "sort": "mostrecent"}
            try:
                r = self.session.get("https://zenodo.org/api/records",
                                     params=params, timeout=15)
                r.raise_for_status()
                hits = r.json().get("hits", {}).get("hits", [])
                log.info(f"  Zenodo '{query}': {len(hits)} resultados")
                for hit in hits:
                    pdf_url = ""
                    # Opción 1: campo files[] (requiere auth en algunos registros)
                    for f in hit.get("files", []):
                        if f.get("type") == "pdf":
                            pdf_url = f.get("links", {}).get("self", "")
                            break
                    # Opción 2: construir URL desde el DOI / record id
                    if not pdf_url:
                        rec_id  = str(hit.get("id", ""))
                        rec_doi = hit.get("doi", "")
                        # Zenodo PDFs públicos: https://zenodo.org/record/{id}/files/*.pdf
                        files_url = f"https://zenodo.org/api/records/{rec_id}/files"
                        try:
                            fr = self.session.get(files_url, timeout=10)
                            if fr.status_code == 200:
                                for entry in fr.json().get("entries", []):
                                    if entry.get("key", "").lower().endswith(".pdf"):
                                        pdf_url = entry.get("links", {}).get("content", "")
                                        break
                        except Exception:
                            pass
                    if pdf_url:
                        self._wait("Zenodo download")
                        res = self._download_pdf(
                            pdf_url, src["category"],
                            src["tags"] + [query], src["name"])
                        if res:
                            docs_dl += 1
            except Exception as e:
                log.error(f"  Zenodo error ({query}): {e}")
        log.info(f"  Zenodo finalizado: {docs_dl} docs.")

    # ─────────────────────────────────────────────────────────
    # EJECUTAR TODO
    # ─────────────────────────────────────────────────────────
    def run(self):
        log.info("=" * 60)
        log.info("ESCUELA INTELIGENTE — Web Scraper v2")
        log.info(f"Delay: {MIN_DELAY}–{MAX_DELAY}s | Máx/fuente: {MAX_DOCS_PER_SOURCE}")
        log.info("=" * 60)

        self.run_direct_pdfs()
        self.run_crawl_sources()
        self.run_api_sources()
        self._summary()

    def _summary(self):
        log.info("\n" + "=" * 60)
        log.info("RESUMEN FINAL")
        log.info(f"  ✓ Descargados : {self.stats['downloaded']}")
        log.info(f"  ○ Omitidos    : {self.stats['skipped']}")
        log.info(f"  ✗ Errores     : {self.stats['errors']}")
        log.info(f"  Carpeta       : {OUTPUT_DIR.resolve()}")
        log.info("=" * 60)


if __name__ == "__main__":
    scraper = EthicalScraper()
    scraper.run()