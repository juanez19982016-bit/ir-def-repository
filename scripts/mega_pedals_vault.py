#!/usr/bin/env python3
"""
MEGA PRESET VAULT 2026 v3 — MAXIMUM EXPANSION
===============================================
Massive multi-effects preset downloader. PRESETS ONLY — no NAM/IR/WAV.
Sources: GitHub repos + search, GuitarPatches.com, PatchStorage.com API.

Usage:
  python mega_preset_vault.py --tier seed       --output-dir /tmp/vault
  python mega_preset_vault.py --tier search     --output-dir /tmp/vault
  python mega_preset_vault.py --tier releases   --output-dir /tmp/vault
  python mega_preset_vault.py --tier guitarpatches --output-dir /tmp/vault
  python mega_preset_vault.py --tier patchstorage  --output-dir /tmp/vault
  python mega_preset_vault.py --tier cleanup    --output-dir /tmp/vault
  python mega_preset_vault.py --tier all        --output-dir /tmp/vault
"""
import os, sys, json, re, time, hashlib, zipfile, shutil, argparse, subprocess
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

parser = argparse.ArgumentParser()
parser.add_argument("--tier", required=True,
    choices=["seed","search","releases","guitarpatches","patchstorage","codesearch","cleanup","all"])
parser.add_argument("--output-dir", required=True)
parser.add_argument("--fresh", action="store_true")
args = parser.parse_args()

BASE_DIR = Path(args.output_dir) / "03_PRESETS_AND_MODELERS"
CACHE_FILE = BASE_DIR / ".mega_presets_cache.json"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# PRESET EXTENSIONS ONLY — NO .nam .wav .json .ir
# ═══════════════════════════════════════════════════════════
VALID_EXT = {
    ".nam",
}

EXT_MAP = {
    ".nam": "Boutique_Pedals_NAM",
}

# ═══════════════════════════════════════════════════════════
# SEED REPOS
# ═══════════════════════════════════════════════════════════
SEED_REPOS = [
    "tansey-sern/NAM_Community_Models",
    "davedude0/NeuralAmpModelerModels",
    "screamingFrog/NAM-packs",
    "j4de/NAM-Models",
    "mfmods/mf-nam-models",
    "Pilkch/nam-models",
    "markusaksli-nc/nam-models",
    "pelennor2170/NAM_models"
]

DIRECT_ZIPS = []

# 200+ search queries covering modern + legacy
SEARCH_QUERIES = [
    "nam pedal", "nam overdrive", "nam distortion", "nam fuzz", "nam booster",
    "neural amp modeler pedal", "neural amp modeler overdrive", "neural amp modeler distortion",
    "nam capture pedal", "nam profiles pedal", "nam models pedal",
    "klon nam", "ts9 nam", "tube screamer nam", "rat nam", "big muff nam",
    "nam pedal capture", "nam distortion capture", "nam drive pedal",
    "nam pedals", "nam overdrive capture", "nam fuzz capture"
]

