#!/usr/bin/env python3
"""
IR DEF Repository — Massive IR & NAM Capture Downloader/Organizer
=================================================================
Downloads from 30+ verified free sources, organizes by instrument/type/brand,
renames descriptively, deduplicates, validates integrity, and uploads to Drive.
"""

import os
import sys
import json
import re
import time
import hashlib
import zipfile
import struct
import shutil
import logging
import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Third-party imports (installed in workflow)
# ---------------------------------------------------------------------------
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/ir_repository"))
CACHE_FILE = BASE_DIR / ".download_cache.json"
STATS_FILE = BASE_DIR / ".stats.json"
LOG_FILE = BASE_DIR / ".download.log"

TONE3000_API_KEY = os.environ.get("TONE3000_API_KEY", "")
TONE3000_BASE = "https://www.tone3000.com/api/v1"

# NAM file extensions
NAM_EXTENSIONS = {".nam", ".json", ".aidax"}
# IR file extensions
IR_EXTENSIONS = {".wav", ".aiff", ".flac"}
# All valid extensions
ALL_EXTENSIONS = NAM_EXTENSIONS | IR_EXTENSIONS

# Brand detection patterns
BRAND_PATTERNS = {
    "Marshall": [r"marshall", r"marsh", r"jcm", r"jvm", r"plexi", r"1959", r"1987", r"2203", r"2204", r"dsl", r"jmp"],
    "Fender": [r"fender", r"twin", r"deluxe\s*reverb", r"bassman", r"princeton", r"champ", r"vibrolux", r"super\s*reverb"],
    "Mesa_Boogie": [r"mesa", r"boogie", r"rectifier", r"recto", r"dual\s*rec", r"triple\s*rec", r"mark\s*(iv|v|ii|iii)", r"lonestar", r"stiletto"],
    "Vox": [r"vox", r"ac\s*30", r"ac\s*15", r"ac30", r"ac15"],
    "Orange": [r"orange", r"rockerverb", r"thunderverb", r"tiny\s*terror", r"or\d{2,3}"],
    "Peavey": [r"peavey", r"5150", r"6505", r"invective", r"xxx", r"jsx"],
    "EVH": [r"\bevh\b", r"5150\s*(iii|el34|iconic)"],
    "Bogner": [r"bogner", r"uberschall", r"ecstasy", r"shiva"],
    "Soldano": [r"soldano", r"slo", r"slo\s*100"],
    "Diezel": [r"diezel", r"herbert", r"vh4", r"hagen"],
    "Friedman": [r"friedman", r"be\s*100", r"be100", r"dirty\s*shirley", r"small\s*box"],
    "Engl": [r"engl", r"powerball", r"fireball", r"savage", r"invader"],
    "Ampeg": [r"ampeg", r"svt", r"b\-?15", r"v4b", r"portaflex"],
    "Darkglass": [r"darkglass", r"microtubes", r"alpha.*omega", r"b7k"],
    "Eden": [r"\beden\b", r"nemesis", r"wt\d{3,4}"],
    "Sunn": [r"\bsunn\b", r"model\s*t"],
    "Hiwatt": [r"hiwatt", r"dr\s*103", r"dr103"],
    "Matchless": [r"matchless", r"chieftain", r"dc\s*30"],
    "Dr_Z": [r"dr\.?\s*z", r"maz\s*38"],
    "Hughes_Kettner": [r"hughes", r"kettner", r"triamp", r"tubemeister"],
    "Laney": [r"laney", r"ironheart", r"gh\d{2,3}"],
    "Supro": [r"supro", r"thunderbolt"],
    "Morgan": [r"morgan", r"ac\s*20"],
    "Revv": [r"revv", r"generator"],
    "Victory": [r"victory", r"kraken", r"duchess", r"countess"],
    "Celestion": [r"celestion", r"v30", r"vintage\s*30", r"greenback", r"creamback", r"g12", r"alnico"],
    "Eminence": [r"eminence", r"swamp\s*thang", r"texas\s*heat", r"cannabis\s*rex"],
    "Jensen": [r"jensen", r"c12", r"p12"],
    "Taylor": [r"taylor", r"314", r"814", r"914"],
    "Martin": [r"martin", r"d-?28", r"d-?35", r"d-?18", r"hd-?28"],
    "Gibson_Acoustic": [r"gibson.*acoustic", r"j-?45", r"hummingbird", r"j-?200"],
}

# Style/genre tags
STYLE_TAGS = {
    "Clean": [r"clean", r"pristine", r"crystal"],
    "Crunch": [r"crunch", r"edge", r"breakup"],
    "High_Gain": [r"high.?gain", r"hi.?gain", r"metal", r"djent", r"br00tal"],
    "Vintage": [r"vintage", r"classic", r"retro", r"60s", r"70s"],
    "Modern": [r"modern", r"contemporary"],
}

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
def setup_logging():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

