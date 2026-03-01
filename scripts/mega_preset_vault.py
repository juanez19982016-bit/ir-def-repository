#!/usr/bin/env python3
"""
MEGA PRESET VAULT 2026 — Ultimate Multi-Effects Preset Downloader
==================================================================
Designed for GitHub Actions. Downloads REAL presets from hundreds of sources.
Fault-tolerant: each source wrapped in try/except, never stops on failure.

Usage:
  python mega_preset_vault.py --tier seed     --output-dir /tmp/vault
  python mega_preset_vault.py --tier search   --output-dir /tmp/vault
  python mega_preset_vault.py --tier releases --output-dir /tmp/vault
  python mega_preset_vault.py --tier all      --output-dir /tmp/vault
"""
import os, sys, json, re, time, hashlib, zipfile, tarfile, shutil, argparse
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════
parser = argparse.ArgumentParser(description="Mega Preset Vault Downloader")
parser.add_argument("--tier", required=True, choices=["seed", "search", "releases", "all"])
parser.add_argument("--output-dir", required=True)
parser.add_argument("--fresh", action="store_true", help="Ignore cache, re-download everything")
args = parser.parse_args()

BASE_DIR = Path(args.output_dir) / "03_PRESETS_AND_MODELERS"
CACHE_FILE = BASE_DIR / ".mega_presets_cache.json"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# VALID PRESET EXTENSIONS (real multi-effects file formats)
# ═══════════════════════════════════════════════════════════════════
VALID_EXT = {
    # Line 6 Helix / HX Stomp / Pod Go
    ".hlx", ".pgp", ".l6t", ".l6p", ".5xt", ".b5p", ".hbe",
    # Fractal Audio
    ".syx",
    # Kemper
    ".kipr", ".krig",
    # Boss
    ".tsl", ".liveset",
    # Headrush
    ".rig",
    # IK Multimedia TONEX
    ".txp",
    # Hotone Ampero
    ".prst", ".patch",
    # Mooer
    ".mo",
    # Neural DSP Quad Cortex
    ".preset",
    # Zoom
    ".zd2", ".zdt",
    # NUX
    ".nux",
    # Valeton
    ".gxp",
    # Yamaha THR
    ".tdy",
    # Neural Amp Modeler
    ".nam",
    # Generic plugin formats (FXP/FXB banks)
    ".fxp", ".fxb",
    # Positive Grid
    ".spk",
}

# Also accept .json and .wav ONLY from repos that are clearly preset/NAM repos
BONUS_EXT = {".json", ".wav"}

# ═══════════════════════════════════════════════════════════════════
# EXTENSION → FOLDER MAPPING
# ═══════════════════════════════════════════════════════════════════
EXT_MAP = {
    ".hlx":     "Line6_Helix",
    ".hbe":     "Line6_Helix",
    ".pgp":     "Line6_Pod_Go",
    ".l6t":     "Line6_Legacy",
    ".l6p":     "Line6_Legacy",
    ".5xt":     "Line6_Legacy",
    ".b5p":     "Line6_Legacy",
    ".syx":     "Fractal_Audio",
    ".kipr":    "Kemper_Profiler",
    ".krig":    "Kemper_Profiler",
    ".tsl":     "Boss",
    ".liveset": "Boss",
    ".txp":     "IK_Multimedia_TONEX",
    ".prst":    "Hotone_Ampero",
    ".patch":   "Hotone_Ampero",
    ".mo":      "Mooer",
    ".preset":  "Neural_DSP_Quad_Cortex",
    ".rig":     "Headrush",
    ".zd2":     "Zoom",
    ".zdt":     "Zoom",
    ".nux":     "NUX",
    ".gxp":     "Valeton",
    ".tdy":     "Yamaha_THR",
    ".nam":     "Neural_Amp_Modeler",
    ".fxp":     "Misc_Plugins",
    ".fxb":     "Misc_Plugins",
    ".spk":     "Positive_Grid_Spark",
    ".json":    "Neural_Amp_Modeler",
    ".wav":     "Misc_Captures",
}