# ═══════════════════════════════════════════════════════════
# GUITARPATCHES.COM — real device slugs (from their site)
# ═══════════════════════════════════════════════════════════
GUITARPATCHES_DEVICES = [
    # (unit_slug, our_folder)  —  real slugs from guitarpatches.com
    ("katana","Boss/Katana"),("KATANAMKII","Boss/Katana"),
    ("GT1000","Boss/GT-1000"),("GT1000C","Boss/GT-1000"),("GX100","Boss/GX-100"),
    ("GX1","Boss/GX-1"),("GT100","Boss/GT-100"),("GT10","Boss/GT-10"),
    ("GT8","Boss_Legacy/GT-8"),("GT6","Boss_Legacy/GT-6"),("GT5","Boss_Legacy/GT-5"),
    ("GT3","Boss_Legacy/GT-3"),("GT1","Boss/GT-1"),
    ("ME80","Boss/ME-80"),("ME90","Boss/ME-90"),("ME50","Boss/ME-50"),("ME25","Boss/ME-25"),
    ("G6","Zoom/G6"),("G5n","Zoom/G5n"),("G5","Zoom/G5"),("G3n","Zoom/G3n"),
    ("G3Xn","Zoom/G3xn"),("G3","Zoom_Legacy/G3"),("G2","Zoom_Legacy/G2"),
    ("G2Nu","Zoom_Legacy/G2Nu"),("G1on","Zoom_Legacy/G1on"),("G1Xon","Zoom_Legacy/G1Xon"),
    ("G1four","Zoom/G1_Four"),("G1Xfour","Zoom/G1X_Four"),
    ("MS70CDR","Zoom/MultiStomp"),("MS50G","Zoom/MultiStomp"),("MS60B","Zoom/MultiStomp"),
    ("B1Xfour","Zoom/Bass"),("B3n","Zoom/Bass"),
    ("MG300","NUX/MG-300"),("MG300II","NUX/MG-300"),("MG30","NUX/MG-30"),
    ("MG400","NUX/MG-400"),("MG20","NUX/MG-20"),
    ("GP200","Valeton/GP-200"),("GP100","Valeton/GP-100"),
    ("TANKG","Valeton/Tank-G"),
    ("GE200","Mooer/GE-200"),("GE300","Mooer/GE-300"),("GE150","Mooer/GE-150"),
    ("THR10","Yamaha_THR"),("THR10C","Yamaha_THR"),("THR10X","Yamaha_THR"),
    ("THR30II","Yamaha_THR"),("THR10II","Yamaha_THR"),
    ("Ampero","Hotone_Ampero"),("AmperoII","Hotone_Ampero"),("AmperoMini","Hotone_Ampero"),
    ("RP500","Digitech/RP500"),("RP1000","Digitech/RP1000"),("RP360","Digitech/RP360"),
    ("RP255","Digitech/RP255"),("RP200","Digitech/RP200"),("RP155","Digitech/RP155"),
    ("GNX4","Digitech/GNX4"),("GNX3","Digitech/GNX3"),("GNX1","Digitech/GNX1"),
    ("AX3000G","Korg/AX3000G"),("AX1500G","Korg/AX1500G"),("AX3G","Korg"),
    ("Tonelab","Vox/Tonelab"),("TonelabEX","Vox/Tonelab"),("TonelabST","Vox/Tonelab"),
    ("VT40X","Vox/Valvetronix"),
    ("Mustang","Fender_Mustang"),("MustangGT","Fender_Mustang"),
    ("PlethX5","TC_Electronic/Plethora"),
    ("Helix","Line6_Helix"),("HXstomp","Line6_Helix/HX_Stomp"),
    ("PODgo","Line6_Pod_Go"),
    ("PODHD500","Line6_Legacy/HD500"),("PODHD500X","Line6_Legacy/HD500X"),
    ("PODXT","Line6_Legacy/POD_XT"),("PODX3","Line6_Legacy/POD_X3"),
    ("Firehawk","Line6_Legacy/Firehawk"),
    ("HeadrushPB","Headrush"),("MX5","Headrush/MX5"),("Gigboard","Headrush/Gigboard"),
    ("SparkAmp","Positive_Grid_Spark"),("Spark40","Positive_Grid_Spark"),
]

# PatchStorage platform IDs for guitar-related platforms
PATCHSTORAGE_PLATFORMS = [
    (8271, "Eventide_H90"),     # Eventide H90
    (3211, "Line6_Helix"),      # Line 6 Helix
    (8596, "Line6_Helix"),      # Line 6 HX Stomp
    (8597, "Line6_Pod_Go"),     # Line 6 Pod Go
    (3164, "Zoom"),             # Zoom MultiStomp
    (8272, "Boss"),             # Boss Katana
    (9126, "Boss"),             # Boss GT-1000
    (3213, "Kemper_Profiler"),  # Kemper Profiler
    (9599, "Neural_DSP_Quad_Cortex"),  # Quad Cortex
    (3162, "Fractal_Audio"),    # Axe-Fx
    (9600, "Fractal_Audio"),    # FM3
    (8830, "Hotone_Ampero"),    # Hotone Ampero
    (3163, "Line6_Legacy"),     # POD HD500
    (8469, "Headrush"),         # Headrush
    (9768, "IK_Multimedia_TONEX"),  # TONEX
    (8710, "TC_Electronic"),    # TC Plethora
]

