#!/usr/bin/env python3
"""
MEGA DOWNLOADER v3 — Clean + Expand
=====================================
1. CLEANUP: Removes junk files from Drive (non .wav/.nam, corrupted, dupes, metadata)
2. EXPAND: Downloads from 100+ verified sources

All runs on GitHub Actions. Zero local bandwidth.
Uploads to gdrive2:IR_DEF_REPOSITORY.
"""
import os, sys, json, re, time, hashlib, zipfile, struct, shutil, logging, argparse, subprocess
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============ CONFIG ============
BASE_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/ir_repository"))
CACHE_FILE = BASE_DIR / ".download_cache.json"
LOG_FILE = BASE_DIR / ".download.log"
VALID_EXT = {".wav", ".nam"}
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive2:IR_DEF_REPOSITORY")
MAX_WORKERS = 6

# Junk patterns — files to delete from Drive
JUNK_EXTENSIONS = {
    ".json", ".log", ".md", ".txt", ".py", ".yml", ".yaml", ".csv", ".html",
    ".xml", ".cfg", ".ini", ".toml", ".sh", ".bat", ".ps1", ".gitignore",
    ".gitattributes", ".git", ".ds_store", ".thumbs.db", ".desktop",
    ".exe", ".dll", ".so", ".dylib", ".pkg", ".dmg", ".msi", ".deb", ".rpm",
    ".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
    ".mp3", ".mp4", ".mkv", ".avi", ".mov", ".flac", ".ogg", ".aac", ".m4a",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    ".js", ".ts", ".jsx", ".tsx", ".css", ".scss", ".less", ".vue",
    ".h", ".c", ".cpp", ".hpp", ".java", ".rb", ".go", ".rs", ".swift",
    ".plist", ".nfo", ".url", ".lnk", ".rtf",
}

JUNK_FILENAMES = {
    ".download_cache.json", ".download.log", ".stats.json", "README.md",
    ".gitignore", ".gitattributes", "LICENSE", "LICENSE.md", "LICENSE.txt",
    "CHANGELOG.md", "CONTRIBUTING.md", "Makefile", "CMakeLists.txt",
    "package.json", "requirements.txt", "setup.py", "Dockerfile",
    ".DS_Store", "Thumbs.db", "desktop.ini",
}

# ============ LOGGING ============
def setup():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

# ============ SESSION ============
def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]),
        pool_maxsize=20
    ))
    s.mount("http://", HTTPAdapter(
        max_retries=Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503]),
        pool_maxsize=10
    ))
    s.headers.update({"User-Agent": "IR-DEF-Mega/3.0", "Accept-Encoding": "gzip, deflate"})
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s

# ============ CACHE ============
class Cache:
    def __init__(self):
        self.data = {"urls": [], "hashes": {}}
        if CACHE_FILE.exists():
            try:
                self.data = json.loads(CACHE_FILE.read_text("utf-8"))
            except:
                pass

    def save(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.data), "utf-8")

    def seen(self, url):
        return url in self.data["urls"]

    def seen_any(self, *keys):
        """Check if ANY of the given keys have been seen (for backwards compat)."""
        for k in keys:
            if k in self.data["urls"]:
                return True
        return False

    def mark(self, url):
        if url not in self.data["urls"]:
            self.data["urls"].append(url)

    def is_dup(self, filepath):
        h = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
        if h in self.data["hashes"]:
            return True
        self.data["hashes"][h] = str(filepath)
        return False

    def reset_for_expansion(self):
        """Clear only the URL cache (not hashes) to re-download from same sources."""
        self.data["urls"] = []

# ============ VALIDATION ============
def is_valid_wav(path):
    try:
        with open(path, "rb") as f:
            h = f.read(12)
            if len(h) < 12:
                return False
            r, _, w = struct.unpack("<4sI4s", h)
            return r == b"RIFF" and w == b"WAVE"
    except:
        return False

def is_valid(path):
    p = Path(path)
    try:
        if p.stat().st_size < 100:
            return False
    except:
        return False
    if p.suffix.lower() == ".wav":
        return is_valid_wav(p)
    return p.suffix.lower() == ".nam"

# ============ BRAND DETECTION ============
BRANDS = {
    "Marshall": [r"marshall", r"jcm", r"jvm", r"plexi", r"1959", r"1987", r"2203", r"2204", r"dsl", r"jmp"],
    "Fender": [r"fender", r"twin", r"deluxe.reverb", r"bassman", r"princeton", r"champ", r"vibrolux"],
    "Mesa": [r"mesa", r"boogie", r"rectifier", r"recto", r"dual.rec", r"triple.rec", r"mark.(iv|v|ii|iii)", r"lonestar"],
    "Vox": [r"vox", r"ac.?30", r"ac.?15"],
    "Orange": [r"orange", r"rockerverb", r"thunderverb", r"tiny.terror"],
    "Peavey": [r"peavey", r"5150", r"6505", r"invective"],
    "EVH": [r"\bevh\b", r"stealth"],
    "Bogner": [r"bogner", r"uberschall", r"ecstasy", r"shiva"],
    "Soldano": [r"soldano", r"slo"],
    "Diezel": [r"diezel", r"herbert", r"vh4"],
    "Friedman": [r"friedman", r"be.?100", r"dirty.shirley", r"butterslax"],
    "Engl": [r"engl", r"powerball", r"fireball", r"savage"],
    "Ampeg": [r"ampeg", r"svt", r"b-?15", r"portaflex"],
    "Darkglass": [r"darkglass", r"b7k"],
    "Hiwatt": [r"hiwatt"],
    "Suhr": [r"\bsuhr\b", r"badger"],
    "Hughes_Kettner": [r"hughes.*kettner", r"triamp", r"tubemeister"],
    "Laney": [r"laney", r"ironheart"],
    "Revv": [r"\brevv\b", r"generator"],
    "Victory": [r"victory", r"kraken"],
    "Celestion": [r"celestion", r"v30", r"vintage.30", r"greenback", r"creamback", r"g12", r"alnico"],
    "Eminence": [r"eminence", r"swamp.thang", r"legend"],
    "Jensen": [r"jensen"],
    "Randall": [r"randall", r"satan"],
    "Blackstar": [r"blackstar", r"ht.?club"],
    "Two_Rock": [r"two.rock"],
    "Matchless": [r"matchless", r"dc.?30"],
    "Dr_Z": [r"dr.?z", r"maz"],
    "Dumble": [r"dumble", r"overdrive.special"],
    "Trainwreck": [r"trainwreck"],
    "Rivera": [r"rivera"],
    "Kemper": [r"kemper"],
    "Line6": [r"line.?6", r"helix", r"pod"],
    "Boss": [r"\bboss\b", r"katana"],
    "TC_Electronic": [r"tc.electronic"],
}
CABS = {"1x12": [r"1x12"], "2x12": [r"2x12"], "4x12": [r"4x12"], "4x10": [r"4x10"], "8x10": [r"8x10"], "1x15": [r"1x15"]}
MICS = {"SM57": [r"sm57"], "MD421": [r"md421"], "R121": [r"r121", r"royer"], "U87": [r"u87"], "E609": [r"e609"]}

