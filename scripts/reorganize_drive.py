import subprocess
import time

RCLONE_REMOTE = "gdrive2:IR_DEF_REPOSITORY"

MOVES = [
    # Crear la carpeta de inicio
    ("mkdir", f"{RCLONE_REMOTE}/00_EMPIEZA_AQUI"),
    
    # Renombrar carpetas principales
    ("moveto", f"{RCLONE_REMOTE}/IR_Guitarra", f"{RCLONE_REMOTE}/01_GABINETES_IRs_GUITARRA"),
    ("moveto", f"{RCLONE_REMOTE}/NAM_Capturas", f"{RCLONE_REMOTE}/02_AMPLIFICADORES_NAM"),
    ("moveto", f"{RCLONE_REMOTE}/04_BOUTIQUE_PEDALS_NAM", f"{RCLONE_REMOTE}/03_PEDALES_BOUTIQUE_NAM"),
    ("moveto", f"{RCLONE_REMOTE}/03_PRESETS_AND_MODELERS", f"{RCLONE_REMOTE}/04_PRESETS_MULTI_EFECTOS"),
    
    # Combinar Bajo y Acústica
    ("mkdir", f"{RCLONE_REMOTE}/05_BAJO_Y_ACUSTICA"),
    ("move", f"{RCLONE_REMOTE}/IR_Bajo", f"{RCLONE_REMOTE}/05_BAJO_Y_ACUSTICA/Bajo"),
    ("move", f"{RCLONE_REMOTE}/IR_Acustica", f"{RCLONE_REMOTE}/05_BAJO_Y_ACUSTICA/Acustica"),
    
    # Renombrar utilidades
    ("moveto", f"{RCLONE_REMOTE}/IR_Utilidades", f"{RCLONE_REMOTE}/06_REVERBS_DE_ESTUDIO")
]

print("Iniciando reorganización premium del Drive en Español...")

for action in MOVES:
    cmd_type = action[0]
    
    if cmd_type == "mkdir":
        path = action[1]
        print(f"Creando: {path}")
        subprocess.run(["rclone", "mkdir", path])
    
    elif cmd_type == "moveto":
        src, dest = action[1], action[2]
        print(f"Renombrando: {src} -> {dest}")
        subprocess.run(["rclone", "moveto", src, dest])
        
    elif cmd_type == "move":
        src, dest = action[1], action[2]
        print(f"Moviendo contenido: {src} -> {dest}")
        subprocess.run(["rclone", "move", src, dest])

print("✅ Reorganización básica de carpetas completada.")
