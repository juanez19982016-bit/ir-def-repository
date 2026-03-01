#!/usr/bin/env python3
"""
MEGA PRESET VAULT 2026 v2 — PRESETS ONLY (No NAM/IR/WAV)
==========================================================
Massive multi-effects preset downloader for GitHub Actions.
Only downloads real preset files for modelers/multi-effects.
Fault-tolerant: each source individually wrapped.

Usage:
  python mega_preset_vault.py --tier seed       --output-dir /tmp/vault
  python mega_preset_vault.py --tier search     --output-dir /tmp/vault
  python mega_preset_vault.py --tier releases   --output-dir /tmp/vault
  python mega_preset_vault.py --tier patches    --output-dir /tmp/vault
  python mega_preset_vault.py --tier all        --output-dir /tmp/vault
"""
import os, sys, json, re, time, hashlib, zipfile, shutil, argparse
from pathlib import Path
from urllib.parse import quote, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

parser = argparse.ArgumentParser()
parser.add_argument("--tier", required=True, choices=["seed", "search", "releases", "patches", "cleanup", "all"])
parser.add_argument("--output-dir", required=True)
parser.add_argument("--fresh", action="store_true")
args = parser.parse_args()

BASE_DIR = Path(args.output_dir) / "03_PRESETS_AND_MODELERS"
CACHE_FILE = BASE_DIR / ".mega_presets_cache.json"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# ONLY real multi-effects preset extensions — NO .nam .wav .json
# ═══════════════════════════════════════════════════════════════
VALID_EXT = {
    ".hlx",      # Line 6 Helix / HX Stomp
    ".hbe",      # Helix bundle export
    ".pgp",      # Pod Go
    ".l6t",      # Line 6 legacy (POD XT, X3)
    ".l6p",      # Line 6 legacy patch
    ".5xt",      # POD XT
    ".b5p",      # Bass POD
    ".syx",      # Fractal Audio / MIDI SysEx presets
    ".kipr",     # Kemper Profiler rig
    ".krig",     # Kemper rig
    ".tsl",      # Boss TONE STUDIO liveset
    ".liveset",  # Boss liveset
    ".txp",      # IK Multimedia TONEX
    ".prst",     # Hotone Ampero / preset generic
    ".patch",    # Hotone Ampero / generic patch
    ".mo",       # Mooer
    ".preset",   # Neural DSP Quad Cortex
    ".rig",      # Headrush / generic rig
    ".zd2",      # Zoom effect/patch
    ".zdt",      # Zoom tone data
    ".nux",      # NUX
    ".gxp",      # Valeton GP series
    ".tdy",      # Yamaha THR
    ".fxp",      # VST preset (generic)
    ".fxb",      # VST bank
    ".spk",      # Positive Grid Spark
    ".zd2e",     # Zoom extended
    ".ms3p",     # Zoom MS patch
    ".g5n",      # Zoom G5n data
    ".g6p",      # Zoom G6 patch data
    ".bos",      # Boss backup
    ".gt1",      # Boss GT-1
    ".gx1p",     # Boss GX-1 patch
    ".me80",     # Boss ME-80 data
    ".me90",     # Boss ME-90 data
}

EXT_MAP = {
    ".hlx": "Line6_Helix", ".hbe": "Line6_Helix",
    ".pgp": "Line6_Pod_Go",
    ".l6t": "Line6_Legacy", ".l6p": "Line6_Legacy",
    ".5xt": "Line6_Legacy", ".b5p": "Line6_Legacy",
    ".syx": "Fractal_Audio",
    ".kipr": "Kemper_Profiler", ".krig": "Kemper_Profiler",
    ".tsl": "Boss", ".liveset": "Boss", ".bos": "Boss",
    ".gt1": "Boss", ".gx1p": "Boss", ".me80": "Boss", ".me90": "Boss",
    ".txp": "IK_Multimedia_TONEX",
    ".prst": "Hotone_Ampero", ".patch": "Hotone_Ampero",
    ".mo": "Mooer",
    ".preset": "Neural_DSP_Quad_Cortex",
    ".rig": "Headrush",
    ".zd2": "Zoom", ".zdt": "Zoom", ".zd2e": "Zoom",
    ".ms3p": "Zoom", ".g5n": "Zoom", ".g6p": "Zoom",
    ".nux": "NUX",
    ".gxp": "Valeton",
    ".tdy": "Yamaha_THR",
    ".fxp": "Misc_Plugins", ".fxb": "Misc_Plugins",
    ".spk": "Positive_Grid_Spark",
}

