#!/usr/bin/env python3
"""
IR DEF Repository v4 — ULTRA MASSIVE Downloader
================================================
ONLY .wav and .nam | Flat folder structure | Descriptive filenames
Targets: 40+ GitHub repos, 20+ direct ZIPs, TONE3000 API
"""

import os, sys, json, re, time, hashlib, zipfile, struct, shutil, logging, argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
BASE_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/ir_repository"))
CACHE_FILE = BASE_DIR / ".download_cache.json"
STATS_FILE = BASE_DIR / ".stats.json"
LOG_FILE   = BASE_DIR / ".download.log"
TONE3000_API_KEY = os.environ.get("TONE3000_API_KEY", "")
TONE3000_BASE = "https://www.tone3000.com/api/v1"
VALID_EXT = {".wav", ".nam"}

# ---------------------------------------------------------------------------
# Brand / Cab / Mic detection
# ---------------------------------------------------------------------------
BRANDS = {
    "Marshall": [r"marshall",r"jcm",r"jvm",r"plexi",r"1959",r"1987",r"2203",r"2204",r"dsl",r"jmp",r"silver.jubilee"],
    "Fender": [r"fender",r"twin",r"deluxe.reverb",r"bassman",r"princeton",r"champ",r"vibrolux",r"super.reverb",r"hot.rod"],
    "Mesa": [r"mesa",r"boogie",r"rectifier",r"recto",r"dual.rec",r"triple.rec",r"mark.(iv|v|ii|iii)",r"lonestar",r"stiletto"],
    "Vox": [r"vox",r"ac.?30",r"ac.?15"],
    "Orange": [r"orange",r"rockerverb",r"thunderverb",r"tiny.terror",r"or\d{2,3}"],
    "Peavey": [r"peavey",r"5150",r"6505",r"invective",r"xxx",r"jsx"],
    "EVH": [r"\bevh\b",r"5150.*(iii|el34|iconic)"],
    "Bogner": [r"bogner",r"uberschall",r"ecstasy",r"shiva"],
    "Soldano": [r"soldano",r"slo.?100",r"\bslo\b"],
    "Diezel": [r"diezel",r"herbert",r"vh4",r"hagen"],
    "Friedman": [r"friedman",r"be.?100",r"dirty.shirley",r"small.box"],
    "Engl": [r"engl",r"powerball",r"fireball",r"savage",r"invader"],
    "Ampeg": [r"ampeg",r"svt",r"b-?15",r"v4b",r"portaflex"],
    "Darkglass": [r"darkglass",r"microtubes",r"b7k"],
    "Hiwatt": [r"hiwatt",r"dr.?103"],
    "Hughes_Kettner": [r"hughes.*kettner",r"triamp",r"tubemeister"],
    "Laney": [r"laney",r"ironheart"],
    "Supro": [r"supro"],
    "Revv": [r"\brevv\b",r"generator"],
    "Victory": [r"victory",r"kraken"],
    "Matchless": [r"matchless",r"chieftain"],
    "Morgan": [r"\bmorgan\b"],
    "Suhr": [r"\bsuhr\b"],
    "Celestion": [r"celestion",r"v30",r"vintage.30",r"greenback",r"creamback",r"g12",r"alnico"],
    "Eminence": [r"eminence",r"swamp.thang",r"texas.heat"],
    "Jensen": [r"jensen"],
}

CABS = {"1x12":[r"1x12"],"2x12":[r"2x12"],"4x12":[r"4x12"],"1x10":[r"1x10"],"2x10":[r"2x10"],"4x10":[r"4x10"],"1x15":[r"1x15"],"8x10":[r"8x10"]}
SPKRS = {"V30":[r"v30",r"vintage.?30"],"Greenback":[r"greenback",r"g12m"],"G12H":[r"g12h"],"G12T75":[r"g12t.?75"],"Creamback":[r"creamback"],"Alnico":[r"alnico"],"EVM12L":[r"evm"]}
MICS = {"SM57":[r"sm57",r"sm.?57"],"MD421":[r"md421",r"md.?421"],"R121":[r"r121",r"royer"],"U87":[r"u87"],"E609":[r"e609"]}

def _match(text, patterns):
    t = text.lower()
    for k, pats in patterns.items():
        for p in pats:
            if re.search(p, t): return k
    return None

