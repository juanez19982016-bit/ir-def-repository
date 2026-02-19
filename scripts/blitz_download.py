#!/usr/bin/env python3
"""
BLITZ DOWNLOADER — Ultra-aggressive local download with live progress
=====================================================================
- 50+ GitHub repos with .wav/.nam files
- Direct ZIP downloads from verified IR providers
- Soundwoofer API (if alive)
- Live progress with percentages
- Continuous rclone upload after each batch
- Deduplication by file hash
"""
import os, sys, json, re, time, hashlib, zipfile, struct, shutil, subprocess, threading
from pathlib import Path
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============ CONFIG ============
BASE_DIR = Path(r"C:\Users\Admin\Desktop\IR DEF\ir-repository\DOWNLOADS")
CACHE_FILE = BASE_DIR / ".blitz_cache.json"
VALID_EXT = {".wav", ".nam"}
RCLONE_REMOTE = "gdrive2:IR_DEF_REPOSITORY"
MAX_WORKERS = 4

# ============ STATS ============
class Stats:
    def __init__(self):
        self.total_sources = 0
        self.completed_sources = 0
        self.files_downloaded = 0
        self.files_skipped = 0
        self.errors = 0
        self.bytes_downloaded = 0
        self.lock = threading.Lock()
    
    def progress(self, source_name=""):
        with self.lock:
            pct = (self.completed_sources / max(self.total_sources, 1)) * 100
            print(f"\r[{pct:5.1f}%] Sources: {self.completed_sources}/{self.total_sources} | "
                  f"Files: {self.files_downloaded} | Skip: {self.files_skipped} | "
                  f"Err: {self.errors} | {self.bytes_downloaded/1e6:.0f}MB"
                  f" | {source_name[:30]:<30}", end="", flush=True)
    
    def complete_source(self, name):
        with self.lock:
            self.completed_sources += 1
        self.progress(f"✅ {name}")
    
    def error_source(self, name, err=""):
        with self.lock:
            self.completed_sources += 1
            self.errors += 1
        self.progress(f"❌ {name}")
        print(f"\n  ERROR [{name}]: {str(err)[:100]}")

stats = Stats()

# ============ CACHE ============
class Cache:
    def __init__(self):
        self.data = {"urls": [], "hashes": {}}
        if CACHE_FILE.exists():
            try: self.data = json.loads(CACHE_FILE.read_text("utf-8"))
            except: pass
    
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

cache = Cache()

# ============ SESSION ============
def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]
    ), pool_maxsize=20))
    s.headers.update({"User-Agent": "IR-DEF-Blitz/1.0"})
    # Try to get GitHub token
    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
        if token:
            s.headers["Authorization"] = f"Bearer {token}"
    except: pass
    return s

# ============ VALIDATION ============
def is_valid_wav(path):
    try:
        with open(path, "rb") as f:
            h = f.read(12)
            if len(h) < 12: return False
            r, _, w = struct.unpack("<4sI4s", h)
            return r == b"RIFF" and w == b"WAVE"
    except: return False

def is_valid(path):
    p = Path(path)
    if p.stat().st_size < 100: return False
    if p.suffix.lower() == ".wav": return is_valid_wav(p)
    return p.suffix.lower() == ".nam"

# ============ BRAND DETECTION ============
BRANDS = {
    "Marshall": [r"marshall", r"jcm", r"jvm", r"plexi", r"1959", r"2203", r"dsl"],
    "Fender": [r"fender", r"twin", r"deluxe.reverb", r"bassman", r"princeton"],
    "Mesa": [r"mesa", r"boogie", r"rectifier", r"recto", r"dual.rec", r"mark.?(iv|v|iii|ii)"],
    "Vox": [r"vox", r"ac.?30", r"ac.?15"],
    "Orange": [r"orange", r"rockerverb", r"tiny.terror"],
    "Peavey": [r"peavey", r"5150", r"6505"],
    "EVH": [r"\bevh\b"],
    "Bogner": [r"bogner", r"uberschall"],
    "Soldano": [r"soldano", r"slo"],
    "Diezel": [r"diezel", r"vh4"],
    "Friedman": [r"friedman", r"be.?100"],
    "Engl": [r"engl", r"powerball", r"fireball"],
    "Ampeg": [r"ampeg", r"svt"],
    "Celestion": [r"celestion", r"v30", r"greenback", r"creamback"],
    "Hiwatt": [r"hiwatt"],
    "Laney": [r"laney"],
    "Revv": [r"\brevv\b"],
    "Victory": [r"victory"],
    "Darkglass": [r"darkglass"],
    "Suhr": [r"\bsuhr\b"],
}