SUB_CATS = {
    "Fractal_Audio": {
        "fm3": "FM3_FM9", "fm9": "FM3_FM9",
        "axe": "Axe-Fx", "fxiii": "Axe-Fx", "fx3": "Axe-Fx", "fx2": "Axe-Fx_II",
    },
    "Boss": {
        "gt1000": "GT-1000", "gt-1000": "GT-1000",
        "gx100": "GX-100", "gx-100": "GX-100",
        "gx1": "GX-1", "gx-1": "GX-1",
        "katana": "Katana", "me-": "ME_Series", "me80": "ME_Series", "me90": "ME_Series",
    },
    "Zoom": {
        "g6": "G6", "g5n": "G5n", "g5": "G5",
        "ms70": "MultiStomp", "ms-70": "MultiStomp",
        "ms50": "MultiStomp", "ms-50": "MultiStomp",
    },
    "Line6_Helix": {
        "stomp": "HX_Stomp", "hx": "HX_Stomp",
        "native": "Helix_Native", "floor": "Helix_Floor",
    },
}

# ═══════════════════════════════════════════════════════════════
# SEED REPOS — only repos known to contain actual preset files
# ═══════════════════════════════════════════════════════════════
SEED_REPOS = [
    # ── Helix / Pod Go / Line 6 ──
    "MoisesM/Helix-Presets",
    "EmmanuelBeziat/helix-presets",
    "bellol/helix-presets",
    "Tonalize/HelixNativePresets",
    "sj-williams/pod-go-patches",
    "engageintellect/pod-go-patches",
    "jyanes83/Line6-Helix-Bundle-Parser",
    "MrCitron/helaix",
    "niksoper/helix-presets",
    "TylerK07/Helix-Patches",
    "jbmikk/helix-presets",
    "mattlemmone/helix-presets",
    "rawkode/line6-helix",
    "danbuckland/helix-presets",
    "chrishoward/podgo-patches",
    "lardinstruments/helix-preset-ripper",
    "rvnrstnsyh/Line6-Helix-Patches",
    "olioapps/helix-patches",
    "lukemcd/helix-presets",
    # ── Fractal Audio ──
    "alexander-makarov/Fractal-AxeFx2-Presets",
    "bbuehrig/AxeFx2000",
    "justinnewbold/fractal-ai-builder",
    "ThibaultDucray/PatchOrganizer",
    "mguedesbarros/Fractal-Audio-Presets",
    "petermuessig/axe-fx-presets",
    # ── Boss ──
    "bohoffi/boss-gt-1000-patch-editor",
    "thjorth/GT1kScenes",
    "fourth44/boss-gt1000",
    "lamparom2025/GT1000-UNLEASHED",
    "dmillard14/boss-katana-patches",
    "snhirsch/katana-patches",
    # ── Kemper ──
    "JanosGit/smallKemperRemote",
    "paynterf/KemperUtilities",
    # ── Ampero / Hotone ──
    "ray-su/Ampero-presets",
    "ThibaultDucray/TouchOSC-Hotone-Ampero-template",
    # ── Headrush ──
    "bloodysummers/headrushfx-editor",
    "DrkSdeOfMnn/headrush-mx5",
    "pdec5504/MX5-rig-manager",
    "rockrep/headrush-browser",
    # ── Zoom ──
    "G6-Presets/zoom",
    "g200kg/zoom-ms-utility",
    "thepensivepoet/zoom-guitar-patches",
    "shooking/zoom-ms70cdr-patches",
    # ── Valeton ──
    "ciyi/Valeton-GP-Preset-Sorter",
]

DIRECT_ZIPS = [
    ("https://github.com/alexander-makarov/Fractal-AxeFx2-Presets/archive/refs/heads/master.zip", "Fractal_Makarov"),
    ("https://github.com/bbuehrig/AxeFx2000/archive/refs/heads/main.zip", "AxeFx2000"),
    ("https://github.com/MoisesM/Helix-Presets/archive/refs/heads/master.zip", "Helix_Moises"),
    ("https://github.com/Tonalize/HelixNativePresets/archive/refs/heads/main.zip", "HelixNative"),
    ("https://github.com/sj-williams/pod-go-patches/archive/refs/heads/main.zip", "PodGo_Williams"),
    ("https://github.com/engageintellect/pod-go-patches/archive/refs/heads/master.zip", "PodGo_Engage"),
    ("https://github.com/EmmanuelBeziat/helix-presets/archive/refs/heads/master.zip", "Helix_EB"),
    ("https://github.com/bellol/helix-presets/archive/refs/heads/master.zip", "Helix_Bellol"),
    ("https://github.com/jyanes83/Line6-Helix-Bundle-Parser/archive/refs/heads/master.zip", "Helix_Bundle"),
    ("https://github.com/MrCitron/helaix/archive/refs/heads/main.zip", "Helaix"),
    ("https://github.com/justinnewbold/fractal-ai-builder/archive/refs/heads/master.zip", "FractalAI"),
    ("https://github.com/ThibaultDucray/PatchOrganizer/archive/refs/heads/master.zip", "PatchOrganizer"),
    ("https://github.com/JanosGit/smallKemperRemote/archive/refs/heads/main.zip", "KemperRemote"),
    ("https://github.com/bohoffi/boss-gt-1000-patch-editor/archive/refs/heads/main.zip", "BossGT1000"),
    ("https://github.com/thjorth/GT1kScenes/archive/refs/heads/main.zip", "BossGT1kScenes"),
    ("https://github.com/ray-su/Ampero-presets/archive/refs/heads/master.zip", "AmperoRaySu"),
    ("https://github.com/bloodysummers/headrushfx-editor/archive/refs/heads/master.zip", "HeadrushEditor"),
    ("https://github.com/DrkSdeOfMnn/headrush-mx5/archive/refs/heads/master.zip", "HeadrushMX5"),
    ("https://github.com/pdec5504/MX5-rig-manager/archive/refs/heads/master.zip", "HeadrushMX5Mgr"),
    ("https://github.com/G6-Presets/zoom/archive/refs/heads/main.zip", "ZoomG6"),
    ("https://github.com/g200kg/zoom-ms-utility/archive/refs/heads/master.zip", "ZoomMSUtility"),
    ("https://github.com/ciyi/Valeton-GP-Preset-Sorter/archive/refs/heads/main.zip", "ValetonSorter"),
    ("https://github.com/niksoper/helix-presets/archive/refs/heads/master.zip", "Helix_Niksoper"),
    ("https://github.com/rockrep/headrush-browser/archive/refs/heads/master.zip", "HeadrushBrowser"),
    ("https://github.com/ThibaultDucray/TouchOSC-Hotone-Ampero-template/archive/refs/heads/master.zip", "AmperoTouchOSC"),
    ("https://github.com/fourth44/boss-gt1000/archive/refs/heads/master.zip", "BossGT1000_2"),
    ("https://github.com/lamparom2025/GT1000-UNLEASHED/archive/refs/heads/main.zip", "BossGT1000_Unleashed"),
    ("https://github.com/thepensivepoet/zoom-guitar-patches/archive/refs/heads/master.zip", "ZoomPatches"),
]

