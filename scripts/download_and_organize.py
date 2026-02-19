#!/usr/bin/env python3
"""
IR DEF Repository — Massive IR & NAM Capture Downloader/Organizer v3
=====================================================================
ONLY downloads .wav and .nam files.
NO subfolders — all files flat in category folders with descriptive names.
Categories: IR_Guitarra, IR_Bajo, IR_Acustica, IR_Utilidades, NAM_Capturas
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

# ONLY these extensions
VALID_EXTENSIONS = {".wav", ".nam"}

# ---------------------------------------------------------------------------
# Brand detection patterns
# ---------------------------------------------------------------------------
BRAND_PATTERNS = {
    "Marshall": [r"marshall", r"jcm", r"jvm", r"plexi", r"1959", r"1987", r"2203", r"2204", r"dsl", r"jmp"],
    "Fender": [r"fender", r"twin", r"deluxe.reverb", r"bassman", r"princeton", r"champ", r"vibrolux", r"super.reverb"],
    "Mesa_Boogie": [r"mesa", r"boogie", r"rectifier", r"recto", r"dual.rec", r"triple.rec", r"mark.(iv|v|ii|iii)", r"lonestar"],
    "Vox": [r"vox", r"ac.?30", r"ac.?15"],
    "Orange": [r"orange", r"rockerverb", r"thunderverb", r"tiny.terror", r"or\d{2,3}"],
    "Peavey": [r"peavey", r"5150", r"6505", r"invective", r"xxx", r"jsx"],
    "EVH": [r"\bevh\b", r"5150.*(iii|el34|iconic)"],
    "Bogner": [r"bogner", r"uberschall", r"ecstasy", r"shiva"],
    "Soldano": [r"soldano", r"slo.?100", r"\bslo\b"],
    "Diezel": [r"diezel", r"herbert", r"vh4", r"hagen"],
    "Friedman": [r"friedman", r"be.?100", r"dirty.shirley", r"small.box"],
    "Engl": [r"engl", r"powerball", r"fireball", r"savage", r"invader"],
    "Ampeg": [r"ampeg", r"svt", r"b-?15", r"v4b", r"portaflex"],
    "Darkglass": [r"darkglass", r"microtubes", r"alpha.*omega", r"b7k"],
    "Hiwatt": [r"hiwatt", r"dr.?103"],
    "Matchless": [r"matchless", r"chieftain"],
    "Hughes_Kettner": [r"hughes", r"kettner", r"triamp", r"tubemeister"],
    "Laney": [r"laney", r"ironheart"],
    "Supro": [r"supro"],
    "Morgan": [r"\bmorgan\b"],
    "Revv": [r"\brevv\b", r"generator"],
    "Victory": [r"victory", r"kraken", r"duchess"],
    "Celestion": [r"celestion", r"v30", r"vintage.30", r"greenback", r"creamback", r"g12", r"alnico"],
    "Eminence": [r"eminence", r"swamp.thang", r"texas.heat"],
    "Jensen": [r"jensen"],
    "Taylor": [r"\btaylor\b"],
    "Martin": [r"\bmartin\b", r"d-?28", r"d-?18"],
    "Gibson": [r"gibson", r"j-?45", r"hummingbird"],
}

# Cabinet/speaker patterns for IR naming
CAB_PATTERNS = {
    "1x12": [r"1x12"],
    "2x12": [r"2x12"],
    "4x12": [r"4x12"],
    "1x10": [r"1x10"],
    "2x10": [r"2x10"],
    "4x10": [r"4x10"],
    "1x15": [r"1x15"],
    "8x10": [r"8x10"],
}

SPEAKER_PATTERNS = {
    "V30": [r"v30", r"vintage.?30"],
    "G12M": [r"g12m", r"greenback"],
    "G12H": [r"g12h"],
    "G12T75": [r"g12t.?75"],
    "Creamback": [r"creamback", r"g12m.?65"],
    "Alnico_Blue": [r"alnico.?blue", r"blue.?alnico"],
    "P12R": [r"p12r"],
    "C12N": [r"c12n"],
    "JBL_D120": [r"jbl", r"d120"],
    "EVM12L": [r"evm", r"evm12"],
}

MIC_PATTERNS = {
    "SM57": [r"sm57", r"sm.?57"],
    "MD421": [r"md421", r"md.?421"],
    "R121": [r"r121", r"royer"],
    "U87": [r"u87", r"u.?87"],
    "E609": [r"e609", r"609"],
    "M160": [r"m160"],
    "C414": [r"c414"],
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
        "User-Agent": "IR-DEF-Repository/3.0 (github.com/ir-def-repository)",
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
# File Validation
# ---------------------------------------------------------------------------
def validate_wav(path):
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
    p = Path(path)
    if p.stat().st_size < 100:
        return False
    if p.suffix.lower() == ".wav":
        return validate_wav(path)
    if p.suffix.lower() == ".nam":
        return True  # .nam binary, just check size
    return False

# ---------------------------------------------------------------------------
# Smart Flat Organizer — NO subfolders
# ---------------------------------------------------------------------------
class FlatOrganizer:
    """Organizes files into flat category folders with descriptive names."""

    @staticmethod
    def _detect_patterns(text, patterns):
        """Return first matching key from pattern dict."""
        text_lower = text.lower()
        for key, pats in patterns.items():
            for pat in pats:
                if re.search(pat, text_lower):
                    return key
        return None

    def detect_category(self, filepath, filename):
        """Detect which flat category folder this file belongs to."""
        context = (str(filepath) + " " + filename).lower()
        ext = Path(filename).suffix.lower()

        # NAM captures
        if ext == ".nam":
            return "NAM_Capturas"

        # Bass IRs
        if any(k in context for k in ["bass", "bajo", "b15", "svt", "ampeg", "darkglass",
                                       "eden", "sunn", "8x10", "4x10", "portaflex"]):
            return "IR_Bajo"

        # Acoustic IRs
        if any(k in context for k in ["acoustic", "acustic", "electroac", "piezo",
                                       "body_sim", "taylor", "martin", "d-28", "j-45",
                                       "fingerpick", "nylon"]):
            return "IR_Acustica"

        # Utility IRs (reverbs, rooms, mics)
        if any(k in context for k in ["reverb", "room", "hall", "plate", "spring",
                                       "mic_emu", "microphone", "convolution",
                                       "echo", "ambient", "space"]):
            return "IR_Utilidades"

        # Default: guitar IRs
        return "IR_Guitarra"

    def build_descriptive_name(self, filepath, filename, source_name=""):
        """Build a flat, descriptive filename like:
        Marshall_JCM800_4x12_V30_SM57_Clean.wav
        """
        context = str(filepath) + " " + filename
        stem = Path(filename).stem
        ext = Path(filename).suffix.lower()
        parts = []

        # 1. Brand
        brand = self._detect_patterns(context, BRAND_PATTERNS)
        if brand:
            parts.append(brand)

        # 2. Try to extract model name from original filename
        model = self._extract_model(stem, context)
        if model:
            parts.append(model)

        # 3. Cabinet size
        cab = self._detect_patterns(context, CAB_PATTERNS)
        if cab:
            parts.append(cab)

        # 4. Speaker
        speaker = self._detect_patterns(context, SPEAKER_PATTERNS)
        if speaker:
            parts.append(speaker)

        # 5. Microphone
        mic = self._detect_patterns(context, MIC_PATTERNS)
        if mic:
            parts.append(mic)

        # 6. Style tags
        style = self._detect_style(context)
        if style:
            parts.append(style)

        # If we couldn't detect anything useful, use cleaned original name
        if not parts:
            parts.append(self._clean_stem(stem))
        elif len(parts) == 1 and parts[0] == brand:
            # Only have brand, add cleaned stem for more info
            clean = self._clean_stem(stem)
            if clean and clean.lower() != brand.lower():
                parts.append(clean)

        # Add source prefix if from known source
        if source_name and source_name not in "_".join(parts):
            # Only add for non-obvious sources
            pass

        name = "_".join(parts)
        # Sanitize
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')

        return f"{name}{ext}"

    @staticmethod
    def _extract_model(stem, context):
        """Try to extract amp/cab model name."""
        # Common model patterns
        model_patterns = [
            r"(JCM\s*\d+)", r"(JVM\s*\d+)", r"(DSL\s*\d+)",
            r"(5150\s*\w*)", r"(6505\s*\w*)",
            r"(Dual\s*Rec\w*)", r"(Triple\s*Rec\w*)", r"(Rectifier\w*)",
            r"(Mark\s*(?:IV|V|III|II)\w*)",
            r"(AC\s*30\w*)", r"(AC\s*15\w*)",
            r"(SLO\s*\d*)", r"(VH4\w*)", r"(Herbert\w*)",
            r"(BE\s*100\w*)", r"(Dirty\s*Shirley\w*)",
            r"(Powerball\w*)", r"(Fireball\w*)",
            r"(SVT\w*)", r"(B-?15\w*)",
            r"(Twin\s*Reverb\w*)", r"(Deluxe\s*Reverb\w*)",
            r"(Bassman\w*)", r"(Princeton\w*)",
            r"(Plexi\w*)", r"(Silver\s*Jubilee\w*)",
            r"(Tiny\s*Terror\w*)", r"(Rockerverb\w*)",
            r"(Uberschall\w*)", r"(Ecstasy\w*)",
            r"(Kraken\w*)", r"(Invective\w*)",
        ]
        for pat in model_patterns:
            m = re.search(pat, context, re.I)
            if m:
                return re.sub(r'\s+', '_', m.group(1).strip())
        return None

    @staticmethod
    def _detect_style(context):
        ctx = context.lower()
        if any(k in ctx for k in ["high gain", "hi gain", "highgain", "metal", "djent"]):
            return "HiGain"
        if any(k in ctx for k in ["crunch", "breakup", "edge"]):
            return "Crunch"
        if any(k in ctx for k in ["clean", "pristine", "crystal", "jazz"]):
            return "Clean"
        if any(k in ctx for k in ["vintage", "classic", "retro"]):
            return "Vintage"
        if any(k in ctx for k in ["modern", "contemporary"]):
            return "Modern"
        return None

    @staticmethod
    def _clean_stem(stem):
        """Clean filename stem."""
        stem = re.sub(r"[\[\(]?(free|download|pack|sample|demo|www\.\S+)[\]\)]?", "", stem, flags=re.I)
        stem = re.sub(r"[\s\-\.]+", "_", stem)
        stem = re.sub(r"_+", "_", stem)
        stem = stem.strip("_")
        if stem:
            parts = stem.split("_")
            parts = [p.capitalize() if len(p) > 2 else p.upper() for p in parts if p]
            stem = "_".join(parts)
        return stem

    def organize_file(self, src_path, original_rel_path="", source_name=""):
        """Determine flat destination path for a file. Returns (dest_path)."""
        filename = Path(src_path).name
        context_path = original_rel_path or str(src_path)

        category = self.detect_category(context_path, filename)
        dest_dir = BASE_DIR / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        clean_name = self.build_descriptive_name(context_path, filename, source_name)
        dest = dest_dir / clean_name

        # Handle collisions
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        return dest

# ---------------------------------------------------------------------------
# GitHub Repos
# ---------------------------------------------------------------------------
GITHUB_REPOS = [
    {"url": "https://github.com/pelennor2170/NAM_models", "desc": "Massive NAM model collection"},
    {"url": "https://github.com/GuitarML/ToneLibrary", "desc": "GuitarML Tone Library models"},
    {"url": "https://github.com/GuitarML/Proteus", "desc": "Proteus tone models"},
    {"url": "https://github.com/sdatkinson/neural-amp-modeler", "desc": "NAM official examples"},
    {"url": "https://github.com/mikeoliphant/NeuralAmpModels", "desc": "Neural amp model collection"},
    {"url": "https://github.com/orodamaral/Speaker-Cabinets-IRs", "desc": "Speaker Cabinet IRs"},
    {"url": "https://github.com/keyth72/AxeFxImpulseResponses", "desc": "Axe-Fx IRs"},
    {"url": "https://github.com/Alec-Wright/Automated-GuitarAmpModelling", "desc": "ML guitar amp models"},
    {"url": "https://github.com/GuitarML/SmartGuitarAmp", "desc": "SmartGuitarAmp models"},
    {"url": "https://github.com/GuitarML/SmartGuitarPedal", "desc": "SmartGuitarPedal models"},
    {"url": "https://github.com/GuitarML/TS-M1N3", "desc": "TS-M1N3 overdrive models"},
    {"url": "https://github.com/GuitarML/Chameleon", "desc": "Chameleon amp modeler"},
    {"url": "https://github.com/AidaDSP/AIDA-X", "desc": "AIDA-X amp modeler models"},
]

GITHUB_RELEASE_REPOS = [
    {"owner": "GuitarML", "repo": "Proteus", "desc": "Proteus releases"},
    {"owner": "GuitarML", "repo": "TS-M1N3", "desc": "TS-M1N3 releases"},
    {"owner": "GuitarML", "repo": "SmartGuitarAmp", "desc": "SmartGuitarAmp releases"},
    {"owner": "GuitarML", "repo": "Chameleon", "desc": "Chameleon releases"},
    {"owner": "mikeoliphant", "repo": "NeuralAmpModels", "desc": "Neural amp model releases"},
]

def download_github_repos(session, cache, organizer):
    """Download GitHub repos as ZIP, extract only .wav and .nam files."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}
    tmp_dir = Path("/tmp/github_zips")

    for repo in GITHUB_REPOS:
        repo_url = repo["url"]
        repo_name = repo_url.split("/")[-1]
        zip_url = f"{repo_url}/archive/refs/heads/main.zip"

        if cache.is_downloaded(zip_url):
            logging.info(f"SKIP (cached): {repo_name}")
            stats["skipped"] += 1
            continue

        logging.info(f"Downloading {repo_name}...")
        zip_path = tmp_dir / f"{repo_name}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            resp = session.get(zip_url, stream=True, timeout=300)
            if resp.status_code == 404:
                zip_url = f"{repo_url}/archive/refs/heads/master.zip"
                resp = session.get(zip_url, stream=True, timeout=300)
            resp.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

            size_mb = zip_path.stat().st_size / (1024 * 1024)
            logging.info(f"Downloaded {repo_name}: {size_mb:.1f} MB")
            stats["downloaded"] += 1

            extract_dir = tmp_dir / repo_name
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            file_count = 0
            for root, dirs, files in os.walk(extract_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel_root = os.path.relpath(root, extract_dir)

                for fname in files:
                    ext = Path(fname).suffix.lower()
                    if ext not in VALID_EXTENSIONS:
                        continue

                    src = Path(root) / fname
                    if not validate_file(src):
                        continue
                    if cache.is_duplicate(src):
                        continue

                    context = f"{repo_name}/{rel_root}/{fname}"
                    dest = organizer.organize_file(src, context, source_name=repo_name)
                    shutil.copy2(src, dest)
                    file_count += 1
                    stats["organized"] += 1

            logging.info(f"Organized {file_count} files from {repo_name}")
            cache.mark_downloaded(zip_url)
            cache.save()

            shutil.rmtree(extract_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)

        except Exception as e:
            logging.error(f"Error downloading {repo_name}: {e}")
            stats["errors"] += 1

    return stats

def download_github_releases(session, cache, organizer):
    """Download .wav and .nam from GitHub release assets."""
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
                continue
            resp.raise_for_status()
            releases = resp.json()

            file_count = 0
            for release in releases[:10]:
                for asset in release.get("assets", []):
                    asset_name = asset["name"]
                    asset_url = asset["browser_download_url"]
                    ext = Path(asset_name).suffix.lower()

                    if ext not in VALID_EXTENSIONS and ext != ".zip":
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
                            try:
                                extract_dir = tmp_path.parent / tmp_path.stem
                                with zipfile.ZipFile(tmp_path, "r") as zf:
                                    zf.extractall(extract_dir)
                                for root, dirs, files in os.walk(extract_dir):
                                    dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                                    for fn in files:
                                        if Path(fn).suffix.lower() not in VALID_EXTENSIONS:
                                            continue
                                        src = Path(root) / fn
                                        if not validate_file(src) or cache.is_duplicate(src):
                                            continue
                                        context = f"releases/{repo_name}/{asset_name}/{fn}"
                                        dest = organizer.organize_file(src, context, source_name=repo)
                                        shutil.copy2(src, dest)
                                        file_count += 1
                                        stats["organized"] += 1
                                shutil.rmtree(extract_dir, ignore_errors=True)
                            except zipfile.BadZipFile:
                                logging.warning(f"Bad ZIP in release: {asset_name}")
                        else:
                            if validate_file(tmp_path) and not cache.is_duplicate(tmp_path):
                                context = f"releases/{repo_name}/{asset_name}"
                                dest = organizer.organize_file(tmp_path, context, source_name=repo)
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
# TONE3000 API Downloader — ROBUST
# ---------------------------------------------------------------------------
def download_tone3000(session, cache, organizer, gear_filter=None, max_pages=500):
    """Download from TONE3000 API. Only keeps .wav and .nam files."""
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "organized": 0}

    if not TONE3000_API_KEY:
        logging.warning("TONE3000_API_KEY not set, skipping TONE3000 downloads")
        return stats

    headers = {
        "Authorization": f"Bearer {TONE3000_API_KEY}",
        "Content-Type": "application/json",
    }

    gear_types = gear_filter or ["amp", "pedal", "full-rig", "ir", "outboard"]
    page_size = 25
    consecutive_errors = 0
    max_consecutive_errors = 10

    for gear in gear_types:
        logging.info(f"=== TONE3000: gear={gear} ===")
        page = 1
        total_pages = 1

        while page <= min(total_pages, max_pages):
            if consecutive_errors >= max_consecutive_errors:
                logging.error(f"Too many consecutive errors ({consecutive_errors}), stopping {gear}")
                consecutive_errors = 0
                break

            try:
                url = f"{TONE3000_BASE}/tones/search?gear={gear}&page={page}&page_size={page_size}&sort=most-downloaded"
                resp = session.get(url, headers=headers, timeout=60)

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 60))
                    logging.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code in (401, 403):
                    logging.error(f"Auth error on TONE3000 (HTTP {resp.status_code}). Check API key.")
                    return stats

                if resp.status_code >= 400:
                    logging.warning(f"TONE3000 HTTP {resp.status_code} on page {page}, skipping page")
                    consecutive_errors += 1
                    page += 1
                    continue

                resp.raise_for_status()
                data = resp.json()

                total_pages = data.get("total_pages", 1)
                tones = data.get("data", [])

                if not tones:
                    logging.info(f"No more tones for gear={gear} at page {page}")
                    break

                logging.info(f"Page {page}/{total_pages} — {len(tones)} tones")
                consecutive_errors = 0  # Reset on success

                for tone in tones:
                    tone_id = tone.get("id")
                    title = tone.get("title", f"unknown_{tone_id}")
                    tone_gear = tone.get("gear", gear)

                    try:
                        models_url = f"{TONE3000_BASE}/models?tone_id={tone_id}&page=1&page_size=100"
                        models_resp = session.get(models_url, headers=headers, timeout=60)

                        if models_resp.status_code == 429:
                            time.sleep(30)
                            models_resp = session.get(models_url, headers=headers, timeout=60)

                        if models_resp.status_code >= 400:
                            continue

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

                            try:
                                dl_resp = session.get(model_url, headers=headers, timeout=120)
                                dl_resp.raise_for_status()

                                # Determine extension
                                url_path = urlparse(model_url).path
                                ext = Path(url_path).suffix.lower()
                                if ext not in VALID_EXTENSIONS:
                                    ct = dl_resp.headers.get("Content-Type", "")
                                    if "wav" in ct:
                                        ext = ".wav"
                                    else:
                                        ext = ".nam"

                                # ONLY keep .wav and .nam
                                if ext not in VALID_EXTENSIONS:
                                    cache.mark_downloaded(model_url)
                                    continue

                                # Build filename
                                clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                                if model_name and model_name != title:
                                    clean_model = re.sub(r'[<>:"/\\|?*]', '_', model_name)
                                    fname = f"{clean_title}_{clean_model}{ext}"
                                else:
                                    fname = f"{clean_title}{ext}"

                                tmp_path = Path("/tmp/tone3000_tmp") / fname
                                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                                tmp_path.write_bytes(dl_resp.content)

                                if validate_file(tmp_path) and not cache.is_duplicate(tmp_path):
                                    context = f"tone3000/{tone_gear}/{title}/{fname}"
                                    dest = organizer.organize_file(tmp_path, context, source_name="TONE3000")
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

                        if stats["downloaded"] % 50 == 0 and stats["downloaded"] > 0:
                            cache.save()

                    except Exception as e:
                        logging.warning(f"Error fetching models for tone {tone_id}: {e}")
                        stats["errors"] += 1

                page += 1
                time.sleep(0.5)

            except Exception as e:
                logging.error(f"Error on page {page} gear={gear}: {e}")
                stats["errors"] += 1
                consecutive_errors += 1
                page += 1
                time.sleep(5)

    cache.save()
    return stats

