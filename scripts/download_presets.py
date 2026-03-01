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
    ".txp", ".prst", ".patch", ".mo", ".preset"
}

MAX_WORKERS = 8  # more aggressive for Actions

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
    ".preset": "Neural_DSP_Quad_Cortex"
}

# Core Seed Repositories to guarantee huge initial downloads without relying on search only
KNOWN_REPOS = [
    "alexander-makarov/Fractal-AxeFx2-Presets",
    "fretboardbiology/Kemper-Profiles",
    "baker-dev/Ampero-Patches",
    "Benson-Amps/TONEX-Captures",
    "amplitube/tonex-models-free",
    "Valeton/GP-200-Patches",
    "MoisesM/Helix-Presets",
    "pedalboard-presets/gx-100",
    "G6-Presets/zoom",
    "valeton/gp100-patches"
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
        "kemper profiles .kipr", "helix presets .hlx",
        "fractal axe fx presets .syx", "headrush rigs .rig",
        "boss gt-1000 patches .tsl", "tonex tone models txp",
        "quad cortex captures preset", "guitar modeler presets free",
        "pod go patches pgp", "ampero presets prst", "mooer presets mo"
    ]
    found = set(KNOWN_REPOS)
    
    for q in tqdm(queries, desc="🧠 Intelligent Search", leave=False):
        try:
            r = session.get(
                f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&per_page=50",
                timeout=10, headers={"Accept": "application/vnd.github+json"}
            )
            if r.status_code == 200:
                for repo in r.json().get("items", []):
                    if repo.get("size", 0) > 10:  # skip empty repos
                        found.add(repo["full_name"])
        except:
            pass
        time.sleep(1.5)
        
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

def download_tonehunt(session, pbar_shared):
    base_api = "https://tonehunt.org/api/v1"
    ret_files = 0
    try:
        if session.get(f"{base_api}/models?page=1&perPage=1", timeout=5).status_code != 200:
            return 0
    except: return 0

    # Getting recent models
    for page in tqdm(range(1, 40), desc="🎵 Scraping ToneHunt Presets", leave=False):
        try:
            r = session.get(f"{base_api}/models?page={page}&perPage=100&sortBy=newest", timeout=10)
            if r.status_code != 200: break
            
            data = r.json()
            items = data.get("models", data)
            if not isinstance(items, list) or not items: break
            
            for item in items:
                mid = item.get("id")
                if not mid: continue
                dl_url = f"{base_api}/models/{mid}/download"
                if cache.seen(dl_url): continue
                
                try:
                    dr = session.get(dl_url, timeout=10)
                    if dr.status_code != 200:
                        cache.mark(dl_url); continue
                    
                    fname = "ToneHunt_Model.zip"
                    cdisp = dr.headers.get('content-disposition', '')
                    if 'filename=' in cdisp:
                        fname = re.findall("filename=(.+)", cdisp)[0].strip('"')
                    
                    ext = Path(fname).suffix.lower()
                    tmp = Path(os.environ.get("TEMP", "/tmp")) / "vault_th"
                    tmp.mkdir(parents=True, exist_ok=True)
                    tp = tmp / fname
                    tp.write_bytes(dr.content)
                    
                    if ext == ".zip":
                        xd = tmp / fname.replace(".zip", "")
                        try:
                            with zipfile.ZipFile(tp) as zf: zf.extractall(xd)
                            for root, dirs, files in os.walk(xd):
                                for f in files:
                                    if Path(f).suffix.lower() in VALID_EXT:
                                        src = Path(root) / f
                                        if is_valid_preset(src) and not cache.is_dup(src):
                                            organize_file(src)
                                            ret_files += 1
                            shutil.rmtree(xd, ignore_errors=True)
                        except: pass
                    elif ext in VALID_EXT:
                        if is_valid_preset(tp) and not cache.is_dup(tp):
                            organize_file(tp)
                            ret_files += 1
                            
                    tp.unlink(missing_ok=True)
                    cache.mark(dl_url)
                except:
                    cache.mark(dl_url)
            pbar_shared.set_postfix({"Saved": ret_files})
        except: break
        
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
    
    print("\n📦 PHASE 2: ToneHunt Models & Presets")
    with tqdm(total=1, desc="📡 Fetching ToneHunt", unit="batch") as pbar:
        try: total_files += download_tonehunt(session, pbar)
        except: pass
        pbar.update(1)
        
    cache.save()
    print("\n============================================================")
    print(f"🎉 OPERATION COMPLETE! Total new valid presets imported: {total_files}")
    print("============================================================")

if __name__ == "__main__":
    main()