# ═══════════════════════════════════════════════════════════════
# GITHUB SEARCH QUERIES — focused on preset file extensions
# ═══════════════════════════════════════════════════════════════
SEARCH_QUERIES = [
    # Direct extension search (most effective)
    "extension:hlx", "extension:hlx guitar", "extension:hlx preset",
    "extension:hlx helix", "extension:hlx patch", "extension:hlx tone",
    "extension:hlx stomp", "extension:hlx worship", "extension:hlx metal",
    "extension:hlx blues", "extension:hlx rock", "extension:hlx clean",
    "extension:hlx bass", "extension:hlx acoustic", "extension:hlx ambient",
    "extension:pgp guitar", "extension:pgp preset", "extension:pgp pod",
    "extension:pgp patch", "extension:pgp go",
    "extension:syx guitar", "extension:syx preset", "extension:syx fractal",
    "extension:syx axe", "extension:syx midi", "extension:syx amp",
    "extension:syx patch", "extension:syx tone",
    "extension:tsl guitar", "extension:tsl boss", "extension:tsl patch",
    "extension:tsl liveset", "extension:tsl preset", "extension:tsl tone",
    "extension:tsl katana", "extension:tsl gt",
    "extension:kipr kemper", "extension:kipr guitar", "extension:kipr profile",
    "extension:kipr rig", "extension:kipr amp",
    "extension:txp tonex", "extension:txp guitar", "extension:txp preset",
    "extension:txp amp", "extension:txp model", "extension:txp tone",
    "extension:prst guitar", "extension:prst ampero", "extension:prst preset",
    "extension:prst hotone", "extension:prst patch",
    "extension:preset guitar", "extension:preset neural", "extension:preset quad",
    "extension:preset cortex", "extension:preset amp",
    "extension:rig guitar", "extension:rig headrush", "extension:rig preset",
    "extension:rig amp", "extension:rig patch",
    "extension:zd2 zoom", "extension:zd2 guitar", "extension:zd2 patch",
    "extension:zd2 effect", "extension:zd2 multistomp",
    "extension:l6t guitar", "extension:l6t preset", "extension:l6t line6",
    "extension:l6t pod", "extension:l6t tone",
    "extension:mo mooer", "extension:mo guitar", "extension:mo preset",
    "extension:tdy yamaha", "extension:tdy guitar", "extension:tdy thr",
    "extension:fxp guitar", "extension:fxp preset", "extension:fxp amp",
    "extension:fxb guitar", "extension:fxb bank",
    "extension:patch guitar", "extension:patch ampero", "extension:patch hotone",
    "extension:spk spark", "extension:spk guitar",
    # Product-focused queries
    "helix preset", "helix patch", "helix presets collection",
    "helix stomp preset", "hx stomp patch", "hx effects presets",
    "helix worship", "helix metal", "helix blues", "helix rock",
    "helix country", "helix jazz", "helix ambient",
    "helix preset pack", "helix tone pack",
    "pod go patch", "pod go preset", "pod go patches collection",
    "pod go worship", "pod go metal",
    "axe-fx preset", "axe fx preset", "axe-fx patch collection",
    "fractal audio preset", "fm3 preset", "fm9 preset",
    "fractal preset pack", "axe-fx III preset",
    "kemper profile pack", "kemper rig collection", "kemper profiler preset",
    "kemper profiles free", "kemper community rigs",
    "quad cortex preset", "quad cortex patch collection",
    "neural dsp preset", "neural dsp patch",
    "cortex cloud preset", "qc preset",
    "tonex preset", "tonex model collection", "tonex tone model pack",
    "tonex capture collection", "ik multimedia tonex presets",
    "boss gt-1000 patch", "boss gt1000 preset collection",
    "boss gx-100 patch", "boss gx100 preset",
    "boss gx-1 preset", "boss katana preset collection",
    "boss me-80 patch", "boss me80 preset", "boss me-90 preset",
    "boss gt-1 preset", "boss tone studio preset",
    "headrush preset collection", "headrush rig pack",
    "headrush mx5 preset", "headrush pedalboard patch",
    "headrush gigboard preset",
    "zoom g5n patch collection", "zoom g6 preset pack",
    "zoom multistomp preset", "zoom ms-70cdr patch pack",
    "zoom ms-50g preset", "zoom guitar patch collection",
    "zoom g3n preset", "zoom g3xn patch",
    "ampero preset pack", "ampero patch collection", "hotone ampero presets",
    "ampero ii preset", "ampero mini patch",
    "mooer ge300 preset pack", "mooer ge200 patch collection",
    "mooer ge150 preset", "mooer preset pack",
    "nux mg-300 patch collection", "nux mg300 preset pack",
    "nux mg-400 patch", "nux mg400 preset",
    "nux cerberus preset",
    "valeton gp-200 preset", "valeton gp200 patch collection",
    "valeton gp-100 preset pack",
    "guitar preset pack free", "guitar presets collection free",
    "guitar patch collection download", "guitar tone preset pack",
    "guitar amp preset collection", "guitar multi effects preset pack",
    "multieffects patch collection", "guitar processor preset pack",
    "positive grid spark preset", "spark amp preset pack",
    "yamaha thr preset collection", "yamaha thr patch",
    "worship guitar preset pack", "worship guitar patch collection",
    "metal guitar preset pack", "blues guitar preset collection",
    "rock guitar preset pack", "jazz guitar preset collection",
    "bass preset pack", "bass guitar multi effects patch",
    "guitar effects preset collection", "pedalboard preset pack",
    "line6 preset", "line6 patch collection",
]

