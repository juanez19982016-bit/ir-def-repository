#!/usr/bin/env python3
"""
PRESET VAULT DOWNLOADER 2026 — GitHub Actions Optimized
==========================================================
- Massive Multieffect/Modeler preset extraction
- Beautiful tqdm progress bars
- Fail-fast network requests, dynamic source discovery
- Outputs directly to the provided --output-dir (for remote rclone upload)
"""
import os, sys, json, re, time, hashlib, zipfile, shutil
import argparse
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", required=True, help="Base directory for the vault")
args = parser.parse_args()

BASE_DIR = Path(args.output_dir) / "03_PRESETS_AND_MODELERS"
CACHE_FILE = BASE_DIR / ".presets_cache.json"

VALID_EXT = {
    ".kipr", ".hlx", ".pgp", ".syx", ".rig", ".tsl", 
    ".txp", ".prst", ".patch", ".mo", ".preset", ".nam", ".json", ".wav",
    ".fxp", ".fxb", ".tdy"
}

MAX_WORKERS = 12

EXT_MAP = {
    ".kipr": "Kemper_Profiler",
    ".hlx": "Line6/Helix_HXStomp",
    ".pgp": "Line6/Pod_Go",
    ".syx": "Fractal_Audio",
    ".rig": "Headrush",
    ".tsl": "Boss",
    ".txp": "IK_Multimedia_TONEX",
    ".prst": "Hotone_Ampero",
    ".patch": "Hotone_Ampero",
    ".mo": "Mooer",
    ".preset": "Neural_DSP_Quad_Cortex",
    ".nam": "Neural_Amp_Modeler",
    ".json": "Neural_Amp_Modeler_Misc",
    ".wav": "Misc_Captures",
    ".fxp": "Misc_Plugins",
    ".fxb": "Misc_Plugins_Bank",
    ".tdy": "Yamaha_THR"
}

# Core Seed Repositories
KNOWN_REPOS = [
    "alexander-makarov/Fractal-AxeFx2-Presets",
    "davedude0/NeuralAmpModelerModels",
    "screamingFrog/NAM-packs",
    "j4de/NAM-Models",
    "tansey-sern/NAM_Community_Models",
    "mfmods/mf-nam-models",
    "Pilkch/nam-models",
    "studioroberto/guitar-impulse-responses",
    "romancardenas/guitar-cabinet-ir",
    "markusaksli-nc/nam-models",
    "GuitarML/ToneLibrary",
    "pelennor2170/NAM_models",
    "MoisesM/Helix-Presets",
    "EmmanuelBeziat/helix-presets",
    "bellol/helix-presets"
]