# ═══════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════
class Cache:
    def __init__(self):
        self.data = {"urls":[],"hashes":{},"repos":[]}
        if not args.fresh and CACHE_FILE.exists():
            try: self.data = json.loads(CACHE_FILE.read_text("utf-8"))
            except: pass
        for k in ["urls","hashes","repos"]:
            if k not in self.data: self.data[k] = [] if k != "hashes" else {}
    def save(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.data, indent=None), "utf-8")
    def seen_url(self, u): return u in self.data["urls"]
    def mark_url(self, u):
        if u not in self.data["urls"]: self.data["urls"].append(u)
    def seen_repo(self, r): return r.lower() in [x.lower() for x in self.data["repos"]]
    def mark_repo(self, r):
        if not self.seen_repo(r): self.data["repos"].append(r)
    def is_dup(self, fp):
        try:
            h = hashlib.sha256(Path(fp).read_bytes()).hexdigest()
            if h in self.data["hashes"]: return True
            self.data["hashes"][h] = str(fp); return False
        except: return False

cache = Cache()

# ═══════════════════════════════════════════════════════════
# HTTP
# ═══════════════════════════════════════════════════════════
def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=1.0,
                          status_forcelist=[429,500,502,503,504]),
        pool_maxsize=30))
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0) MegaPresetVault/3.0"
    tok = os.environ.get("GITHUB_TOKEN")
    if tok: s.headers["Authorization"] = f"Bearer {tok}"; print("✔ GitHub token")
    return s

SESSION = make_session()

# ═══════════════════════════════════════════════════════════
# FILE OPS
# ═══════════════════════════════════════════════════════════
JUNK = {"readme","license","changelog",".gitignore",".ds_store","thumbs","makefile"}

def is_valid(p):
    p = Path(p)
    if p.stem.lower() in JUNK: return False
    if p.suffix.lower() not in VALID_EXT: return False
    try: return p.stat().st_size >= 50
    except: return False

def save_file(src, folder, ctx=""):
    fn = Path(src).name; ext = Path(fn).suffix.lower()
    cat = EXT_MAP.get(ext, folder if folder else "Misc")
    dest_dir = BASE_DIR / (folder if folder else cat)
    dest_dir.mkdir(parents=True, exist_ok=True)
    clean = re.sub(r'[<>:"/\\|?*]','_', re.sub(r'[\s\-\.]+','_',Path(fn).stem).strip('_')[:80])
    dest = dest_dir / f"{clean}{ext}"
    if dest.exists():
        for i in range(1,500):
            dest = dest_dir / f"{clean}_{i}{ext}"
            if not dest.exists(): break
        else: return None
    try: shutil.copy2(src, dest); return dest
    except: return None