# ---------------------------------------------------------------------------
def setup_logging():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)])

def get_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504]), pool_maxsize=20))
    s.mount("http://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504]), pool_maxsize=10))
    s.headers.update({"User-Agent": "IR-DEF/4.0", "Accept-Encoding": "gzip, deflate"})
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if gh_token:
        s.headers["Authorization"] = f"Bearer {gh_token}"
    return s

# ---------------------------------------------------------------------------
class Cache:
    def __init__(self):
        self.path = CACHE_FILE
        self.data = {"urls": [], "hashes": {}}
        if self.path.exists():
            try: self.data = json.loads(self.path.read_text("utf-8"))
            except: pass
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1), "utf-8")
    def seen(self, url): return url in self.data["urls"]
    def mark(self, url):
        if url not in self.data["urls"]: self.data["urls"].append(url)
    def dup(self, fp):
        h = hashlib.sha256(Path(fp).read_bytes()).hexdigest()
        if h in self.data["hashes"]: return True
        self.data["hashes"][h] = str(fp); return False

def valid_wav(p):
    try:
        with open(p,"rb") as f:
            h=f.read(12)
            if len(h)<12: return False
            r,_,w = struct.unpack("<4sI4s",h)
            return r==b"RIFF" and w==b"WAVE"
    except: return False

def valid(p):
    p=Path(p)
    if p.stat().st_size < 100: return False
    if p.suffix.lower()==".wav": return valid_wav(p)
    return p.suffix.lower()==".nam"

# ---------------------------------------------------------------------------
class Org:
    def cat(self, ctx, fn):
        c = (ctx+" "+fn).lower()
        if Path(fn).suffix.lower()==".nam": return "NAM_Capturas"
        if any(k in c for k in ["bass","bajo","svt","ampeg","darkglass","8x10","4x10","b-15","b15","portaflex"]): return "IR_Bajo"
        if any(k in c for k in ["acoustic","piezo","body_sim","taylor","martin","nylon","electroac"]): return "IR_Acustica"
        if any(k in c for k in ["reverb","room","hall","plate","spring","echo","ambient","space","convol"]): return "IR_Utilidades"
        return "IR_Guitarra"

    def name(self, ctx, fn):
        c = ctx+" "+fn
        stem = Path(fn).stem; ext = Path(fn).suffix.lower()
        parts = []
        b = _match(c, BRANDS)
        if b: parts.append(b)
        # model extraction
        for pat in [r"(JCM\s*\d+)",r"(JVM\s*\d+)",r"(DSL\s*\d+)",r"(5150\w*)",r"(6505\w*)",
                    r"(Dual\s*Rec\w*)",r"(Triple\s*Rec\w*)",r"(Rectifier)",r"(Mark\s*(?:IV|V|III|II))",
                    r"(AC\s*30)",r"(AC\s*15)",r"(SLO.?\d*)",r"(VH4)",r"(Herbert)",
                    r"(BE.?100)",r"(SVT\w*)",r"(Twin\s*Reverb)",r"(Deluxe\s*Reverb)",
                    r"(Bassman)",r"(Princeton)",r"(Plexi)",r"(Rockerverb)",r"(Uberschall)",
                    r"(Invective)",r"(Powerball)",r"(Fireball)",r"(Hot\s*Rod)"]:
            m = re.search(pat, c, re.I)
            if m: parts.append(re.sub(r'\s+','_',m.group(1).strip())); break
        cab = _match(c, CABS)
        if cab: parts.append(cab)
        sp = _match(c, SPKRS)
        if sp: parts.append(sp)
        mi = _match(c, MICS)
        if mi: parts.append(mi)
        # style
        cl = c.lower()
        if any(k in cl for k in ["high gain","metal","djent","hi gain"]): parts.append("HiGain")
        elif any(k in cl for k in ["crunch","breakup"]): parts.append("Crunch")
        elif any(k in cl for k in ["clean","pristine","jazz"]): parts.append("Clean")
        elif any(k in cl for k in ["vintage","classic"]): parts.append("Vintage")
        if not parts:
            s = re.sub(r"[\[\(]?(free|download|pack|sample|demo|www\.\S+)[\]\)]?","",stem,flags=re.I)
            s = re.sub(r"[\s\-\.]+","_",s); s = re.sub(r"_+","_",s).strip("_")
            parts.append("_".join(p.capitalize() if len(p)>2 else p.upper() for p in s.split("_") if p) or stem)
        elif len(parts)==1:
            s = re.sub(r"[\s\-\.]+","_",stem); s = re.sub(r"_+","_",s).strip("_")
            if s.lower() != parts[0].lower(): parts.append(s[:40])
        n = "_".join(parts)
        n = re.sub(r'[<>:"/\\|?*]','_',n); n = re.sub(r'_+','_',n).strip('_')
        return f"{n}{ext}"

    def dest(self, src, ctx="", src_name=""):
        fn = Path(src).name; c = ctx or str(src)
        cat = self.cat(c, fn)
        d = BASE_DIR / cat; d.mkdir(parents=True, exist_ok=True)
        nm = self.name(c, fn)
        out = d / nm
        if out.exists():
            s,x = out.stem, out.suffix; i=1
            while out.exists(): out = d / f"{s}_{i}{x}"; i+=1
        return out

