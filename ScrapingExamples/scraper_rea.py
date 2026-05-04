"""
scraper_rea.py — Descargador masivo ultrarrápido REA · Escuela Inteligente v4
Especializado en: pensamiento matemático, científico, computacional, lectura crítica, IA, STEM, ciberseguridad.
"""
import json, hashlib, logging, random, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN OPTIMIZADA PARA VELOCIDAD "CASI INMEDIATA"
# ══════════════════════════════════════════════════════════════════════════
OUTPUT_DIR          = Path("knowledge_base") # Descarga directa a la base de conocimiento
LOGS_DIR            = Path("logs")
DELAY               = (0.01, 0.05)           # Pausa mínima entre requests (casi sin retraso)
MAX_DOCS_PER_SOURCE = 500                    # Mayor cantidad de docs por fuente
MAX_PAGES_PER_CRAWL = 100                    # Mayor profundidad
MAX_PDF_BYTES       = 50 * 1024 * 1024       # 50 MB límite por archivo
MAX_WORKERS         = 30                     # Salto a 30 workers paralelos (Ultra rápido)

HEADERS = {
    "User-Agent": (
        "EscuelaInteligente-REABot/4.0 "
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
        logging.FileHandler(LOGS_DIR / "scraper_rea.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 1: PDFs DIRECTOS (Documentos Clave Internacionales)
# ══════════════════════════════════════════════════════════════════════════
DIRECT_PDFS = [
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000373755/PDF/pf0000373755_spa.pdf.multi",
        "name": "UNESCO - Recomendación sobre REA 2019",
        "category": "REA",
    },
    {
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000374287/PDF/pf0000374287_spa.pdf.multi",
        "name": "UNESCO - IA y Educación: orientaciones para políticas 2021",
        "category": "REA",
    }
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 2: CRAWLING (Páginas con REA y contenido en español)
# ══════════════════════════════════════════════════════════════════════════
CRAWL_SOURCES = [
    {
        "name": "Eduteka - Recursos Universitarios y Escolares",
        "base_url": "https://eduteka.icesi.edu.co",
        "start_urls": ["https://eduteka.icesi.edu.co/recursos/"],
        "category": "REA",
        "link_keywords": [
            "pdf", "descargar", "documento", "archivo", "pensamiento", "stem", "guia"
        ],
    },
    {
        "name": "Colombia Aprende",
        "base_url": "https://colombiaaprende.edu.co",
        "start_urls": ["https://colombiaaprende.edu.co/"],
        "category": "REA",
        "link_keywords": [
            "recurso", "guia", "cartilla", "orientacion",
            "documento", "pdf", "descarg", "material", "actividad",
        ],
    },
    {
        "name": "Computadores para Educar",
        "base_url": "https://www.computadoresparaeducar.gov.co",
        "start_urls": ["https://www.computadoresparaeducar.gov.co/"],
        "category": "REA",
        "link_keywords": ["recurso", "documento", "pdf", "cartilla", "guia", "descarg"],
        "verify_ssl": False,
    }
]

# ══════════════════════════════════════════════════════════════════════════
# FUENTES 3: APIs DOCUMENTALES (MÁXIMA VELOCIDAD Y VOLUMEN)
# Consultas especializadas en los temas requeridos
# ══════════════════════════════════════════════════════════════════════════
API_SOURCES = [
    {
        "name": "ERIC - Educación STEM y Computacional",
        "type": "eric",
        "category": "REA",
        "queries": [
            "mathematical thinking elementary", "scientific thinking inquiry",
            "computational thinking K-12", "critical reading comprehension",
            "artificial intelligence education K-12", "STEM education activities",
            "cybersecurity awareness schools", "online safety digital citizenship",
            "open educational resources STEM", "math problem solving strategies"
        ],
        "max_per_query": 50, # Incrementado para obtener cientos
    },
    {
        "name": "CORE - Recursos y Teoría Educativa (Hispano/OpenAccess)",
        "type": "core",
        "category": "REA",
        "queries": [
            "pensamiento matemático educación básica",
            "pensamiento científico didáctica",
            "pensamiento computacional currículo",
            "lectura crítica estrategias",
            "inteligencia artificial en educación",
            "educación STEM STEAM",
            "ciberseguridad jóvenes escuelas",
            "cuidado en la red internet seguros",
            "recursos educativos abiertos matemáticas",
            "recursos educativos abiertos ciencias"
        ],
        "max_per_query": 50,
    },
    {
        "name": "Zenodo - OER y Materiales Educativos Abiertos",
        "type": "zenodo",
        "category": "REA",
        "queries": [
            "open educational resources mathematical thinking",
            "open educational resources computational thinking",
            "AI ethics education guidelines students",
            "digital citizenship online safety youth",
            "educación STEM", "recursos educativos STEM",
            "lectura crítica primaria secundaria"
        ],
        "max_per_query": 50,
    },
    {
        "name": "OpenAlex - Investigación Educativa Abierta",
        "type": "openalex",
        "category": "REA",
        "queries": [
            "pensamiento matemático educación",
            "pensamiento computacional",
            "inteligencia artificial educación",
            "recursos educativos abiertos",
            "lectura crítica comprensión",
            "ciberseguridad educación"
        ],
        "max_per_query": 40,
    },
    {
        "name": "Semantic Scholar - IA, STEM y Computación Abierta",
        "type": "semantic_scholar",
        "category": "REA",
        "queries": [
            "artificial intelligence education resources",
            "computational thinking programming children",
            "cybersecurity education awareness youth",
            "digital safety privacy children education",
            "critical reading teaching strategies oer"
        ],
        "max_per_query": 40,
    },
]

# ══════════════════════════════════════════════════════════════════════════
# SCRAPER ENGINE (Optimizado)
# ══════════════════════════════════════════════════════════════════════════
class ScraperREA:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._seen:  set   = set()
        self._queue: list  = []          
        self._lock         = threading.Lock()
        self.stats         = {"downloaded": 0, "skipped": 0, "errors": 0}

    def _get(self, url, stream=False, verify=True, timeout=10): # Timeout más rápido
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

    def _enqueue(self, url, category, tags, name, verify=True):
        if url and url.startswith("http") and url not in self._seen:
            self._seen.add(url)
            self._queue.append((url, category, tags, name, verify))

    def _download_pdf(self, url, category, tags, name, verify=True):
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
                for chunk in r.iter_content(16384): # Bloques de descarga grandes (16KB)
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

        # Guardar metadata
        meta = {
            "file": fname, "source": name, "url": url,
            "category": category, "tags": tags,
            "topic_focus": "REA, STEM, IA, Lectura Critica",
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(fpath.with_suffix(".meta.json"), "w", encoding="utf-8") as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=2)

        log.info(f"✓ REA/{fname} ({total/1024:.0f} KB)")
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
                self._enqueue(url, source["category"], [], source["name"], verify)
                pdfs_found += 1
                continue

            r = self._get(url, verify=verify)
            if not r: continue
            pages_visited += 1

            pdf_links, page_links = self._links_from_page(r.text, url, base, keywords)
            
            for link in pdf_links:
                self._enqueue(link, source["category"], [], source["name"], verify)
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
                    self._enqueue(url, source["category"], [query], source["name"])
                log.info(f"  {source['type']} '{query[:50]}': {len(urls)} URLs encontradas")
            except requests.exceptions.HTTPError as e:
                pass
            except Exception as e:
                pass
            time.sleep(random.uniform(*DELAY))

    def _api_pdf_urls(self, api_type, query, limit):
        # Mismas integraciones que scraper normal
        if api_type == "eric":
            r = self.session.get("https://api.ies.ed.gov/eric/", timeout=10, params={
                "search": query, "format": "json", "fields": "id,pdfurl", "rows": limit,
            })
            r.raise_for_status()
            return [
                d.get("pdfurl") or f"https://files.eric.ed.gov/fulltext/{d['id']}.pdf"
                for d in r.json().get("response", {}).get("docs", [])
            ]
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
        elif api_type == "zenodo":
            r = self.session.get("https://zenodo.org/api/records", timeout=10, params={
                "q": query, "type": "publication", "size": limit, "sort": "mostrecent",
            })
            r.raise_for_status()
            urls = []
            for hit in r.json().get("hits", {}).get("hits", []):
                pdf_url = next((f["links"]["self"] for f in hit.get("files", []) if f.get("type") == "pdf"), "")
                if pdf_url: urls.append(pdf_url)
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
        elif api_type == "semantic_scholar":
            r = self.session.get(
                "https://api.semanticscholar.org/graph/v1/paper/search", timeout=15,
                params={"query": query, "fields": "openAccessPdf", "limit": limit},
            )
            r.raise_for_status()
            return [
                item["openAccessPdf"]["url"]
                for item in r.json().get("data", [])
                if item.get("openAccessPdf") and item["openAccessPdf"].get("url")
            ]
        return []

    def _execute_queue(self):
        log.info(f"\n══ Descargando {len(self._queue)} PDFs con {MAX_WORKERS} workers en paralelo ══")
        def _worker(args):
            url, category, tags, name, verify = args
            return self._download_pdf(url, category, tags, name, verify)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(_worker, item): item for item in self._queue}
            for future in as_completed(futures):
                try: future.result()
                except Exception: pass

    def run(self):
        log.info("═" * 65)
        log.info("ESCUELA INTELIGENTE — Scraper REA Ultra-Fast v4")
        log.info("═" * 65)
        for item in DIRECT_PDFS:
            self._enqueue(item["url"], item["category"], item.get("tags", []), item["name"], item.get("verify_ssl", True))
        for src in CRAWL_SOURCES: self._collect_crawl(src)
        for src in API_SOURCES: self._collect_api(src)
        self._execute_queue()
        
        log.info("\n═" * 65)
        log.info("RESUMEN FINAL REA")
        log.info(f"  ✓ Descargados : {self.stats['downloaded']}")
        log.info(f"  ○ Omitidos    : {self.stats['skipped']}")
        log.info(f"  ✗ Errores     : {self.stats['errors']}")
        log.info("═" * 65)

if __name__ == "__main__":
    ScraperREA().run()