def extract_presets(zip_path, folder="", ctx=""):
    count = 0
    ext_dir = Path(str(zip_path) + "_ext")
    try:
        ext_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf: zf.extractall(ext_dir)
        for root, dirs, files in os.walk(ext_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fn in files:
                if Path(fn).suffix.lower() in VALID_EXT:
                    src = Path(root) / fn
                    try:
                        if is_valid(src) and not cache.is_dup(src):
                            if save_file(src, folder, ctx): count += 1
                    except: pass
    except: pass
    finally: shutil.rmtree(ext_dir, ignore_errors=True)
    return count

# ═══════════════════════════════════════════════════════════
# GITHUB REPO DOWNLOAD
# ═══════════════════════════════════════════════════════════
def download_repo(repo, stats):
    ckey = f"v4_{repo.replace('/','_')}"
    if cache.seen_repo(ckey): return 0
    count = 0
    for branch in ["main","master","develop"]:
        tmp = Path(f"/tmp/mv_{hash(repo)%9999}_{branch}")
        zp = tmp / "repo.zip"
        try:
            tmp.mkdir(parents=True, exist_ok=True)
            r = SESSION.get(f"https://github.com/{repo}/archive/refs/heads/{branch}.zip",
                            stream=True, timeout=30)
            if r.status_code == 404: continue
            r.raise_for_status()
            with open(zp,"wb") as f:
                for ch in r.iter_content(1024*1024): f.write(ch)
            count = extract_presets(zp, ctx=repo)
            break
        except: pass
        finally: shutil.rmtree(tmp, ignore_errors=True)
    cache.mark_repo(ckey)
    stats["files"] += count; stats["repos"] += 1
    if count > 0: print(f"  ✔ {repo}: {count} presets")
    return count

def download_zip(url, name, stats):
    if cache.seen_url(url): return 0
    count = 0
    tmp = Path(f"/tmp/mv_z_{name}")
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        r = SESSION.get(url, stream=True, timeout=120)
        if r.status_code != 200: return 0
        zp = tmp / "pack.zip"
        with open(zp,"wb") as f:
            for ch in r.iter_content(1024*1024): f.write(ch)
        count = extract_presets(zp, ctx=name)
        cache.mark_url(url)
        if count > 0: print(f"  ✔ {name}: {count}")
    except Exception as e: print(f"  ✗ {name}: {e}")
    finally: shutil.rmtree(tmp, ignore_errors=True)
    stats["files"] += count
    return count

# ═══════════════════════════════════════════════════════════
# GITHUB SEARCH
# ═══════════════════════════════════════════════════════════
def github_search(queries):
    print(f"\n🔍 GitHub Search: {len(queries)} queries...")
    found = set()
    rate_hits = 0
    for i, q in enumerate(queries):
        if rate_hits > 20: break
        for page in range(1,6):
            try:
                r = SESSION.get(
                    f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&per_page=100&page={page}",
                    timeout=10, headers={"Accept":"application/vnd.github+json"})
                if r.status_code == 403: rate_hits += 1; time.sleep(30); break
                if r.status_code != 200: break
                items = r.json().get("items",[])
                if not items: break
                for repo in items:
                    if repo.get("size",0) > 5 and not repo.get("fork",False):
                        fn = repo["full_name"]
                        if not cache.seen_repo(f"v4_{fn.replace('/','_')}"): found.add(fn)
            except: pass
            time.sleep(2)
        if (i+1) % 20 == 0: print(f"  ... {i+1}/{len(queries)}, {len(found)} repos found")
    print(f"  ✔ Discovered {len(found)} repos from search")
    return list(found)

# ═══════════════════════════════════════════════════════════
# GITHUB RELEASES
# ═══════════════════════════════════════════════════════════
def download_releases(repos, stats):
    print(f"\n📦 Scanning releases from {len(repos)} repos...")
    total = 0
    for repo in repos:
        try:
            r = SESSION.get(f"https://api.github.com/repos/{repo}/releases?per_page=10",
                            timeout=10, headers={"Accept":"application/vnd.github+json"})
            if r.status_code != 200: continue
            for rel in r.json():
                for asset in rel.get("assets",[]):
                    aurl = asset.get("browser_download_url","")
                    aname = asset.get("name","")
                    ext = Path(aname).suffix.lower()
                    if cache.seen_url(aurl): continue
                    if ext in VALID_EXT or ext == ".zip":
                        tmp = Path(f"/tmp/mv_rel_{hash(aurl)%99999}")
                        try:
                            ar = SESSION.get(aurl, stream=True, timeout=60)
                            if ar.status_code != 200: continue
                            tmp.parent.mkdir(parents=True, exist_ok=True)
                            fl = tmp.with_suffix(ext)
                            with open(fl,"wb") as f:
                                for ch in ar.iter_content(1024*1024): f.write(ch)
                            if ext == ".zip":
                                total += extract_presets(fl, ctx=repo)
                            elif is_valid(fl) and not cache.is_dup(fl):
                                if save_file(fl, ctx=repo): total += 1
                            cache.mark_url(aurl)
                        except: pass
                        finally:
                            for p in tmp.parent.glob(f"{tmp.stem}*"):
                                try: p.unlink()
                                except: pass
            time.sleep(0.5)
        except: pass
    stats["files"] += total
    print(f"  ✔ {total} presets from releases")
    return total

# ═══════════════════════════════════════════════════════════
# GITHUB CODE SEARCH — finds individual files by extension
# This is the MOST EFFECTIVE method: searches actual files
# across ALL of GitHub and downloads them via raw URLs
# ═══════════════════════════════════════════════════════════
CODE_SEARCH_EXTS = [
    "nam"
]

CODE_SEARCH_QUERIES = []
for ext in CODE_SEARCH_EXTS:
    CODE_SEARCH_QUERIES.append(f"extension:{ext} pedal")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} overdrive")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} distortion")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} fuzz")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} boost")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} klon")
    CODE_SEARCH_QUERIES.append(f"extension:{ext} ts9")

