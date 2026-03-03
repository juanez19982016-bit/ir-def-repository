#!/usr/bin/env python3
"""
Orquesta la organización de archivos dentro del Drive dividiéndolos en subcarpetas
por Marca/Modelo para IRs, Amps, Pedales y Plataforma para Presets.
Cero descarga requerida, solo operaciones de 'rclone move' en el servidor de Drive.
"""
import os
import subprocess
import json
import re

REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")
SRC_IR = f"{REMOTE}/01_GABINETES_IRs_GUITARRA"
SRC_PRESETS = f"{REMOTE}/04_PRESETS_MULTI_EFECTOS"
SRC_NAM_AMPS = f"{REMOTE}/02_AMPLIFICADORES_NAM"
SRC_NAM_PEDALS = f"{REMOTE}/03_PEDALES_BOUTIQUE_NAM"

BRANDS_IR = {
    "01_Marshall": [r"marshall", r"jcm", r"jvm", r"plexi", r"1959", r"1987", r"2203", r"2204", r"dsl", r"jmp"],
    "02_Mesa_Boogie": [r"mesa", r"boogie", r"rectifier", r"recto", r"dual.?rec", r"triple.?rec", r"mark\.*[iv]"],
    "03_Fender": [r"fender", r"twin", r"deluxe", r"bassman", r"princeton", r"champ", r"vibrolux"],
    "04_Orange": [r"orange", r"rockerverb", r"thunderverb", r"tiny.?terror"],
    "05_Peavey_y_EVH": [r"peavey", r"5150", r"6505", r"invective", r"\bevh\b"],
    "06_Bogner_y_Diezel": [r"bogner", r"uberschall", r"ecstasy", r"shiva", r"diezel", r"herbert", r"vh4"],
    "07_Vox": [r"vox", r"ac.?30", r"ac.?15"],
    "08_Friedman_y_Soldano": [r"friedman", r"be.?100", r"dirty.?shirley", r"soldano", r"slo"],
    "09_Engl": [r"engl", r"powerball", r"fireball", r"savage"],
    "10_Boutique_y_Otros": [r"two.?rock", r"matchless", r"dr.?z", r"dumble", r"suhr", r"victory", r"laney", r"revv"],
    "99_Otras_Marcas": [r".*"]
}

PLATFORMS_PRESETS = {
    "01_Line6_Helix": [r"\.hlx$"],
    "02_Fractal_Audio": [r"\.syx$"],
    "03_Boss_Katana_y_GT": [r"\.tsl$"],
    "04_Hotone_Ampero": [r"\.txp$", r"\.prst$"],
    "05_Mooer": [r"\.mo$"],
    "06_Zoom": [r"\.zd2$"],
    "07_Kemper": [r"\.kipr$"],
    "08_Line6_PodGo": [r"\.pgp$"],
    "09_Headrush": [r"\.rig$"],
    "99_Otras_Plataformas": [r".*"]
}

BRANDS_NAM_AMPS = {
    "01_Marshall": [r"\bmarshall\b", r"\bjcm\b", r"\bjvm\b", r"\bplexi\b", r"1959", r"1987", r"2203"],
    "02_Mesa_Boogie": [r"\bmesa\b", r"\bboogie\b", r"rectifier", r"recto", r"dual.?rec", r"mark\.*[iv]"],
    "03_Fender": [r"\bfender\b", r"twin", r"deluxe", r"bassman", r"princeton"],
    "04_Orange": [r"\borange\b", r"rockerverb", r"terror", r"th30"],
    "05_Peavey_y_EVH": [r"\bpeavey\b", r"5150", r"6505", r"\bevh\b"],
    "06_Bogner_y_Diezel": [r"bogner", r"uberschall", r"diezel", r"vh4", r"herbert"],
    "07_Vox_y_Matchless": [r"\bvox\b", r"ac.?30", r"matchless"],
    "08_Friedman_y_Soldano": [r"friedman", r"be.?100", r"soldano", r"slo"],
    "09_Engl_y_Revv": [r"\bengl\b", r"powerball", r"\brevv\b"],
    "10_Boutique_y_Otros": [r"fortin", r"two.?rock", r"dr.?z", r"dumble", r"suhr", r"victory", r"laney", r"carvin"],
    "99_Otras_Marcas": [r".*"]
}

TYPES_NAM_PEDALS = {
    "01_Overdrives_y_Boosts": [r"overdrive", r"tube.?screamer", r"ts9", r"ts808", r"klon", r"centaur", r"plumes", r"sd-?1", r"od-?1", r"boost", r"timmy", r"precision"],
    "02_Distorsiones": [r"distortion", r"\brat\b", r"ds-?1", r"metal.?zone", r"mt-?2", r"hm-?2", r"shredmaster", r"riot", r"be-od"],
    "03_Fuzzes": [r"fuzz", r"muff", r"tone.?bender", r"zvex", r"factory"],
    "04_Preamps_y_EQs": [r"preamp", r"eq", r"equalizer", r"sansamp", r"b7k", r"darkglass", r"microtubes"],
    "99_Otros_Pedales": [r".*"]
}


def get_category(filename, rules):
    fn = filename.lower()
    for cat, patterns in rules.items():
        if cat.startswith("99"): continue
        for p in patterns:
            if re.search(p, fn):
                return cat
    return list(rules.keys())[-1]

def process_folder(srcpath, rules):
    print(f"\n=============================================")
    print(f"Analizando {srcpath}...")
    
    # lsjson only files on root level (max-depth 1)
    res = subprocess.run(
        ["rclone", "lsjson", srcpath, "--files-only", "--max-depth", "1"], 
        capture_output=True, text=True
    )
    if res.returncode != 0:
        print(f"Error listando {srcpath}: {res.stderr}")
        return

    try:
        files = json.loads(res.stdout)
    except:
        print("Error parseando JSON de rclone")
        return
        
    if not files:
        print("No hay archivos en la raiz para mover.")
        return

    mapping = {k: [] for k in rules.keys()}
    
    for f in files:
        name = f["Path"]
        cat = get_category(name, rules)
        mapping[cat].append(name)
        
    for cat, flist in mapping.items():
        if not flist: continue
        print(f"  -> Moviendo {len(flist):>5} archivos a {cat}...")
        
        list_file = f"/tmp/list_{cat.replace(' ', '_')}.txt"
        with open(list_file, "w", encoding="utf-8") as out:
            for n in flist:
                out.write(n + "\n")
                
        dest = f"{srcpath}/{cat}"
        
        subprocess.run([
            "rclone", "move", srcpath, dest, 
            "--files-from", list_file, 
            "--transfers", "16",
            "--drive-server-side-across-configs=true",
            "--fast-list"
        ])
        
        os.unlink(list_file)

if __name__ == "__main__":
    os.makedirs("/tmp", exist_ok=True)
    process_folder(SRC_IR, BRANDS_IR)
    process_folder(SRC_PRESETS, PLATFORMS_PRESETS)
    process_folder(SRC_NAM_AMPS, BRANDS_NAM_AMPS)
    process_folder(SRC_NAM_PEDALS, TYPES_NAM_PEDALS)
    print("\n✅ Sub-categorización masiva finalizada!")