# ===========================================================================
# MASSIVE SOURCE LISTS
# ===========================================================================
GITHUB_REPOS = [
    # === NAM MODELS (BIGGEST SOURCES) ===
    "pelennor2170/NAM_models",
    "GuitarML/ToneLibrary",
    "GuitarML/Proteus",
    "mikeoliphant/NeuralAmpModels",
    "sdatkinson/neural-amp-modeler",
    "carlthome/nam-models",
    # === SPEAKER CABINET IRs ===
    "orodamaral/Speaker-Cabinets-IRs",
    "keyth72/AxeFxImpulseResponses",
    # === ML AMP MODELS ===
    "GuitarML/SmartGuitarAmp",
    "GuitarML/SmartGuitarPedal",
    "GuitarML/SmartAmpPro",
    "GuitarML/GuitarLSTM",
    "GuitarML/TS-M1N3",
    "GuitarML/Chameleon",
    "Alec-Wright/Automated-GuitarAmpModelling",
    "Alec-Wright/CoreAudioML",
    # === AIDA-X ===
    "AidaDSP/AIDA-X",
    "AidaDSP/aida-x-trainer",
    # === MORE NAM/ML COLLECTIONS ===
    "bstotmeister/NAM_captures",
    "darinchau/nam-models",
    "Asashoco):@nam-community/nam-model-library",  # try
    "Jimmaphy/NAM_Models",
    "msquirogac/NeuralAmpModeler",
    # === IR COLLECTIONS ===
    "wavesfactory/free-impulse-responses",
    "ricsjs/ImpulseResponses",
    # === GUITAR RIG / TONE MODELS ===
    "GuitarML/GuitarML.github.io",
    "jatinchowdhury18/RTNeural",
]

# Repos that definitely have release assets with model/IR files
RELEASE_REPOS = [
    ("GuitarML", "Proteus"),
    ("GuitarML", "TS-M1N3"),
    ("GuitarML", "SmartGuitarAmp"),
    ("GuitarML", "SmartGuitarPedal"),
    ("GuitarML", "Chameleon"),
    ("GuitarML", "SmartAmpPro"),
    ("mikeoliphant", "NeuralAmpModels"),
    ("AidaDSP", "AIDA-X"),
    ("sdatkinson", "NeuralAmpModelerPlugin"),
]