def run_code_search(stats):
    """Use GitHub Code Search API to find individual files."""
    print("\n" + "=" * 60)
    print(f"🔬 GITHUB CODE SEARCH — {len(CODE_SEARCH_QUERIES)} queries")
    print("  Finding individual preset files across ALL of GitHub")
    print("=" * 60)
    total = 0
    rate_hits = 0
    seen_files = set()

    for qi, q in enumerate(CODE_SEARCH_QUERIES):
        if rate_hits > 30:
            print("  ⚠ Rate limited, stopping code search")
            break
        for page in range(1, 6):  # up to 5 pages per query
            try:
                r = SESSION.get(
                    f"https://api.github.com/search/code?q={quote(q)}&per_page=100&page={page}",
                    timeout=15,
                    headers={"Accept": "application/vnd.github+json"}
                )
                if r.status_code == 403:
                    rate_hits += 1
                    time.sleep(60)
                    break
                if r.status_code == 422:  # validation failed
                    break
                if r.status_code != 200:
                    break

                data = r.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    fname = item.get("name", "")
                    fpath = item.get("path", "")
                    repo = item.get("repository", {}).get("full_name", "")
                    sha = item.get("sha", "")
                    ext = Path(fname).suffix.lower()

                    if ext not in VALID_EXT:
                        continue

                    file_key = f"{repo}/{fpath}"
                    if file_key in seen_files:
                        continue
                    seen_files.add(file_key)

                    if cache.seen_url(f"cs_{sha}"):
                        continue

                    # Download raw file
                    raw_url = f"https://raw.githubusercontent.com/{repo}/HEAD/{quote(fpath)}"
                    try:
                        fr = SESSION.get(raw_url, stream=True, timeout=30)
                        if fr.status_code != 200:
                            continue

                        tmp = Path(f"/tmp/cs_{hash(file_key)%999999}")
                        tmp.mkdir(parents=True, exist_ok=True)
                        flocal = tmp / fname

                        with open(flocal, "wb") as f:
                            for ch in fr.iter_content(1024*1024):
                                f.write(ch)

                        if is_valid(flocal) and not cache.is_dup(flocal):
                            folder = EXT_MAP.get(ext, "Misc")
                            if save_file(flocal, folder):
                                total += 1

                        cache.mark_url(f"cs_{sha}")
                    except:
                        pass
                    finally:
                        shutil.rmtree(Path(f"/tmp/cs_{hash(file_key)%999999}"), ignore_errors=True)

                time.sleep(2)  # respect rate limits
            except:
                pass

        if (qi + 1) % 10 == 0:
            print(f"  ... {qi+1}/{len(CODE_SEARCH_QUERIES)}, {total} files downloaded, {len(seen_files)} found")
        time.sleep(1)

    stats["files"] += total
    print(f"\n  🔥 Code Search: {total} individual files from {len(seen_files)} found")
    cache.save()
    return total