# ═══════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════
class Cache:
    def __init__(self):
        self.data = {"urls": [], "hashes": {}, "repos": []}
        if not args.fresh and CACHE_FILE.exists():
            try: self.data = json.loads(CACHE_FILE.read_text("utf-8"))
            except: pass
        for k in ["urls", "hashes", "repos"]:
            if k not in self.data: self.data[k] = [] if k != "hashes" else {}

    def save(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.data, indent=None), "utf-8")

    def seen_url(self, url): return url in self.data["urls"]
    def mark_url(self, url):
        if url not in self.data["urls"]: self.data["urls"].append(url)

    def seen_repo(self, repo): return repo.lower() in [r.lower() for r in self.data["repos"]]
    def mark_repo(self, repo):
        if not self.seen_repo(repo): self.data["repos"].append(repo)

    def is_dup(self, filepath):
        try:
            h = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
            if h in self.data["hashes"]: return True
            self.data["hashes"][h] = str(filepath)
            return False
        except: return False

cache = Cache()

# ═══════════════════════════════════════════════════════════════
# HTTP SESSION
# ═══════════════════════════════════════════════════════════════
def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=1.0,
                          status_forcelist=[429, 500, 502, 503, 504]),
        pool_maxsize=30
    ))
    s.headers.update({"User-Agent": "MegaPresetVault/2.0"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
        print("✔ GitHub token loaded")
    return s

SESSION = make_session()

# ═══════════════════════════════════════════════════════════════
# FILE HANDLING
# ═══════════════════════════════════════════════════════════════
JUNK_STEMS = {"readme", "license", "changelog", "contributing", "makefile",
    ".gitignore", ".gitattributes", "dockerfile", "requirements", "setup",
    "package", "node_modules", "__pycache__", ".ds_store", "thumbs"}

def is_valid_preset(path):
    p = Path(path)
    if p.stem.lower() in JUNK_STEMS: return False
    if p.suffix.lower() not in VALID_EXT: return False
    try:
        if p.stat().st_size < 50: return False
    except: return False
    return True

def categorize(filename, ctx=""):
    ext = Path(filename).suffix.lower()
    cat = EXT_MAP.get(ext, "Misc")
    fn_lower = (filename + " " + ctx).lower()
    if cat in SUB_CATS:
        for kw, sub in SUB_CATS[cat].items():
            if kw in fn_lower: return cat, sub
    return cat, ""

def organize_file(src_path, ctx=""):
    fn = Path(src_path).name
    cat, sub = categorize(fn, ctx)
    dest_dir = BASE_DIR / cat
    if sub: dest_dir = dest_dir / sub
    dest_dir.mkdir(parents=True, exist_ok=True)

    clean = re.sub(r'[\s\-\.]+', '_', Path(fn).stem).strip('_')[:80]
    ext = Path(fn).suffix.lower()
    name = re.sub(r'[<>:"/\\|?*]', '_', f"{clean}{ext}")

    dest = dest_dir / name
    if dest.exists():
        for i in range(1, 200):
            dest = dest_dir / f"{clean}_{i}{ext}"
            if not dest.exists(): break
        else: return None

    try:
        shutil.copy2(src_path, dest)
        return dest
    except: return None

# ═══════════════════════════════════════════════════════════════
# DOWNLOAD GITHUB REPO
# ═══════════════════════════════════════════════════════════════
def download_repo(repo, stats):
    owner, name = repo.split("/", 1)
    ckey = f"v3_{owner}_{name}"
    if cache.seen_repo(ckey): return 0

    count = 0
    for branch in ["main", "master", "develop"]:
        tmp = Path("/tmp") / f"mv_{name}_{hash(repo)%9999}"
        tmp.mkdir(parents=True, exist_ok=True)
        zp = tmp / "repo.zip"
        try:
            r = SESSION.get(f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip",
                             stream=True, timeout=30)
            if r.status_code == 404: continue
            r.raise_for_status()
            with open(zp, "wb") as f:
                for chunk in r.iter_content(1024*1024): f.write(chunk)

            ext_dir = tmp / "ext"
            with zipfile.ZipFile(zp) as zf: zf.extractall(ext_dir)
            for root, dirs, files in os.walk(ext_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fn in files:
                    if Path(fn).suffix.lower() in VALID_EXT:
                        src = Path(root) / fn
                        try:
                            if is_valid_preset(src) and not cache.is_dup(src):
                                if organize_file(src, repo): count += 1
                        except: pass
            break
        except: pass
        finally: shutil.rmtree(tmp, ignore_errors=True)

    cache.mark_repo(ckey)
    stats["files"] += count
    stats["repos"] += 1
    if count > 0: print(f"  ✔ {repo}: {count} presets")
    return count

# ═══════════════════════════════════════════════════════════════
# DOWNLOAD DIRECT ZIP
# ═══════════════════════════════════════════════════════════════
def download_zip(url, name, stats):
    if cache.seen_url(url): return 0
    count = 0
    tmp = Path("/tmp") / f"mv_z_{name}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        r = SESSION.get(url, stream=True, timeout=120)
        if r.status_code != 200: return 0
        zp = tmp / "pack.zip"
        with open(zp, "wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)
        ext_dir = tmp / "ext"
        with zipfile.ZipFile(zp) as zf: zf.extractall(ext_dir)
        for root, dirs, files in os.walk(ext_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fn in files:
                if Path(fn).suffix.lower() in VALID_EXT:
                    src = Path(root) / fn
                    try:
                        if is_valid_preset(src) and not cache.is_dup(src):
                            if organize_file(src, name): count += 1
                    except: pass
        cache.mark_url(url)
        if count > 0: print(f"  ✔ {name}: {count} presets")
    except Exception as e: print(f"  ✗ {name}: {e}")
    finally: shutil.rmtree(tmp, ignore_errors=True)
    stats["files"] += count
    return count

# ═══════════════════════════════════════════════════════════════
# GITHUB SEARCH
# ═══════════════════════════════════════════════════════════════
def github_search(queries):
    print(f"\n🔍 GitHub Search: {len(queries)} queries...")
    found = set()
    rate_hits = 0
    done = 0
    for q in queries:
        if rate_hits > 15: break
        for page in range(1, 8):
            try:
                r = SESSION.get(
                    f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&order=desc&per_page=100&page={page}",
                    timeout=10, headers={"Accept": "application/vnd.github+json"})
                if r.status_code == 403:
                    rate_hits += 1; time.sleep(30); break
                if r.status_code != 200: break
                items = r.json().get("items", [])
                if not items: break
                for repo in items:
                    if repo.get("size", 0) > 5 and not repo.get("fork", False):
                        full = repo["full_name"]
                        if not cache.seen_repo(f"v3_{full.replace('/', '_')}"):
                            found.add(full)
            except: pass
            time.sleep(2)
        done += 1
        if done % 25 == 0: print(f"  ... {done}/{len(queries)} queries, {len(found)} repos")
    print(f"  ✔ Discovered {len(found)} repos")
    return list(found)

# ═══════════════════════════════════════════════════════════════
# GITHUB RELEASES
# ═══════════════════════════════════════════════════════════════
def download_releases(repos, stats):
    print(f"\n📦 Scanning releases from {len(repos)} repos...")
    total = 0
    for repo in repos:
        try:
            r = SESSION.get(f"https://api.github.com/repos/{repo}/releases?per_page=10",
                            timeout=10, headers={"Accept": "application/vnd.github+json"})
            if r.status_code != 200: continue
            for release in r.json():
                for asset in release.get("assets", []):
                    aname = asset.get("name", "")
                    aurl = asset.get("browser_download_url", "")
                    ext = Path(aname).suffix.lower()
                    if cache.seen_url(aurl): continue

                    if ext in VALID_EXT:
                        tmp = Path("/tmp") / f"mv_rel_{aname}"
                        try:
                            ar = SESSION.get(aurl, stream=True, timeout=60)
                            if ar.status_code != 200: continue
                            with open(tmp, "wb") as f:
                                for chunk in ar.iter_content(1024*1024): f.write(chunk)
                            if is_valid_preset(tmp) and not cache.is_dup(tmp):
                                if organize_file(tmp, repo): total += 1
                            cache.mark_url(aurl)
                        except: pass
                        finally: tmp.unlink(missing_ok=True)

                    elif ext == ".zip":
                        tmp_z = Path("/tmp") / f"mv_relz_{aname}"
                        ext_d = Path("/tmp") / f"mv_relx_{aname}"
                        try:
                            ar = SESSION.get(aurl, stream=True, timeout=60)
                            if ar.status_code != 200: continue
                            with open(tmp_z, "wb") as f:
                                for chunk in ar.iter_content(1024*1024): f.write(chunk)
                            ext_d.mkdir(parents=True, exist_ok=True)
                            with zipfile.ZipFile(tmp_z) as zf: zf.extractall(ext_d)
                            for root, dirs, files in os.walk(ext_d):
                                dirs[:] = [d for d in dirs if not d.startswith('.')]
                                for fn in files:
                                    if Path(fn).suffix.lower() in VALID_EXT:
                                        src = Path(root) / fn
                                        try:
                                            if is_valid_preset(src) and not cache.is_dup(src):
                                                if organize_file(src, repo): total += 1
                                        except: pass
                            cache.mark_url(aurl)
                        except: pass
                        finally:
                            tmp_z.unlink(missing_ok=True)
                            shutil.rmtree(ext_d, ignore_errors=True)
            time.sleep(1)
        except: pass
    stats["files"] += total
    print(f"  ✔ Got {total} presets from releases")
    return total

# ═══════════════════════════════════════════════════════════════
# GUITARPATCHES.COM SCRAPER — huge source of patches
# ═══════════════════════════════════════════════════════════════
GUITARPATCHES_DEVICES = [
    # (slug, platform_folder, pages_to_scrape)
    ("zoom-g5n", "Zoom/G5n", 50),
    ("zoom-g6", "Zoom/G6", 30),
    ("zoom-ms70cdr", "Zoom/MultiStomp", 30),
    ("zoom-ms50g", "Zoom/MultiStomp", 20),
    ("zoom-g3n", "Zoom/G3n", 30),
    ("zoom-g3xn", "Zoom/G3xn", 20),
    ("zoom-g5", "Zoom/G5", 20),
    ("zoom-g1xfour", "Zoom/G1_Four", 20),
    ("zoom-g1four", "Zoom/G1_Four", 15),
    ("boss-gt-1000", "Boss/GT-1000", 30),
    ("boss-gx-100", "Boss/GX-100", 20),
    ("boss-katana", "Boss/Katana", 40),
    ("boss-me-80", "Boss/ME_Series", 30),
    ("boss-gt-1", "Boss/GT-1", 30),
    ("boss-gt-100", "Boss/GT-100", 40),
    ("boss-me-50", "Boss/ME_Series", 20),
    ("boss-gt-10", "Boss/GT-10", 20),
    ("nux-mg-300", "NUX/MG-300", 30),
    ("nux-mg-400", "NUX/MG-400", 20),
    ("valeton-gp-200", "Valeton", 15),
    ("valeton-gp-100", "Valeton", 15),
    ("digitech-rp500", "Digitech", 20),
    ("digitech-rp1000", "Digitech", 15),
    ("digitech-rp360", "Digitech", 15),
    ("line6-pod-go", "Line6_Pod_Go", 20),
    ("line6-helix", "Line6_Helix", 30),
    ("line6-pod-hd500", "Line6_Legacy", 40),
    ("line6-pod-hd500x", "Line6_Legacy", 30),
    ("line6-pod-xt", "Line6_Legacy", 20),
    ("line6-pod-x3", "Line6_Legacy", 15),
    ("mooer-ge200", "Mooer/GE-200", 15),
    ("mooer-ge300", "Mooer/GE-300", 10),
    ("mooer-ge150", "Mooer/GE-150", 10),
    ("hotone-ampero", "Hotone_Ampero", 15),
    ("headrush-pedalboard", "Headrush", 10),
    ("headrush-mx5", "Headrush", 10),
    ("tc-electronic-plethora-x5", "TC_Electronic", 10),
    ("korg-ax3000g", "Korg", 10),
    ("vox-tonelab", "Vox", 10),
    ("fender-mustang", "Fender_Mustang", 20),
]

def scrape_guitarpatches_page(device_slug, page):
    """Scrape a single page from guitarpatches.com and return download URLs."""
    urls = []
    try:
        url = f"https://guitarpatches.com/{device_slug}/patches?page={page}"
        r = SESSION.get(url, timeout=15)
        if r.status_code != 200: return urls
        text = r.text

        # Find download links — they follow a pattern like /download/XXXXX
        download_pattern = re.findall(r'href=["\'](/download/\d+)["\']', text)
        for dp in download_pattern:
            full_url = f"https://guitarpatches.com{dp}"
            if not cache.seen_url(full_url):
                urls.append(full_url)
    except: pass
    return urls

def download_guitarpatch(url, platform_folder, stats):
    """Download a single patch from guitarpatches.com."""
    if cache.seen_url(url): return 0
    count = 0
    tmp = Path("/tmp") / f"gp_{hash(url)%999999}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        r = SESSION.get(url, stream=True, timeout=30, allow_redirects=True)
        if r.status_code != 200:
            cache.mark_url(url)
            return 0

        # Determine filename from Content-Disposition or URL
        cd = r.headers.get("Content-Disposition", "")
        fn_match = re.search(r'filename["\s]*=\s*"?([^";\n]+)', cd)
        if fn_match:
            fname = fn_match.group(1).strip()
        else:
            fname = url.split("/")[-1]
            if "." not in fname: fname = f"patch_{hash(url)%99999}.bin"

        fpath = tmp / fname
        with open(fpath, "wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)

        ext = Path(fname).suffix.lower()

        if ext == ".zip":
            ext_d = tmp / "extracted"
            ext_d.mkdir(exist_ok=True)
            try:
                with zipfile.ZipFile(fpath) as zf: zf.extractall(ext_d)
                for root, dirs, files in os.walk(ext_d):
                    for fn in files:
                        src = Path(root) / fn
                        se = Path(fn).suffix.lower()
                        if se in VALID_EXT and is_valid_preset(src) and not cache.is_dup(src):
                            # Use platform_folder structure
                            dest_dir = BASE_DIR / platform_folder
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            clean_name = re.sub(r'[\s\-\.]+', '_', Path(fn).stem).strip('_')[:80]
                            dest = dest_dir / f"{clean_name}{se}"
                            if not dest.exists():
                                shutil.copy2(src, dest)
                                count += 1
            except: pass
        elif ext in VALID_EXT:
            if is_valid_preset(fpath) and not cache.is_dup(fpath):
                dest_dir = BASE_DIR / platform_folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                clean_name = re.sub(r'[\s\-\.]+', '_', Path(fname).stem).strip('_')[:80]
                dest = dest_dir / f"{clean_name}{ext}"
                if not dest.exists():
                    shutil.copy2(fpath, dest)
                    count += 1
        else:
            # Try to see if it's a binary patch file — save with platform-specific extension
            if fpath.stat().st_size > 50 and fpath.stat().st_size < 10_000_000:
                dest_dir = BASE_DIR / platform_folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                clean_name = re.sub(r'[\s\-\.]+', '_', Path(fname).stem).strip('_')[:80]
                # Guess extension from platform
                if "zoom" in platform_folder.lower(): ext = ".zd2"
                elif "boss" in platform_folder.lower(): ext = ".tsl"
                elif "nux" in platform_folder.lower(): ext = ".nux"
                elif "helix" in platform_folder.lower(): ext = ".hlx"
                elif "pod" in platform_folder.lower(): ext = ".pgp"
                elif "mooer" in platform_folder.lower(): ext = ".mo"
                elif "ampero" in platform_folder.lower(): ext = ".prst"
                elif "headrush" in platform_folder.lower(): ext = ".rig"
                elif "valeton" in platform_folder.lower(): ext = ".gxp"
                else: ext = ".patch"
                dest = dest_dir / f"{clean_name}{ext}"
                if not dest.exists() and not cache.is_dup(fpath):
                    shutil.copy2(fpath, dest)
                    count += 1

        cache.mark_url(url)
    except: pass
    finally: shutil.rmtree(tmp, ignore_errors=True)
    stats["files"] += count
    return count

def run_guitarpatches(stats):
    """Scrape guitarpatches.com for ALL supported devices."""
    print("\n" + "=" * 60)
    print("🌐 GUITARPATCHES.COM MEGA SCRAPER")
    print(f"   {len(GUITARPATCHES_DEVICES)} devices × up to 50 pages each")
    print("=" * 60)

    total = 0
    for slug, folder, max_pages in GUITARPATCHES_DEVICES:
        device_count = 0
        print(f"\n  📱 {slug} → {folder}")

        for page in range(1, max_pages + 1):
            urls = scrape_guitarpatches_page(slug, page)
            if not urls:
                break  # no more pages

            for url in urls:
                try:
                    c = download_guitarpatch(url, folder, stats)
                    device_count += c
                    total += c
                except: pass
                time.sleep(0.5)  # be nice

            time.sleep(1)

        if device_count > 0:
            print(f"    ✔ {device_count} patches downloaded")

    print(f"\n  🔥 GuitarPatches.com total: {total} presets")
    return total

# ═══════════════════════════════════════════════════════════════
# CLEANUP — remove NAM / WAV / JSON from Drive
# ═══════════════════════════════════════════════════════════════
def run_cleanup():
    """Delete NAM/WAV/JSON folders that don't belong in presets."""
    print("\n" + "=" * 60)
    print("🧹 CLEANUP: Removing NAM/WAV/JSON from presets folder")
    print("=" * 60)

    import subprocess
    folders_to_delete = [
        "Neural_Amp_Modeler",
        "Neural_Amp_Modeler_Misc",
        "Misc_Captures",
        "Neural_DSP_Quad_Cortex",  # only if it has .nam files
    ]

    for folder in folders_to_delete:
        path = f"gdrive2:IR_DEF_REPOSITORY/03_PRESETS_AND_MODELERS/{folder}"
        print(f"  🗑️  Deleting {folder}...")
        try:
            subprocess.run(["rclone", "purge", path], timeout=60,
                         capture_output=True, text=True)
            print(f"    ✔ Deleted {folder}")
        except Exception as e:
            print(f"    ✗ {folder}: {e}")

    # Also clean any .json, .wav, .nam files scattered in other folders
    print("  🗑️  Cleaning stray .json/.wav/.nam files...")
    for ext in ["*.json", "*.wav", "*.nam"]:
        try:
            subprocess.run(["rclone", "delete",
                          "gdrive2:IR_DEF_REPOSITORY/03_PRESETS_AND_MODELERS",
                          "--include", ext], timeout=120, capture_output=True, text=True)
        except: pass

    print("  ✔ Cleanup complete")

# ═══════════════════════════════════════════════════════════════
# PHASE RUNNERS
# ═══════════════════════════════════════════════════════════════
MAX_WORKERS = 12

def run_seed():
    print("\n" + "=" * 60)
    print(f"🌱 PHASE 1: SEED REPOS ({len(SEED_REPOS)} repos)")
    print("=" * 60)
    stats = {"files": 0, "repos": 0}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(download_repo, r, stats): r for r in SEED_REPOS}
        for f in as_completed(futs):
            try: f.result()
            except: pass
    cache.save()
    # Also do direct zips
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(download_zip, u, n, stats): n for u, n in DIRECT_ZIPS}
        for f in as_completed(futs):
            try: f.result()
            except: pass
    cache.save()
    print(f"\n📊 Phase 1: {stats['files']} presets")
    return stats["files"]

def run_search():
    print("\n" + "=" * 60)
    print("🔍 PHASE 2: GITHUB SEARCH DISCOVERY")
    print("=" * 60)
    disc = github_search(SEARCH_QUERIES)
    if not disc: print("  No new repos"); return 0
    print(f"\n📡 Downloading {len(disc)} discovered repos...")
    stats = {"files": 0, "repos": 0}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(download_repo, r, stats): r for r in disc}
        for f in as_completed(futs):
            try: f.result()
            except: pass
    cache.save()
    print(f"\n📊 Phase 2: {stats['files']} presets from {stats['repos']} repos")
    return stats["files"]

def run_releases():
    print("\n" + "=" * 60)
    print("📦 PHASE 3: GITHUB RELEASES")
    print("=" * 60)
    all_repos = list(set(SEED_REPOS))
    stats = {"files": 0}
    download_releases(all_repos, stats)
    cache.save()
    print(f"\n📊 Phase 3: {stats['files']} presets from releases")
    return stats["files"]

def run_patches():
    print("\n" + "=" * 60)
    print("🌐 PHASE 4: GUITARPATCHES.COM")
    print("=" * 60)
    stats = {"files": 0}
    run_guitarpatches(stats)
    cache.save()
    print(f"\n📊 Phase 4: {stats['files']} presets from guitarpatches.com")
    return stats["files"]

def print_stats():
    print("\n" + "=" * 60)
    print("📊 CONTENT BY PLATFORM")
    print("=" * 60)
    gt = 0
    for d in sorted(BASE_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            c = sum(1 for _ in d.rglob("*") if _.is_file() and not _.name.startswith('.'))
            if c > 0:
                print(f"  📁 {d.name:<40} {c:>6} files")
                gt += c
    print("-" * 60)
    print(f"  🔥 TOTAL: {gt:>46} files")
    print("=" * 60)

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   MEGA PRESET VAULT 2026 v2 — PRESETS ONLY              ║")
    print("║   No NAM · No WAV · No JSON · Pure Presets Only         ║")
    print("╚══════════════════════════════════════════════════════════╝")

    total = 0
    tier = args.tier

    if tier == "cleanup" or tier == "all":
        run_cleanup()

    if tier in ("seed", "all"):
        total += run_seed()
    if tier in ("search", "all"):
        total += run_search()
    if tier in ("releases", "all"):
        total += run_releases()
    if tier in ("patches", "all"):
        total += run_patches()

    print_stats()
    print(f"\n🎉 COMPLETE! Total new presets: {total}")
    cache.save()

if __name__ == "__main__":
    main()