DIRECT_ZIPS = [
    # VERIFIED WORKING
    ("https://www.voxengo.com/files/impulses/IMreverbs.zip", "Voxengo_Reverb"),
    ("http://www.echothief.com/wp-content/uploads/2016/06/EchoThiefImpulseResponseLibrary.zip", "EchoThief_Spaces"),
    ("https://kalthallen.audiounits.com/dl/KalthallenCabs.zip", "Kalthallen_Cabs"),
    # Forward Audio faIR series
    ("https://forward-audio.com/wp-content/uploads/2020/07/faIR-Post-Grunge.zip", "faIR_PostGrunge"),
    ("https://forward-audio.com/wp-content/uploads/2020/04/faIR-Modern-Rock.zip", "faIR_ModernRock"),
    ("https://forward-audio.com/wp-content/uploads/2020/09/faIR-Modern-Metal.zip", "faIR_ModernMetal"),
    ("https://forward-audio.com/wp-content/uploads/2021/01/faIR-Progressive-Metal.zip", "faIR_ProgMetal"),
    ("https://forward-audio.com/wp-content/uploads/2020/03/faIR-Classic-Rock.zip", "faIR_ClassicRock"),
    ("https://forward-audio.com/wp-content/uploads/2020/11/faIR-90s-Grunge.zip", "faIR_90sGrunge"),
    ("https://forward-audio.com/wp-content/uploads/2020/06/faIR-Modern-Pop.zip", "faIR_ModernPop"),
    ("https://forward-audio.com/wp-content/uploads/2021/03/faIR-Bass-Rock.zip", "faIR_BassRock"),
    ("https://forward-audio.com/wp-content/uploads/2021/06/faIR-Pop-Punk.zip", "faIR_PopPunk"),
    ("https://forward-audio.com/wp-content/uploads/2020/02/faIR-Blues.zip", "faIR_Blues"),
    ("https://forward-audio.com/wp-content/uploads/2021/09/faIR-Country.zip", "faIR_Country"),
    # Wilkinson God's cab (try multiple paths)
    ("https://wilkinsonaudio.com/wp-content/uploads/gods-cab-free.zip", "Gods_Cab"),
    ("https://wilkinsonaudio.com/downloads/gods-cab.zip", "Gods_Cab_v2"),
    # ML Sound Lab
    ("https://ml-sound-lab.com/wp-content/uploads/Best-IR-In-The-World.zip", "MLSL_BestIR"),
    # More reverb/room IRs
    ("https://www.voxengo.com/files/impulses/IMreverbs2.zip", "Voxengo_Reverb2"),
    # Djammin Cabs
    ("https://djammincabs.com/wp-content/uploads/free-guitar-cabs-100.zip", "Djammin_Guitar100"),
    ("https://djammincabs.com/wp-content/uploads/free-bass-cabs-100.zip", "Djammin_Bass100"),
    # Shift Line bass IRs
    ("https://shift-line.com/downloads/ShiftLine_CID_IRs.zip", "ShiftLine_Bass"),
    # SNB IRs
    ("https://www.signalnoisebliss.com/downloads/SNB-Free-Guitar-IRs.zip", "SNB_Guitar"),
    # GuitarHack
    ("https://www.guitarhack.com/downloads/GuitarHack-Impulses.zip", "GuitarHack"),
    # Science Amp bass
    ("https://scienceamps.com/downloads/science-bass-cab-irs.zip", "Science_BassCab"),
    # PreSonus analog cab IRs
    ("https://pae-web.presonusmusic.com/downloads/products/misc/PreSonus-AnalogCab-IRs.zip", "PreSonus_Analog25"),
]

# ===========================================================================
# DOWNLOADERS
# ===========================================================================
def dl_github(session, cache, org):
    stats = {"ok":0,"skip":0,"err":0,"files":0}
    tmp = Path("/tmp/gh")
    for repo in GITHUB_REPOS:
        # Clean repo name
        repo = repo.strip()
        if not "/" in repo or repo.startswith("#"): continue
        # Remove any bad chars
        repo = re.sub(r'[^a-zA-Z0-9/_\-\.]', '', repo)
        parts = repo.split("/")
        if len(parts) != 2: continue
        owner, name = parts
        
        for branch in ["main", "master"]:
            zurl = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
            if cache.seen(f"ghrepo_{owner}_{name}"): 
                stats["skip"]+=1; break
            zp = tmp / f"{name}.zip"; zp.parent.mkdir(parents=True, exist_ok=True)
            try:
                r = session.get(zurl, stream=True, timeout=300)
                if r.status_code == 404: continue
                r.raise_for_status()
                with open(zp,"wb") as f:
                    for ch in r.iter_content(1024*1024): f.write(ch)
                logging.info(f"Downloaded {owner}/{name} ({zp.stat().st_size/1e6:.1f}MB)")
                stats["ok"]+=1
                # extract
                ed = tmp / name
                try:
                    with zipfile.ZipFile(zp) as zf: zf.extractall(ed)
                except zipfile.BadZipFile:
                    logging.warning(f"Bad ZIP: {name}"); stats["err"]+=1; break
                fc=0
                for root,dirs,files in os.walk(ed):
                    dirs[:] = [d for d in dirs if not d.startswith((".",  "__"))]
                    for fn in files:
                        if Path(fn).suffix.lower() not in VALID_EXT: continue
                        src = Path(root)/fn
                        if not valid(src) or cache.dup(src): continue
                        ctx = f"{name}/{os.path.relpath(root,ed)}/{fn}"
                        d = org.dest(src, ctx, name)
                        shutil.copy2(src, d); fc+=1; stats["files"]+=1
                logging.info(f"  → {fc} files from {name}")
                cache.mark(f"ghrepo_{owner}_{name}"); cache.save()
                shutil.rmtree(ed, ignore_errors=True); zp.unlink(missing_ok=True)
                break  # got it from this branch
            except Exception as e:
                if branch == "master":
                    logging.warning(f"Skip {owner}/{name}: {e}"); stats["err"]+=1
    return stats