DIRECT_ZIPS = [
    ("https://github.com/justinnewbold/fractal-ai-builder/archive/refs/heads/master.zip", "Fractal_AI_Builder"),
    ("https://github.com/ThibaultDucray/PatchOrganizer/archive/refs/heads/master.zip", "PatchOrganizer"),
    ("https://github.com/JanosGit/smallKemperRemote/archive/refs/heads/main.zip", "SmallKemperRemote"),
    ("https://github.com/Tonalize/HelixNativePresets/archive/refs/heads/main.zip", "HelixNativePresets"),
    ("https://github.com/sj-williams/pod-go-patches/archive/refs/heads/main.zip", "Pod_Go_Williams"),
    ("https://github.com/MrCitron/helaix/archive/refs/heads/main.zip", "Helaix"),
    ("https://github.com/bbuehrig/AxeFx2000/archive/refs/heads/main.zip", "AxeFx2000"),
    ("https://github.com/ray-su/Ampero-presets/archive/refs/heads/master.zip", "AmperoPresetsRaySu"),
    ("https://github.com/engageintellect/pod-go-patches/archive/refs/heads/master.zip", "PodGoEngage"),
    ("https://github.com/GuitarML/ToneLibrary/archive/refs/heads/main.zip", "GuitarML_ToneLibrary"),
    ("https://github.com/tansey-sern/NAM_Community_Models/archive/refs/heads/main.zip", "NAM_Community_1"),
    ("https://github.com/davedude0/NeuralAmpModelerModels/archive/refs/heads/main.zip", "NAM_DaveDude0"),
    ("https://github.com/screamingFrog/NAM-packs/archive/refs/heads/main.zip", "NAM_ScreamingFrog"),
    ("https://github.com/j4de/NAM-Models/archive/refs/heads/main.zip", "NAM_J4de"),
    ("https://github.com/mfmods/mf-nam-models/archive/refs/heads/main.zip", "NAM_mfmods"),
    ("https://github.com/Pilkch/nam-models/archive/refs/heads/main.zip", "NAM_Pilkch"),
    ("https://github.com/markusaksli-nc/nam-models/archive/refs/heads/main.zip", "NAM_MarkusAksli_NC"),
    ("https://github.com/pelennor2170/NAM_models/archive/refs/heads/main.zip", "NAM_Pelennor2170"),
    ("https://github.com/MoisesM/Helix-Presets/archive/refs/heads/master.zip", "Helix_Moises"),
    ("https://github.com/jyanes83/Line6-Helix-Bundle-Parser/archive/refs/heads/master.zip", "Line6_Helix_Bundle"),
    ("https://github.com/EmmanuelBeziat/helix-presets/archive/refs/heads/master.zip", "Helix_EB"),
    ("https://github.com/bellol/helix-presets/archive/refs/heads/master.zip", "Helix_Bellol"),
    ("https://github.com/bohoffi/boss-gt-1000-patch-editor/archive/refs/heads/main.zip", "BossGT1000"),
    ("https://github.com/thjorth/GT1kScenes/archive/refs/heads/main.zip", "BossGT1kScenes"),
    ("https://github.com/ThibaultDucray/TouchOSC-Hotone-Ampero-template/archive/refs/heads/master.zip", "AmperoTouchOSC"),
    ("https://github.com/bloodysummers/headrushfx-editor/archive/refs/heads/master.zip", "HeadrushEditor"),
    ("https://github.com/DrkSdeOfMnn/headrush-mx5/archive/refs/heads/master.zip", "HeadrushMX5")
]

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