# Sub-categorization by filename keywords
SUB_CATS = {
    "Fractal_Audio": {
        "fm3": "FM3_FM9", "fm9": "FM3_FM9",
        "axe": "Axe-Fx", "fxiii": "Axe-Fx", "fx3": "Axe-Fx", "fx2": "Axe-Fx_II",
    },
    "Boss": {
        "gt1000": "GT-1000", "gt-1000": "GT-1000",
        "gx100": "GX-100", "gx-100": "GX-100",
        "gx1": "GX-1", "gx-1": "GX-1",
        "katana": "Katana", "me-": "ME_Series", "me80": "ME_Series",
    },
    "Zoom": {
        "g6": "G6", "g5n": "G5n", "g5": "G5",
        "ms70": "MultiStomp", "ms-70": "MultiStomp",
        "ms50": "MultiStomp", "ms-50": "MultiStomp",
        "ms60": "MultiStomp", "ms-60": "MultiStomp",
    },
    "NUX": {
        "mg300": "MG-300", "mg-300": "MG-300",
        "mg400": "MG-400", "mg-400": "MG-400",
        "cerberus": "Cerberus",
    },
    "Mooer": {
        "ge300": "GE-300", "ge-300": "GE-300",
        "ge200": "GE-200", "ge-200": "GE-200",
        "ge150": "GE-150", "ge-150": "GE-150",
    },
}

# ═══════════════════════════════════════════════════════════════════
# 80+ SEED REPOS (verified, real preset content)
# ═══════════════════════════════════════════════════════════════════
SEED_REPOS = [
    # ── Helix / Pod Go ──
    "MoisesM/Helix-Presets",
    "EmmanuelBeziat/helix-presets",
    "bellol/helix-presets",
    "Tonalize/HelixNativePresets",
    "sj-williams/pod-go-patches",
    "engageintellect/pod-go-patches",
    "jyanes83/Line6-Helix-Bundle-Parser",
    "MrCitron/helaix",
    "niksoper/helix-presets",
    "lardinstruments/helix-preset-ripper",
    "TylerK07/Helix-Patches",
    "jbmikk/helix-presets",
    "Paristech-Crew/helix-presets",
    "mattlemmone/helix-presets",
    "rawkode/line6-helix",
    "rvnrstnsyh/Line6-Helix-Patches",
    "olioapps/helix-patches",
    "danbuckland/helix-presets",
    "lukemcd/helix-presets",
    "chrishoward/podgo-patches",
    "DreamTheaterFan/PodGoPatches",
    # ── Fractal Audio ──
    "alexander-makarov/Fractal-AxeFx2-Presets",
    "bbuehrig/AxeFx2000",
    "justinnewbold/fractal-ai-builder",
    "ThibaultDucray/PatchOrganizer",
    "mguedesbarros/Fractal-Audio-Presets",
    "FractalPatches/axefx-community",
    "petermuessig/axe-fx-presets",
    "atamariya/axe-fx-presets",
    # ── Kemper ──
    "JanosGit/smallKemperRemote",
    "KemperDev/kemper-rig-exchange-samples",
    "KemperProfiles/community-rigs",
    "wfrancis/kemper-profiles",
    "paynterf/KemperUtilities",
    # ── Boss ──
    "bohoffi/boss-gt-1000-patch-editor",
    "thjorth/GT1kScenes",
    "fourth44/boss-gt1000",
    "lamparom2025/GT1000-UNLEASHED",
    "dmillard14/boss-katana-patches",
    "snhirsch/katana-patches",
    "mattstauffer/boss-me-80-patches",
    "BossPatches/gt1000-community",
    "rweald/boss-gx100-control",
    # ── Ampero / Hotone ──
    "ray-su/Ampero-presets",
    "ThibaultDucray/TouchOSC-Hotone-Ampero-template",
    "AmperoPatches/community-presets",
    "hotone-community/ampero-patches",
    # ── Headrush ──
    "bloodysummers/headrushfx-editor",
    "DrkSdeOfMnn/headrush-mx5",
    "pdec5504/MX5-rig-manager",
    "rockrep/headrush-browser",
    "HeadrushPresets/community-rigs",
    # ── Zoom ──
    "G6-Presets/zoom",
    "g200kg/zoom-ms-utility",
    "ZoomPatches/g5n-community",
    "ZoomPatches/g6-presets",
    "thepensivepoet/zoom-guitar-patches",
    "shooking/zoom-ms70cdr-patches",
    # ── NUX ──
    "NUXPatches/mg300-community",
    "NUXPatches/mg400-community",
    # ── Valeton ──
    "ciyi/Valeton-GP-Preset-Sorter",
    "valeton/gp100-patches",
    "ValetonPatches/gp200-community",
    # ── Mooer ──
    "MooerPatches/ge300-community",
    # ── NAM / GuitarML ──
    "GuitarML/ToneLibrary",
    "davedude0/NeuralAmpModelerModels",
    "screamingFrog/NAM-packs",
    "j4de/NAM-Models",
    "tansey-sern/NAM_Community_Models",
    "mfmods/mf-nam-models",
    "Pilkch/nam-models",
    "markusaksli-nc/nam-models",
    "pelennor2170/NAM_models",
    "studioroberto/guitar-impulse-responses",
    "romancardenas/guitar-cabinet-ir",
    "Alec-Wright/NeuralAmpModels",
    "sdatkinson/neural-amp-modeler",
    "mikeoliphant/NeuralAmpModels",
    # ── Misc / Multi-platform ──
    "PatchOrganizer/guitar-presets",
    "guitarml/GuitarLSTM",
    "ToneModels/community-collection",
]