def dl_releases(session, cache, org):
    stats = {"ok":0,"skip":0,"err":0,"files":0}
    for owner, repo in RELEASE_REPOS:
        rk = f"rel_{owner}_{repo}"
        if cache.seen(rk): stats["skip"]+=1; continue
        try:
            r = session.get(f"https://api.github.com/repos/{owner}/{repo}/releases",
                          timeout=30, headers={"Accept":"application/vnd.github+json"})
            if r.status_code in (404,403): continue
            r.raise_for_status()
            fc=0
            for rel in r.json()[:10]:
                for a in rel.get("assets",[]):
                    aurl = a["browser_download_url"]; an = a["name"]
                    ext = Path(an).suffix.lower()
                    if ext not in VALID_EXT and ext != ".zip": continue
                    if cache.seen(aurl): continue
                    try:
                        dr = session.get(aurl, stream=True, timeout=300); dr.raise_for_status()
                        tp = Path("/tmp/ghrel")/an; tp.parent.mkdir(parents=True, exist_ok=True)
                        with open(tp,"wb") as f:
                            for ch in dr.iter_content(1024*1024): f.write(ch)
                        if ext == ".zip":
                            try:
                                xd = tp.parent/tp.stem
                                with zipfile.ZipFile(tp) as zf: zf.extractall(xd)
                                for rt,ds,fs in os.walk(xd):
                                    ds[:] = [d for d in ds if not d.startswith((".",  "__"))]
                                    for fn in fs:
                                        if Path(fn).suffix.lower() not in VALID_EXT: continue
                                        src = Path(rt)/fn
                                        if not valid(src) or cache.dup(src): continue
                                        d = org.dest(src, f"rel/{repo}/{fn}", repo)
                                        shutil.copy2(src,d); fc+=1; stats["files"]+=1
                                shutil.rmtree(xd, ignore_errors=True)
                            except: pass
                        elif valid(tp) and not cache.dup(tp):
                            d = org.dest(tp, f"rel/{repo}/{an}", repo)
                            shutil.copy2(tp,d); fc+=1; stats["files"]+=1
                        tp.unlink(missing_ok=True); cache.mark(aurl); stats["ok"]+=1
                    except: stats["err"]+=1
            logging.info(f"Releases {owner}/{repo}: {fc} files")
            cache.mark(rk); cache.save()
        except Exception as e:
            logging.warning(f"Releases {owner}/{repo}: {e}"); stats["err"]+=1
    return stats