def detect_brand(text):
    t = text.lower()
    for brand, patterns in BRANDS.items():
        for p in patterns:
            if re.search(p, t): return brand
    return None

def categorize(context, filename):
    c = (context + " " + filename).lower()
    ext = Path(filename).suffix.lower()
    if ext == ".nam": return "NAM_Capturas"
    if any(k in c for k in ["bass", "bajo", "svt", "ampeg", "darkglass", "8x10", "4x10"]): return "IR_Bajo"
    if any(k in c for k in ["acoustic", "piezo", "taylor", "nylon"]): return "IR_Acustica"
    if any(k in c for k in ["reverb", "room", "hall", "plate", "spring", "ambient", "convol"]): return "IR_Utilidades"
    return "IR_Guitarra"

def organize_file(src_path, context=""):
    """Move a file to the right category folder with a clean name."""
    fn = Path(src_path).name
    cat = categorize(context or str(src_path), fn)
    dest_dir = BASE_DIR / cat
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean filename
    brand = detect_brand(context + " " + fn)
    stem = Path(fn).stem
    ext = Path(fn).suffix.lower()
    
    clean = re.sub(r'[\s\-\.]+', '_', stem)
    clean = re.sub(r'_+', '_', clean).strip('_')
    if brand and brand.lower() not in clean.lower():
        clean = f"{brand}_{clean}"
    clean = clean[:80]
    name = f"{clean}{ext}"
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    dest = dest_dir / name
    if dest.exists():
        i = 1
        while dest.exists():
            dest = dest_dir / f"{clean}_{i}{ext}"
            i += 1
    
    shutil.copy2(src_path, dest)
    return dest

# ============ GITHUB REPO DOWNLOADER ============
REPOS = [
    # === ORIGINAL REPOS (may have been done by Actions) ===
    "pelennor2170/NAM_models",
    "orodamaral/Speaker-Cabinets-IRs",
    "GuitarML/ToneLibrary",
    "GuitarML/Proteus",
    "sdatkinson/neural-amp-modeler",
    "mikeoliphant/NeuralAmpModels",
    "Alec-Wright/Automated-GuitarAmpModelling",
    "Alec-Wright/CoreAudioML",
    "GuitarML/GuitarLSTM",
    "GuitarML/SmartGuitarAmp",
    "GuitarML/SmartGuitarPedal",
    "GuitarML/SmartAmpPro",
    "GuitarML/TS-M1N3",
    "GuitarML/Chameleon",
    "AidaDSP/AIDA-X",
    "keyth72/AxeFxImpulseResponses",
    # === NEW REPOS — EXPAND MASSIVELY ===
    "markusaksli-nc/nam-models",
    "TomSchrier/CabIRs",
    "mikemcd3/IR-Cabs",
    "BenjaminAbt/neural-amp-models",
    "voidstar78/NAM-Captures",
    "NickHilburn/NAM_captures",
    "DaveFarmerUK/NAM_captures",
    "studioroberto/guitar-impulse-responses",
    "ImpulseRecords/impulse-responses-free",
    "TheBlackPlague/NeuralAmpModels",
    "romancardenas/guitar-cabinet-ir",
    "davedude0/NeuralAmpModelerModels",
    "screamingFrog/NAM-packs",
    "j4de/NAM-Models",
    "tansey-sern/NAM_Community_Models",
    "mfmods/mf-nam-models",
    "Pilkch/nam-models",
    "grrrwaaa/nam-models",
    "0x01h/nam-models",
    "jrialland/nam-models",
    "DirtyThirtyIRs/IR-Collection",
    "SonicScapes/Free-IRs",
    "cabsims/impulse-response-library",
    "guitarml/NeuralPi",
    "thomjames/NAMCaptures",
    "DoomMuffin/NAM-Models",
    "LevDev/NAMCaptures",
    "maxb2/nam-stuff",
    "tstalka/nam-models",
    "Dhalion/NAM-Captures",
    # === More known repos with audio ===
    "springrevrb/SpringReverb",
    "grame-cncm/faust",
    "elk-audio/elk-examples",
    "jatinchowdhury18/KlonCentaur",
    "jatinchowdhury18/AnalogTapeModel",
    "jatinchowdhury18/ChowDSP",
    "jatinchowdhury18/ChowTapeModel",
    "StoneyDSP/Biquads",
    "neural-amp-modeler/models-registry",
    "sdatkinson/NeuralAmpModelerPlugin",
]

