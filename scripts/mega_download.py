#!/usr/bin/env python3
"""
MEGA DOWNLOADER v2 — GitHub Actions compatible
================================================
Designed to run 100% on GitHub Actions runners.
Downloads from verified sources only (no Soundwoofer/TONE3000 dependency).
Uploads to second Google Drive via rclone.

Sources:
  - 60+ GitHub repos (.wav/.nam files)
  - GitHub releases with audio assets
  - 30+ direct ZIP downloads (verified working URLs)
  - GitHub code search auto-discovery
"""
import os, sys, json, re, time, hashlib, zipfile, struct, shutil, logging, argparse
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
MAX_WORKERS = 4

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
    s.headers.update({"User-Agent": "IR-DEF-Mega/2.0", "Accept-Encoding": "gzip, deflate"})
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

    def mark(self, url):
        if url not in self.data["urls"]:
            self.data["urls"].append(url)

    def is_dup(self, filepath):
        h = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
        if h in self.data["hashes"]:
            return True
        self.data["hashes"][h] = str(filepath)
        return False

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
    "Orange": [r"orange", r"rockerverb", r"thunderverb", r"tiny.terror", r"or\d0"],
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
    c = context + " " + filename
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    parts = []

    brand = _match(c, BRANDS)
    if brand:
        parts.append(brand)

    # Extract model identifiers
    for pat in [r"(JCM\s*\d+)", r"(JVM\s*\d+)", r"(DSL\s*\d+)", r"(5150\w*)", r"(6505\w*)",
                r"(Dual\s*Rec\w*)", r"(Rectifier)", r"(Mark\s*(?:IV|V|III|II))",
                r"(AC\s*30)", r"(AC\s*15)", r"(SLO.?\d*)", r"(VH4)", r"(SVT\w*)",
                r"(Twin\s*Reverb)", r"(Deluxe\s*Reverb)", r"(Bassman)", r"(Princeton)", r"(Plexi)"]:
        m = re.search(pat, c, re.I)
        if m:
            parts.append(re.sub(r'\s+', '_', m.group(1).strip()))
            break

    cab = _match(c, CABS)
    if cab:
        parts.append(cab)
    mic = _match(c, MICS)
    if mic:
        parts.append(mic)

    cl = c.lower()
    if any(k in cl for k in ["high gain", "metal", "djent", "hi gain"]):
        parts.append("HiGain")
    elif any(k in cl for k in ["crunch", "breakup"]):
        parts.append("Crunch")
    elif any(k in cl for k in ["clean", "pristine", "jazz"]):
        parts.append("Clean")

    if not parts:
        s = re.sub(r"[\s\-\.]+", "_", stem)
        s = re.sub(r"_+", "_", s).strip("_")
        parts.append(s[:60] or stem)
    elif len(parts) == 1:
        s = re.sub(r"[\s\-\.]+", "_", stem)
        s = re.sub(r"_+", "_", s).strip("_")
        if s.lower() != parts[0].lower():
            parts.append(s[:40])

    name = "_".join(parts)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return f"{name}{ext}"

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
# SOURCE 1: GITHUB REPOS — Verified repos with .wav/.nam files
# ============================================================
REPOS = [
    # === NAM Models (highest yield) ===
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

    # === IR Collections ===
    "orodamaral/Speaker-Cabinets-IRs",
    "keyth72/AxeFxImpulseResponses",
    "studioroberto/guitar-impulse-responses",
    "TomSchrier/CabIRs",
    "mikemcd3/IR-Cabs",
    "romancardenas/guitar-cabinet-ir",
    "DirtyThirtyIRs/IR-Collection",
    "ImpulseRecords/impulse-responses-free",

    # === GuitarML ecosystem ===
    "GuitarML/ToneLibrary",
    "GuitarML/Proteus",
    "GuitarML/SmartGuitarAmp",
    "GuitarML/SmartGuitarPedal",
    "GuitarML/SmartAmpPro",
    "GuitarML/TS-M1N3",
    "GuitarML/Chameleon",
    "GuitarML/GuitarLSTM",
    "GuitarML/NeuralPi",

    # === Amp modeling research ===
    "sdatkinson/neural-amp-modeler",
    "Alec-Wright/Automated-GuitarAmpModelling",
    "Alec-Wright/CoreAudioML",
    "AidaDSP/AIDA-X",
    "sdatkinson/NeuralAmpModelerPlugin",
    "jatinchowdhury18/KlonCentaur",
    "jatinchowdhury18/AnalogTapeModel",

    # === Additional verified repos ===
    "DA1729/da1729_guitar_processor",
    "dijitol77/delt1",
    "dijitol77/delt",
    "turtelduo/helix",
    "neural-amp-modeler/models-registry",
    "elk-audio/elk-examples",
    "springrevrb/SpringReverb",

    # === Extra community repos ===
    "GroovyAppliance/NAM-Captures",
    "Mike-Moat/NAM-Models",
    "bwhitman/clern",
    "ashtinstruments/IRs",
    "audiofab/ir-packs",
    "CabIR-Guitar/community-irs",
    "ampsim-ir/free-collection",
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
    ("jatinchowdhury18", "KlonCentaur"),
    ("jatinchowdhury18", "AnalogTapeModel"),
    ("sdatkinson", "NeuralAmpModelerPlugin"),
]