def _match(text, patterns):
    t = text.lower()
    for key, pats in patterns.items():
        for p in pats:
            if re.search(p, t):
                return key
    return None

def categorize(context, filename):
    c = (context + " " + filename).lower()
    ext = Path(filename).suffix.lower()
    if ext == ".nam":
        return "NAM_Capturas"
    if any(k in c for k in ["bass", "bajo", "svt", "ampeg", "darkglass", "8x10", "4x10", "b-15", "b15", "portaflex"]):
        return "IR_Bajo"
    if any(k in c for k in ["acoustic", "piezo", "electroac", "taylor", "martin", "nylon", "body"]):
        return "IR_Acustica"
    if any(k in c for k in ["reverb", "room", "hall", "plate", "spring", "echo", "ambient", "space", "convol"]):
        return "IR_Utilidades"
    return "IR_Guitarra"

def clean_filename(context, filename):
    """
    Genera un nombre estandarizado: Marca_Modelo_Cabina_Mic_Info.
    Si no detecta info relevante, usa el nombre del Pack/Repo como prefijo.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    
    # Pre-limpieza del stem
    stem = re.sub(r"[\(\)\[\]]", "", stem) # Quitar parentesis/corchetes
    stem = stem.replace(" ", "_").replace("-", "_").replace(".", "_")
    
    # Contexto completo para busqueda (nombre archivo + carpeta padre + nombre repo)
    full_context = (context + "_" + stem).lower()
    
    parts = []

    # 1. DETECTAR MARCA (Prioridad Alta)
    brand = _match(full_context, BRANDS)
    if brand:
        parts.append(brand)
    
    # 2. DETECTAR MODELO (Agresivo)
    # Buscamos patrones comunes de amplis/pedales
    model_patterns = [
        (r"(JCM\s*?800|JCM\s*?900|JCM\s*?2000)", "JCM"),
        (r"(Dual\s*?Rect|Triple\s*?Rect|Recto)", "Rectifier"),
        (r"(5150|6505)", "5150"),
        (r"(AC\s*?30|AC\s*?15)", "VoxAC"),
        (r"(Twin|Deluxe|Princeton|Bassman)", "Fender"),
        (r"(SVT|B15)", "Ampeg"),
        (r"(Plexi|1959|1987)", "Plexi"),
        (r"(Uberschall|Ecstasy)", "Bogner"),
        (r"(VH4|Herbert)", "Diezel"),
        (r"(BE\s*?100|HBE)", "FriedmanBE"),
        (r"(Satan|Thrasher)", "Randall"),
    ]
    
    for pat, label in model_patterns:
        if re.search(pat, full_context, re.I):
            if label not in parts and (not brand or brand not in label): 
                parts.append(label)
            break

    # 3. CABINA (1x12, 4x12, etc)
    cab = _match(full_context, CABS)
    if cab:
        parts.append(cab)

    # 4. MICROFONO
    mic = _match(full_context, MICS)
    if mic:
        parts.append(mic)

    # 5. TONO / CANAL
    if re.search(r"(high|hi).?gain|metal|lead|dist|ch3|red", full_context):
        parts.append("HiGain")
    elif re.search(r"crunch|drive|breakup|ch2|orange", full_context):
        parts.append("Crunch")
    elif re.search(r"clean|jazz|ch1|green", full_context):
        parts.append("Clean")

    # 6. INSTANCIA DE RESPALDO (Si no hay mucha info)
    # Si tenemos muy pocas partes, usamos limpiamente el nombre original o el de la carpeta
    if len(parts) < 2:
        # Extraer palabras clave del nombre original que no sean basura
        clean_stem = re.sub(r"(ir|demo|test|v[0-9]|final|mix|wav|nam|capture|profile|rig)", "", stem, flags=re.I)
        clean_stem = re.sub(r"_+", "_", clean_stem).strip("_")
        
        # Si el nombre quedo muy corto (ej: "01"), traemos el nombre de la carpeta padre
        if len(clean_stem) < 3:
            parent = Path(context).parent.name if "/" in context else context
            parent = re.sub(r"[^a-zA-Z0-9]", "", parent)
            clean_stem = f"{parent}_{clean_stem}"
            
        parts.append(clean_stem[:40]) # Limite de caracteres para evitar nombres kilometricos

    # Ensamblar y limpiar final
    final_name = "_".join(parts)
    final_name = re.sub(r"_+", "_", final_name).strip("_")
    
    # Capitalizar estilo Titulo (Marshall_Jcm800...)
    final_name = "_".join([p.capitalize() for p in final_name.split("_")])

    return f"{final_name}{suffix}"

def organize_file(src_path, context=""):
    fn = Path(src_path).name
    cat = categorize(context or str(src_path), fn)
    dest_dir = BASE_DIR / cat
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = clean_filename(context or str(src_path), fn)
    dest = dest_dir / name
    if dest.exists():
        s, x = Path(name).stem, Path(name).suffix
        i = 1
        while dest.exists():
            dest = dest_dir / f"{s}_{i}{x}"
            i += 1
    shutil.copy2(src_path, dest)
    return dest

# ============================================================
# CLEANUP: Delete junk from Google Drive
# ============================================================
def cleanup_drive():
    """Delete all non-.wav/.nam files from the Drive remote."""
    logging.info("=" * 60)
    logging.info("🧹 CLEANUP: Removing junk files from Drive")
    logging.info("=" * 60)

    deleted = 0
    errors = 0

    # 1. Delete known junk files at root level
    junk_root_files = [
        ".download_cache.json", ".download.log", ".stats.json", "README.md"
    ]
    for jf in junk_root_files:
        try:
            result = subprocess.run(
                ["rclone", "deletefile", f"{RCLONE_REMOTE}/{jf}"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logging.info(f"  🗑️  Deleted root: {jf}")
                deleted += 1
            else:
                logging.debug(f"  Skip {jf}: {result.stderr.strip()[:80]}")
        except:
            pass

    # 2. Delete all non-wav/non-nam files from every folder
    for ext in list(JUNK_EXTENSIONS):
        try:
            result = subprocess.run(
                ["rclone", "delete", RCLONE_REMOTE,
                 "--include", f"*{ext}",
                 "--verbose"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0 and result.stderr.strip():
                # Count deleted lines
                del_lines = [l for l in result.stderr.split("\n") if "Deleted" in l or "deleted" in l]
                if del_lines:
                    logging.info(f"  🗑️  Deleted {len(del_lines)} *{ext} files")
                    deleted += len(del_lines)
        except:
            pass

    # 3. Delete hidden/dot files
    for pattern in [".*", "__*"]:
        try:
            subprocess.run(
                ["rclone", "delete", RCLONE_REMOTE, "--include", pattern],
                capture_output=True, text=True, timeout=60
            )
        except:
            pass

    # 4. Cleanup empty directories
    try:
        subprocess.run(
            ["rclone", "rmdirs", RCLONE_REMOTE],
            capture_output=True, text=True, timeout=60
        )
    except:
        pass

    logging.info(f"  ✅ Cleanup done: ~{deleted} junk items removed")
    return deleted

def cleanup_local():
    """Delete invalid files from local download directory."""
    logging.info("🧹 Cleaning local files...")
    valid = invalid = junk = dup_count = 0
    seen_hashes = set()

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            fp = Path(root) / f
            ext = fp.suffix.lower()

            # Delete junk extensions
            if ext in JUNK_EXTENSIONS or fp.name in JUNK_FILENAMES:
                fp.unlink(missing_ok=True)
                junk += 1
                continue

            # Skip non-audio
            if ext not in VALID_EXT:
                fp.unlink(missing_ok=True)
                junk += 1
                continue

            # Validate audio
            if not is_valid(fp):
                fp.unlink(missing_ok=True)
                invalid += 1
                continue

            # Deduplicate
            try:
                h = hashlib.sha256(fp.read_bytes()).hexdigest()
                if h in seen_hashes:
                    fp.unlink(missing_ok=True)
                    dup_count += 1
                    continue
                seen_hashes.add(h)
            except:
                pass

            valid += 1

    logging.info(f"  Local cleanup: valid={valid}, invalid={invalid}, junk={junk}, dupes={dup_count}")
    return {"valid": valid, "invalid": invalid, "junk": junk, "dupes": dup_count}

# ============================================================
# GITHUB REPOS — 100+ verified sources
# ============================================================
REPOS = [
    # === NAM Models — HUGE collections ===
    "pelennor2170/NAM_models",
    "mikeoliphant/NeuralAmpModels",
    "markusaksli-nc/nam-models",
    "BenjaminAbt/neural-amp-models",
    "NickHilburn/NAM_captures",
    "DaveFarmerUK/NAM_captures",
    "davedude0/NeuralAmpModelerModels",
    "Pilkch/nam-models",
    "grrrwaaa/nam-models",
    "0x01h/nam-models",
    "jrialland/nam-models",
    "maxb2/nam-stuff",
    "tstalka/nam-models",
    "Dhalion/NAM-Captures",
    "j4de/NAM-Models",
    "mfmods/mf-nam-models",
    "tansey-sern/NAM_Community_Models",
    "voidstar78/NAM-Captures",
    "thomjames/NAMCaptures",
    "DoomMuffin/NAM-Models",
    "LevDev/NAMCaptures",
    "TheBlackPlague/NeuralAmpModels",
    "screamingFrog/NAM-packs",
    "GroovyAppliance/NAM-Captures",
    "Mike-Moat/NAM-Models",

    # === NAM — extra community ===
    "bwhitman/clern",
    "audiofab/ir-packs",
    "CabIR-Guitar/community-irs",
    "ampsim-ir/free-collection",
    "ashtinstruments/IRs",
    "IbanezEd/NAM-Models",
    "robrohan/nam",
    "mlp-s/nam-models",
    "edcorners/nam-captures",
    "Vince-VDR/NAM-Models",
    "Xalyr/NAM-Captures",
    "pablojrl/NAM-models",
    "Rhijul/NAM",
    "AndWeAreN0thing/NAM_Captures",
    "DanielMPires/nam-models",
    "Makarov96/nam-captures",
    "NellielOwens/NAM-Models",
    "SamSche/NAM",
    "RyanKnack/NAM_files",
    "eostrov/NAM-models",

    # === IR Collections (verified real captures) ===
    "orodamaral/Speaker-Cabinets-IRs",
    "keyth72/AxeFxImpulseResponses",
    "studioroberto/guitar-impulse-responses",
    "TomSchrier/CabIRs",
    "mikemcd3/IR-Cabs",
    "romancardenas/guitar-cabinet-ir",
    "DirtyThirtyIRs/IR-Collection",
    "ImpulseRecords/impulse-responses-free",

    # === GuitarML ecosystem (well-maintained) ===
    "GuitarML/ToneLibrary",
    "GuitarML/Proteus",
    "GuitarML/SmartGuitarAmp",
    "GuitarML/SmartGuitarPedal",
    "GuitarML/SmartAmpPro",
    "GuitarML/TS-M1N3",
    "GuitarML/Chameleon",
    "GuitarML/GuitarLSTM",
    "GuitarML/NeuralPi",

    # === Amp modeling / research ===
    "sdatkinson/neural-amp-modeler",
    "Alec-Wright/Automated-GuitarAmpModelling",
    "Alec-Wright/CoreAudioML",
    "AidaDSP/AIDA-X",
    "sdatkinson/NeuralAmpModelerPlugin",
    "jatinchowdhury18/KlonCentaur",
    "jatinchowdhury18/AnalogTapeModel",
    "neural-amp-modeler/models-registry",

    # === Extra verified repos ===
    "DA1729/da1729_guitar_processor",
    "dijitol77/delt1",
    "dijitol77/delt",
    "turtelduo/helix",
    "elk-audio/elk-examples",
    "springrevrb/SpringReverb",

    # === New wave — discovered via search ===
    "JackMJones/nam-captures",
    "Seggino/NAM-Models",
    "Quist/IR",
    "kailincoborn/NAM-models",
    "MStiffworthy/NAM-Captures",
    "zach-goh/nam-captures",
    "LjutaPapworka/NAM_Models",
    "Flabadac/NAM_Models",
    "richi-perez/NAM-Captures",
    "shumway10/NAM-Models",
    "defsyndicate/Guitar-IRs",
    "juhomi/nam-models",
    "andradesilvestre/NAM-captures",
    "fabiomilheiro/nam-models",
    "the-drunk-coder/nam-models",
    "remisonfire/nam-models",
    "Thibault-music/NAM-captures",
    "BorisTheBear/NAMModels",
    "jshawdev/nam-models",
]

RELEASE_REPOS = [
    ("GuitarML", "Proteus"),
    ("GuitarML", "TS-M1N3"),
    ("GuitarML", "Chameleon"),
    ("GuitarML", "SmartGuitarAmp"),
    ("GuitarML", "NeuralPi"),
    ("mikeoliphant", "NeuralAmpModels"),
    ("AidaDSP", "AIDA-X"),
    ("sdatkinson", "neural-amp-modeler"),
    ("sdatkinson", "NeuralAmpModelerPlugin"),
    ("jatinchowdhury18", "KlonCentaur"),
    ("jatinchowdhury18", "AnalogTapeModel"),
    ("GuitarML", "SmartAmpPro"),
    ("GuitarML", "GuitarLSTM"),
]

# ============================================================
# DIRECT ZIP DOWNLOADS — Massively expanded, verified URLs
# ============================================================
DIRECT_ZIPS = [
    # === Voxengo (free reverb/space IRs — ALL of them) ===
    ("https://www.voxengo.com/files/impulses/IMreverbs.zip", "Voxengo_Reverb"),
    ("https://www.voxengo.com/files/impulses/BrightHall.zip", "Voxengo_BrightHall"),
    ("https://www.voxengo.com/files/impulses/Parking_garage.zip", "Voxengo_Parking"),
    ("https://www.voxengo.com/files/impulses/SquareVictorianRoom.zip", "Voxengo_Victorian"),
    ("https://www.voxengo.com/files/impulses/Large_bottle_hall.zip", "Voxengo_BottleHall"),
    ("https://www.voxengo.com/files/impulses/In_the_silo_revised.zip", "Voxengo_Silo"),
    ("https://www.voxengo.com/files/impulses/Nice_drum_room.zip", "Voxengo_DrumRoom"),
    ("https://www.voxengo.com/files/impulses/Right_glass_triangle.zip", "Voxengo_GlassTriangle"),
    ("https://www.voxengo.com/files/impulses/St_Nicolaes_church.zip", "Voxengo_Church"),
    ("https://www.voxengo.com/files/impulses/Masonic_lodge.zip", "Voxengo_MasonicLodge"),
    ("https://www.voxengo.com/files/impulses/Highly_damped_plate.zip", "Voxengo_DampedPlate"),
    ("https://www.voxengo.com/files/impulses/On_a_star.zip", "Voxengo_OnAStar"),
    ("https://www.voxengo.com/files/impulses/Rays.zip", "Voxengo_Rays"),
    ("https://www.voxengo.com/files/impulses/Bottle_hall.zip", "Voxengo_BottleHall2"),
    ("https://www.voxengo.com/files/impulses/Cinema_hall.zip", "Voxengo_CinemaHall"),
    ("https://www.voxengo.com/files/impulses/Direct_cabinet_n1-n4.zip", "Voxengo_DirectCab"),
    ("https://www.voxengo.com/files/impulses/Five_columns.zip", "Voxengo_FiveColumns"),
    ("https://www.voxengo.com/files/impulses/French_18th_century_salon.zip", "Voxengo_Salon"),
    ("https://www.voxengo.com/files/impulses/Going_home.zip", "Voxengo_GoingHome"),
    ("https://www.voxengo.com/files/impulses/Greek_7_echo_hall.zip", "Voxengo_GreekEcho"),
    ("https://www.voxengo.com/files/impulses/In_the_silo.zip", "Voxengo_Silo2"),
    ("https://www.voxengo.com/files/impulses/Large_long_echo_hall.zip", "Voxengo_LongEcho"),
    ("https://www.voxengo.com/files/impulses/Musikvereinsaal.zip", "Voxengo_Musikverein"),
    ("https://www.voxengo.com/files/impulses/Narrow_bumpy_space.zip", "Voxengo_NarrowBumpy"),
    ("https://www.voxengo.com/files/impulses/Scala_Milan_opera_hall.zip", "Voxengo_ScalaMilan"),
    ("https://www.voxengo.com/files/impulses/Small_drum_room.zip", "Voxengo_SmallDrum"),
    ("https://www.voxengo.com/files/impulses/Small_prehistoric_cave.zip", "Voxengo_Cave"),
    ("https://www.voxengo.com/files/impulses/Vocal_duo.zip", "Voxengo_VocalDuo"),

    # === Kalthallen (guitar cab IRs) ===
    ("https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "Kalthallen_Cabs"),

    # === EchoThief (real acoustic spaces — reverb IRs) ===
    ("http://www.echothief.com/downloads/EchoThiefImpulseResponseLibrary.zip", "EchoThief"),

    # === God's Cab — 700+ Mesa OS Rectifier IRs (via web archive) ===
    ("https://web.archive.org/web/20150325152659/http://www.signalsaudio.com/free/Gods_Cab_1.4.zip", "Gods_Cab_Mesa"),

    # === OpenAIR — University of York (academic quality reverb/room IRs) ===
    ("https://www.openair.hosted.york.ac.uk/wp-content/uploads/2021/01/openair_all.zip", "OpenAIR_All"),

    # === Voxengo — Additional collections ===
    ("https://www.voxengo.com/files/impulses/Tunnel.zip", "Voxengo_Tunnel"),
    ("https://www.voxengo.com/files/impulses/Large_wide_echo_hall.zip", "Voxengo_WideEcho"),
    ("https://www.voxengo.com/files/impulses/Conic_long_echo_hall.zip", "Voxengo_ConicEcho"),
    ("https://www.voxengo.com/files/impulses/Deep_space.zip", "Voxengo_DeepSpace"),
    ("https://www.voxengo.com/files/impulses/Inside_piano.zip", "Voxengo_InsidePiano"),
    ("https://www.voxengo.com/files/impulses/Chateau_de_Logne.zip", "Voxengo_ChateauLogne"),
    ("https://www.voxengo.com/files/impulses/Block_inside.zip", "Voxengo_BlockInside"),
    ("https://www.voxengo.com/files/impulses/Under_the_bridge.zip", "Voxengo_UnderBridge"),
    ("https://www.voxengo.com/files/impulses/Terry's_factory_warehouse.zip", "Voxengo_FactoryWarehouse"),
    ("https://www.voxengo.com/files/impulses/Ruby_room.zip", "Voxengo_RubyRoom"),
    ("https://www.voxengo.com/files/impulses/Trig_room.zip", "Voxengo_TrigRoom"),
    ("https://www.voxengo.com/files/impulses/Empty_apartment_bedroom.zip", "Voxengo_EmptyApt"),
    ("https://www.voxengo.com/files/impulses/On_a_star2.zip", "Voxengo_OnAStar2"),
    ("https://www.voxengo.com/files/impulses/1st_baptist_nashville.zip", "Voxengo_BaptistNashville"),
    ("https://www.voxengo.com/files/impulses/St_Andrews_Church.zip", "Voxengo_StAndrews"),

    # === Djammincabs (free community guitar + bass cab IRs) ===
    ("https://djammincabs.com/wp-content/uploads/2023/04/djammincabs_100_free_guitar_cabs.zip", "Djammincabs_Guitar_100"),
    ("https://djammincabs.com/wp-content/uploads/2023/04/djammincabs_100_free_bass_cabs.zip", "Djammincabs_Bass_100"),
    ("https://djammincabs.com/wp-content/uploads/2023/10/djammincabs_200_free_guitar_cabs.zip", "Djammincabs_Guitar_200"),
    ("https://djammincabs.com/wp-content/uploads/2023/10/djammincabs_200_free_bass_cabs.zip", "Djammincabs_Bass_200"),

    # === SNB Impulse Responses ===
    ("https://drive.google.com/uc?export=download&id=0BwA9sW5PdfKxUW5sTWk0NjM5Qzg", "SNB_IRs"),
]

# ============================================================
# DOWNLOADER FUNCTIONS
# ============================================================
def download_repo(session, cache, repo):
    if "/" not in repo:
        return 0
    owner, name = repo.split("/", 1)
    cache_key = f"v3_gh_{owner}_{name}"
    # Check all historical prefixes so we don't re-download
    if cache.seen_any(cache_key, f"mega_gh_{owner}_{name}", f"gh_{owner}_{name}", f"blitz_gh_{owner}_{name}"):
        return 0

    tmp_dir = Path("/tmp/mega_gh")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for branch in ["main", "master"]:
        zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
        zip_path = tmp_dir / f"{name}.zip"
        try:
            r = session.get(zip_url, stream=True, timeout=300)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            cl = int(r.headers.get("Content-Length", "0"))
            if cl > 500 * 1024 * 1024:
                cache.mark(cache_key)
                return 0
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)
            logging.info(f"Downloaded {owner}/{name} ({zip_path.stat().st_size/1e6:.1f}MB)")
            extract_dir = tmp_dir / name
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)
            except:
                zip_path.unlink(missing_ok=True)
                cache.mark(cache_key)
                return 0
            file_count = 0
            for root, dirs, files in os.walk(extract_dir):
                dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                for fn in files:
                    if Path(fn).suffix.lower() not in VALID_EXT:
                        continue
                    src = Path(root) / fn
                    try:
                        if not is_valid(src) or cache.is_dup(src):
                            continue
                        ctx = f"{name}/{os.path.relpath(root, extract_dir)}/{fn}"
                        organize_file(src, ctx)
                        file_count += 1
                    except:
                        pass
            logging.info(f"  → {file_count} files from {name}")
            cache.mark(cache_key)
            cache.save()
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
            return file_count
        except requests.exceptions.RequestException as e:
            if branch == "master":
                logging.warning(f"Skip {repo}: {e}")
                cache.mark(cache_key)
                return 0
    cache.mark(cache_key)
    return 0

def download_releases(session, cache, owner, repo_name):
    cache_key = f"v3_rel_{owner}_{repo_name}"
    # Check all historical prefixes
    if cache.seen_any(cache_key, f"mega_rel_{owner}_{repo_name}", f"rel_{owner}_{repo_name}", f"blitz_rel_{owner}_{repo_name}"):
        return 0
    try:
        r = session.get(
            f"https://api.github.com/repos/{owner}/{repo_name}/releases",
            timeout=30, headers={"Accept": "application/vnd.github+json"}
        )
        if r.status_code in (404, 403):
            cache.mark(cache_key)
            return 0
        r.raise_for_status()
        file_count = 0
        tmp = Path("/tmp/mega_rel")
        tmp.mkdir(parents=True, exist_ok=True)
        for rel in r.json()[:10]:
            for asset in rel.get("assets", []):
                url = asset["browser_download_url"]
                name = asset["name"]
                ext = Path(name).suffix.lower()
                if ext not in VALID_EXT and ext != ".zip":
                    continue
                if cache.seen(url):
                    continue
                try:
                    dr = session.get(url, stream=True, timeout=300)
                    dr.raise_for_status()
                    tp = tmp / name
                    with open(tp, "wb") as f:
                        for chunk in dr.iter_content(1024 * 1024):
                            f.write(chunk)
                    if ext == ".zip":
                        try:
                            xd = tmp / Path(name).stem
                            with zipfile.ZipFile(tp) as zf:
                                zf.extractall(xd)
                            for root, dirs, files in os.walk(xd):
                                dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                                for fn in files:
                                    if Path(fn).suffix.lower() not in VALID_EXT:
                                        continue
                                    src = Path(root) / fn
                                    if is_valid(src) and not cache.is_dup(src):
                                        organize_file(src, f"rel/{repo_name}/{fn}")
                                        file_count += 1
                            shutil.rmtree(xd, ignore_errors=True)
                        except:
                            pass
                    elif is_valid(tp) and not cache.is_dup(tp):
                        organize_file(tp, f"rel/{repo_name}/{name}")
                        file_count += 1
                    tp.unlink(missing_ok=True)
                    cache.mark(url)
                except:
                    pass
        logging.info(f"Releases {owner}/{repo_name}: {file_count} files")
        cache.mark(cache_key)
        cache.save()
        return file_count
    except Exception as e:
        logging.warning(f"Releases {owner}/{repo_name}: {e}")
        cache.mark(cache_key)
        return 0

def download_direct_zip(session, cache, url, name):
    if cache.seen(url):
        return 0
    tmp = Path("/tmp/mega_direct")
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        r = session.get(url, stream=True, timeout=300, allow_redirects=True)
        if r.status_code in (404, 403, 410):
            cache.mark(url)
            return 0
        r.raise_for_status()
        cd = r.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            fn_match = re.findall(r'filename="?([^";\n]+)', cd)
            fn = fn_match[0] if fn_match else f"{name}.zip"
        else:
            fn = unquote(urlparse(url).path.split("/")[-1]) or f"{name}.zip"
        download_path = tmp / fn
        with open(download_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
        logging.info(f"Direct: {name} ({download_path.stat().st_size/1e6:.1f}MB)")
        file_count = 0
        if download_path.suffix.lower() == ".zip":
            extract_dir = tmp / name
            try:
                with zipfile.ZipFile(download_path) as zf:
                    zf.extractall(extract_dir)
            except zipfile.BadZipFile:
                download_path.unlink(missing_ok=True)
                cache.mark(url)
                return 0
            for root, dirs, files in os.walk(extract_dir):
                dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                for fn in files:
                    if Path(fn).suffix.lower() not in VALID_EXT:
                        continue
                    src = Path(root) / fn
                    try:
                        if is_valid(src) and not cache.is_dup(src):
                            organize_file(src, f"{name}/{os.path.relpath(root, extract_dir)}/{fn}")
                            file_count += 1
                    except:
                        pass
            shutil.rmtree(extract_dir, ignore_errors=True)
        elif is_valid(download_path) and not cache.is_dup(download_path):
            organize_file(download_path, f"direct/{name}/{fn}")
            file_count += 1
        download_path.unlink(missing_ok=True)
        logging.info(f"  → {file_count} from {name}")
        cache.mark(url)
        cache.save()
        return file_count
    except Exception as e:
        logging.error(f"Direct {name}: {e}")
        cache.mark(url)
        return 0

def github_search_discover(session, cache):
    queries = [
        "impulse response guitar cabinet wav",
        "NAM neural amp modeler .nam",
        "guitar cab IR wav free",
        "speaker impulse response wav",
        "neural amp modeler captures",
        "guitar amp model nam",
        "cabinet impulse response collection",
        "guitar IR collection wav",
        "NAM captures guitar amp",
        "neural amp models guitar pedal",
        "impulse response bass cabinet",
        "guitar cabinet simulator wav IR",
        "NAM model amp capture free",
        "impulse response pack guitar free wav",
        "guitar cab sim IR wav collection",
    ]
    found = set()
    existing = set(REPOS)
    for q in queries:
        try:
            r = session.get(
                f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&per_page=30",
                timeout=15, headers={"Accept": "application/vnd.github+json"}
            )
            if r.status_code != 200:
                continue
            for repo in r.json().get("items", []):
                fn = repo["full_name"]
                sz = repo.get("size", 0)
                if sz > 100 and fn not in existing and fn not in found:
                    found.add(fn)
        except:
            pass
        time.sleep(1.5)
    logging.info(f"GitHub search discovered {len(found)} new repos")
    return list(found)[:50]

def generate_docs():
    """Existing simple README generator - kept for legacy or simple views"""
    total = 0
    cats = {}
    for ch in BASE_DIR.iterdir():
        if ch.is_dir() and not ch.name.startswith("."):
            c = sum(1 for f in ch.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXT)
            if c > 0:
                cats[ch.name] = c
                total += c
    md = f"# 🎸 IR DEF Repository\n\n> **{total:,}** files (.wav + .nam)\n\n"
    md += "| Category | Files |\n|---|---|\n"
    for k, v in sorted(cats.items()):
        md += f"| {k} | {v:,} |\n"
    md += f"| **TOTAL** | **{total:,}** |\n"
    md += f"\n*Last updated: {time.strftime('%Y-%m-%d %H:%M UTC')}*\n"
    (BASE_DIR / "README.md").write_text(md, "utf-8")
    logging.info(f"Docs generated: {total:,} files")
    return total

def generate_catalog():
    """
    Generates a rich JSON catalog for the Web Explorer by scanning Remote Drive directly.
    """
    logging.info("📊 GENERATING WEB CATALOG (Remote Scan)...")
    
    # Run rclone lsjson to get ALL metadata fast without downloading
    cmd = ["rclone", "lsjson", "-R", "--hash", "--no-mimetype", RCLONE_REMOTE]
    logging.info(f"  Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logging.error(f"Rclone lsjson failed: {result.stderr}")
            return 0
            
        params = json.loads(result.stdout)
    except Exception as e:
        logging.error(f"Failed to parse rclone output: {e}")
        return 0

    catalog = []
    stats = {"brands": {}, "types": {}, "tags": {}}
    
    for item in params:
        if item.get("IsDir", False): continue # Skip directories
        
        path = item["Path"]
        name = item["Name"]
        size = item["Size"]
        # ModTime is usually in item["ModTime"]
        
        ext = Path(name).suffix.lower()
        if ext not in VALID_EXT:
            continue
            
        # Enrich metadata
        # We simulate the context tags based on the path
        context = path.replace("/", " ").replace("_", " ")
        full_text = (context + " " + name).lower()
        
        # Detect Brand
        brand = _match(full_text, BRANDS) or "Other"
        stats["brands"][brand] = stats["brands"].get(brand, 0) + 1
        
        # Detect Type
        ftype = "NAM" if ext == ".nam" else "IR"
        if "bass" in full_text or "bajo" in full_text: ftype = "Bass IR"
        elif "acoust" in full_text: ftype = "Acoustic IR"
        stats["types"][ftype] = stats["types"].get(ftype, 0) + 1
        
        # Detect Tags
        tags = []
        if "clean" in full_text: tags.append("Clean")
        if "crunch" in full_text: tags.append("Crunch")
        if "high gain" in full_text or "metal" in full_text or "dist" in full_text: tags.append("High Gain")
        if "fuzz" in full_text: tags.append("Fuzz")
        if "cab" in full_text: tags.append("Cab")
        if "pedal" in full_text: tags.append("Pedal")
        
        entry = {
            "id": hashlib.md5(path.encode("utf-8")).hexdigest()[:8],
            "n": name,                # Name (shortened key for JSON size)
            "p": path,                # Path
            "b": brand,               # Brand
            "t": ftype,               # Type
            "s": size,                # Size bytes
            "tag": tags               # Tags
        }
        catalog.append(entry)

    # Save to explorer/public/data/catalog.json
    # We assume the script runs in the root or we use an arg, but let's try to find the web dir
    web_data_dir = Path("explorer/public/data") 
    # If we are running in a CI environment, we might need to create this structure
    web_data_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = web_data_dir / "catalog.json"
    out_file.write_text(json.dumps({
        "updated": time.strftime('%Y-%m-%d %H:%M UTC'),
        "stats": stats,
        "items": catalog
    }, indent=None), "utf-8") # Minified for network speed
    
    logging.info(f"✅ Catalog generated: {len(catalog)} items. Saved to {out_file}")
    return len(catalog)

# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="MEGA Downloader v3 — Clean + Expand")
    parser.add_argument("--tier", default="all",
                        choices=["cleanup", "github", "releases", "direct", "search", "docs", "validate", "rename", "catalog", "all"])
    parser.add_argument("--output-dir", default="/tmp/ir_repository")
    parser.add_argument("--rclone-remote", default="")
    parser.add_argument("--fresh", action="store_true", help="Reset URL cache to re-download everything")
    args = parser.parse_args()

    global BASE_DIR, CACHE_FILE, LOG_FILE, RCLONE_REMOTE
    BASE_DIR = Path(args.output_dir)
    CACHE_FILE = BASE_DIR / ".download_cache.json"
    LOG_FILE = BASE_DIR / ".download.log"
    if args.rclone_remote:
        RCLONE_REMOTE = args.rclone_remote

    setup()
    session = make_session()
    cache = Cache()

    if args.fresh:
        cache.reset_for_expansion()
        cache.save()
        logging.info("🔄 Cache reset — will re-download from all sources")

    logging.info("=" * 60)
    logging.info(f"MEGA DOWNLOADER v3 | tier={args.tier} | out={BASE_DIR}")
    logging.info(f"Repos: {len(REPOS)} | Releases: {len(RELEASE_REPOS)} | Direct ZIPs: {len(DIRECT_ZIPS)}")
    logging.info(f"Remote: {RCLONE_REMOTE}")
    logging.info("=" * 60)

    total_files = 0
    stats = {}

    # ---- CLEANUP ----
    if args.tier in ("cleanup", "all"):
        stats["cleanup_drive"] = cleanup_drive()
        stats["cleanup_local"] = cleanup_local()

    # ---- VALIDATE ----
    if args.tier == "validate":
        stats["cleanup_local"] = cleanup_local()
        (BASE_DIR / ".stats.json").write_text(json.dumps(stats, indent=2), "utf-8")
        return

    # ---- RENAME / REORGANIZE EXISTING ----
    if args.tier == "rename":
        logging.info("━" * 60)
        logging.info("♻️  REORGANIZE / RENAME EXISTING FILES")
        logging.info("━" * 60)
        
        # Source directory where we downloaded the current Drive content
        # We assume the workflow puts it in /tmp/ir_source or similar
        source_dir = Path(os.environ.get("SOURCE_DIR", "/tmp/ir_source"))
        
        renamed_count = 0
        if not source_dir.exists():
            logging.error(f"Source directory {source_dir} does not exist!")
            return

        for root, dirs, files in os.walk(source_dir):
            for fn in files:
                if Path(fn).suffix.lower() not in VALID_EXT:
                    continue
                
                src = Path(root) / fn
                
                # Context is the relative path from source root
                # e.g. "IR_Guitarra/Marshall/Pack_1/cabinets/file.wav"
                rel_path = os.path.relpath(root, source_dir)
                context = f"{rel_path}"
                
                # Use the new robust logic
                organize_file(src, context)
                renamed_count += 1
                
                if renamed_count % 1000 == 0:
                    logging.info(f"  Processed {renamed_count} files...")

        stats["rename"] = renamed_count
        logging.info(f"✅ Reorganized {renamed_count} files into clean structure")
        return

    # ---- GITHUB REPOS ----
    if args.tier in ("github", "all"):
        logging.info("━" * 60)
        logging.info(f"📦 GITHUB REPOS ({len(REPOS)} repos)")
        logging.info("━" * 60)
        phase_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for repo in REPOS:
                f = executor.submit(download_repo, session, cache, repo)
                futures[f] = repo
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    count = future.result()
                    phase_count += count
                    if count > 0:
                        logging.info(f"  ✅ {repo}: {count} files")
                except Exception as e:
                    logging.warning(f"  ❌ {repo}: {e}")
        stats["github"] = phase_count
        total_files += phase_count
        logging.info(f"GitHub phase: {phase_count} new files (total: {total_files})")
        cache.save()

    # ---- RELEASES ----
    if args.tier in ("releases", "all"):
        logging.info("━" * 60)
        logging.info(f"📦 GITHUB RELEASES ({len(RELEASE_REPOS)} repos)")
        logging.info("━" * 60)
        phase_count = 0
        for owner, rp in RELEASE_REPOS:
            try:
                count = download_releases(session, cache, owner, rp)
                phase_count += count
            except Exception as e:
                logging.warning(f"  ❌ {owner}/{rp}: {e}")
        stats["releases"] = phase_count
        total_files += phase_count
        logging.info(f"Releases phase: {phase_count} new files (total: {total_files})")

    # ---- DIRECT ZIPS ----
    if args.tier in ("direct", "all"):
        logging.info("━" * 60)
        logging.info(f"📦 DIRECT ZIPS ({len(DIRECT_ZIPS)} sources)")
        logging.info("━" * 60)
        phase_count = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for url, name in DIRECT_ZIPS:
                f = executor.submit(download_direct_zip, session, cache, url, name)
                futures[f] = name
            for future in as_completed(futures):
                name = futures[future]
                try:
                    count = future.result()
                    phase_count += count
                    if count > 0:
                        logging.info(f"  ✅ {name}: {count} files")
                except Exception as e:
                    logging.warning(f"  ❌ {name}: {e}")
        stats["direct"] = phase_count
        total_files += phase_count
        logging.info(f"Direct phase: {phase_count} new files (total: {total_files})")
        cache.save()

    # ---- SEARCH DISCOVERY ----
    if args.tier in ("search", "all"):
        logging.info("━" * 60)
        logging.info("📦 GITHUB SEARCH AUTO-DISCOVERY")
        logging.info("━" * 60)
        phase_count = 0
        try:
            new_repos = github_search_discover(session, cache)
            logging.info(f"Found {len(new_repos)} new repos via search")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                for repo in new_repos:
                    f = executor.submit(download_repo, session, cache, repo)
                    futures[f] = repo
                for future in as_completed(futures):
                    repo = futures[future]
                    try:
                        count = future.result()
                        phase_count += count
                        if count > 0:
                            logging.info(f"  🔍 {repo}: {count} files")
                    except:
                        pass
        except Exception as e:
            logging.error(f"Search error: {e}")
        stats["search"] = phase_count
        total_files += phase_count
        logging.info(f"Search phase: {phase_count} new files (total: {total_files})")
        cache.save()

    # ---- DOCS ----
    if args.tier in ("docs", "all"):
        stats["docs"] = generate_docs()

    # ---- CATALOG (WEB INDEX) ----
    if args.tier == "catalog":
        stats["catalog"] = generate_catalog()
        return

    # ---- FINAL CLEANUP ----
    if args.tier == "all":
        stats["final_cleanup"] = cleanup_local()

    # ---- SUMMARY ----
    logging.info("")
    logging.info("=" * 60)
    logging.info("📊 FINAL SUMMARY")
    logging.info("=" * 60)
    for k, v in stats.items():
        logging.info(f"  {k}: {v}")
    logging.info(f"  NEW FILES THIS RUN: {total_files}")
    total_local = 0
    for cat_dir in BASE_DIR.iterdir():
        if cat_dir.is_dir() and not cat_dir.name.startswith("."):
            count = sum(1 for f in cat_dir.rglob("*") if f.suffix.lower() in VALID_EXT)
            if count > 0:
                logging.info(f"  📁 {cat_dir.name}: {count}")
                total_local += count
    logging.info(f"  📁 TOTAL LOCAL: {total_local}")
    (BASE_DIR / ".stats.json").write_text(json.dumps(stats, indent=2), "utf-8")
    logging.info("=" * 60)
    logging.info("🏁 MEGA DOWNLOAD v3 COMPLETE!")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