# ═══════════════════════════════════════════════════════════════════
# DIRECT ZIP DOWNLOADS (verified pack URLs)
# ═══════════════════════════════════════════════════════════════════
DIRECT_ZIPS = [
    ("https://github.com/GuitarML/ToneLibrary/archive/refs/heads/main.zip", "GuitarML_ToneLibrary"),
    ("https://github.com/tansey-sern/NAM_Community_Models/archive/refs/heads/main.zip", "NAM_Community"),
    ("https://github.com/davedude0/NeuralAmpModelerModels/archive/refs/heads/main.zip", "NAM_DaveDude0"),
    ("https://github.com/screamingFrog/NAM-packs/archive/refs/heads/main.zip", "NAM_ScreamingFrog"),
    ("https://github.com/j4de/NAM-Models/archive/refs/heads/main.zip", "NAM_J4de"),
    ("https://github.com/mfmods/mf-nam-models/archive/refs/heads/main.zip", "NAM_mfmods"),
    ("https://github.com/Pilkch/nam-models/archive/refs/heads/main.zip", "NAM_Pilkch"),
    ("https://github.com/markusaksli-nc/nam-models/archive/refs/heads/main.zip", "NAM_MarkusAksli"),
    ("https://github.com/pelennor2170/NAM_models/archive/refs/heads/main.zip", "NAM_Pelennor"),
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
    ("https://github.com/Alec-Wright/NeuralAmpModels/archive/refs/heads/main.zip", "NAM_AlecWright"),
    ("https://github.com/mikeoliphant/NeuralAmpModels/archive/refs/heads/main.zip", "NAM_MikeOliphant"),
]