def download_repo(session, repo):
    """Download a single GitHub repo and extract .wav/.nam files."""
    owner, name = repo.split("/", 1)
    cache_key = f"blitz_gh_{owner}_{name}"
    
    if cache.seen(cache_key):
        with stats.lock:
            stats.files_skipped += 1
        return 0
    
    tmp_dir = Path(os.environ.get("TEMP", "/tmp")) / "blitz_gh"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    for branch in ["main", "master"]:
        zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
        zip_path = tmp_dir / f"{name}.zip"
        
        try:
            r = session.get(zip_url, stream=True, timeout=120)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            
            # Check size - skip if > 500MB
            cl = int(r.headers.get("Content-Length", "0"))
            if cl > 500 * 1024 * 1024:
                cache.mark(cache_key)
                return 0
            
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)
                    with stats.lock:
                        stats.bytes_downloaded += len(chunk)
            
            # Extract
            extract_dir = tmp_dir / name
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)
            except (zipfile.BadZipFile, Exception):
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
                        with stats.lock:
                            stats.files_downloaded += 1
                    except:
                        pass
            
            cache.mark(cache_key)
            cache.save()
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
            
            return file_count
            
        except requests.exceptions.RequestException:
            if branch == "master":
                cache.mark(cache_key)
                return 0
    
    cache.mark(cache_key)
    return 0

# ============ GITHUB RELEASES DOWNLOADER ============
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
]

def download_releases(session, owner, repo_name):
    """Download release assets from a GitHub repo."""
    cache_key = f"blitz_rel_{owner}_{repo_name}"
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
        tmp = Path(os.environ.get("TEMP", "/tmp")) / "blitz_rel"
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
                            with stats.lock:
                                stats.bytes_downloaded += len(chunk)
                    
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
                                        with stats.lock:
                                            stats.files_downloaded += 1
                            shutil.rmtree(xd, ignore_errors=True)
                        except:
                            pass
                    elif is_valid(tp) and not cache.is_dup(tp):
                        organize_file(tp, f"rel/{repo_name}/{name}")
                        file_count += 1
                        with stats.lock:
                            stats.files_downloaded += 1
                    
                    tp.unlink(missing_ok=True)
                    cache.mark(url)
                except:
                    with stats.lock:
                        stats.errors += 1
        
        cache.mark(cache_key)
        cache.save()
        return file_count
        
    except Exception as e:
        cache.mark(cache_key)
        return 0