# ---------------------------------------------------------------------------
# Direct Sites
# ---------------------------------------------------------------------------
DIRECT_SOURCES = [
    {"url": "https://www.voxengo.com/files/impulses/IMreverbs.zip", "name": "Voxengo_Reverb_IRs"},
    {"url": "http://www.echothief.com/wp-content/uploads/2016/06/EchoThiefImpulseResponseLibrary.zip",
     "name": "EchoThief_Real_Spaces"},
    {"url": "https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "name": "Kalthallen_Cabs"},
    {"url": "https://forward-audio.com/wp-content/uploads/2020/07/faIR-Post-Grunge.zip", "name": "faIR_Post_Grunge"},
    {"url": "https://forward-audio.com/wp-content/uploads/2020/04/faIR-Modern-Rock.zip", "name": "faIR_Modern_Rock"},
    {"url": "https://forward-audio.com/wp-content/uploads/2020/09/faIR-Modern-Metal.zip", "name": "faIR_Modern_Metal"},
    {"url": "https://forward-audio.com/wp-content/uploads/2021/01/faIR-Progressive-Metal.zip", "name": "faIR_Progressive_Metal"},
]

def download_direct_sources(session, cache, organizer):
    """Download from direct URL sources. Only keeps .wav and .nam."""
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

            if dl_path.suffix.lower() == ".zip":
                try:
                    extract_dir = tmp_dir / name
                    with zipfile.ZipFile(dl_path, "r") as zf:
                        zf.extractall(extract_dir)

                    file_count = 0
                    for root, dirs, files in os.walk(extract_dir):
                        dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
                        for fn in files:
                            if Path(fn).suffix.lower() not in VALID_EXTENSIONS:
                                continue
                            src = Path(root) / fn
                            if not validate_file(src):
                                continue
                            if cache.is_duplicate(src):
                                continue
                            rel = os.path.relpath(root, extract_dir)
                            context = f"{name}/{rel}/{fn}"
                            dest = organizer.organize_file(src, context, source_name=name)
                            shutil.copy2(src, dest)
                            file_count += 1
                            stats["organized"] += 1

                    logging.info(f"Organized {file_count} files from {name}")
                    shutil.rmtree(extract_dir, ignore_errors=True)
                except zipfile.BadZipFile:
                    logging.error(f"Bad ZIP file: {name}")
                    stats["errors"] += 1
            else:
                ext = dl_path.suffix.lower()
                if ext in VALID_EXTENSIONS and validate_file(dl_path) and not cache.is_duplicate(dl_path):
                    context = f"direct/{name}/{fname}"
                    dest = organizer.organize_file(dl_path, context, source_name=name)
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
# Documentation
# ---------------------------------------------------------------------------
def generate_documentation():
    """Generate README with flat structure info."""
    total_files = 0
    categories = {}

    for child in BASE_DIR.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            count = sum(1 for f in child.iterdir()
                       if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS)
            if count > 0:
                categories[child.name] = count
                total_files += count

    readme = f"""# 🎸 IR DEF Repository — The Ultimate Free IR & NAM Collection

> **{total_files:,} archivos** — Solo .wav y .nam
> Organización plana por categoría — nombres descriptivos con modelo/cab/info

---

## 📊 Contenido

| Categoría | Archivos |
|-----------|----------|
"""
    for cat, count in sorted(categories.items()):
        readme += f"| {cat} | {count:,} |\n"
    readme += f"| **TOTAL** | **{total_files:,}** |\n"

    readme += """
---

## 📂 Estructura (plana, sin subcarpetas)

```
├── IR_Guitarra/     — Todos los IRs de guitarra (wav) con nombre descriptivo
├── IR_Bajo/         — Todos los IRs de bajo (wav)
├── IR_Acustica/     — IRs para acústica/piezo (wav)
├── IR_Utilidades/   — Reverbs, rooms, mic emulations (wav)
└── NAM_Capturas/    — Todas las capturas Neural Amp Modeler (.nam)
```

### Ejemplo de nombres de archivo:
- `Marshall_JCM800_4x12_V30_SM57_Crunch.wav`
- `Fender_Twin_Reverb_2x12_Clean.wav`
- `Mesa_Boogie_Dual_Rectifier_HiGain.nam`
- `Vox_AC30_Greenback_Vintage.wav`

---

*100% contenido gratuito y legal de fuentes verificadas*
"""
    (BASE_DIR / "README.md").write_text(readme, encoding="utf-8")
    logging.info(f"README generated ({total_files:,} total files)")
    return total_files

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="IR DEF Repository Downloader v3")
    parser.add_argument("--tier", type=str, default="all",
                        choices=["github", "tone3000-amps", "tone3000-pedals", "direct", "docs", "all"],
                        help="Which tier to download")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output-dir", type=str, default="/tmp/ir_repository")
    args = parser.parse_args()

    global BASE_DIR, CACHE_FILE, STATS_FILE, LOG_FILE
    BASE_DIR = Path(args.output_dir)
    CACHE_FILE = BASE_DIR / ".download_cache.json"
    STATS_FILE = BASE_DIR / ".stats.json"
    LOG_FILE = BASE_DIR / ".download.log"

    setup_logging()
    logging.info("=" * 60)
    logging.info("IR DEF Repository v3 — ONLY .wav and .nam — FLAT structure")
    logging.info(f"Tier: {args.tier} | Output: {BASE_DIR}")
    logging.info("=" * 60)

    session = get_session()
    cache = DownloadCache()
    organizer = FlatOrganizer()

    all_stats = {}

    if args.validate_only:
        invalid = valid = 0
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in VALID_EXTENSIONS:
                    if validate_file(fp):
                        valid += 1
                    else:
                        logging.warning(f"INVALID: {fp}")
                        fp.unlink()
                        invalid += 1
        logging.info(f"Validation: {valid} valid, {invalid} invalid (deleted)")
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

    STATS_FILE.write_text(json.dumps(all_stats, indent=2), encoding="utf-8")
    logging.info("=" * 60)
    logging.info("ALL DONE!")
    logging.info(json.dumps(all_stats, indent=2))
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