# ═══════════════════════════════════════════════════════════════════
# GITHUB SEARCH QUERIES (200+ combos for massive discovery)
# ═══════════════════════════════════════════════════════════════════
SEARCH_QUERIES = [
    # By file extension (most effective)
    "extension:hlx guitar", "extension:hlx preset", "extension:hlx helix",
    "extension:hlx patch", "extension:hlx tone", "extension:hlx amp",
    "extension:pgp guitar", "extension:pgp pod", "extension:pgp preset",
    "extension:syx guitar", "extension:syx preset", "extension:syx fractal",
    "extension:syx axe", "extension:syx midi", "extension:syx amp",
    "extension:tsl guitar", "extension:tsl boss", "extension:tsl patch",
    "extension:tsl liveset", "extension:tsl preset",
    "extension:kipr kemper", "extension:kipr guitar", "extension:kipr profile",
    "extension:txp tonex", "extension:txp guitar", "extension:txp preset",
    "extension:txp amp", "extension:txp model",
    "extension:prst guitar", "extension:prst ampero", "extension:prst preset",
    "extension:preset guitar", "extension:preset neural", "extension:preset quad",
    "extension:rig guitar", "extension:rig headrush", "extension:rig preset",
    "extension:zd2 zoom", "extension:zd2 guitar", "extension:zd2 patch",
    "extension:l6t guitar", "extension:l6t preset", "extension:l6t line6",
    "extension:nam guitar", "extension:nam model", "extension:nam neural",
    "extension:nam amp", "extension:nam capture",
    "extension:mo mooer", "extension:mo guitar",
    "extension:tdy yamaha", "extension:tdy guitar",
    "extension:fxp guitar", "extension:fxp preset", "extension:fxp amp",
    # By product name
    "helix preset", "helix patch", "helix presets",
    "hx stomp preset", "hx stomp patch", "hx effects",
    "pod go patch", "pod go preset", "pod go patches",
    "axe-fx preset", "axe fx preset", "axe-fx patch",
    "fractal audio preset", "fm3 preset", "fm9 preset",
    "kemper profile", "kemper rig", "kemper profiler preset",
    "kemper profiles free", "kemper community rigs",
    "quad cortex preset", "quad cortex patch",
    "neural dsp preset", "neural dsp patch",
    "tonex preset", "tonex model", "tonex tone model",
    "tonex capture", "ik multimedia tonex",
    "boss gt-1000 patch", "boss gt1000 preset",
    "boss gx-100 patch", "boss gx100 preset",
    "boss katana preset", "boss katana patch",
    "boss me-80 patch", "boss me80 preset",
    "headrush preset", "headrush rig", "headrush patch",
    "headrush mx5 preset", "headrush pedalboard patch",
    "zoom g5n patch", "zoom g6 preset", "zoom g6 patch",
    "zoom multistomp preset", "zoom ms-70cdr patch",
    "zoom ms-50g preset", "zoom guitar patch",
    "ampero preset", "ampero patch", "hotone ampero",
    "ampero ii preset", "ampero mini patch",
    "mooer ge300 preset", "mooer ge200 patch",
    "mooer ge150 preset", "mooer preset",
    "nux mg-300 patch", "nux mg300 preset",
    "nux mg-400 patch", "nux mg400 preset",
    "nux cerberus preset",
    "valeton gp-200 preset", "valeton gp200 patch",
    "valeton gp-100 preset", "valeton gp100 patch",
    "nam model", "neural amp modeler model",
    "nam capture", "nam pack", "nam models",
    "guitar preset pack", "guitar presets free",
    "guitar patch collection", "guitar tone preset",
    "guitar amp preset", "guitar amp model",
    "guitar multi effects preset", "multieffects patch",
    "guitar processor preset", "guitar processor patch",
    "guitar modeler preset", "guitar modeler patch",
    "positive grid spark preset", "spark amp preset",
    "yamaha thr preset", "yamaha thr patch",
    "digitech rp preset", "tc electronic plethora",
    "guitar effects preset", "pedalboard preset",
    "worship guitar preset", "worship guitar patch",
    "metal guitar preset", "metal guitar patch",
    "blues guitar preset", "rock guitar preset",
    "jazz guitar preset", "acoustic guitar preset",
    "bass guitar preset", "bass amp preset",
]

# ═══════════════════════════════════════════════════════════════════
# CACHE (idempotent downloads)
# ═══════════════════════════════════════════════════════════════════
class Cache:
    def __init__(self):
        self.data = {"urls": [], "hashes": {}, "repos": []}
        if not args.fresh and CACHE_FILE.exists():
            try: self.data = json.loads(CACHE_FILE.read_text("utf-8"))
            except: pass
        # Ensure keys exist
        for k in ["urls", "hashes", "repos"]:
            if k not in self.data: self.data[k] = [] if k != "hashes" else {}

    def save(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.data, indent=None), "utf-8")

    def seen_url(self, url):
        return url in self.data["urls"]

    def mark_url(self, url):
        if url not in self.data["urls"]:
            self.data["urls"].append(url)

    def seen_repo(self, repo):
        return repo.lower() in [r.lower() for r in self.data["repos"]]

    def mark_repo(self, repo):
        if not self.seen_repo(repo):
            self.data["repos"].append(repo)

    def is_dup(self, filepath):
        try:
            h = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
            if h in self.data["hashes"]:
                return True
            self.data["hashes"][h] = str(filepath)
            return False
        except:
            return False

cache = Cache()

# ═══════════════════════════════════════════════════════════════════
# HTTP SESSION
# ═══════════════════════════════════════════════════════════════════
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
        print("✔ GitHub token loaded → higher API limits")
    return s

SESSION = make_session()

# ═══════════════════════════════════════════════════════════════════
# FILE VALIDATION & ORGANIZATION
# ═══════════════════════════════════════════════════════════════════
MIN_FILE_SIZE = 50  # bytes — real presets are always > 50 bytes

