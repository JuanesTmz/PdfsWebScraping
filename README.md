# 🤖 Escuela Inteligente — Arquitectura de Scraping RAG

El proyecto dispone de un potente y altamente concurrente motor de extracción de datos (web scraping y llamadas API). Está diseñado para recolectar, de forma automatizada y masiva, documentos (principalmente archivos `.pdf` y `.txt`) y centralizarlos en una robusta **Base de Conocimiento (Knowledge Base)** segmentada por categorías de nuestro interés.

Esta recolección es la fuente de datos bruta que posteriormente alimenta la arquitectura RAG (**Retrieval-Augmented Generation**) de nuestro LLM.

## Tabla de contenido

1. [Filosofía y Arquitectura Técnica](#1-filosofía-y-arquitectura-técnica)
2. [¿Cómo funciona el scraper?](#2-cómo-funciona-el-scraper)
3. [Estructura de carpetas](#3-estructura-de-carpetas)
4. [Las tres fases de descarga](#4-las-tres-fases-de-descarga)
5. [Cómo añadir fuentes nuevas](#5-cómo-añadir-fuentes-nuevas)
6. [Categorías disponibles](#6-categorías-disponibles)
7. [Cómo ejecutar el scraper](#7-cómo-ejecutar-el-scraper)
8. [Parámetros de configuración](#8-parámetros-de-configuración)
9. [Solución de problemas](#9-solución-de-problemas)

---

## 1. Filosofía y Arquitectura Técnica

Nuestra arquitectura está diseñada bajo los principios de **Alta Velocidad**, **Ejecución Paralela** y **Gestión de Recursos Escalable**. Todo el proceso se orquesta mediante scripts en Python apoyándose en utilidades como `requests`, `BeautifulSoup` y librerías concurrentes nativas (`concurrent.futures`).

* **Sistema Asíncrono Basado en Hilos (Threading):** Cada scraper crea un pool dinámico de hasta **30 hilos simultáneos (`MAX_WORKERS = 30`)**. Estos procesan una cola central de URLs, lo que permite reducir drásticamente los tiempos de recolección.
* **Zero Delays (Flujo Dinámico y Sin Bloqueos):** Ajustado con *micro-delays* (`0.01s - 0.05s`), acelerando de forma exponencial el resultado al aprovechar activamente APIs documentales abiertas y repositorios open-access. 
* **Almacenamiento Optimizado para RAG:** Directorio totalmente plano sin meta-datos incrustados (el script prescinde de archivos `.meta.json` adjuntos que contaminarían el flujo del vector store). Posee un control estricto de pesos (ignora archivos > 50MB) para evitar ruido a los motores semánticos, usando un hash en el nombre para unicidad: `{md5_hash}_{nombre_pdf.pdf}`.

---

## 2. ¿Cómo funciona el scraper?

El scraper descarga documentos de fuentes educativas abiertas en tres etapas:

```text
FASE 1: PDFs directos  →  URLs conocidas, descarga inmediata
FASE 2: Crawling       →  Rastrea dominios institucionales y busca links a PDFs ocultos
FASE 3: APIs           →  Consulta directa de repositorios académicos mediante queries (ERIC, CORE, etc.)
```

Las tres fases acumulan URLs en una **cola de descarga**. Al final, los PDFs se descargan en **paralelo** (hasta 30 trabajadores simultáneos), ingresando limpios a la Base de Conocimiento.

### Flujo interno

```text
DIRECT_PDFS  ─┐
CRAWL_SOURCES ─┼──► cola de URLs ──► 30 workers paralelos ──► knowledge_base/categoria/
API_SOURCES   ─┘
```

---

## 3. Estructura de carpetas

```text
PdfsWebScraping/
├── scraper.py              ← código principal (el motor / plantilla)
├── README.md               ← esta guía híbrida definitiva
├── README copy.md          ← notas de arquitectura (deprecated)
├── knowledge_base/         ← carpeta raíz de extracción documental
│   ├── mi_categoria_personalizada/
│   ├── contexto_educativo/
│   ├── uso_etico_IA/
│   └── ...
└── logs/
    └── scraper_generico.log ← registro detallado de comportamientos asíncronos y errores
```

Cada archivo descargado tiene el formato base optimizado para RAG garantizando unicidad:
```text
knowledge_base/categoria/a1b2c3d4_nombre-del-archivo.pdf
```

---

## 4. Las tres fases de descarga

### Fase 1: PDFs directos (`DIRECT_PDFS`)
Lista de URLs conocidas que apuntan directamente a un PDF. El scraper las descarga sin navegación previa. Útil para documentos singulares (Leyes, Planes de Desarrollo, Informes específicos).

### Fase 2: Crawling (`CRAWL_SOURCES`)
Si deseas indexar un dominio entero (ej: ministerio.edu.co o repositorio.udea.edu.co). El scraper visita las páginas iniciales `start_urls` y sigue recursivamente los enlaces que coincidan con las palabras establecidas en `link_keywords`.  

### Fase 3: APIs Documentales Académicas (`API_SOURCES`)
El eslabón más productivo e inteligente del scraper. Activa peticiones directas a repositorios remotos evadiendo el scraping de HTML. Bajan el flujo completo de PDFs de bases de datos *open-access*.

**APIs soportadas nativamente:**
| `type` | Repositorio | Fortaleza |
|---|---|---|
| `core` | CORE.ac.uk | Open access multidisciplinar agregado. |
| `openalex` | OpenAlex | Red de literatura académica extensísima (español/inglés). |
| `eric` | ERIC (IES) | Enfoque completo en educación y contexto escolar. Funciona mejor en inglés. |
| `zenodo` | Zenodo (CERN) | Reportes estadísticos, datasets e investigaciones. |
| `semantic_scholar` | Semantic Scholar | Inteligencia Artificial enfocada a citaciones. |

---

## 5. Cómo añadir fuentes nuevas

Copia, lee y adapta este documento base (`scraper.py`) para recolectar tus fuentes:

### 5.1 Añadir un PDF directo (`DIRECT_PDFS`)

```python
DIRECT_PDFS = [
    {
        "url": "https://www.medellin.gov.co/plandesarrollo/documento.pdf",
        "name": "Plan de Desarrollo Local",    # Visible en los Logs
        "category": "Mi_Categoria_Local"       # Carpeta destino dentro de knowledge_base/
    }
]
```

### 5.2 Añadir un sitio para crawling (`CRAWL_SOURCES`)

```python
CRAWL_SOURCES = [
    {
        "name": "Portal Universidad",          
        "base_url": "https://www.sitio.edu.co",          
        "start_urls": ["https://www.sitio.edu.co/documentos/"], 
        "category": "Educacion_Universitarias",         
        "link_keywords": ["pdf", "descargar", "informe", "proyecto"],
    }
]
```

### 5.3 Añadir limitantes de búsqueda en APIs (`API_SOURCES`)

Envía palabras clave que funcionen como búsquedas literales reales contra los motores.
```python
API_SOURCES = [
    {
        "name": "Extracción ERIC Colombia",             
        "type": "eric",                                 
        "category": "Investigacion_Escolar",            
        "queries": [                                    
            "calidad educativa secundaria en medellin",
            "pensamiento computacional"
        ],
        "max_per_query": 50, # Cantidad máxima de papers a descargar por frase
    }
]
```

---

## 6. Categorías disponibles

El destino de todos los documentos será `knowledge_base/<Tu_Categoria>/...`. Si se emplean arquitecturas de conocimiento, es idóneo segregarlos en carpetas temáticas para segmentar el RAG. Algunos ejemplos relevantes:

| Carpeta en `knowledge_base/`    | Contenido de Ejemplo                                         |
|---------------------------------|--------------------------------------------------------------|
| `REA`                           | Recursos educativos abiertos: STEM, pensamiento computacional |
| `teoria_educativa`              | Pedagogía, constructivismo, rutinas de aprendizaje            |
| `contexto_educativo`            | DBA, estándares, mallas curriculares, pruebas                |
| `mediacion_socratica`           | Metodología socrática, tutoría IA, retroalimentación formativa|
| `uso_etico_IA`                  | Normativa y ética de la inteligencia artificial              |

---

## 7. Cómo ejecutar el scraper

**1. Habilita tu entorno virtual:**
```bash
python -m venv .venv
source .venv/Scripts/activate  # MacOS / Linux
# En Windows: .venv\Scripts\activate
```

**2. Instala dependencias obligatorias:**
```bash
pip install requests beautifulsoup4
# o bien: pip install -r requirements.txt
```

**3. Modifica tus parámetros en `scraper.py` (o en una copia limpia) e inicia:**
```bash
python scraper.py
```
> Todo el progreso asíncrono en tiempo real se mostrará por consola y se guardará centralizado en la carpeta de `logs/`.

*(Nota: el diseño del scraper es idempotente. Puedes ejecutarlo infinitas veces; sólo descargará lo que no cuente con su hash existente previniendo duplicidad).*

---

## 8. Parámetros de configuración

En el bloque superior de tu archivo `scraper.py` puedes afinar el comportamiento agresivo o prudente de tu instancia de recolección:

| Parámetro | Valor por defecto | Descripción |
|---|---|---|
| `OUTPUT_DIR` | `knowledge_base` | Carpeta raíz donde se integrará localmente tu RAG. |
| `DELAY` | `(0.01, 0.05)` | Micro-latencia aleatoria entre peticiones asíncronas para evadir mitigaciones de Firewall. |
| `MAX_DOCS_PER_SOURCE` | `600` | Tope brutal de PDFs por web objetivo `[Crawling]`. |
| `MAX_PAGES_PER_CRAWL` | `150` | Seguridad para no rastrear una página web ad infinitum `[Crawling]`. |
| `MAX_PDF_BYTES` | `50 * 1024 * 1024` | 50 MB - Descarte silencioso de documentos de extrema densidad para blindar el vector store. |
| `MAX_WORKERS` | `30` | Escalado de concurrencia Threading para la cola final. |

---

## 9. Solución de problemas

### "GET [url]: 403 Forbidden"
El sitio está bloqueando las tramas asíncronas del bot. 
→ **Solución**: Aumenta el rango de latencia en el `DELAY` (ej: `(1.5, 3.0)`). O descarga puntualmente los PDFs de allí listándolos como `DIRECT_PDFS`.

### Muchos Errores "SSLError"
El HTTPS o los certificados del servidor de esa entidad universitaria/estatal han caducado.
→ **Solución**: El parser interno cuenta con `verify=False` como sistema de respaldo integrado. En ocasiones muy restrictivas, revisa que la clave `"verify_ssl": False` esté activa en la declaración manual de tu fuente en Python.

### "No es PDF (text/html)"
La ruta final era en verdad un redirect interactivo perjudicial que no aloja el binario real, o requería autenticación humana y el servidor rechazó al crawler redireccionando. El script abortará automáticamente y descarta el elemento sin comprometer el proceso general.

### "Abortado (muy grande)" o "Ignorado" silencioso
El tamaño del documento supera la barrera segura para nuestro contexto LLM RAG (`50MB`). Los archivos gigantes son excluidos antes de ser persistidos. Expandelo cambiando `MAX_PDF_BYTES`.

### Demasiadas omisiones
El bot detecto que el hash temporal de los documentos en la base de colas ya exísten y han sido rebotados eficientemente sin malgastar CPU. El ciclo sigue sano.