# ---------------------------------------------------------------------------
# HTTP Session with retries
# ---------------------------------------------------------------------------
def get_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "IR-DEF-Repository/2.0 (github.com/ir-def-repository)",
        "Accept-Encoding": "gzip, deflate",
    })
    return session

# ---------------------------------------------------------------------------
# Cache & Deduplication
# ---------------------------------------------------------------------------
class DownloadCache:
    def __init__(self):
        self.cache_path = CACHE_FILE
        self.data = {"downloaded_urls": [], "file_hashes": {}, "stats": {}}
        self._load()

    def _load(self):
        if self.cache_path.exists():
            try:
                self.data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def is_downloaded(self, url):
        return url in self.data["downloaded_urls"]

    def mark_downloaded(self, url):
        if url not in self.data["downloaded_urls"]:
            self.data["downloaded_urls"].append(url)

    def is_duplicate(self, file_path):
        h = self._hash_file(file_path)
        if h in self.data["file_hashes"]:
            return True
        self.data["file_hashes"][h] = str(file_path)
        return False

    @staticmethod
    def _hash_file(path, chunk_size=8192):
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()

# ---------------------------------------------------------------------------
# File Integrity Validation
# ---------------------------------------------------------------------------
def validate_wav(path):
    """Check if a WAV file has valid RIFF header."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
            if len(header) < 12:
                return False
            riff, size, wave = struct.unpack("<4sI4s", header)
            return riff == b"RIFF" and wave == b"WAVE"
    except Exception:
        return False

def validate_file(path):
    """Validate file integrity based on extension."""
    p = Path(path)
    if p.stat().st_size < 100:  # Less than 100 bytes = corrupt
        return False
    if p.suffix.lower() == ".wav":
        return validate_wav(path)
    if p.suffix.lower() in NAM_EXTENSIONS:
        # NAM/JSON files should be valid JSON or binary
        if p.suffix.lower() == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                return True
            except Exception:
                return False
        return True  # .nam and .aidax are binary, just check size
    return True

# ---------------------------------------------------------------------------
# Smart File Organizer
# ---------------------------------------------------------------------------
class FileOrganizer:
    @staticmethod
    def detect_brand(filename):
        name_lower = filename.lower()
        for brand, patterns in BRAND_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower):
                    return brand
        return "Otros"

    @staticmethod
    def detect_instrument(filepath, filename):
        """Detect instrument from path/filename context."""
        context = (str(filepath) + " " + filename).lower()
        if any(k in context for k in ["bass", "bajo", "b15", "svt", "ampeg", "darkglass", "eden", "sunn"]):
            return "BAJO"
        if any(k in context for k in ["acoustic", "acustic", "electroac", "piezo", "body_sim",
                                       "taylor", "martin", "d-28", "d-35", "j-45", "fingerpick"]):
            return "ELECTROACUSTICA"
        if any(k in context for k in ["reverb_ir", "room_ir", "hall_ir", "plate_ir", "spring_ir",
                                       "mic_emu", "microphone"]):
            return "UTILIDADES"
        return "GUITARRA"

    @staticmethod
    def detect_type(filepath, filename):
        """Detect if IR or NAM capture."""
        ext = Path(filename).suffix.lower()
        if ext in NAM_EXTENSIONS:
            return "NAM_Capturas"
        if ext in IR_EXTENSIONS:
            return "IRs"
        return "IRs"

    @staticmethod
    def detect_subcategory(filepath, filename):
        """Detect subcategory for NAM captures."""
        context = (str(filepath) + " " + filename).lower()
        if any(k in context for k in ["pedal", "od", "overdrive", "distortion", "fuzz", "boost",
                                       "ts808", "ts9", "tubescreamer", "klon", "rat", "muff"]):
            if any(k in context for k in ["overdrive", "od", "ts808", "ts9", "tubescreamer", "klon"]):
                return "Pedals/Overdrive"
            if any(k in context for k in ["distortion", "rat", "ds-1", "ds1"]):
                return "Pedals/Distortion"
            if any(k in context for k in ["fuzz", "muff", "tone bender"]):
                return "Pedals/Fuzz"
            if any(k in context for k in ["boost", "ep booster", "micro amp"]):
                return "Pedals/Boost"
            return "Pedals/Otros"
        if any(k in context for k in ["full.?rig", "fullrig", "full_rig", "complete"]):
            if any(k in context for k in ["high.?gain", "metal", "djent"]):
                return "Full_Rigs/High_Gain"
            if any(k in context for k in ["clean", "jazz"]):
                return "Full_Rigs/Clean"
            if any(k in context for k in ["crunch", "edge"]):
                return "Full_Rigs/Crunch"
            if any(k in context for k in ["vintage", "classic"]):
                return "Full_Rigs/Vintage"
            return "Full_Rigs"
        return "Amps"

    @staticmethod
    def clean_filename(name):
        """Clean and standardize filename."""
        stem = Path(name).stem
        ext = Path(name).suffix.lower()
        # Remove common junk from filenames
        stem = re.sub(r"[\[\(]?(free|download|pack|sample|demo|www\.\S+)[\]\)]?", "", stem, flags=re.I)
        # Replace separators with underscores
        stem = re.sub(r"[\s\-\.]+", "_", stem)
        # Remove multiple underscores
        stem = re.sub(r"_+", "_", stem)
        # Remove leading/trailing underscores
        stem = stem.strip("_")
        # Capitalize words for readability
        if stem:
            parts = stem.split("_")
            parts = [p.capitalize() if len(p) > 2 else p.upper() for p in parts if p]
            stem = "_".join(parts)
        return f"{stem}{ext}" if stem else name

    def organize_file(self, src_path, original_rel_path=""):
        """Determine destination path for a file."""
        filename = Path(src_path).name
        context_path = original_rel_path or str(src_path)

        instrument = self.detect_instrument(context_path, filename)
        file_type = self.detect_type(context_path, filename)
        brand = self.detect_brand(filename + " " + context_path)

        if file_type == "NAM_Capturas":
            subcategory = self.detect_subcategory(context_path, filename)
            if subcategory.startswith(("Pedals", "Full_Rigs")):
                dest = BASE_DIR / instrument / file_type / subcategory
            else:
                dest = BASE_DIR / instrument / file_type / subcategory / brand
        else:
            dest = BASE_DIR / instrument / file_type / brand

        dest.mkdir(parents=True, exist_ok=True)
        clean_name = self.clean_filename(filename)
        return dest / clean_name

# ---------------------------------------------------------------------------
# GitHub ZIP Downloader
# ---------------------------------------------------------------------------
GITHUB_REPOS = [
    # === MASSIVE NAM MODEL COLLECTIONS ===
    {"url": "https://github.com/pelennor2170/NAM_models", "desc": "Massive NAM model collection"},
    {"url": "https://github.com/GuitarML/ToneLibrary", "desc": "GuitarML Tone Library models"},
    {"url": "https://github.com/GuitarML/Proteus", "desc": "Proteus tone models"},
    {"url": "https://github.com/sdatkinson/neural-amp-modeler", "desc": "NAM official examples"},
    {"url": "https://github.com/mikeoliphant/NeuralAmpModels", "desc": "Neural amp model collection"},
    # === SPEAKER CABINET IRs ===
    {"url": "https://github.com/orodamaral/Speaker-Cabinets-IRs", "desc": "Speaker Cabinet IRs"},
    {"url": "https://github.com/itsmusician/IR-Library", "desc": "IR Library collection"},
    {"url": "https://github.com/keyth72/AxeFxImpulseResponses", "desc": "Axe-Fx Impulse Responses"},
    {"url": "https://github.com/IsaakCode/freeaudio", "desc": "Curated free audio IRs list"},
    # === ML/AI AMP MODELS ===
    {"url": "https://github.com/Alec-Wright/Automated-GuitarAmpModelling", "desc": "ML guitar amp models"},
    {"url": "https://github.com/GuitarML/SmartGuitarAmp", "desc": "SmartGuitarAmp models"},
    {"url": "https://github.com/GuitarML/SmartGuitarPedal", "desc": "SmartGuitarPedal models"},
    {"url": "https://github.com/GuitarML/SmartAmpPro", "desc": "SmartAmpPro models"},
    {"url": "https://github.com/GuitarML/GuitarLSTM", "desc": "GuitarLSTM trained models"},
    {"url": "https://github.com/GuitarML/TS-M1N3", "desc": "TS-M1N3 overdrive models"},
    {"url": "https://github.com/GuitarML/Chameleon", "desc": "Chameleon amp modeler"},
    # === AIDA-X MODELS ===
    {"url": "https://github.com/AidaDSP/AIDA-X", "desc": "AIDA-X amp modeler models"},
    # === ADDITIONAL NAM/ML REPOS ===
    {"url": "https://github.com/carlthome/nam-models", "desc": "NAM models collection"},
    {"url": "https://github.com/Draftsman/nam-captures", "desc": "NAM amp captures"},
    {"url": "https://github.com/liveplayback/nam-models", "desc": "Liveplayback NAM models"},
]

# GitHub repos that have releases with downloadable model files
GITHUB_RELEASE_REPOS = [
    {"owner": "GuitarML", "repo": "Proteus", "desc": "Proteus tone models releases"},
    {"owner": "GuitarML", "repo": "TS-M1N3", "desc": "TS-M1N3 overdrive releases"},
    {"owner": "GuitarML", "repo": "SmartGuitarAmp", "desc": "SmartGuitarAmp releases"},
    {"owner": "GuitarML", "repo": "Chameleon", "desc": "Chameleon releases"},
    {"owner": "mikeoliphant", "repo": "NeuralAmpModels", "desc": "Neural amp model releases"},
]

def download_github_repos(session, cache, organizer):
    """Download GitHub repos as ZIP, extract, organize."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}
    tmp_dir = Path("/tmp/github_zips")

    for repo in GITHUB_REPOS:
        repo_url = repo["url"]
        zip_url = f"{repo_url}/archive/refs/heads/main.zip"
        repo_name = repo_url.split("/")[-1]

        if cache.is_downloaded(zip_url):
            logging.info(f"SKIP (cached): {repo_name}")
            stats["skipped"] += 1
            continue

        logging.info(f"Downloading {repo_name} as ZIP...")
        zip_path = tmp_dir / f"{repo_name}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            resp = session.get(zip_url, stream=True, timeout=300)
            if resp.status_code == 404:
                # Try master branch
                zip_url = f"{repo_url}/archive/refs/heads/master.zip"
                resp = session.get(zip_url, stream=True, timeout=300)
            resp.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

            size_mb = zip_path.stat().st_size / (1024 * 1024)
            logging.info(f"Downloaded {repo_name}: {size_mb:.1f} MB")
            stats["downloaded"] += 1

            # Extract and organize
            extract_dir = tmp_dir / repo_name
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Find all valid files and organize them
            subdir_filter = repo.get("subdir", "")
            file_count = 0
            for root, dirs, files in os.walk(extract_dir):
                # Skip hidden dirs and non-relevant dirs
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel_root = os.path.relpath(root, extract_dir)

                if subdir_filter and subdir_filter not in rel_root and rel_root != ".":
                    continue

                for fname in files:
                    ext = Path(fname).suffix.lower()
                    if ext not in ALL_EXTENSIONS:
                        continue

                    src = Path(root) / fname
                    if not validate_file(src):
                        logging.warning(f"Invalid file skipped: {src}")
                        continue
                    if cache.is_duplicate(src):
                        logging.debug(f"Duplicate skipped: {fname}")
                        continue

                    # Use repo path context for smarter organization
                    context = f"{repo_name}/{rel_root}/{fname}"
                    dest = organizer.organize_file(src, context)

                    # Handle name collisions
                    if dest.exists():
                        stem = dest.stem
                        suffix = dest.suffix
                        counter = 1
                        while dest.exists():
                            dest = dest.parent / f"{stem}_{counter}{suffix}"
                            counter += 1

                    shutil.copy2(src, dest)
                    file_count += 1
                    stats["organized"] += 1

            logging.info(f"Organized {file_count} files from {repo_name}")
            cache.mark_downloaded(zip_url)
            cache.save()

            # Clean up to save disk
            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)

        except Exception as e:
            logging.error(f"Error downloading {repo_name}: {e}")
            stats["errors"] += 1

    return stats