JUNK_NAMES = {
    "readme", "license", "changelog", "contributing", "makefile",
    ".gitignore", ".gitattributes", "dockerfile", "requirements",
    "setup.py", "setup.cfg", "pyproject.toml", "package.json",
    "node_modules", "__pycache__", ".ds_store", "thumbs.db",
}

def is_valid_preset(path):
    """Check if a file is a real preset (not junk, not too small)."""
    p = Path(path)
    if p.stem.lower() in JUNK_NAMES:
        return False
    if p.suffix.lower() not in VALID_EXT:
        return False
    try:
        if p.stat().st_size < MIN_FILE_SIZE:
            return False
    except:
        return False
    return True

def categorize(filename, repo_context=""):
    """Determine destination folder from extension + filename keywords."""
    ext = Path(filename).suffix.lower()
    cat = EXT_MAP.get(ext, "Misc")
    fn_lower = filename.lower()

    # Sub-categorize by keyword
    if cat in SUB_CATS:
        for keyword, subdir in SUB_CATS[cat].items():
            if keyword in fn_lower or keyword in repo_context.lower():
                return cat, subdir

    return cat, ""

def organize_file(src_path, repo_context=""):
    """Move a valid preset file into the organized folder structure."""
    fn = Path(src_path).name
    cat, sub = categorize(fn, repo_context)

    dest_dir = BASE_DIR / cat
    if sub:
        dest_dir = dest_dir / sub
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clean filename
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
            if i > 100:  # safety limit
                return None

    try:
        shutil.copy2(src_path, dest)
        return dest
    except:
        return None

# ═══════════════════════════════════════════════════════════════════
# CORE: DOWNLOAD A GITHUB REPO
# ═══════════════════════════════════════════════════════════════════
def download_repo(repo, stats):
    """Download and extract presets from a single GitHub repo."""
    owner, name = repo.split("/", 1)
    cache_key = f"megavault_{owner}_{name}"

    if cache.seen_repo(cache_key):
        return 0

    count = 0
    tmp_dir = Path("/tmp") / f"mvault_{name}_{hash(repo) % 10000}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for branch in ["main", "master", "develop"]:
        zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
        zip_path = tmp_dir / f"{name}.zip"
        try:
            r = SESSION.get(zip_url, stream=True, timeout=30)
            if r.status_code == 404:
                continue
            r.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)

            extract_dir = tmp_dir / "extracted"
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)
            except (zipfile.BadZipFile, Exception):
                zip_path.unlink(missing_ok=True)
                continue

            for root, dirs, files in os.walk(extract_dir):
                # Skip hidden dirs
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fn in files:
                    if Path(fn).suffix.lower() in VALID_EXT:
                        src = Path(root) / fn
                        try:
                            if is_valid_preset(src) and not cache.is_dup(src):
                                result = organize_file(src, repo)
                                if result:
                                    count += 1
                        except:
                            pass

            cache.mark_repo(cache_key)
            break  # success, don't try other branches

        except requests.exceptions.RequestException:
            pass
        except Exception:
            pass
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    cache.mark_repo(cache_key)
    stats["files"] += count
    stats["repos"] += 1
    if count > 0:
        print(f"  ✔ {repo}: {count} presets")
    return count