def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]
    ), pool_maxsize=30))
    s.headers.update({"User-Agent": "IR-DEF-Vault-Actions/1.0"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
        print("✔ GitHub Actions Token loaded for maximum API rate limits.")
    return s

def is_valid_preset(path):
    p = Path(path)
    if p.stat().st_size < 100: return False
    return p.suffix.lower() in VALID_EXT

def categorize(filename):
    return EXT_MAP.get(Path(filename).suffix.lower(), "Misc")

def organize_file(src_path, context=""):
    fn = Path(src_path).name
    cat = categorize(fn)
    dest_dir = BASE_DIR / cat
    
    fn_lower = fn.lower()
    if cat == "Kemper_Profiler":
        if any(k in fn_lower for k in ["bass", "svt", "bajo"]):
            dest_dir = dest_dir / "Bass"
        elif any(k in fn_lower for k in ["acoust", "taylor", "martin", "piezo"]):
            dest_dir = dest_dir / "Acoustic Guitars"
        else:
            dest_dir = dest_dir / "Electric Guitars"
    elif cat == "Fractal_Audio":
        if "fm3" in fn_lower or "fm9" in fn_lower: dest_dir = dest_dir / "FM3_FM9"
        elif "axe" in fn_lower or "fxiii" in fn_lower or "fx3" in fn_lower: dest_dir = dest_dir / "Axe-Fx III"
    elif cat == "Boss":
        if "gt1000" in fn_lower or "gt-1000" in fn_lower: dest_dir = dest_dir / "GT-1000"
        elif "gx100" in fn_lower or "gx-100" in fn_lower: dest_dir = dest_dir / "GX-100"

    dest_dir.mkdir(parents=True, exist_ok=True)
    
    clean = re.sub(r'[\s\-\.]+', '_', Path(fn).stem).strip('_')[:80]
    ext = Path(fn).suffix.lower()
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

def github_search_preset_repos(session):
    print("\n🔍 Expanding Vault targets via GitHub Search...")
    queries = [
        "guitar presets", "kemper profile", "nam captures", "syx preset", 
        "helix patch", "rig preset headrush", "tsl boss", "tonex model",
        "quad cortex", "ampero patch"
    ]
    found = set(KNOWN_REPOS)
    
    for q in tqdm(queries, desc="🧠 Intelligent Deep Search", leave=False):
        for page in range(1, 10):  # Hit up to 10 pages * 100 = 1000 repos per query!
            try:
                r = session.get(
                    f"https://api.github.com/search/repositories?q={quote(q)}&sort=stars&order=desc&per_page=100&page={page}",
                    timeout=10, headers={"Accept": "application/vnd.github+json"}
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if not items: break
                    for repo in items:
                        if repo.get("size", 0) > 10:  # skip almost empty repos
                            found.add(repo["full_name"])
                else: break
            except: pass
            time.sleep(1)
        
    res = list(found)
    print(f"✔ Target locked onto {len(res)} preset databases.")
    return res

def download_repo(session, repo, pbar_shared):
    owner, name = repo.split("/", 1)
    cache_key = f"vault_v2_{owner}_{name}"
    
    ret_files = 0
    if cache.seen(cache_key):
        pbar_shared.update(1)
        return 0
    
    tmp_dir = Path(os.environ.get("TEMP", "/tmp")) / f"vault_{name}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    for branch in ["main", "master"]:
        zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
        zip_path = tmp_dir / f"{name}.zip"
        try:
            r = session.get(zip_url, stream=True, timeout=15)
            if r.status_code == 404: continue
            r.raise_for_status()
            
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024): f.write(chunk)
            
            extract_dir = tmp_dir / name
            try:
                with zipfile.ZipFile(zip_path) as zf: zf.extractall(extract_dir)
            except:
                zip_path.unlink(missing_ok=True)
                break
            
            for root, dirs, files in os.walk(extract_dir):
                for fn in files:
                    if Path(fn).suffix.lower() in VALID_EXT:
                        src = Path(root) / fn
                        try:
                            if is_valid_preset(src) and not cache.is_dup(src):
                                organize_file(src)
                                ret_files += 1
                        except: pass
            
            cache.mark(cache_key)
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
            break
        except requests.exceptions.RequestException:
            pass
            
    cache.mark(cache_key)
    pbar_shared.set_postfix({"Saved": ret_files})
    pbar_shared.update(1)
    return ret_files

def download_direct_zips(session, pbar_shared):
    ret_files = 0
    
    for url, name in tqdm(DIRECT_ZIPS, desc="🎵 Fetching Huge Preset Archives", leave=False):
        if cache.seen(url): continue
        tmp_dir = Path(os.environ.get("TEMP", "/tmp")) / f"vault_zip_{name}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = tmp_dir / f"{name}.zip"
        
        try:
            r = session.get(url, stream=True, timeout=120)
            if r.status_code != 200: continue
            
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024): f.write(chunk)
                
            extract_dir = tmp_dir / name
            try:
                with zipfile.ZipFile(zip_path) as zf: zf.extractall(extract_dir)
                for root, dirs, files in os.walk(extract_dir):
                    for fn in files:
                        if Path(fn).suffix.lower() in VALID_EXT:
                            src = Path(root) / fn
                            try:
                                if is_valid_preset(src) and not cache.is_dup(src):
                                    organize_file(src)
                                    ret_files += 1
                            except: pass
            except: pass
            
            cache.mark(url)
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
        except Exception as e:
            pass
        pbar_shared.set_postfix({"Saved": ret_files})
        
    return ret_files

def main():
    print("============================================================")
    print("🔥 THE ULTIMATE FULL-THROTTLE PRESET VAULT DOWNLOADER 2026 🔥")
    print("============================================================")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    session = make_session()
    
    repos = github_search_preset_repos(session)
    
    print("\n📦 PHASE 1: Scrape GitHub Repositories (Multi-Threaded)")
    total_files = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        with tqdm(total=len(repos), desc="📡 Cloning Databases", unit="repo") as pbar:
            futures = [executor.submit(download_repo, session, repo, pbar) for repo in repos]
            for future in as_completed(futures):
                try: total_files += future.result()
                except: pass
                
    cache.save()
    
    print("\n📦 PHASE 2: Huge Preset Archives (Direct ZIPs)")
    with tqdm(total=len(DIRECT_ZIPS), desc="📡 Fetching Direct ZIPs", unit="zip") as pbar:
        try: total_files += download_direct_zips(session, pbar)
        except: pass
        
    cache.save()
    print("\n============================================================")
    print(f"🎉 OPERATION COMPLETE! Total new valid presets imported: {total_files}")
    print("============================================================")

if __name__ == "__main__":
    main()