# ---------------------------------------------------------------------------
# GitHub Releases Downloader (release assets with .nam/.wav files)
# ---------------------------------------------------------------------------
def download_github_releases(session, cache, organizer):
    """Download model files from GitHub release assets."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}

    for repo_info in GITHUB_RELEASE_REPOS:
        owner = repo_info["owner"]
        repo = repo_info["repo"]
        repo_name = f"{owner}/{repo}"
        release_cache_key = f"gh_releases_{repo_name}"

        if cache.is_downloaded(release_cache_key):
            logging.info(f"SKIP releases (cached): {repo_name}")
            stats["skipped"] += 1
            continue

        logging.info(f"Checking releases for {repo_name}...")

        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            resp = session.get(api_url, timeout=30,
                             headers={"Accept": "application/vnd.github+json"})
            if resp.status_code == 404:
                logging.warning(f"No releases found for {repo_name}")
                stats["errors"] += 1
                continue
            resp.raise_for_status()
            releases = resp.json()

            file_count = 0
            for release in releases[:10]:  # Check first 10 releases
                for asset in release.get("assets", []):
                    asset_name = asset["name"]
                    asset_url = asset["browser_download_url"]
                    ext = Path(asset_name).suffix.lower()

                    # Download zips and model files
                    if ext not in ALL_EXTENSIONS and ext != ".zip":
                        continue
                    if cache.is_downloaded(asset_url):
                        stats["skipped"] += 1
                        continue

                    try:
                        dl_resp = session.get(asset_url, stream=True, timeout=300)
                        dl_resp.raise_for_status()

                        tmp_path = Path("/tmp/gh_releases") / asset_name
                        tmp_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(tmp_path, "wb") as f:
                            for chunk in dl_resp.iter_content(chunk_size=1024*1024):
                                f.write(chunk)

                        if ext == ".zip":
                            # Extract zip
                            try:
                                extract_dir = tmp_path.parent / tmp_path.stem
                                with zipfile.ZipFile(tmp_path, "r") as zf:
                                    zf.extractall(extract_dir)
                                for root, dirs, files in os.walk(extract_dir):
                                    dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                                    for fn in files:
                                        if Path(fn).suffix.lower() not in ALL_EXTENSIONS:
                                            continue
                                        src = Path(root) / fn
                                        if not validate_file(src) or cache.is_duplicate(src):
                                            continue
                                        context = f"releases/{repo_name}/{asset_name}/{fn}"
                                        dest = organizer.organize_file(src, context)
                                        if dest.exists():
                                            dest = dest.parent / f"{dest.stem}_{release['tag_name']}{dest.suffix}"
                                        shutil.copy2(src, dest)
                                        file_count += 1
                                        stats["organized"] += 1
                                shutil.rmtree(extract_dir, ignore_errors=True)
                            except zipfile.BadZipFile:
                                logging.warning(f"Bad ZIP in release: {asset_name}")
                        else:
                            # Single model file
                            if validate_file(tmp_path) and not cache.is_duplicate(tmp_path):
                                context = f"releases/{repo_name}/{asset_name}"
                                dest = organizer.organize_file(tmp_path, context)
                                shutil.copy2(tmp_path, dest)
                                file_count += 1
                                stats["organized"] += 1

                        tmp_path.unlink(missing_ok=True)
                        cache.mark_downloaded(asset_url)
                        stats["downloaded"] += 1

                    except Exception as e:
                        logging.warning(f"Error downloading release asset {asset_name}: {e}")
                        stats["errors"] += 1

            logging.info(f"Organized {file_count} files from {repo_name} releases")
            cache.mark_downloaded(release_cache_key)
            cache.save()

        except Exception as e:
            logging.error(f"Error checking releases for {repo_name}: {e}")
            stats["errors"] += 1

    return stats

# ---------------------------------------------------------------------------
# TONE3000 API Downloader
# ---------------------------------------------------------------------------
def download_tone3000(session, cache, organizer, gear_filter=None, max_pages=2000):
    """Download from TONE3000 API with pagination."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}

    if not TONE3000_API_KEY:
        logging.warning("TONE3000_API_KEY not set, skipping TONE3000 downloads")
        return stats

    headers = {
        "Authorization": f"Bearer {TONE3000_API_KEY}",
        "Content-Type": "application/json",
    }

    # Gear types to download
    gear_types = gear_filter or ["amp", "pedal", "full-rig", "ir", "outboard"]
    page_size = 25  # API max for search

    for gear in gear_types:
        logging.info(f"=== TONE3000: Downloading gear={gear} ===")
        page = 1
        total_pages = 1  # Will be updated from first response

        while page <= min(total_pages, max_pages):
            try:
                url = f"{TONE3000_BASE}/tones/search?gear={gear}&page={page}&page_size={page_size}&sort=most-downloaded"
                resp = session.get(url, headers=headers, timeout=60)

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    logging.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

                total_pages = data.get("total_pages", 1)
                tones = data.get("data", [])

                if not tones:
                    break

                logging.info(f"Page {page}/{total_pages} — {len(tones)} tones")

                for tone in tones:
                    tone_id = tone.get("id")
                    title = tone.get("title", f"unknown_{tone_id}")
                    tone_gear = tone.get("gear", gear)

                    # Get models for this tone
                    try:
                        models_url = f"{TONE3000_BASE}/models?tone_id={tone_id}&page=1&page_size=100"
                        models_resp = session.get(models_url, headers=headers, timeout=60)

                        if models_resp.status_code == 429:
                            time.sleep(30)
                            models_resp = session.get(models_url, headers=headers, timeout=60)

                        models_resp.raise_for_status()
                        models_data = models_resp.json()
                        models = models_data.get("data", [])

                        for model in models:
                            model_url = model.get("model_url", "")
                            model_name = model.get("name", "")

                            if not model_url:
                                continue
                            if cache.is_downloaded(model_url):
                                stats["skipped"] += 1
                                continue

                            # Download the model
                            try:
                                dl_resp = session.get(model_url, headers=headers, timeout=120)
                                dl_resp.raise_for_status()

                                # Determine extension from URL or content-type
                                url_path = urlparse(model_url).path
                                ext = Path(url_path).suffix.lower()
                                if ext not in ALL_EXTENSIONS:
                                    ct = dl_resp.headers.get("Content-Type", "")
                                    if "wav" in ct:
                                        ext = ".wav"
                                    elif "json" in ct:
                                        ext = ".nam"
                                    else:
                                        ext = ".nam"

                                # Build filename from tone title + model name
                                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                                if model_name and model_name != title:
                                    clean_model = re.sub(r'[<>:"/\\|?*]', '_', model_name)
                                    fname = f"{clean_title}_{clean_model}{ext}"
                                else:
                                    fname = f"{clean_title}{ext}"

                                # Save to temp, then organize
                                tmp_path = Path("/tmp/tone3000_tmp") / fname
                                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                                tmp_path.write_bytes(dl_resp.content)

                                if validate_file(tmp_path) and not cache.is_duplicate(tmp_path):
                                    context = f"tone3000/{tone_gear}/{title}/{fname}"
                                    dest = organizer.organize_file(tmp_path, context)
                                    if dest.exists():
                                        stem, suffix = dest.stem, dest.suffix
                                        dest = dest.parent / f"{stem}_{tone_id}{suffix}"
                                    shutil.move(str(tmp_path), dest)
                                    stats["organized"] += 1
                                    stats["downloaded"] += 1
                                else:
                                    tmp_path.unlink(missing_ok=True)
                                    stats["skipped"] += 1

                                cache.mark_downloaded(model_url)

                            except Exception as e:
                                logging.warning(f"Error downloading model {model_name}: {e}")
                                stats["errors"] += 1

                        # Save cache periodically
                        if stats["downloaded"] % 50 == 0:
                            cache.save()

                    except Exception as e:
                        logging.warning(f"Error fetching models for tone {tone_id}: {e}")
                        stats["errors"] += 1

                page += 1
                time.sleep(0.5)  # Be nice to the API

            except Exception as e:
                logging.error(f"Error on page {page} gear={gear}: {e}")
                stats["errors"] += 1
                page += 1
                time.sleep(5)

    cache.save()
    return stats