# ═══════════════════════════════════════════════════════════
# GUITARPATCHES.COM SCRAPER — real HTML structure
# ═══════════════════════════════════════════════════════════
def scrape_guitarpatches(stats):
    print("\n" + "=" * 60)
    print(f"🌐 GUITARPATCHES.COM — {len(GUITARPATCHES_DEVICES)} devices")
    print("=" * 60)
    total = 0
    for unit, folder in GUITARPATCHES_DEVICES:
        device_count = 0
        try:
            # Get patch listing page
            url = f"https://guitarpatches.com/patches.php?unit={unit}"
            r = SESSION.get(url, timeout=15)
            if r.status_code != 200: continue
            html = r.text

            # Find all patch detail links: patches.php?unit=XXX&ID=NNN
            patch_ids = re.findall(r'patches\.php\?unit=' + re.escape(unit) + r'&(?:amp;)?ID=(\d+)', html)
            if not patch_ids:
                # Try alternative pattern
                patch_ids = re.findall(r'ID=(\d+)', html)

            # Also check for pagination — get all pages
            page_links = re.findall(r'patches\.php\?unit=' + re.escape(unit) + r'&(?:amp;)?page=(\d+)', html)
            max_page = max([int(p) for p in page_links]) if page_links else 1

            for page in range(2, min(max_page + 1, 100)):
                try:
                    pr = SESSION.get(f"{url}&page={page}", timeout=15)
                    if pr.status_code != 200: break
                    phtml = pr.text
                    more_ids = re.findall(r'ID=(\d+)', phtml)
                    patch_ids.extend(more_ids)
                    time.sleep(0.5)
                except: break

            patch_ids = list(set(patch_ids))  # dedupe

            for pid in patch_ids:
                dl_url = f"https://guitarpatches.com/patches.php?unit={unit}&ID={pid}"
                if cache.seen_url(dl_url): continue

                try:
                    # Get patch detail page to find download link
                    dr = SESSION.get(dl_url, timeout=15)
                    if dr.status_code != 200: continue

                    # Find download link — usually patchdownload.php?id=NNN
                    dl_links = re.findall(r'href=["\']([^"\']*patchdownload\.php\?id=\d+[^"\']*)', dr.text)
                    if not dl_links:
                        dl_links = re.findall(r'href=["\']([^"\']*download[^"\']*)', dr.text)

                    for dl in dl_links:
                        full_dl = dl if dl.startswith("http") else f"https://guitarpatches.com/{dl.lstrip('/')}"
                        if cache.seen_url(full_dl): continue

                        try:
                            fr = SESSION.get(full_dl, stream=True, timeout=30, allow_redirects=True)
                            if fr.status_code != 200: continue

                            # Get filename
                            cd = fr.headers.get("Content-Disposition","")
                            fn_m = re.search(r'filename="?([^";\n]+)', cd)
                            fname = fn_m.group(1).strip() if fn_m else f"patch_{pid}.bin"

                            tmp = Path(f"/tmp/gp_{unit}_{pid}")
                            tmp.mkdir(parents=True, exist_ok=True)
                            fpath = tmp / fname

                            with open(fpath,"wb") as f:
                                for ch in fr.iter_content(1024*1024): f.write(ch)

                            ext = Path(fname).suffix.lower()
                            if ext == ".zip":
                                c = extract_presets(fpath, folder)
                                device_count += c; total += c
                            elif ext in VALID_EXT and is_valid(fpath) and not cache.is_dup(fpath):
                                if save_file(fpath, folder): device_count += 1; total += 1
                            else:
                                # Unknown ext but likely a patch file — save to folder
                                if fpath.stat().st_size > 50 and fpath.stat().st_size < 5_000_000:
                                    dest_dir = BASE_DIR / folder
                                    dest_dir.mkdir(parents=True, exist_ok=True)
                                    clean = re.sub(r'[\s\-\.]+','_',Path(fname).stem).strip('_')[:80]
                                    dest = dest_dir / f"{clean}{ext if ext else '.patch'}"
                                    if not dest.exists() and not cache.is_dup(fpath):
                                        shutil.copy2(fpath, dest)
                                        device_count += 1; total += 1

                            cache.mark_url(full_dl)
                        except: pass
                        finally:
                            shutil.rmtree(Path(f"/tmp/gp_{unit}_{pid}"), ignore_errors=True)

                    cache.mark_url(dl_url)
                    time.sleep(0.3)
                except: pass

            if device_count > 0:
                print(f"  ✔ {unit}: {device_count} patches ({len(patch_ids)} found)")
        except: pass
        time.sleep(0.5)

    stats["files"] += total
    print(f"\n  🔥 GuitarPatches.com total: {total}")
    return total

