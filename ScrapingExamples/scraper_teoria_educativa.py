"""
scraper_teoria_educativa.py — Descargador masivo Teoría Educativa · Escuela Inteligente v4
Especializado en: Educación, pedagogía, didáctica, constructivismo, y discurso educativo actual.
"""
import hashlib, logging, random, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN OPTIMIZADA PARA VELOCIDAD (ALTO VOLUMEN)
# ══════════════════════════════════════════════════════════════════════════
OUTPUT_DIR          = Path("knowledge_base") 
LOGS_DIR            = Path("logs")
DELAY               = (0.01, 0.05)           
MAX_DOCS_PER_SOURCE = 600                    
MAX_PAGES_PER_CRAWL = 150                    
MAX_PDF_BYTES       = 50 * 1024 * 1024       
MAX_WORKERS         = 30                     

HEADERS = {
    "User-Agent": (
        "EscuelaInteligente-TeoriaBot/4.0 "
        "(Proyecto educativo Medellín; info@escuelainteligente.edu.co)"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

for _d in [OUTPUT_DIR, LOGS_DIR]:
    _d.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scraper_teoria.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

TARGET_CAT = "Experticia en teoría educativa"

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 1: PDFs DIRECTOS (Documentos fundamentales)
# ══════════════════════════════════════════════════════════════════════════
DIRECT_PDFS = [
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000370294/PDF/pf0000370294_spa.pdf.multi",
        "name": "UNESCO - Marco de Competencias Docentes en TIC",
        "category": TARGET_CAT,
    },
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000232022/PDF/pf0000232022_spa.pdf.multi",
        "name": "UNESCO - Replantear la educación 2015",
        "category": TARGET_CAT,
    },
    {
        "url": "https://repositorio.cepal.org/bitstream/handle/11362/48099/S2200803_es.pdf",
        "name": "CEPAL - Habilidades del siglo XXI 2022",
        "category": TARGET_CAT,
    }
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 2: CRAWLING INSTITUCIONAL Y REVISTAS DE EDUCACIÓN
# ══════════════════════════════════════════════════════════════════════════
CRAWL_SOURCES = [
    {
        "name": "REDALYC - Educación y Pedagogía",
        "base_url": "https://www.redalyc.org",
        "start_urls": [
            "https://www.redalyc.org/busqueda.oa?q=pedagogia+didactica&tipo=bd",
            "https://www.redalyc.org/busqueda.oa?q=constructivismo+educacion&tipo=bd",
            "https://www.redalyc.org/busqueda.oa?q=teoria+educativa&tipo=bd"
        ],
        "category": TARGET_CAT,
        "link_keywords": ["pdf", "articulo", "download", "descargar"],
    },
    {
        "name": "SciELO - Educación",
        "base_url": "https://scielo.org.co",
        "start_urls": ["https://scielo.org.co/"],
        "category": TARGET_CAT,
        "link_keywords": ["pdf", "articulo", "educacion", "pedagogia", "didactica"],
    },
    {
        "name": "IDEP Bogotá - Repositorio",
        "base_url": "https://repositorio.idep.edu.co",
        "start_urls": ["https://repositorio.idep.edu.co/"],
        "category": TARGET_CAT,
        "link_keywords": ["pdf", "educacion", "pedagog", "didactica", "bitstream", "handle"],
    },
    {
        "name": "CLACSO Biblioteca Digital",
        "base_url": "https://biblioteca.clacso.edu.ar",
        "start_urls": ["https://biblioteca.clacso.edu.ar/"],
        "category": TARGET_CAT,
        "link_keywords": ["pdf", "educacion", "pedagogia", "descarga", "libro"],
    }
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 3: APIs DOCUMENTALES (MÁXIMA VELOCIDAD Y VOLUMEN)
# ══════════════════════════════════════════════════════════════════════════
API_SOURCES = [
    {
        "name": "CORE - Teoría Educativa (Open Access)",
        "type": "core",
        "category": TARGET_CAT,
        "queries": [
            "teoría educativa pedagogía contemporánea",
            "didáctica general y específica",
            "modelos pedagógicos constructivismo",
            "evaluación formativa didáctica",
            "currículo y pedagogía innovación",
            "estrategias didácticas aprendizaje",
            "teorías del aprendizaje educación"
        ],
        "max_per_query": 60,
    },
    {
        "name": "OpenAlex - Investigación en Pedagogía",
        "type": "openalex",
        "category": TARGET_CAT,
        "queries": [
            "pedagogía crítica",
            "didáctica educación contemporánea",
            "modelos de enseñanza aprendizaje",
            "teoría de la educación",
            "práctica docente reflexión pedagogía"
        ],
        "max_per_query": 50,
    },
    {
        "name": "ERIC - Educational Theory & Pedagogy",
        "type": "eric",
        "category": TARGET_CAT,
        "queries": [
            "educational theory pedagogy constructivism",
            "didactics teaching methods curriculum",
            "formative assessment critical pedagogy",
            "learning theories modern education"
        ],
        "max_per_query": 50,
    }
]

# ══════════════════════════════════════════════════════════════════════════
# SCRAPER ENGINE (Optimizado, sin crear .meta.json)
# ══════════════════════════════════════════════════════════════════════════
class ScraperTeoria:
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
            self._queue.append((url, category, name, verify))

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
        dest  = OUTPUT_DIR / category
        dest.mkdir(parents=True, exist_ok=True)
        fpath = dest / fname

        if fpath.exists():
            with self._lock:
                self.stats["skipped"] += 1
            return False

        total = 0
        try:
            with open(fpath, "wb") as f:
                for chunk in r.iter_content(16384): # Bloques de descarga grandes 16KB
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

        if total < 1024:
            fpath.unlink(missing_ok=True)
            return False

        log.info(f"✓ Teoría/{fname} ({total/1024:.0f} KB) - {name}")
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
        log.info(f"\n─── Crawling: {source['name']}")
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
        log.info(f"\n─── API: {source['name']}")
        for query in source["queries"]:
            try:
                urls = self._api_pdf_urls(source["type"], query, source.get("max_per_query", 10))
                for url in urls:
                    self._enqueue(url, source["category"], source["name"])
                log.info(f"  {source['type']} '{query[:50]}': {len(urls)} URLs encontradas")
            except requests.exceptions.HTTPError:
                pass
            except Exception:
                pass
            time.sleep(random.uniform(*DELAY))

    def _api_pdf_urls(self, api_type, query, limit):
        if api_type == "core":
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
                item["open_access"]["oa_url"]
                for item in r.json().get("results", [])
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

    def run(self):
        log.info("═" * 65)
        log.info("ESCUELA INTELIGENTE — Scraper Teoría Educativa Ultra-Fast")
        log.info("═" * 65)
        for item in DIRECT_PDFS:
            self._enqueue(item["url"], item["category"], item["name"])
        for src in CRAWL_SOURCES: self._collect_crawl(src)
        for src in API_SOURCES: self._collect_api(src)
        self._execute_queue()
        
        log.info("\n═" * 65)
        log.info("RESUMEN FINAL TEORÍA EDUCATIVA")
        log.info(f"  ✓ Descargados : {self.stats['downloaded']}")
        log.info(f"  ○ Omitidos    : {self.stats['skipped']}")
        log.info(f"  ✗ Errores     : {self.stats['errors']}")
        log.info("═" * 65)

if __name__ == "__main__":
    ScraperTeoria().run()