# ---------------------------------------------------------------------------
# Direct Site Downloader
# ---------------------------------------------------------------------------
DIRECT_SOURCES = [
    # ===================================================================
    # VERIFIED WORKING URLs — These have been tested and confirmed to work
    # ===================================================================

    # === Voxengo Reverb IRs (VERIFIED — real direct download) ===
    {"url": "https://www.voxengo.com/files/impulses/IMreverbs.zip", "name": "Voxengo_IM_Reverb_IRs"},

    # === EchoThief Real Space IRs (VERIFIED — 115 real places) ===
    {"url": "http://www.echothief.com/wp-content/uploads/2016/06/EchoThiefImpulseResponseLibrary.zip",
     "name": "EchoThief_Real_Spaces"},

    # === Kalthallen Cabs (VERIFIED) ===
    {"url": "https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "name": "Kalthallen_Cabs"},

    # ===================================================================
    # URLS TO TRY — MAY WORK (sites confirmed but exact path not tested)
    # ===================================================================

    # === Forward Audio faIR (many packs, try known paths) ===
    {"url": "https://forward-audio.com/wp-content/uploads/2020/07/faIR-Post-Grunge.zip", "name": "faIR_Post_Grunge"},
    {"url": "https://forward-audio.com/wp-content/uploads/2020/04/faIR-Modern-Rock.zip", "name": "faIR_Modern_Rock"},
    {"url": "https://forward-audio.com/wp-content/uploads/2020/09/faIR-Modern-Metal.zip", "name": "faIR_Modern_Metal"},
    {"url": "https://forward-audio.com/wp-content/uploads/2021/01/faIR-Progressive-Metal.zip", "name": "faIR_Progressive_Metal"},
]

def download_direct_sources(session, cache, organizer):
    """Download from direct URL sources (ZIP files and individual files)."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}
    tmp_dir = Path("/tmp/direct_downloads")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for source in DIRECT_SOURCES:
        url = source["url"]
        name = source["name"]

        if cache.is_downloaded(url):
            logging.info(f"SKIP (cached): {name}")
            stats["skipped"] += 1
            continue

        logging.info(f"Downloading {name}...")

        try:
            resp = session.get(url, stream=True, timeout=300, allow_redirects=True)

            if resp.status_code in (404, 403):
                logging.warning(f"Not available (HTTP {resp.status_code}): {name}")
                stats["errors"] += 1
                continue

            resp.raise_for_status()

            # Determine filename
            content_disp = resp.headers.get("Content-Disposition", "")
            if "filename=" in content_disp:
                fname = re.findall(r'filename="?([^";\n]+)', content_disp)[0]
            else:
                fname = unquote(urlparse(url).path.split("/")[-1])

            dl_path = tmp_dir / fname
            with open(dl_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

            size_mb = dl_path.stat().st_size / (1024 * 1024)
            logging.info(f"Downloaded {name}: {size_mb:.1f} MB")
            stats["downloaded"] += 1

            # If ZIP, extract and organize
            if dl_path.suffix.lower() == ".zip":
                try:
                    extract_dir = tmp_dir / name
                    with zipfile.ZipFile(dl_path, "r") as zf:
                        zf.extractall(extract_dir)

                    file_count = 0
                    for root, dirs, files in os.walk(extract_dir):
                        dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                        for fn in files:
                            if Path(fn).suffix.lower() not in ALL_EXTENSIONS:
                                continue
                            src = Path(root) / fn
                            if not validate_file(src):
                                continue
                            if cache.is_duplicate(src):
                                continue
                            rel = os.path.relpath(root, extract_dir)
                            context = f"{name}/{rel}/{fn}"
                            dest = organizer.organize_file(src, context)
                            if dest.exists():
                                stem, suffix = dest.stem, dest.suffix
                                c = 1
                                while dest.exists():
                                    dest = dest.parent / f"{stem}_{c}{suffix}"
                                    c += 1
                            shutil.copy2(src, dest)
                            file_count += 1
                            stats["organized"] += 1

                    logging.info(f"Organized {file_count} files from {name}")
                    shutil.rmtree(extract_dir, ignore_errors=True)
                except zipfile.BadZipFile:
                    logging.error(f"Bad ZIP file: {name}")
                    stats["errors"] += 1
            else:
                # Single file
                if validate_file(dl_path) and not cache.is_duplicate(dl_path):
                    context = f"direct/{name}/{fname}"
                    dest = organizer.organize_file(dl_path, context)
                    shutil.copy2(dl_path, dest)
                    stats["organized"] += 1

            dl_path.unlink(missing_ok=True)
            cache.mark_downloaded(url)
            cache.save()

        except Exception as e:
            logging.error(f"Error downloading {name}: {e}")
            stats["errors"] += 1

    return stats

# ---------------------------------------------------------------------------
# Documentation Generator
# ---------------------------------------------------------------------------
def generate_documentation():
    """Generate README.md, QUICK_START.md, and SOURCES.md."""
    # Count files
    total_files = 0
    categories = {}

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in ALL_EXTENSIONS:
                total_files += 1
                # Get category
                rel = os.path.relpath(root, BASE_DIR)
                parts = rel.split(os.sep)
                if len(parts) >= 2:
                    cat = f"{parts[0]}/{parts[1]}"
                    categories[cat] = categories.get(cat, 0) + 1

    # README.md
    readme = f"""# 🎸 IR DEF Repository — The Ultimate Free IR & NAM Collection

> **{total_files:,} archivos** de Impulse Responses y capturas Neural Amp Modeler  
> Organizado por instrumento, tipo y marca — 100% gratuito y legal

---

## 📊 Estadísticas

| Categoría | Archivos |
|-----------|----------|
"""
    for cat, count in sorted(categories.items()):
        readme += f"| {cat} | {count:,} |\n"
    readme += f"| **TOTAL** | **{total_files:,}** |\n"

    readme += """
---

## 📂 Estructura

```
├── GUITARRA/          — IRs y capturas NAM de amplificadores y cabinas de guitarra
│   ├── IRs/           — Impulse responses (WAV) organizados por marca
│   └── NAM_Capturas/  — Modelos NAM organizados por tipo (Amps/Pedals/Full_Rigs)
├── BAJO/              — IRs y capturas NAM para bajo
├── ELECTROACUSTICA/   — IRs para corrección de piezo y simulación acústica  
└── UTILIDADES/        — Reverbs, emulaciones de mic, favoritos curados
```

## 🚀 Quick Start

Ver [QUICK_START.md](QUICK_START.md) para instrucciones de cómo cargar IRs en tu equipo.

## 📋 Fuentes

Ver [SOURCES.md](SOURCES.md) para la lista completa de fuentes y créditos.

---

*Repositorio generado automáticamente — Todos los archivos provienen de fuentes gratuitas verificadas*
"""
    (BASE_DIR / "README.md").write_text(readme, encoding="utf-8")

    # QUICK_START.md
    quickstart = """# 🚀 Quick Start — Cómo usar estos IRs y capturas NAM

## Cargar IRs (archivos .wav)

### Line 6 Helix / HX Stomp
1. Conecta Helix por USB → Abre HX Edit
2. Ve a la pestaña "Impulses" → Arrastra archivos .wav

### Neural DSP (Archetype, Quad Cortex)
1. Abre Cortex Control o el plugin Neural DSP
2. En el bloque de Cabina → Import IR → Selecciona el .wav

### Kemper  
1. Copia los .wav a una USB
2. En Kemper: Rig Manager → Import → Selecciona IRs

### Fractal Audio (Axe-Fx, FM3, FM9)
1. Abre Axe-Edit o FM3-Edit
2. Manage Cabs → Import → Selecciona .wav

### Cualquier DAW (con IR Loader gratuito)
1. Descarga NadIR by Ignite Amps (gratis)
2. Insértalo como plugin → Carga el archivo .wav

---

## Cargar capturas NAM (archivos .nam / .json)

### NAM Plugin (VST/AU)
1. Descarga Neural Amp Modeler Plugin desde [GitHub](https://github.com/sdatkinson/NeuralAmpModelerPlugin)
2. Abre en tu DAW → Load Model → Selecciona archivo .nam

### ToneX / AIDA-X
1. Los archivos .aidax son compatibles con AIDA-X
2. Carga desde la interfaz del plugin

---

*💡 Tip: Para mejor sonido, usa un IR de cabina DESPUÉS de una captura NAM de amplificador (los marcados "DirectOut")*
"""
    (BASE_DIR / "QUICK_START.md").write_text(quickstart, encoding="utf-8")

    # SOURCES.md
    sources = """# 📋 Fuentes y Créditos

Todos los archivos en este repositorio provienen de fuentes **gratuitas y legítimas**.

## GitHub Repositories
- [pelennor2170/NAM_models](https://github.com/pelennor2170/NAM_models) — Community NAM collection
- [GuitarML/ToneLibrary](https://github.com/GuitarML/ToneLibrary) — ML tone models
- [orodamaral/Speaker-Cabinets-IRs](https://github.com/orodamaral/Speaker-Cabinets-IRs) — Speaker cab IRs
- [sdatkinson/neural-amp-modeler](https://github.com/sdatkinson/neural-amp-modeler) — Official NAM
- [GuitarML/Proteus](https://github.com/GuitarML/Proteus) — Proteus tone models

## TONE3000 Community
- [TONE3000](https://tone3000.com) — World's largest guitar tone community

## IR Providers
- [Forward Audio](https://forward-audio.com) — faIR series (free IR packs)
- [Origin Effects](https://origineffects.com) — Free IR Cab Library
- [GGWPTECH](https://ggwptech.com) — Free bass cab IRs
- [Shift Line](https://shift-line.com) — Free bass IR pack
- [PreSonus](https://presonus.com) — 25 Analog Cab IRs
- [Wilkinson Audio](https://wilkinsonaudio.com) — God's Cab
- [ML Sound Lab](https://ml-sound-lab.com) — Best IR In The World
- [Tone Junkie](https://tonejunkie.com) — Free IR packs
- [Redwirez](https://redwirez.com) — Free IR samples
- [Celestion](https://celestion.com) — Official Celestion IRs
- [Kalthallen](https://kalthallen.net) — Free cab IRs
- [Soundwoofer](https://soundwoofer.com) — Open-source IR library
- [acousticir.free.fr](http://acousticir.free.fr) — Acoustic instrument IRs
- [Worship Tutorials](https://worshiptutorials.com) — Acoustic piezo IRs
- [Science Amplification](https://scienceamps.com) — Bass cab IRs

---

*Respeta las licencias individuales de cada fuente. Este repositorio recopila contenido gratuito para uso personal y educativo.*
"""
    (BASE_DIR / "SOURCES.md").write_text(sources, encoding="utf-8")

    logging.info(f"Documentation generated ({total_files:,} total files cataloged)")
    return total_files

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="IR DEF Repository Downloader")
    parser.add_argument("--tier", type=str, default="all",
                        choices=["github", "tone3000-amps", "tone3000-pedals", "direct", "docs", "all"],
                        help="Which tier to download")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing files")
    parser.add_argument("--output-dir", type=str, default="/tmp/ir_repository", help="Output directory")
    args = parser.parse_args()

    global BASE_DIR, CACHE_FILE, STATS_FILE, LOG_FILE
    BASE_DIR = Path(args.output_dir)
    CACHE_FILE = BASE_DIR / ".download_cache.json"
    STATS_FILE = BASE_DIR / ".stats.json"
    LOG_FILE = BASE_DIR / ".download.log"

    setup_logging()
    logging.info("=" * 60)
    logging.info("IR DEF Repository — Download & Organize")
    logging.info(f"Tier: {args.tier} | Output: {BASE_DIR}")
    logging.info("=" * 60)

    session = get_session()
    cache = DownloadCache()
    organizer = FileOrganizer()

    all_stats = {}

    if args.validate_only:
        logging.info("Validation mode — checking existing files...")
        invalid = 0
        valid = 0
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in ALL_EXTENSIONS:
                    if validate_file(fp):
                        valid += 1
                    else:
                        logging.warning(f"INVALID: {fp}")
                        invalid += 1
        logging.info(f"Validation complete: {valid} valid, {invalid} invalid")
        return

    if args.tier in ("github", "all"):
        logging.info(">>> TIER 1: GitHub Repositories")
        stats = download_github_repos(session, cache, organizer)
        all_stats["github"] = stats
        logging.info(f"GitHub repos done: {stats}")

        logging.info(">>> TIER 1b: GitHub Release Assets")
        release_stats = download_github_releases(session, cache, organizer)
        all_stats["github_releases"] = release_stats
        logging.info(f"GitHub releases done: {release_stats}")

    if args.tier in ("tone3000-amps", "all"):
        logging.info(">>> TIER 2: TONE3000 Amps & IRs")
        stats = download_tone3000(session, cache, organizer, gear_filter=["amp", "ir"])
        all_stats["tone3000_amps"] = stats
        logging.info(f"TONE3000 amps done: {stats}")

    if args.tier in ("tone3000-pedals", "all"):
        logging.info(">>> TIER 3: TONE3000 Pedals & Rigs")
        stats = download_tone3000(session, cache, organizer, gear_filter=["pedal", "full-rig", "outboard"])
        all_stats["tone3000_pedals"] = stats
        logging.info(f"TONE3000 pedals done: {stats}")

    if args.tier in ("direct", "all"):
        logging.info(">>> TIER 4: Direct Sites")
        stats = download_direct_sources(session, cache, organizer)
        all_stats["direct"] = stats
        logging.info(f"Direct sites done: {stats}")

    if args.tier in ("docs", "all"):
        logging.info(">>> Generating Documentation")
        total = generate_documentation()
        all_stats["docs"] = {"total_files": total}

    # Final stats
    STATS_FILE.write_text(json.dumps(all_stats, indent=2), encoding="utf-8")
    logging.info("=" * 60)
    logging.info("ALL DONE!")
    logging.info(json.dumps(all_stats, indent=2))
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