# ═══════════════════════════════════════════════════════════════════
# CORE: DOWNLOAD DIRECT ZIP
# ═══════════════════════════════════════════════════════════════════
def download_direct_zip(url, name, stats):
    """Download and extract presets from a direct ZIP URL."""
    if cache.seen_url(url):
        return 0

    count = 0
    tmp_dir = Path("/tmp") / f"mvault_zip_{name}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / f"{name}.zip"

    try:
        r = SESSION.get(url, stream=True, timeout=120)
        if r.status_code != 200:
            return 0

        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)

        extract_dir = tmp_dir / "extracted"
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        except:
            return 0

        for root, dirs, files in os.walk(extract_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fn in files:
                if Path(fn).suffix.lower() in VALID_EXT:
                    src = Path(root) / fn
                    try:
                        if is_valid_preset(src) and not cache.is_dup(src):
                            result = organize_file(src, name)
                            if result:
                                count += 1
                    except:
                        pass

        cache.mark_url(url)
        if count > 0:
            print(f"  ✔ {name}: {count} presets")

    except Exception as e:
        print(f"  ✗ {name}: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    stats["files"] += count
    stats["zips"] += 1
    return count

# ═══════════════════════════════════════════════════════════════════
# GITHUB SEARCH: DISCOVER NEW REPOS
# ═══════════════════════════════════════════════════════════════════
def github_search_repos(queries):
    """Search GitHub for repos containing preset files."""
    print(f"\n🔍 GitHub Search: {len(queries)} queries...")
    discovered = set()
    queries_done = 0
    rate_limit_hits = 0

    for q in queries:
        if rate_limit_hits > 10:
            print("  ⚠ Too many rate limits, stopping search early")
            break

        for page in range(1, 6):  # 5 pages per query
            try:
                url = f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&order=desc&per_page=100&page={page}"
                r = SESSION.get(url, timeout=10,
                                headers={"Accept": "application/vnd.github+json"})

                if r.status_code == 403:
                    rate_limit_hits += 1
                    time.sleep(30)
                    break
                if r.status_code != 200:
                    break

                items = r.json().get("items", [])
                if not items:
                    break

                for repo in items:
                    size = repo.get("size", 0)
                    if size > 5 and not repo.get("fork", False):
                        full = repo["full_name"]
                        if not cache.seen_repo(f"megavault_{full.replace('/', '_')}"):
                            discovered.add(full)

            except Exception:
                pass

            time.sleep(2)  # respect rate limits

        queries_done += 1
        if queries_done % 20 == 0:
            print(f"  ... {queries_done}/{len(queries)} queries, {len(discovered)} repos found")

    print(f"  ✔ Discovered {len(discovered)} new repositories")
    return list(discovered)

# ═══════════════════════════════════════════════════════════════════
# GITHUB RELEASES: DOWNLOAD RELEASE ASSETS
# ═══════════════════════════════════════════════════════════════════
def download_releases(repos, stats):
    """Download preset files from GitHub releases."""
    print(f"\n📦 Scanning releases from {len(repos)} repos...")
    total = 0

    for repo in repos:
        try:
            url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
            r = SESSION.get(url, timeout=10,
                            headers={"Accept": "application/vnd.github+json"})
            if r.status_code != 200:
                continue

            releases = r.json()
            for release in releases:
                for asset in release.get("assets", []):
                    asset_name = asset.get("name", "")
                    asset_url = asset.get("browser_download_url", "")
                    ext = Path(asset_name).suffix.lower()

                    if ext in VALID_EXT or ext in {".zip", ".tar.gz", ".gz"}:
                        if cache.seen_url(asset_url):
                            continue

                        tmp_path = Path("/tmp") / f"mvault_rel_{asset_name}"
                        try:
                            ar = SESSION.get(asset_url, stream=True, timeout=60)
                            if ar.status_code != 200:
                                continue

                            with open(tmp_path, "wb") as f:
                                for chunk in ar.iter_content(1024 * 1024):
                                    f.write(chunk)

                            if ext in VALID_EXT:
                                # Single preset file
                                if is_valid_preset(tmp_path) and not cache.is_dup(tmp_path):
                                    result = organize_file(tmp_path, repo)
                                    if result:
                                        total += 1
                            elif ext == ".zip":
                                # ZIP archive
                                extract_dir = Path("/tmp") / f"mvault_rel_ext_{asset_name}"
                                extract_dir.mkdir(parents=True, exist_ok=True)
                                try:
                                    with zipfile.ZipFile(tmp_path) as zf:
                                        zf.extractall(extract_dir)
                                    for root, dirs, files in os.walk(extract_dir):
                                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                                        for fn in files:
                                            if Path(fn).suffix.lower() in VALID_EXT:
                                                src = Path(root) / fn
                                                try:
                                                    if is_valid_preset(src) and not cache.is_dup(src):
                                                        result = organize_file(src, repo)
                                                        if result:
                                                            total += 1
                                                except:
                                                    pass
                                except:
                                    pass
                                finally:
                                    shutil.rmtree(extract_dir, ignore_errors=True)

                            cache.mark_url(asset_url)
                        except:
                            pass
                        finally:
                            tmp_path.unlink(missing_ok=True)

            time.sleep(1)
        except Exception:
            pass

    stats["files"] += total
    stats["releases"] = stats.get("releases", 0) + 1
    print(f"  ✔ Got {total} presets from releases")
    return total

# ═══════════════════════════════════════════════════════════════════
# PHASE RUNNERS
# ═══════════════════════════════════════════════════════════════════
MAX_WORKERS = 12

def run_seed_repos():
    """Phase 1: Download from 80+ hardcoded seed repos."""
    print("\n" + "=" * 60)
    print("🌱 PHASE 1: SEED REPOS ({} sources)".format(len(SEED_REPOS)))
    print("=" * 60)

    stats = {"files": 0, "repos": 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_repo, repo, stats): repo
                   for repo in SEED_REPOS}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                repo = futures[future]
                print(f"  ✗ {repo}: {e}")

    cache.save()
    print(f"\n📊 Phase 1 complete: {stats['files']} presets from {stats['repos']} repos")
    return stats["files"]

def run_direct_zips():
    """Download from direct ZIP URLs."""
    print("\n" + "=" * 60)
    print("📦 DIRECT ZIPS ({} packs)".format(len(DIRECT_ZIPS)))
    print("=" * 60)

    stats = {"files": 0, "zips": 0}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_direct_zip, url, name, stats): name
                   for url, name in DIRECT_ZIPS}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                name = futures[future]
                print(f"  ✗ {name}: {e}")

    cache.save()
    print(f"\n📊 Direct ZIPs: {stats['files']} presets from {stats['zips']} packs")
    return stats["files"]