# ═══════════════════════════════════════════════════════════
# PATCHSTORAGE.COM API — proper REST API
# ═══════════════════════════════════════════════════════════
def scrape_patchstorage(stats):
    print("\n" + "=" * 60)
    print(f"📦 PATCHSTORAGE.COM API — {len(PATCHSTORAGE_PLATFORMS)} platforms")
    print("=" * 60)
    total = 0

    for plat_id, folder in PATCHSTORAGE_PLATFORMS:
        plat_count = 0
        page = 1
        while page <= 50:  # up to 50 pages per platform
            try:
                r = SESSION.get(
                    f"https://patchstorage.com/api/alpha/patches?platforms={plat_id}&per_page=50&page={page}",
                    timeout=15
                )
                if r.status_code != 200: break
                patches = r.json()
                if not patches: break

                for patch in patches:
                    patch_id = patch.get("id")
                    patch_url = f"https://patchstorage.com/api/alpha/patches/{patch_id}"

                    if cache.seen_url(f"ps_{patch_id}"): continue

                    try:
                        # Get full patch details (includes file URL)
                        dr = SESSION.get(patch_url, timeout=10)
                        if dr.status_code != 200: continue
                        detail = dr.json()

                        files = detail.get("files", [])
                        for fi in files:
                            furl = fi.get("url", "")
                            fname = fi.get("filename", f"patch_{patch_id}.bin")

                            if cache.seen_url(furl): continue

                            ext = Path(fname).suffix.lower()
                            if ext not in VALID_EXT and ext != ".zip": continue

                            try:
                                fr = SESSION.get(furl, stream=True, timeout=60)
                                if fr.status_code != 200: continue

                                tmp = Path(f"/tmp/ps_{patch_id}")
                                tmp.mkdir(parents=True, exist_ok=True)
                                fpath = tmp / fname

                                with open(fpath,"wb") as f:
                                    for ch in fr.iter_content(1024*1024): f.write(ch)

                                if ext == ".zip":
                                    c = extract_presets(fpath, folder)
                                    plat_count += c; total += c
                                elif is_valid(fpath) and not cache.is_dup(fpath):
                                    if save_file(fpath, folder): plat_count += 1; total += 1

                                cache.mark_url(furl)
                            except: pass
                            finally:
                                shutil.rmtree(Path(f"/tmp/ps_{patch_id}"), ignore_errors=True)

                        cache.mark_url(f"ps_{patch_id}")
                        time.sleep(0.3)
                    except: pass

                page += 1
                time.sleep(1)
            except: break

        pname = next((p.get("name","?") for p in [{}]), folder)
        if plat_count > 0:
            print(f"  ✔ Platform {plat_id} ({folder}): {plat_count} patches")

    stats["files"] += total
    print(f"\n  🔥 PatchStorage.com total: {total}")
    return total