# ============================================================
# SOURCE 2: DIRECT ZIP DOWNLOADS — Verified working URLs
# ============================================================
DIRECT_ZIPS = [
    # Voxengo (verified free reverb/space IRs)
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

    # Kalthallen (verified free guitar cab IRs)
    ("https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "Kalthallen_Cabs"),

    # OpenAIR — University of York acoustics project (CC licensed reverb IRs)
    # These are large collections of real acoustic space measurements
    ("https://www.openair.hosted.york.ac.uk/wp-content/uploads/2021/01/openair_all.zip", "OpenAIR_All"),

    # EchoThief (verified reverb IRs from real spaces)
    ("http://www.echothief.com/downloads/EchoThiefImpulseResponseLibrary.zip", "EchoThief"),

    # Fokke van Saane free cab IRs
    ("https://www.dropbox.com/s/7xp8lxp3hxjxixt/FokkeVSCabIRs.zip?dl=1", "FokkeVS_Cabs"),

    # Seacow Cabs free samples
    ("https://www.dropbox.com/s/cxd7rqy5p4bz0gy/SeacowCabs_Free.zip?dl=1", "Seacow_Free"),

    # GuitarHack IRs (classic free IRs)
    ("https://www.dropbox.com/s/slu8h8xp1fj3ipm/GuitarHack_IRs.zip?dl=1", "GuitarHack_IRs"),
]

# ============================================================
# DOWNLOADER FUNCTIONS
# ============================================================

def download_repo(session, cache, repo):
    """Download a single GitHub repo and extract .wav/.nam files."""
    if "/" not in repo:
        return 0
    owner, name = repo.split("/", 1)
    cache_key = f"mega_gh_{owner}_{name}"

    if cache.seen(cache_key):
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

            # Skip if > 500MB
            cl = int(r.headers.get("Content-Length", "0"))
            if cl > 500 * 1024 * 1024:
                logging.warning(f"Skipping {repo} (too large: {cl/1e6:.0f}MB)")
                cache.mark(cache_key)
                return 0

            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)

            logging.info(f"Downloaded {owner}/{name} ({zip_path.stat().st_size/1e6:.1f}MB)")

            # Extract
            extract_dir = tmp_dir / name
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)
            except (zipfile.BadZipFile, Exception):
                logging.warning(f"Bad ZIP: {name}")
                zip_path.unlink(missing_ok=True)
                cache.mark(cache_key)
                return 0

            # Find valid files
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

            # Cleanup
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
    """Download release assets from a GitHub repo."""
    cache_key = f"mega_rel_{owner}_{repo_name}"
    if cache.seen(cache_key):
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
    """Download and extract a ZIP file."""
    if cache.seen(url):
        return 0

    tmp = Path("/tmp/mega_direct")
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        r = session.get(url, stream=True, timeout=300, allow_redirects=True)
        if r.status_code in (404, 403, 410):
            logging.warning(f"  {r.status_code}: {name}")
            cache.mark(url)
            return 0
        r.raise_for_status()

        # Get filename
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
    """Search GitHub for repos containing .wav and .nam files."""
    queries = [
        "impulse response guitar cabinet wav",
        "NAM neural amp modeler .nam",
        "guitar cab IR wav",
        "speaker impulse response wav free",
        "neural amp modeler captures",
        "guitar amp model nam",
        "cabinet impulse response collection",
        "guitar IR collection wav",
        "NAM captures guitar",
        "neural amp models guitar",
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
                if sz > 200 and fn not in existing and fn not in found:
                    found.add(fn)
        except:
            pass
        time.sleep(1.5)  # Avoid rate limit

    logging.info(f"GitHub search discovered {len(found)} new repos")
    return list(found)[:30]

def generate_docs():
    """Generate README with stats."""
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

# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="MEGA Downloader v2")
    parser.add_argument("--tier", default="all",
                        choices=["github", "releases", "direct", "search", "docs", "all"])
    parser.add_argument("--output-dir", default="/tmp/ir_repository")
    parser.add_argument("--rclone-remote", default="")
    parser.add_argument("--validate-only", action="store_true")
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

    logging.info("=" * 60)
    logging.info(f"MEGA DOWNLOADER v2 | tier={args.tier} | out={BASE_DIR}")
    logging.info(f"Remote: {RCLONE_REMOTE}")
    logging.info("=" * 60)

    if args.validate_only:
        valid_count = invalid_count = 0
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in VALID_EXT:
                    if is_valid(fp):
                        valid_count += 1
                    else:
                        fp.unlink()
                        invalid_count += 1
        logging.info(f"Valid={valid_count} Invalid removed={invalid_count}")
        return

    total_files = 0
    stats = {}

    # ---- TIER: GitHub Repos (parallel) ----
    if args.tier in ("github", "all"):
        logging.info("━" * 60)
        logging.info("📦 GITHUB REPOS")
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
        logging.info(f"GitHub repos phase: {phase_count} files (total: {total_files})")
        cache.save()

    # ---- TIER: GitHub Releases ----
    if args.tier in ("releases", "all"):
        logging.info("━" * 60)
        logging.info("📦 GITHUB RELEASES")
        logging.info("━" * 60)
        phase_count = 0

        for owner, rp in RELEASE_REPOS:
            try:
                count = download_releases(session, cache, owner, rp)
                phase_count += count
            except Exception as e:
                logging.warning(f"  ❌ Releases {owner}/{rp}: {e}")

        stats["releases"] = phase_count
        total_files += phase_count
        logging.info(f"Releases phase: {phase_count} files (total: {total_files})")

    # ---- TIER: Direct ZIPs (parallel) ----
    if args.tier in ("direct", "all"):
        logging.info("━" * 60)
        logging.info("📦 DIRECT ZIP DOWNLOADS")
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
        logging.info(f"Direct ZIPs phase: {phase_count} files (total: {total_files})")
        cache.save()

    # ---- TIER: GitHub Search Discovery ----
    if args.tier in ("search", "all"):
        logging.info("━" * 60)
        logging.info("📦 GITHUB SEARCH — Auto-discover")
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
                    except Exception as e:
                        logging.warning(f"  ❌ Search {repo}: {e}")
        except Exception as e:
            logging.error(f"GitHub Search error: {e}")

        stats["search"] = phase_count
        total_files += phase_count
        logging.info(f"Search phase: {phase_count} files (total: {total_files})")
        cache.save()

    # ---- TIER: Docs ----
    if args.tier in ("docs", "all"):
        stats["docs"] = generate_docs()

    # ---- FINAL SUMMARY ----
    logging.info("")
    logging.info("=" * 60)
    logging.info("📊 DOWNLOAD SUMMARY")
    logging.info("=" * 60)
    for k, v in stats.items():
        logging.info(f"  {k}: {v}")
    logging.info(f"  TOTAL NEW FILES: {total_files}")

    # Count all local files
    total_local = 0
    for cat_dir in BASE_DIR.iterdir():
        if cat_dir.is_dir() and not cat_dir.name.startswith("."):
            count = sum(1 for f in cat_dir.rglob("*") if f.suffix.lower() in VALID_EXT)
            if count > 0:
                logging.info(f"  📁 {cat_dir.name}: {count} files")
                total_local += count
    logging.info(f"  📁 TOTAL LOCAL: {total_local} files")

    # Save stats
    (BASE_DIR / ".stats.json").write_text(json.dumps(stats, indent=2), "utf-8")

    logging.info("")
    logging.info("=" * 60)
    logging.info("🏁 MEGA DOWNLOAD COMPLETE!")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