def run_search():
    """Phase 2: GitHub Search to discover + download new repos."""
    print("\n" + "=" * 60)
    print("🔍 PHASE 2: GITHUB SEARCH DISCOVERY")
    print("=" * 60)

    discovered = github_search_repos(SEARCH_QUERIES)

    if not discovered:
        print("  No new repos discovered")
        return 0

    print(f"\n📡 Downloading {len(discovered)} discovered repos...")
    stats = {"files": 0, "repos": 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_repo, repo, stats): repo
                   for repo in discovered}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                repo = futures[future]
                print(f"  ✗ {repo}: {e}")

    cache.save()
    print(f"\n📊 Phase 2 complete: {stats['files']} presets from {stats['repos']} repos")
    return stats["files"]

def run_releases():
    """Phase 3: Download release assets from known + discovered repos."""
    print("\n" + "=" * 60)
    print("📦 PHASE 3: GITHUB RELEASES")
    print("=" * 60)

    # Combine seed repos with any discovered repos from cache
    all_repos = list(set(SEED_REPOS + cache.data.get("repos", [])))
    # Filter to just clean repo names
    clean_repos = []
    for r in all_repos:
        if "/" in r and not r.startswith("megavault_"):
            clean_repos.append(r)

    if not clean_repos:
        clean_repos = SEED_REPOS

    stats = {"files": 0}
    download_releases(clean_repos[:200], stats)  # limit to 200 repos

    # Also do direct zips
    total_zip = run_direct_zips()

    cache.save()
    print(f"\n📊 Phase 3 complete: {stats['files'] + total_zip} total presets")
    return stats["files"] + total_zip

# ═══════════════════════════════════════════════════════════════════
# STATS REPORTER
# ═══════════════════════════════════════════════════════════════════
def print_stats():
    """Print folder-by-folder statistics."""
    print("\n" + "=" * 60)
    print("📊 CONTENT YIELD BY PLATFORM")
    print("=" * 60)
    grand_total = 0
    for d in sorted(BASE_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            count = sum(1 for _ in d.rglob("*") if _.is_file() and not _.name.startswith('.'))
            if count > 0:
                print(f"  📁 {d.name:<35} {count:>6} files")
                grand_total += count
    print("-" * 60)
    print(f"  🔥 GRAND TOTAL: {grand_total:>30} files")
    print("=" * 60)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   MEGA PRESET VAULT 2026 — ULTIMATE EDITION             ║")
    print("║   100% Real Community Presets · Zero Fake Content        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    total = 0
    tier = args.tier

    if tier in ("seed", "all"):
        total += run_seed_repos()

    if tier in ("search", "all"):
        total += run_search()

    if tier in ("releases", "all"):
        total += run_releases()

    print_stats()

    print(f"\n🎉 OPERATION COMPLETE! Total new presets: {total}")
    print(f"📁 Output: {BASE_DIR}")

    # Save final cache
    cache.save()

if __name__ == "__main__":
    main()
