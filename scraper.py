"""
scraper.py — Plantilla Estándar y Universal de Scraping · Escuela Inteligente v4
Arquitectura de Alto Volumen, Hilos Paralelos (30 workers) y almacenamiento limpio (sin metadatos).
Instrucciones: Reemplazar los marcadores en DIRECT_PDFS, CRAWL_SOURCES y API_SOURCES.
"""
import hashlib, logging, random, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN ÓPTIMA DEL MOTOR (ALTO RENDIMIENTO)
# ══════════════════════════════════════════════════════════════════════════
OUTPUT_DIR          = Path("knowledge_base") # Carpeta raíz de salida
LOGS_DIR            = Path("logs")
DELAY               = (0.01, 0.05)           # Micro-pausas para evitar bans
MAX_DOCS_PER_SOURCE = 600                    # Tope por portal en crawler
MAX_PAGES_PER_CRAWL = 150                    # Máximas páginas a navegar por portal
MAX_PDF_BYTES       = 50 * 1024 * 1024       # Ignorar PDFs mayores a 50MB
MAX_WORKERS         = 30                     # Concurrencia masiva

HEADERS = {
    "User-Agent": "EscuelaInteligente-ScraperBot/4.0 (info@escuelainteligente.edu.co)",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

for _d in [OUTPUT_DIR, LOGS_DIR]:
    try:
        _d.mkdir(exist_ok=True)
    except OSError:
        pass

_handlers = [logging.StreamHandler()]
try:
    LOGS_DIR.mkdir(exist_ok=True)
    _handlers.append(logging.FileHandler(LOGS_DIR / "scraper_generico.log", encoding="utf-8"))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger(__name__)

# La carpeta donde se guardarán los resultados por defecto
TARGET_CAT = "mi_categoria_personalizada"

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 1: PDFs DIRECTOS
# Agrega URLs absolutas que terminen en .pdf o que precipiten una descarga
# ══════════════════════════════════════════════════════════════════════════
DIRECT_PDFS = [
    {
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "name": "Documento Ejemplo PDF",
        "category": TARGET_CAT,
    }
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 2: CRAWLING RECURSIVO INSTITUCIONAL
# Busca en las URL semilla todo lo que parezca un PDF
# ══════════════════════════════════════════════════════════════════════════
CRAWL_SOURCES = [
    # Descomenta y llena los datos para habilitarlo
    """
    {
        "name": "Nombre Institucion o Web",
        "base_url": "https://www.portal-web-base.com",
        "start_urls": [
            "https://www.portal-web-base.com/documentos",
            "https://www.portal-web-base.com/publicaciones"
        ],
        "category": TARGET_CAT,
        "link_keywords": ["pdf", "estrategia", "informe", "descargar"],
    }
    """
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 3: APIs BIBLIOGRÁFICAS/DOCUMENTALES
# Options "type": core | openalex | eric | zenodo | semantic_scholar
# ══════════════════════════════════════════════════════════════════════════
API_SOURCES = [
    # Descomenta y llena los datos para habilitarlo
    """
    {
        "name": "Buscador OpenAlex - Tema Específico",
        "type": "openalex", 
        "category": TARGET_CAT,
        "queries": [
            "palabra clave de investigacion",
            "otra busqueda especializada"
        ],
        "max_per_query": 20,
    }
    """
]

# ══════════════════════════════════════════════════════════════════════════
# SCRAPER ENGINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
class ScraperEstandar:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._seen:  set   = set()
        self._queue: list  = []          
        self._lock         = threading.Lock()
        self.stats         = {"downloaded": 0, "skipped": 0, "errors": 0}

    def _get(self, url, stream=False, verify=True, timeout=10):
        try:
            r = self.session.get(url, timeout=timeout, stream=stream, verify=verify)
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError:
            try:
                r = self.session.get(url, timeout=timeout, stream=stream, verify=False)
                r.raise_for_status()
                return r
            except Exception:
                pass
        except Exception:
            pass
        with self._lock:
            self.stats["errors"] += 1
        return None

    def _enqueue(self, url, category, name, verify=True):
        if url and url.startswith("http") and url not in self._seen:
            self._seen.add(url)
            path_segment = urlparse(url).path.rstrip("/").split("/")[-1] or ""
            stem = path_segment.replace(".pdf", "").replace(".PDF", "")
            if len(stem) > 3:
                doc_name = unquote(path_segment).replace("_", " ").replace("-", " ").strip()
                if not doc_name.lower().endswith(".pdf"):
                    doc_name += ".pdf"
            else:
                doc_name = name
            self._queue.append((url, category, doc_name, verify))

    def _download_pdf(self, url, category, name, verify=True):
        r = self._get(url, stream=True, verify=verify, timeout=15)
        if not r: return False

        ct = r.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
            return False

        h     = hashlib.md5(url.encode()).hexdigest()[:8]
        raw   = urlparse(url).path.rstrip("/").split("/")[-1] or "doc"
        raw   = raw if raw.lower().endswith(".pdf") else raw + ".pdf"
        fname = f"{h}_{raw[:80]}"
        
        dest = OUTPUT_DIR / category
        dest.mkdir(parents=True, exist_ok=True)
        fpath = dest / fname

        if fpath.exists():
            with self._lock:
                self.stats["skipped"] += 1
            return False

        total = 0
        try:
            with open(fpath, "wb") as f:
                for chunk in r.iter_content(16384): # Grandes bloques para acelerar
                    f.write(chunk)
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        fpath.unlink(missing_ok=True)
                        return False
        except Exception:
            fpath.unlink(missing_ok=True)
            with self._lock:
                self.stats["errors"] += 1
            return False

        if total < 1024: # Descartar PDFs vacios/corruptos
            fpath.unlink(missing_ok=True)
            return False

        log.info(f"✓ {category}/{fname} ({total/1024:.0f} KB) - {name}")
        with self._lock:
            self.stats["downloaded"] += 1
        return True

    def _links_from_page(self, html, page_url, base_url, keywords):
        soup      = BeautifulSoup(html, "html.parser")
        base_host = urlparse(base_url).netloc
        skip_ext  = (".jpg", ".png", ".zip", ".mp4", ".js", ".css", ".ico", ".svg")
        pdf_links, page_links = [], []

        for a in soup.find_all("a", href=True):
            href = urljoin(page_url, a["href"])
            if urlparse(href).netloc != base_host: continue
            text   = a.get_text(strip=True).lower()
            kw_hit = any(kw in href.lower() or kw in text for kw in keywords)

            if href.lower().endswith(".pdf"):
                pdf_links.append(href)
            elif kw_hit and not any(href.lower().endswith(e) for e in skip_ext):
                page_links.append(href)

        return list(dict.fromkeys(pdf_links)), list(dict.fromkeys(page_links))

    def _collect_crawl(self, source):
        # Evitar fallos si está comentado como string en la plantilla
        if isinstance(source, str): return 
        
        log.info(f"\n─── Crawling: {source.get('name', 'N/A')}")
        verify    = source.get("verify_ssl", True)
        keywords  = source.get("link_keywords", [])
        base      = source["base_url"]
        queue     = list(source["start_urls"])
        seen_p: set = set()
        pdfs_found = pages_visited = 0

        while queue and pdfs_found < MAX_DOCS_PER_SOURCE and pages_visited < MAX_PAGES_PER_CRAWL:
            url = queue.pop(0)
            if url in seen_p: continue
            seen_p.add(url)
            time.sleep(random.uniform(*DELAY))

            if url.lower().endswith(".pdf"):
                self._enqueue(url, source["category"], source["name"], verify)
                pdfs_found += 1
                continue

            r = self._get(url, verify=verify)
            if not r: continue
            pages_visited += 1

            pdf_links, page_links = self._links_from_page(r.text, url, base, keywords)
            
            for link in pdf_links:
                self._enqueue(link, source["category"], source["name"], verify)
                pdfs_found += 1

            if source.get("follow_links", True):
                for link in page_links:
                    if link not in seen_p: queue.append(link)

    def _collect_api(self, source):
        # Evitar fallos si está comentado como string en la plantilla
        if isinstance(source, str): return 
        
        log.info(f"\n─── API: {source.get('name', 'N/A')}")
        for query in source["queries"]:
            try:
                urls = self._api_pdf_urls(source["type"], query, source.get("max_per_query", 10), source.get("custom_url"))
                for url in urls:
                    self._enqueue(url, source["category"], source["name"])
                log.info(f"  {source['type']} '{query[:50]}': {len(urls)} URLs encontradas")
            except Exception:
                pass
            time.sleep(random.uniform(*DELAY))

    def _api_pdf_urls(self, api_type, query, limit, custom_url=None):
        if api_type == "custom" and custom_url:
            r = self.session.get(custom_url, timeout=15, params={"q": query, "query": query, "search": query, "limit": limit})
            if r.status_code == 200:
                # Buscamos de forma genérica cualquier string que sea http...pdf
                import re
                return list(set(re.findall(r'https?://[^\s\'"]+\.pdf', r.text, flags=re.IGNORECASE)))
            return []
        elif api_type == "core":
            r = self.session.get("https://api.core.ac.uk/v3/search/works", timeout=15, params={
                "q": query, "limit": limit, "fulltext": "true",
            })
            r.raise_for_status()
            urls = []
            for item in r.json().get("results", []):
                url = item.get("downloadUrl") or item.get("fullTextUrl", "")
                if not url: url = next((l["url"] for l in item.get("links", []) if l.get("type") == "download"), "")
                if url and url.startswith("http"): urls.append(url)
            return urls
            
        elif api_type == "openalex":
            r = self.session.get("https://api.openalex.org/works", timeout=15, params={
                "search": query, "filter": "open_access.is_oa:true",
                "per_page": limit, "select": "id,open_access",
            })
            r.raise_for_status()
            return [
                item["open_access"]["oa_url"] for item in r.json().get("results", [])
                if item.get("open_access", {}).get("oa_url", "").lower().endswith(".pdf")
            ]
            
        elif api_type == "eric":
            r = self.session.get("https://api.ies.ed.gov/eric/", timeout=10, params={
                "search": query, "format": "json", "fields": "id,pdfurl", "rows": limit,
            })
            r.raise_for_status()
            return [
                d.get("pdfurl") or f"https://files.eric.ed.gov/fulltext/{d['id']}.pdf"
                for d in r.json().get("response", {}).get("docs", [])
            ]
            
        elif api_type == "zenodo":
            r = self.session.get("https://zenodo.org/api/records", timeout=15, params={
                "q": query, "type": "publication", "size": limit, "sort": "mostrecent",
            })
            r.raise_for_status()
            urls = []
            for hit in r.json().get("hits", {}).get("hits", []):
                pdf_url = next((f["links"]["self"] for f in hit.get("files", []) if f.get("type") == "pdf"), "")
                if pdf_url: urls.append(pdf_url)
            return urls
            
        elif api_type == "semantic_scholar":
            r = self.session.get("https://api.semanticscholar.org/graph/v1/paper/search", timeout=15, params={
                "query": query, "fields": "openAccessPdf", "limit": limit
            })
            r.raise_for_status()
            return [
                item["openAccessPdf"]["url"] for item in r.json().get("data", [])
                if item.get("openAccessPdf") and item["openAccessPdf"].get("url")
            ]
        return []

    def _execute_queue(self):
        log.info(f"\n══ Descargando {len(self._queue)} PDFs con {MAX_WORKERS} workers en paralelo ══")
        def _worker(args):
            url, category, name, verify = args
            return self._download_pdf(url, category, name, verify)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(_worker, item): item for item in self._queue}
            for future in as_completed(futures):
                try: future.result()
                except Exception: pass

    def run(self, direct_pdfs=None, crawl_sources=None, api_sources=None, skip_download=False):
        log.info("═" * 65)
        log.info("ESCUELA INTELIGENTE — Scraper Estándar (Plantilla Universal)")
        log.info("═" * 65)
        
        direct_pdfs = direct_pdfs if direct_pdfs is not None else DIRECT_PDFS
        crawl_sources = crawl_sources if crawl_sources is not None else CRAWL_SOURCES
        api_sources = api_sources if api_sources is not None else API_SOURCES
        
        for item in direct_pdfs:
            if isinstance(item, dict):
                self._enqueue(item["url"], item["category"], item["name"])
                
        for src in crawl_sources: self._collect_crawl(src)
        for src in api_sources: self._collect_api(src)
        
        if not skip_download:
            self._execute_queue()
        
        log.info("\n═" * 65)
        log.info("RESUMEN FINAL")
        log.info(f"  ✓ Descargados : {self.stats['downloaded']}")
        log.info(f"  ○ Omitidos    : {self.stats['skipped']}")
        log.info(f"  ✗ Errores     : {self.stats['errors']}")
        log.info("═" * 65)
        
        return self._queue

if __name__ == "__main__":
    ScraperEstandar().run()