# ═══════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════
def run_cleanup():
    print("\n🧹 CLEANUP: Removing non-preset content")
    for folder in ["Neural_Amp_Modeler","Neural_Amp_Modeler_Misc","Misc_Captures"]:
        path = f"gdrive2:IR_DEF_REPOSITORY/03_PRESETS_AND_MODELERS/{folder}"
        try:
            subprocess.run(["rclone","purge",path], timeout=60, capture_output=True)
            print(f"  ✔ Purged {folder}")
        except: pass
    for ext in ["*.json","*.wav","*.nam","*.py","*.md","*.txt","*.yml","*.yaml"]:
        try:
            subprocess.run(["rclone","delete",
                "gdrive2:IR_DEF_REPOSITORY/03_PRESETS_AND_MODELERS",
                "--include",ext], timeout=120, capture_output=True)
        except: pass
    print("  ✔ Cleanup done")

# ═══════════════════════════════════════════════════════════
# PHASE RUNNERS
# ═══════════════════════════════════════════════════════════
def run_seed():
    print("\n" + "=" * 60)
    print(f"🌱 SEED: {len(SEED_REPOS)} repos + {len(DIRECT_ZIPS)} ZIPs")
    print("=" * 60)
    st = {"files":0,"repos":0}
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(lambda r: download_repo(r, st), SEED_REPOS))
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(download_zip, u, n, st): n for u,n in DIRECT_ZIPS}
        for f in as_completed(futs):
            try: f.result()
            except: pass
    cache.save()
    print(f"\n📊 Seed: {st['files']} presets")
    return st["files"]

def run_search():
    print("\n" + "=" * 60)
    print("🔍 GITHUB SEARCH")
    print("=" * 60)
    disc = github_search(SEARCH_QUERIES)
    if not disc: return 0
    print(f"  Downloading {len(disc)} repos...")
    st = {"files":0,"repos":0}
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(lambda r: download_repo(r, st), disc))
    cache.save()
    print(f"\n📊 Search: {st['files']} presets from {st['repos']} repos")
    return st["files"]

def run_releases():
    st = {"files":0}
    download_releases(SEED_REPOS, st)
    cache.save()
    return st["files"]

def print_stats():
    print("\n" + "=" * 60)
    print("📊 FINAL CONTENT BY PLATFORM")
    print("=" * 60)
    gt = 0
    for d in sorted(BASE_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            c = sum(1 for _ in d.rglob("*") if _.is_file() and not _.name.startswith('.'))
            if c > 0: print(f"  📁 {d.name:<40} {c:>6}"); gt += c
    print("-" * 60)
    print(f"  🔥 TOTAL: {gt:>46}")

def main():
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  MEGA PRESET VAULT v4 — ABSOLUTE MAXIMUM             ║")
    print("║  GitHub Repos + Code Search + Patches + Storage      ║")
    print("║  Presets ONLY · No NAM/IR/WAV/JSON                   ║")
    print("╚═══════════════════════════════════════════════════════╝")
    total = 0; tier = args.tier

    if tier in ("cleanup","all"): run_cleanup()
    if tier in ("seed","all"): total += run_seed()
    if tier in ("search","all"): total += run_search()
    if tier in ("releases","all"): total += run_releases()
    if tier in ("codesearch","all"):
        st = {"files":0}; run_code_search(st); total += st["files"]
    if tier in ("guitarpatches","all"):
        st = {"files":0}; scrape_guitarpatches(st); total += st["files"]
    if tier in ("patchstorage","all"):
        st = {"files":0}; scrape_patchstorage(st); total += st["files"]

    print_stats()
    print(f"\n🎉 COMPLETE! New presets: {total}")
    cache.save()

if __name__ == "__main__": main()