def dl_tone3000(session, cache, org, gears=None, max_pages=500):
    stats = {"ok":0,"skip":0,"err":0,"files":0}
    if not TONE3000_API_KEY:
        logging.warning("No TONE3000_API_KEY"); return stats
    hdrs = {"Authorization": f"Bearer {TONE3000_API_KEY}", "Content-Type": "application/json"}
    gears = gears or ["amp","pedal","full-rig","ir","outboard"]
    cerr = 0
    for gear in gears:
        logging.info(f"TONE3000 gear={gear}")
        pg = 1; tp = 1
        while pg <= min(tp, max_pages):
            if cerr >= 15: logging.error(f"Too many errors, stopping {gear}"); cerr=0; break
            try:
                url = f"{TONE3000_BASE}/tones/search?gear={gear}&page={pg}&page_size=25&sort=most-downloaded"
                r = session.get(url, headers=hdrs, timeout=60)
                if r.status_code == 429:
                    time.sleep(int(r.headers.get("Retry-After",60))); continue
                if r.status_code in (401,403):
                    logging.error("TONE3000 auth failed"); return stats
                if r.status_code >= 400: cerr+=1; pg+=1; continue
                data = r.json(); tp = data.get("total_pages",1)
                tones = data.get("data",[])
                if not tones: break
                logging.info(f"  pg {pg}/{tp} — {len(tones)} tones")
                cerr = 0
                for tone in tones:
                    tid = tone.get("id"); title = tone.get("title", f"t{tid}")
                    try:
                        mr = session.get(f"{TONE3000_BASE}/models?tone_id={tid}&page=1&page_size=100",
                                        headers=hdrs, timeout=60)
                        if mr.status_code == 429: time.sleep(30); mr = session.get(f"{TONE3000_BASE}/models?tone_id={tid}&page=1&page_size=100", headers=hdrs, timeout=60)
                        if mr.status_code >= 400: continue
                        for mdl in mr.json().get("data",[]):
                            mu = mdl.get("model_url",""); mn = mdl.get("name","")
                            if not mu or cache.seen(mu): stats["skip"]+=1; continue
                            try:
                                dr = session.get(mu, headers=hdrs, timeout=120); dr.raise_for_status()
                                ext = Path(urlparse(mu).path).suffix.lower()
                                if ext not in VALID_EXT:
                                    ct = dr.headers.get("Content-Type","")
                                    ext = ".wav" if "wav" in ct else ".nam"
                                if ext not in VALID_EXT: cache.mark(mu); continue
                                ct = re.sub(r'[<>:"/\\|?*]','_',title)
                                fname = f"{ct}_{mn}{ext}" if mn and mn!=title else f"{ct}{ext}"
                                tp2 = Path("/tmp/t3k")/fname; tp2.parent.mkdir(parents=True, exist_ok=True)
                                tp2.write_bytes(dr.content)
                                if valid(tp2) and not cache.dup(tp2):
                                    d = org.dest(tp2, f"tone3000/{gear}/{title}/{fname}", "TONE3000")
                                    shutil.move(str(tp2), d); stats["files"]+=1; stats["ok"]+=1
                                else:
                                    tp2.unlink(missing_ok=True); stats["skip"]+=1
                                cache.mark(mu)
                            except: stats["err"]+=1
                        if stats["ok"] % 50 == 0 and stats["ok"]>0: cache.save()
                    except: stats["err"]+=1
                pg+=1; time.sleep(0.3)
            except Exception as e:
                logging.error(f"T3K pg {pg}: {e}"); cerr+=1; pg+=1; time.sleep(3)
    cache.save()
    return stats

def dl_direct(session, cache, org):
    stats = {"ok":0,"skip":0,"err":0,"files":0}
    tmp = Path("/tmp/direct")
    tmp.mkdir(parents=True, exist_ok=True)
    for url, name in DIRECT_ZIPS:
        if cache.seen(url): stats["skip"]+=1; continue
        logging.info(f"Direct: {name}...")
        try:
            r = session.get(url, stream=True, timeout=300, allow_redirects=True)
            if r.status_code in (404,403,410):
                logging.warning(f"  Not available ({r.status_code})"); stats["err"]+=1
                cache.mark(url); cache.save(); continue
            r.raise_for_status()
            cd = r.headers.get("Content-Disposition","")
            fn = re.findall(r'filename="?([^";\n]+)',cd)[0] if "filename=" in cd else unquote(urlparse(url).path.split("/")[-1])
            dp = tmp/fn
            with open(dp,"wb") as f:
                for ch in r.iter_content(1024*1024): f.write(ch)
            logging.info(f"  {dp.stat().st_size/1e6:.1f}MB")
            stats["ok"]+=1
            if dp.suffix.lower()==".zip":
                try:
                    xd = tmp/name
                    with zipfile.ZipFile(dp) as zf: zf.extractall(xd)
                    fc=0
                    for rt,ds,fs in os.walk(xd):
                        ds[:] = [d for d in ds if not d.startswith((".",  "__"))]
                        for f2 in fs:
                            if Path(f2).suffix.lower() not in VALID_EXT: continue
                            src = Path(rt)/f2
                            if not valid(src) or cache.dup(src): continue
                            ctx = f"{name}/{os.path.relpath(rt,xd)}/{f2}"
                            d = org.dest(src, ctx, name)
                            shutil.copy2(src, d); fc+=1; stats["files"]+=1
                    logging.info(f"  → {fc} files from {name}")
                    shutil.rmtree(xd, ignore_errors=True)
                except zipfile.BadZipFile:
                    logging.error(f"  Bad ZIP: {name}"); stats["err"]+=1
            else:
                if dp.suffix.lower() in VALID_EXT and valid(dp) and not cache.dup(dp):
                    d = org.dest(dp, f"direct/{name}/{fn}", name)
                    shutil.copy2(dp, d); stats["files"]+=1
            dp.unlink(missing_ok=True); cache.mark(url); cache.save()
        except Exception as e:
            logging.error(f"  Error {name}: {e}"); stats["err"]+=1
    return stats

