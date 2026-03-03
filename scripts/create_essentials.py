import os
import subprocess
import json
import random

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")
DEST = f"{REMOTE}/00_EMPIEZA_AQUI/⭐_LOS_50_IMPRESCINDIBLES_GUIA_RAPIDA"

# Búsqueda con palabras clave para encontrar lo mejor de lo mejor
SEARCHES = [
    (f"{REMOTE}/01_GABINETES_IRs_GUITARRA", "marshall", 5),
    (f"{REMOTE}/01_GABINETES_IRs_GUITARRA", "mesa", 5),
    (f"{REMOTE}/01_GABINETES_IRs_GUITARRA", "fender", 5),
    (f"{REMOTE}/02_AMPLIFICADORES_NAM", "jcm", 5),
    (f"{REMOTE}/02_AMPLIFICADORES_NAM", "twin", 5),
    (f"{REMOTE}/03_PEDALES_BOUTIQUE_NAM", "klon", 3),
    (f"{REMOTE}/03_PEDALES_BOUTIQUE_NAM", "ts9", 3),
    (f"{REMOTE}/03_PEDALES_BOUTIQUE_NAM", "rat", 3),
    (f"{REMOTE}/04_PRESETS_MULTI_EFECTOS", "helix", 3),
    (f"{REMOTE}/04_PRESETS_MULTI_EFECTOS", "fractal", 3),
    (f"{REMOTE}/05_BAJO_Y_ACUSTICA", "ampeg", 5),
    (f"{REMOTE}/06_REVERBS_DE_ESTUDIO", "hall", 5),
]

selected_files = []

for base_dir, query, count in SEARCHES:
    res = subprocess.run(
        ["rclone", "lsf", base_dir, "--recursive", "--files-only", "--include", f"*{query}*"],
        capture_output=True, text=True
    )
    if res.returncode == 0:
        lines = [x.strip() for x in res.stdout.split('\n') if x.strip()]
        if lines:
            # Seleccionar algunos aleatorios de los resultados
            chosen = random.sample(lines, min(count, len(lines)))
            for c in chosen:
                # lsf devuelve el path relativo a base_dir
                # Necesitamos pasarlo relativo al REMOTE raíz para usar un solo comando rclone si usamos files-from,
                # o podemos simplemente copiar cada uno. Dado que son pocos, hacemos rclone copy directo o armamos una lista.
                
                # Para files-from, la ruta debe ser relativa al source dictado en rclone copy.
                # Si SOURCE = REMOTE, el path es base_dir_relativo / c
                # base_dir_relativo: sacamos el REMOTE/
                rel_base = base_dir.replace(f"{REMOTE}/", "")
                full_rel_path = f"{rel_base}/{c}"
                selected_files.append(full_rel_path)

if selected_files:
    print(f"Encontrados {len(selected_files)} archivos imprescindibles.")
    list_file = "/tmp/essentials_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for sf in selected_files:
            f.write(sf + "\n")
            
    print("Copiando a la carpeta de imprescindibles dentro de Google Drive...")
    subprocess.run([
        "rclone", "copy", REMOTE, DEST,
        "--files-from", list_file,
        "--drive-server-side-across-configs=true",
        "--transfers", "8"
    ])
    
    # Crear un PDF dummy de guía (se puede subir uno real después)
    with open("/tmp/LEER_GUIA_RAPIDA.txt", "w", encoding="utf-8") as f:
        f.write("¡Bienvenido a TONEHUB PRO 2.0!\n\n")
        f.write("Aquí hemos agrupado 50 de los mejores archivos para que no tengas que buscar entre los más de 16,000 que incluye el pack.\n")
        f.write("Prueba estos archivos primero para asegurarte de la calidad del paquete completo.\n\n")
        f.write("- Usa los archivos .wav en tu plugin cargador de IR (Pulse, NadIR, Helix Native).\n")
        f.write("- Usa los archivos .nam en Neural Amp Modeler.\n")
        
    subprocess.run(["rclone", "copyto", "/tmp/LEER_GUIA_RAPIDA.txt", f"{DEST}/LEER_GUIA_RAPIDA.txt"])
    print("✅ Carpeta de imprescindibles creada exitosamente.")
else:
    print("No se encontraron archivos.")