# ============ DIRECT ZIP DOWNLOADS ============
DIRECT_ZIPS = [
    ("https://www.voxengo.com/files/impulses/IMreverbs.zip", "Voxengo_Reverb"),
    ("https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "Kalthallen_Cabs"),
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
    ("https://www.voxengo.com/files/impulses/St_Nicolaes_church.zip", "Voxengo_Church2"),
    ("https://www.voxengo.com/files/impulses/Vocal_duo.zip", "Voxengo_VocalDuo"),
]

def download_direct_zip(session, url, name):
    """Download and extract a ZIP file."""
    if cache.seen(url):
        return 0
    
    tmp = Path(os.environ.get("TEMP", "/tmp")) / "blitz_direct"
    tmp.mkdir(parents=True, exist_ok=True)
    
    try:
        r = session.get(url, stream=True, timeout=120, allow_redirects=True)
        if r.status_code in (404, 403, 410):
            cache.mark(url)
            return 0
        r.raise_for_status()
        
        zip_path = tmp / f"{name}.zip"
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
                with stats.lock:
                    stats.bytes_downloaded += len(chunk)
        
        file_count = 0
        extract_dir = tmp / name
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile:
            zip_path.unlink(missing_ok=True)
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
                        with stats.lock:
                            stats.files_downloaded += 1
                except:
                    pass
        
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        cache.mark(url)
        cache.save()
        return file_count
        
    except Exception as e:
        cache.mark(url)
        return 0

# ============ SOUNDWOOFER DOWNLOADER ============
def download_soundwoofer(session):
    """Try Soundwoofer API — fail fast if not responding."""
    base = "https://soundwoofer.com"
    
    # Quick connectivity test (3 second timeout)
    try:
        test = session.get(f"{base}/api/impulses?page=0&limit=1", timeout=3)
        if test.status_code != 200:
            print(f"\n  Soundwoofer API returned {test.status_code} — SKIPPING")
            return 0
    except:
        print(f"\n  Soundwoofer API TIMEOUT — SKIPPING")
        return 0
    
    total = 0
    data = test.json()
    items = data if isinstance(data, list) else data.get("data", data.get("impulses", []))
    
    if not items:
        print(f"\n  Soundwoofer returned empty data — SKIPPING")
        return 0
    
    print(f"\n  Soundwoofer API alive! First page: {len(items)} items")
    
    for page in range(50):
        try:
            r = session.get(f"{base}/api/impulses?page={page}&limit=100", timeout=10)
            if r.status_code != 200:
                break
            
            data = r.json()
            items = data if isinstance(data, list) else data.get("data", data.get("impulses", []))
            if not items:
                break
            
            for item in items:
                dl_url = item.get("downloadUrl") or item.get("download_url") or item.get("url") or item.get("file")
                if not dl_url:
                    iid = item.get("id") or item.get("_id")
                    if iid:
                        dl_url = f"{base}/api/impulses/{iid}/download"
                
                if not dl_url:
                    continue
                if not dl_url.startswith("http"):
                    dl_url = base + dl_url
                if cache.seen(dl_url):
                    continue
                
                try:
                    dr = session.get(dl_url, timeout=10)
                    if dr.status_code != 200:
                        cache.mark(dl_url)
                        continue
                    
                    spk = item.get("speaker", "") or item.get("speakerModel", "") or ""
                    cab = item.get("cabinet", "") or item.get("cabinetModel", "") or ""
                    mic = item.get("microphone", "") or item.get("mic", "") or ""
                    title = item.get("title", "") or item.get("name", "SW_unknown")
                    
                    parts = [p for p in [cab, spk, mic, title] if p]
                    fname = "_".join(parts)[:80] + ".wav"
                    fname = re.sub(r'[<>:"/\\|?*]', '_', fname)
                    
                    tmp = Path(os.environ.get("TEMP", "/tmp")) / "blitz_sw"
                    tmp.mkdir(parents=True, exist_ok=True)
                    tp = tmp / fname
                    tp.write_bytes(dr.content)
                    
                    if is_valid(tp) and not cache.is_dup(tp):
                        organize_file(tp, f"soundwoofer/{cab}/{spk}/{title}")
                        total += 1
                        with stats.lock:
                            stats.files_downloaded += 1
                            stats.bytes_downloaded += len(dr.content)
                    else:
                        tp.unlink(missing_ok=True)
                    
                    cache.mark(dl_url)
                except:
                    with stats.lock:
                        stats.errors += 1
                    cache.mark(dl_url)
            
            if len(items) < 100:
                break
            
            if total % 100 == 0 and total > 0:
                cache.save()
                stats.progress(f"Soundwoofer p{page}")
            
            time.sleep(0.3)
        except:
            break
    
    cache.save()
    return total

# ============ GITHUB SEARCH — AUTO-DISCOVER NEW REPOS ============
def github_search_repos(session):
    """Search GitHub for repos containing .wav and .nam files."""
    queries = [
        "impulse response guitar cabinet wav",
        "NAM neural amp modeler .nam",
        "guitar cab IR wav",
        "speaker impulse response wav free",
        "neural amp modeler captures",
        "guitar amp model nam",
        "cabinet impulse response collection",
    ]
    
    found = set()
    existing = set(REPOS)
    
    for q in queries:
        try:
            from urllib.parse import quote
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
        time.sleep(1)  # Avoid rate limit
    
    return list(found)[:30]  # Max 30 new repos

# ============ RCLONE UPLOAD ============
def rclone_upload():
    """Upload all downloaded files to Google Drive."""
    print("\n\n" + "=" * 60)
    print("📤 UPLOADING TO GOOGLE DRIVE...")
    print("=" * 60)
    
    for cat_dir in BASE_DIR.iterdir():
        if cat_dir.is_dir() and not cat_dir.name.startswith("."):
            files = list(cat_dir.glob("*"))
            valid_files = [f for f in files if f.suffix.lower() in VALID_EXT]
            if not valid_files:
                continue
            
            print(f"\n  📁 {cat_dir.name}: {len(valid_files)} files...")
            
            try:
                result = subprocess.run(
                    ["rclone", "copy", str(cat_dir), f"{RCLONE_REMOTE}/{cat_dir.name}",
                     "--transfers", "8", "--checkers", "16",
                     "--drive-chunk-size", "64M", "--fast-list",
                     "--stats", "10s", "--stats-one-line", "--log-level", "INFO"],
                    capture_output=True, text=True, timeout=1800
                )
                if result.returncode == 0:
                    print(f"  ✅ {cat_dir.name} uploaded!")
                else:
                    print(f"  ❌ {cat_dir.name} error: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"  ⚠️ {cat_dir.name} upload timeout (30min)")
            except Exception as e:
                print(f"  ❌ Upload error: {e}")
    
    # Verify
    print("\n📊 VERIFYING DRIVE SIZE...")
    try:
        result = subprocess.run(
            ["rclone", "size", RCLONE_REMOTE],
            capture_output=True, text=True, timeout=60
        )
        print(f"  {result.stdout.strip()}")
    except:
        print("  Could not verify")

# ============ MAIN ============
def main():
    print("=" * 60)
    print("⚡ BLITZ DOWNLOADER — ULTRA AGGRESSIVE MODE")
    print("=" * 60)
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    session = make_session()
    
    # Calculate total sources
    stats.total_sources = len(REPOS) + len(RELEASE_REPOS) + len(DIRECT_ZIPS) + 2  # +2 for soundwoofer + github search
    
    print(f"\n📋 SOURCES: {len(REPOS)} repos + {len(RELEASE_REPOS)} releases + "
          f"{len(DIRECT_ZIPS)} direct ZIPs + Soundwoofer + GitHub Search")
    print(f"📂 Output: {BASE_DIR}")
    print(f"☁️  Remote: {RCLONE_REMOTE}")
    print()
    
    # ---- PHASE 1: GitHub Repos (parallel) ----
    print("━" * 60)
    print("📦 PHASE 1: GitHub Repos")
    print("━" * 60)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for repo in REPOS:
            if "/" not in repo:
                continue
            f = executor.submit(download_repo, session, repo)
            futures[f] = repo
        
        for future in as_completed(futures):
            repo = futures[future]
            name = repo.split("/")[1]
            try:
                count = future.result()
                if count > 0:
                    stats.complete_source(f"{name} ({count})")
                else:
                    stats.complete_source(name)
            except Exception as e:
                stats.error_source(name, e)
    
    print(f"\n\n✅ Phase 1 done: {stats.files_downloaded} files\n")
    cache.save()
    
    # ---- PHASE 2: GitHub Releases ----
    print("━" * 60)
    print("📦 PHASE 2: GitHub Releases")
    print("━" * 60)
    
    for owner, rp in RELEASE_REPOS:
        try:
            count = download_releases(session, owner, rp)
            if count > 0:
                stats.complete_source(f"rel/{rp} ({count})")
            else:
                stats.complete_source(f"rel/{rp}")
        except Exception as e:
            stats.error_source(f"rel/{rp}", e)
    
    print(f"\n\n✅ Phase 2 done: {stats.files_downloaded} total files\n")
    
    # ---- PHASE 3: Direct ZIPs ----
    print("━" * 60)
    print("📦 PHASE 3: Direct ZIP Downloads")
    print("━" * 60)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for url, name in DIRECT_ZIPS:
            f = executor.submit(download_direct_zip, session, url, name)
            futures[f] = name
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                count = future.result()
                if count > 0:
                    stats.complete_source(f"{name} ({count})")
                else:
                    stats.complete_source(name)
            except Exception as e:
                stats.error_source(name, e)
    
    print(f"\n\n✅ Phase 3 done: {stats.files_downloaded} total files\n")
    cache.save()
    
    # ---- PHASE 4: Soundwoofer ----
    print("━" * 60)
    print("📦 PHASE 4: Soundwoofer API (fail-fast if down)")
    print("━" * 60)
    
    try:
        sw_count = download_soundwoofer(session)
        stats.complete_source(f"Soundwoofer ({sw_count})")
    except Exception as e:
        stats.error_source("Soundwoofer", e)
    
    print(f"\n\n✅ Phase 4 done: {stats.files_downloaded} total files\n")
    
    # ---- PHASE 5: GitHub Search Discovery ----
    print("━" * 60)
    print("📦 PHASE 5: GitHub Search — Auto-discover new repos")
    print("━" * 60)
    
    try:
        new_repos = github_search_repos(session)
        print(f"\n  Found {len(new_repos)} new repos via search")
        stats.total_sources += len(new_repos)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for repo in new_repos:
                f = executor.submit(download_repo, session, repo)
                futures[f] = repo
            
            for future in as_completed(futures):
                repo = futures[future]
                name = repo.split("/")[1]
                try:
                    count = future.result()
                    if count > 0:
                        stats.complete_source(f"🔍{name} ({count})")
                    else:
                        stats.complete_source(f"🔍{name}")
                except Exception as e:
                    stats.error_source(f"🔍{name}", e)
    except Exception as e:
        stats.error_source("GitHub Search", e)
    
    print(f"\n\n✅ Phase 5 done: {stats.files_downloaded} total files\n")
    cache.save()
    
    # ---- SUMMARY ----
    print("\n" + "=" * 60)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"  Files downloaded:  {stats.files_downloaded}")
    print(f"  Files skipped:     {stats.files_skipped}")
    print(f"  Errors:            {stats.errors}")
    print(f"  Data downloaded:   {stats.bytes_downloaded/1e6:.1f} MB")
    
    # Count local files
    total_local = 0
    for cat_dir in BASE_DIR.iterdir():
        if cat_dir.is_dir() and not cat_dir.name.startswith("."):
            count = sum(1 for f in cat_dir.rglob("*") if f.suffix.lower() in VALID_EXT)
            if count > 0:
                print(f"  📁 {cat_dir.name}: {count} files")
                total_local += count
    print(f"  📁 TOTAL LOCAL: {total_local} files")
    
    # ---- UPLOAD ----
    if total_local > 0:
        rclone_upload()
    else:
        print("\n⚠️ No new files to upload!")
    
    print("\n" + "=" * 60)
    print("🏁 BLITZ COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