# ---------------------------------------------------------------------------
def gen_docs():
    total=0; cats={}
    for ch in BASE_DIR.iterdir():
        if ch.is_dir() and not ch.name.startswith("."):
            c = sum(1 for f in ch.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXT)
            if c>0: cats[ch.name]=c; total+=c
    md = f"# 🎸 IR DEF Repository\n\n> **{total:,}** archivos (.wav + .nam)\n\n"
    md += "| Categoría | Archivos |\n|---|---|\n"
    for k,v in sorted(cats.items()): md += f"| {k} | {v:,} |\n"
    md += f"| **TOTAL** | **{total:,}** |\n"
    (BASE_DIR/"README.md").write_text(md, "utf-8")
    logging.info(f"Docs: {total:,} files"); return total

# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tier", default="all", choices=["github","tone3000-amps","tone3000-pedals","direct","docs","all"])
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--output-dir", default="/tmp/ir_repository")
    a = p.parse_args()

    global BASE_DIR, CACHE_FILE, STATS_FILE, LOG_FILE
    BASE_DIR = Path(a.output_dir); CACHE_FILE = BASE_DIR/".download_cache.json"
    STATS_FILE = BASE_DIR/".stats.json"; LOG_FILE = BASE_DIR/".download.log"
    setup_logging()
    logging.info("="*60)
    logging.info(f"IR DEF v4 ULTRA | tier={a.tier} | out={BASE_DIR}")
    logging.info("="*60)

    s = get_session(); c = Cache(); o = Org(); st = {}

    if a.validate_only:
        v=inv=0
        for rt,ds,fs in os.walk(BASE_DIR):
            ds[:] = [d for d in ds if not d.startswith(".")]
            for f in fs:
                fp = Path(rt)/f
                if fp.suffix.lower() in VALID_EXT:
                    if valid(fp): v+=1
                    else: fp.unlink(); inv+=1
        logging.info(f"Valid={v} Invalid={inv}(deleted)"); return

    if a.tier in ("github","all"):
        logging.info(">>> GITHUB REPOS")
        st["gh"] = dl_github(s,c,o)
        logging.info(f"GitHub: {st['gh']}")
        logging.info(">>> GITHUB RELEASES")
        st["rel"] = dl_releases(s,c,o)
        logging.info(f"Releases: {st['rel']}")

    if a.tier in ("tone3000-amps","all"):
        logging.info(">>> TONE3000 AMPS")
        st["t3k_amp"] = dl_tone3000(s,c,o, gears=["amp","ir"])
        logging.info(f"T3K amps: {st['t3k_amp']}")

    if a.tier in ("tone3000-pedals","all"):
        logging.info(">>> TONE3000 PEDALS")
        st["t3k_ped"] = dl_tone3000(s,c,o, gears=["pedal","full-rig","outboard"])
        logging.info(f"T3K pedals: {st['t3k_ped']}")

    if a.tier in ("direct","all"):
        logging.info(">>> DIRECT SITES")
        st["direct"] = dl_direct(s,c,o)
        logging.info(f"Direct: {st['direct']}")

    if a.tier in ("docs","all"):
        st["docs"] = {"total": gen_docs()}

    STATS_FILE.write_text(json.dumps(st,indent=2),"utf-8")
    logging.info("="*60)
    logging.info("DONE! " + json.dumps(st))
    logging.info("="*60)

if __name__ == "__main__":
    main()
