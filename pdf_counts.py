import os
from collections import defaultdict

def count_pdfs_by_folder(root_dir):
    pdf_counts = defaultdict(int)
    total_pdfs = 0

    for dirpath, _, filenames in os.walk(root_dir):
        # Ignorar carpetas ocultas o entornos virtuales (ej. .venv, .git)
        if any(part.startswith('.') for part in dirpath.split(os.sep)):
            continue
            
        count = sum(1 for f in filenames if f.lower().endswith('.pdf'))
        if count > 0:
            # Obtener ruta relativa para que la tabla sea más legible
            rel_path = os.path.relpath(dirpath, root_dir)
            if rel_path == '.':
                rel_path = '(Raíz del proyecto)'
            pdf_counts[rel_path] += count
            total_pdfs += count

    return pdf_counts, total_pdfs

def print_tabulated(pdf_counts, total_pdfs):
    if not pdf_counts:
        print("No se encontraron archivos PDF en el proyecto.")
        return

    # Preparar datos 
    headers = ["Directorio", "Cantidad de PDFs"]
    
    # Calcular anchos dinámicos para las columnas
    max_dir_len = max([len(d) for d in pdf_counts.keys()] + [len(headers[0]), len("TOTAL")])
    max_count_len = max(len(headers[1]), len(str(total_pdfs)))
    
    # Formato de las filas y caracteres de bordes (Unicode Box Drawing)
    row_format = f"│ {{:<{max_dir_len}}} │ {{:>{max_count_len}}} │"
    
    top_border = f"┌{'─' * (max_dir_len + 2)}┬{'─' * (max_count_len + 2)}┐"
    mid_border = f"├{'─' * (max_dir_len + 2)}┼{'─' * (max_count_len + 2)}┤"
    bot_border = f"└{'─' * (max_dir_len + 2)}┴{'─' * (max_count_len + 2)}┘"

    # Imprimir cabecera
    print(top_border)
    print(row_format.format(*headers))
    print(mid_border)
    
    # Imprimir filas ordenadas por mayor cantidad de PDFs
    for directory, count in sorted(pdf_counts.items(), key=lambda x: (-x[1], x[0])):
        print(row_format.format(directory, count))
        
    # Imprimir final con el total
    print(mid_border)
    print(row_format.format("TOTAL", total_pdfs))
    print(bot_border)

if __name__ == "__main__":
    # Usamos el directorio padre de 'files' asumiendo que el script corre desde root o dentro de files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    
    print(f"\nBuscando PDFs en: {project_root}\n")
    counts, total = count_pdfs_by_folder(project_root)
    print_tabulated(counts, total)
    print("\n")
