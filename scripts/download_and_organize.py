#!/usr/bin/env python3
"""
IR DEF v5 — ULTRA MASSIVE — .wav + .nam only — Flat folders
============================================================
Sources: GitHub repos, Soundwoofer API (1200+ free IRs), Direct ZIPs,
ToneHunt/TONE3000 scraper (no API key needed)
"""
import os,sys,json,re,time,hashlib,zipfile,struct,shutil,logging,argparse
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(os.environ.get("OUTPUT_DIR","/tmp/ir_repository"))
CACHE_FILE = BASE_DIR/".download_cache.json"
LOG_FILE = BASE_DIR/".download.log"
VALID_EXT = {".wav",".nam"}

# -- Brand detection --
BRANDS = {
    "Marshall":[r"marshall",r"jcm",r"jvm",r"plexi",r"1959",r"1987",r"2203",r"2204",r"dsl",r"jmp"],
    "Fender":[r"fender",r"twin",r"deluxe.reverb",r"bassman",r"princeton",r"champ",r"vibrolux"],
    "Mesa":[r"mesa",r"boogie",r"rectifier",r"recto",r"dual.rec",r"triple.rec",r"mark.(iv|v|ii|iii)",r"lonestar"],
    "Vox":[r"vox",r"ac.?30",r"ac.?15"],
    "Orange":[r"orange",r"rockerverb",r"thunderverb",r"tiny.terror"],
    "Peavey":[r"peavey",r"5150",r"6505",r"invective"],
    "EVH":[r"\bevh\b"],
    "Bogner":[r"bogner",r"uberschall",r"ecstasy",r"shiva"],
    "Soldano":[r"soldano",r"slo"],
    "Diezel":[r"diezel",r"herbert",r"vh4"],
    "Friedman":[r"friedman",r"be.?100",r"dirty.shirley"],
    "Engl":[r"engl",r"powerball",r"fireball",r"savage"],
    "Ampeg":[r"ampeg",r"svt",r"b-?15",r"portaflex"],
    "Darkglass":[r"darkglass",r"b7k"],
    "Hiwatt":[r"hiwatt"],
    "Suhr":[r"\bsuhr\b"],
    "Hughes_Kettner":[r"hughes.*kettner",r"triamp",r"tubemeister"],
    "Laney":[r"laney",r"ironheart"],
    "Revv":[r"\brevv\b",r"generator"],
    "Victory":[r"victory",r"kraken"],
    "Celestion":[r"celestion",r"v30",r"vintage.30",r"greenback",r"creamback",r"g12",r"alnico"],
    "Eminence":[r"eminence",r"swamp.thang"],
    "Jensen":[r"jensen"],
}
CABS={"1x12":[r"1x12"],"2x12":[r"2x12"],"4x12":[r"4x12"],"4x10":[r"4x10"],"8x10":[r"8x10"],"1x15":[r"1x15"]}
MICS={"SM57":[r"sm57"],"MD421":[r"md421"],"R121":[r"r121",r"royer"],"U87":[r"u87"],"E609":[r"e609"]}
def _m(t,p):
    t=t.lower()
    for k,ps in p.items():
        for pa in ps:
            if re.search(pa,t): return k
    return None

# -- Logging & Session --
def setup():
    BASE_DIR.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE,encoding="utf-8"),logging.StreamHandler(sys.stdout)])

def sess():
    s=requests.Session()
    s.mount("https://",HTTPAdapter(max_retries=Retry(total=3,backoff_factor=1,status_forcelist=[429,500,502,503,504]),pool_maxsize=20))
    s.mount("http://",HTTPAdapter(max_retries=Retry(total=2,backoff_factor=1,status_forcelist=[500,502,503]),pool_maxsize=10))
    s.headers.update({"User-Agent":"IR-DEF/5.0","Accept-Encoding":"gzip, deflate"})
    t=os.environ.get("GITHUB_TOKEN","")
    if t: s.headers["Authorization"]=f"Bearer {t}"
    return s

# -- Cache --
class C:
    def __init__(self):
        self.p=CACHE_FILE; self.d={"u":[],"h":{}}
        if self.p.exists():
            try: self.d=json.loads(self.p.read_text("utf-8"))
            except: pass
    def save(self): self.p.parent.mkdir(parents=True,exist_ok=True); self.p.write_text(json.dumps(self.d),"utf-8")
    def seen(self,u): return u in self.d["u"]
    def mark(self,u):
        if u not in self.d["u"]: self.d["u"].append(u)
    def dup(self,f):
        h=hashlib.sha256(Path(f).read_bytes()).hexdigest()
        if h in self.d["h"]: return True
        self.d["h"][h]=str(f); return False

# -- Validation --
def vwav(p):
    try:
        with open(p,"rb") as f:
            h=f.read(12)
            if len(h)<12: return False
            r,_,w=struct.unpack("<4sI4s",h)
            return r==b"RIFF" and w==b"WAVE"
    except: return False

def valid(p):
    p=Path(p)
    if p.stat().st_size<100: return False
    return vwav(p) if p.suffix.lower()==".wav" else p.suffix.lower()==".nam"

# -- Organizer --
class O:
    def cat(self,ctx,fn):
        c=(ctx+" "+fn).lower(); e=Path(fn).suffix.lower()
        if e==".nam": return "NAM_Capturas"
        if any(k in c for k in ["bass","bajo","svt","ampeg","darkglass","8x10","4x10","b-15","b15","portaflex"]): return "IR_Bajo"
        if any(k in c for k in ["acoustic","piezo","electroac","taylor","martin","nylon","body"]): return "IR_Acustica"
        if any(k in c for k in ["reverb","room","hall","plate","spring","echo","ambient","space","convol"]): return "IR_Utilidades"
        return "IR_Guitarra"

    def name(self,ctx,fn):
        c=ctx+" "+fn; st=Path(fn).stem; ex=Path(fn).suffix.lower(); p=[]
        b=_m(c,BRANDS)
        if b: p.append(b)
        for pat in [r"(JCM\s*\d+)",r"(JVM\s*\d+)",r"(DSL\s*\d+)",r"(5150\w*)",r"(6505\w*)",
                    r"(Dual\s*Rec\w*)",r"(Rectifier)",r"(Mark\s*(?:IV|V|III|II))",
                    r"(AC\s*30)",r"(AC\s*15)",r"(SLO.?\d*)",r"(VH4)",r"(SVT\w*)",
                    r"(Twin\s*Reverb)",r"(Deluxe\s*Reverb)",r"(Bassman)",r"(Princeton)",r"(Plexi)"]:
            m=re.search(pat,c,re.I)
            if m: p.append(re.sub(r'\s+','_',m.group(1).strip())); break
        cb=_m(c,CABS)
        if cb: p.append(cb)
        mi=_m(c,MICS)
        if mi: p.append(mi)
        cl=c.lower()
        if any(k in cl for k in ["high gain","metal","djent","hi gain"]): p.append("HiGain")
        elif any(k in cl for k in ["crunch","breakup"]): p.append("Crunch")
        elif any(k in cl for k in ["clean","pristine","jazz"]): p.append("Clean")
        if not p:
            s=re.sub(r"[\s\-\.]+","_",st); s=re.sub(r"_+","_",s).strip("_")
            p.append(s[:60] or st)
        elif len(p)==1:
            s=re.sub(r"[\s\-\.]+","_",st); s=re.sub(r"_+","_",s).strip("_")
            if s.lower()!=p[0].lower(): p.append(s[:40])
        n="_".join(p); n=re.sub(r'[<>:"/\\|?*]','_',n); n=re.sub(r'_+','_',n).strip('_')
        return f"{n}{ex}"

    def dest(self,src,ctx=""):
        fn=Path(src).name; ca=self.cat(ctx or str(src),fn)
        d=BASE_DIR/ca; d.mkdir(parents=True,exist_ok=True)
        nm=self.name(ctx or str(src),fn); out=d/nm
        if out.exists():
            s,x=out.stem,out.suffix; i=1
            while out.exists(): out=d/f"{s}_{i}{x}"; i+=1
        return out

# ===========================================================================
# SOURCE 1: GitHub repos (biggest bang for buck)
# ===========================================================================
REPOS=[
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
    "DA1729/da1729_guitar_processor",
    "dijitol77/delt1",
    "dijitol77/delt",
    "turtelduo/helix",
]

def dl_github(s,c,o):
    st={"ok":0,"skip":0,"err":0,"files":0}
    tmp=Path("/tmp/gh")
    for repo in REPOS:
        repo=repo.strip()
        if "/" not in repo: continue
        owner,name=repo.split("/",1)
        ck=f"gh_{owner}_{name}"
        if c.seen(ck): st["skip"]+=1; continue
        for br in ["main","master"]:
            zu=f"https://github.com/{owner}/{name}/archive/refs/heads/{br}.zip"
            zp=tmp/f"{name}.zip"; zp.parent.mkdir(parents=True,exist_ok=True)
            try:
                r=s.get(zu,stream=True,timeout=300)
                if r.status_code==404: continue
                r.raise_for_status()
                with open(zp,"wb") as f:
                    for ch in r.iter_content(1024*1024): f.write(ch)
                logging.info(f"DL {owner}/{name} ({zp.stat().st_size/1e6:.1f}MB)")
                st["ok"]+=1
                ed=tmp/name
                try:
                    with zipfile.ZipFile(zp) as zf: zf.extractall(ed)
                except: logging.warning(f"Bad ZIP {name}"); st["err"]+=1; break
                fc=0
                for rt,ds,fs in os.walk(ed):
                    ds[:]=[d for d in ds if not d.startswith((".",  "__"))]
                    for fn in fs:
                        if Path(fn).suffix.lower() not in VALID_EXT: continue
                        src=Path(rt)/fn
                        if not valid(src) or c.dup(src): continue
                        d=o.dest(src,f"{name}/{os.path.relpath(rt,ed)}/{fn}")
                        shutil.copy2(src,d); fc+=1; st["files"]+=1
                logging.info(f"  → {fc} files from {name}")
                c.mark(ck); c.save()
                shutil.rmtree(ed,ignore_errors=True); zp.unlink(missing_ok=True)
                break
            except Exception as e:
                if br=="master": logging.warning(f"Skip {repo}: {e}"); st["err"]+=1
    return st

def dl_releases(s,c,o):
    st={"ok":0,"skip":0,"err":0,"files":0}
    rels=[("GuitarML","Proteus"),("GuitarML","TS-M1N3"),("GuitarML","Chameleon"),
          ("GuitarML","SmartGuitarAmp"),("mikeoliphant","NeuralAmpModels"),("AidaDSP","AIDA-X")]
    for ow,rp in rels:
        rk=f"rel_{ow}_{rp}"
        if c.seen(rk): st["skip"]+=1; continue
        try:
            r=s.get(f"https://api.github.com/repos/{ow}/{rp}/releases",timeout=30,
                    headers={"Accept":"application/vnd.github+json"})
            if r.status_code in (404,403): continue
            r.raise_for_status(); fc=0
            for rel in r.json()[:10]:
                for a in rel.get("assets",[]):
                    au=a["browser_download_url"]; an=a["name"]; ex=Path(an).suffix.lower()
                    if ex not in VALID_EXT and ex!=".zip": continue
                    if c.seen(au): continue
                    try:
                        dr=s.get(au,stream=True,timeout=300); dr.raise_for_status()
                        tp=Path("/tmp/ghrel")/an; tp.parent.mkdir(parents=True,exist_ok=True)
                        with open(tp,"wb") as f:
                            for ch in dr.iter_content(1024*1024): f.write(ch)
                        if ex==".zip":
                            try:
                                xd=tp.parent/tp.stem
                                with zipfile.ZipFile(tp) as zf: zf.extractall(xd)
                                for rt2,ds2,fs2 in os.walk(xd):
                                    ds2[:]=[d for d in ds2 if not d.startswith((".",  "__"))]
                                    for fn in fs2:
                                        if Path(fn).suffix.lower() not in VALID_EXT: continue
                                        src=Path(rt2)/fn
                                        if not valid(src) or c.dup(src): continue
                                        d=o.dest(src,f"rel/{rp}/{fn}")
                                        shutil.copy2(src,d); fc+=1; st["files"]+=1
                                shutil.rmtree(xd,ignore_errors=True)
                            except: pass
                        elif valid(tp) and not c.dup(tp):
                            d=o.dest(tp,f"rel/{rp}/{an}"); shutil.copy2(tp,d); fc+=1; st["files"]+=1
                        tp.unlink(missing_ok=True); c.mark(au); st["ok"]+=1
                    except: st["err"]+=1
            logging.info(f"Releases {ow}/{rp}: {fc}"); c.mark(rk); c.save()
        except Exception as e: logging.warning(f"Rel {ow}/{rp}: {e}"); st["err"]+=1
    return st

# ===========================================================================
# SOURCE 2: Soundwoofer.com API — FREE, NO KEY, 1200+ guitar cab IRs
# ===========================================================================
def dl_soundwoofer(s,c,o):
    """Soundwoofer has a public JSON API with direct .wav download links."""
    st={"ok":0,"skip":0,"err":0,"files":0}
    base="https://soundwoofer.com"
    api_url=f"{base}/api/impulses"
    
    logging.info("=== SOUNDWOOFER: Fetching impulse list ===")
    
    # Try paginated API
    page = 0
    total_fetched = 0
    
    while True:
        try:
            # Try different API endpoints
            for endpoint in [
                f"{base}/api/impulses?page={page}&limit=100",
                f"{base}/api/v1/impulses?page={page}&limit=100",
                f"{base}/api/impulses?offset={page*100}&limit=100",
            ]:
                try:
                    r = s.get(endpoint, timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        # Handle different response formats
                        items = data if isinstance(data, list) else data.get("data", data.get("impulses", data.get("items", [])))
                        if items:
                            logging.info(f"Soundwoofer page {page}: {len(items)} items")
                            for item in items:
                                # Extract download URL
                                dl_url = item.get("downloadUrl") or item.get("download_url") or item.get("url") or item.get("file")
                                if not dl_url:
                                    # Try to build URL from ID
                                    iid = item.get("id") or item.get("_id")
                                    if iid:
                                        dl_url = f"{base}/api/impulses/{iid}/download"
                                
                                if not dl_url: continue
                                if not dl_url.startswith("http"): dl_url = base + dl_url
                                if c.seen(dl_url): st["skip"]+=1; continue
                                
                                # Get metadata for naming
                                spk = item.get("speaker","") or item.get("speakerModel","") or ""
                                cab = item.get("cabinet","") or item.get("cabinetModel","") or ""
                                mic = item.get("microphone","") or item.get("mic","") or ""
                                title = item.get("title","") or item.get("name","") or f"SW_{iid}"
                                
                                try:
                                    dr = s.get(dl_url, timeout=60)
                                    if dr.status_code != 200: 
                                        c.mark(dl_url); continue
                                    
                                    # Build descriptive filename
                                    parts = [p for p in [cab, spk, mic, title] if p]
                                    fname = "_".join(parts)[:80] + ".wav"
                                    fname = re.sub(r'[<>:"/\\|?*]','_',fname)
                                    
                                    tp = Path("/tmp/sw")/fname
                                    tp.parent.mkdir(parents=True,exist_ok=True)
                                    tp.write_bytes(dr.content)
                                    
                                    if valid(tp) and not c.dup(tp):
                                        ctx = f"soundwoofer/{cab}/{spk}/{mic}/{title}"
                                        d = o.dest(tp, ctx)
                                        shutil.move(str(tp), d)
                                        st["files"]+=1; st["ok"]+=1
                                        total_fetched += 1
                                    else:
                                        tp.unlink(missing_ok=True); st["skip"]+=1
                                    
                                    c.mark(dl_url)
                                    if st["ok"] % 100 == 0 and st["ok"]>0:
                                        c.save()
                                        logging.info(f"  Soundwoofer progress: {st['ok']} downloaded")
                                except Exception as e:
                                    st["err"]+=1
                                    c.mark(dl_url)  # Don't retry failed ones
                            
                            if len(items) < 100:
                                # Last page
                                page = -1
                            break  # This endpoint worked
                        else:
                            page = -1  # No more items
                            break
                    elif r.status_code == 404:
                        continue  # Try next endpoint format
                    else:
                        continue
                except Exception:
                    continue
            
            if page == -1:
                break
            page += 1
            time.sleep(0.5)
            
            # Safety limit
            if page > 50:
                break
                
        except Exception as e:
            logging.error(f"Soundwoofer error page {page}: {e}")
            break
    
    # Also try the standalone impulses page
    try:
        for endpoint in [f"{base}/api/standalone-impulses", f"{base}/api/mispulses"]:
            try:
                r = s.get(endpoint, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get("data", [])
                    logging.info(f"Soundwoofer standalone: {len(items)} items")
                    for item in items:
                        dl_url = item.get("downloadUrl") or item.get("download_url") or item.get("url")
                        if not dl_url: continue
                        if not dl_url.startswith("http"): dl_url = base + dl_url
                        if c.seen(dl_url): continue
                        try:
                            dr = s.get(dl_url, timeout=60)
                            if dr.status_code != 200: c.mark(dl_url); continue
                            title = item.get("title","") or item.get("name","SW_standalone")
                            fname = re.sub(r'[<>:"/\\|?*]','_',title)[:60] + ".wav"
                            tp = Path("/tmp/sw")/fname; tp.parent.mkdir(parents=True,exist_ok=True)
                            tp.write_bytes(dr.content)
                            if valid(tp) and not c.dup(tp):
                                d = o.dest(tp, f"soundwoofer/standalone/{title}")
                                shutil.move(str(tp), d); st["files"]+=1; st["ok"]+=1
                            else: tp.unlink(missing_ok=True)
                            c.mark(dl_url)
                        except: st["err"]+=1
            except: pass
    except: pass
    
    c.save()
    logging.info(f"Soundwoofer total: {st}")
    return st

# ===========================================================================
# SOURCE 3: Direct ZIP downloads (VERIFIED WORKING)
# ===========================================================================
ZIPS=[
    ("https://www.voxengo.com/files/impulses/IMreverbs.zip","Voxengo_Reverb"),
    ("https://kalthallen.audiounits.com/dl/KalthallenCabs.zip","Kalthallen_Cabs"),
]

def dl_direct(s,c,o):
    st={"ok":0,"skip":0,"err":0,"files":0}
    tmp=Path("/tmp/direct"); tmp.mkdir(parents=True,exist_ok=True)
    for url,name in ZIPS:
        if c.seen(url): st["skip"]+=1; continue
        logging.info(f"Direct: {name}...")
        try:
            r=s.get(url,stream=True,timeout=300,allow_redirects=True)
            if r.status_code in (404,403,410):
                logging.warning(f"  {r.status_code}: {name}"); c.mark(url); continue
            r.raise_for_status()
            cd=r.headers.get("Content-Disposition","")
            fn=re.findall(r'filename="?([^";\n]+)',cd)[0] if "filename=" in cd else unquote(urlparse(url).path.split("/")[-1])
            dp=tmp/fn
            with open(dp,"wb") as f:
                for ch in r.iter_content(1024*1024): f.write(ch)
            logging.info(f"  {dp.stat().st_size/1e6:.1f}MB")
            st["ok"]+=1
            if dp.suffix.lower()==".zip":
                try:
                    xd=tmp/name
                    with zipfile.ZipFile(dp) as zf: zf.extractall(xd)
                    fc=0
                    for rt,ds,fs in os.walk(xd):
                        ds[:]=[d for d in ds if not d.startswith((".",  "__"))]
                        for f2 in fs:
                            if Path(f2).suffix.lower() not in VALID_EXT: continue
                            src=Path(rt)/f2
                            if not valid(src) or c.dup(src): continue
                            d=o.dest(src,f"{name}/{os.path.relpath(rt,xd)}/{f2}")
                            shutil.copy2(src,d); fc+=1; st["files"]+=1
                    logging.info(f"  → {fc} from {name}")
                    shutil.rmtree(xd,ignore_errors=True)
                except zipfile.BadZipFile: st["err"]+=1
            dp.unlink(missing_ok=True); c.mark(url); c.save()
        except Exception as e: logging.error(f"  {name}: {e}"); st["err"]+=1
    return st

# ===========================================================================
# SOURCE 4: GitHub search for repos with WAV/NAM files (auto-discovery)
# ===========================================================================
def dl_github_search(s,c,o):
    """Use GitHub code search API to find repos with .nam and .wav files."""
    st={"ok":0,"skip":0,"err":0,"files":0}
    
    queries = [
        "extension:nam path:/ language:''",
        "extension:nam guitar amp",
        "impulse response wav cabinet speaker guitar",
    ]
    
    found_repos = set()
    
    for q in queries:
        try:
            r = s.get(f"https://api.github.com/search/repositories?q={quote(q)}&sort=updated&per_page=30",
                     timeout=30, headers={"Accept":"application/vnd.github+json"})
            if r.status_code != 200: continue
            for repo in r.json().get("items",[]):
                fn = repo["full_name"]
                sz = repo.get("size",0)
                if sz > 500 and fn not in found_repos:  # Only repos > 500KB
                    found_repos.add(fn)
        except: pass
        time.sleep(1)
    
    # Remove already-downloaded repos
    found_repos -= set(REPOS)
    
    logging.info(f"GitHub search found {len(found_repos)} new repos to try")
    
    for repo in list(found_repos)[:20]:  # Limit to 20 new repos
        owner,name = repo.split("/",1)
        ck=f"ghs_{owner}_{name}"
        if c.seen(ck): st["skip"]+=1; continue
        
        for br in ["main","master"]:
            zu=f"https://github.com/{owner}/{name}/archive/refs/heads/{br}.zip"
            zp=Path("/tmp/ghs")/f"{name}.zip"; zp.parent.mkdir(parents=True,exist_ok=True)
            try:
                r=s.get(zu,stream=True,timeout=120)
                if r.status_code==404: continue
                r.raise_for_status()
                # Skip if too large (>500MB)
                cl = int(r.headers.get("Content-Length","0"))
                if cl > 500*1024*1024:
                    logging.warning(f"Skipping {repo} (too large: {cl/1e6:.0f}MB)")
                    c.mark(ck); break
                    
                with open(zp,"wb") as f:
                    for ch in r.iter_content(1024*1024): f.write(ch)
                logging.info(f"Search DL {repo} ({zp.stat().st_size/1e6:.1f}MB)")
                st["ok"]+=1
                ed=Path("/tmp/ghs")/name
                try:
                    with zipfile.ZipFile(zp) as zf: zf.extractall(ed)
                except: st["err"]+=1; break
                fc=0
                for rt,ds,fs in os.walk(ed):
                    ds[:]=[d for d in ds if not d.startswith((".",  "__"))]
                    for fn in fs:
                        if Path(fn).suffix.lower() not in VALID_EXT: continue
                        src=Path(rt)/fn
                        if not valid(src) or c.dup(src): continue
                        d=o.dest(src,f"{name}/{os.path.relpath(rt,ed)}/{fn}")
                        shutil.copy2(src,d); fc+=1; st["files"]+=1
                logging.info(f"  → {fc} from search/{name}")
                c.mark(ck); c.save()
                shutil.rmtree(ed,ignore_errors=True); zp.unlink(missing_ok=True)
                break
            except Exception as e:
                if br=="master": logging.warning(f"Skip search {repo}: {e}"); st["err"]+=1
    return st

# ===========================================================================
# SOURCE 5: TONE3000 public pages (no API key - scrape public listing)
# ===========================================================================
def dl_tone3000_public(s,c,o):
    """Try to get tones from TONE3000 public listing without API key."""
    st={"ok":0,"skip":0,"err":0,"files":0}
    
    # Try the public API endpoints that don't require auth
    base = "https://www.tone3000.com"
    
    for gear in ["amp","pedal","ir"]:
        logging.info(f"TONE3000 public: gear={gear}")
        for page in range(1, 100):
            try:
                # Try different public endpoints
                for endpoint in [
                    f"{base}/api/v1/tones?gear={gear}&page={page}&page_size=50&sort=most-downloaded",
                    f"{base}/api/tones?gear={gear}&page={page}&limit=50",
                    f"{base}/tones.json?gear={gear}&page={page}",
                ]:
                    try:
                        r = s.get(endpoint, timeout=30, headers={"Accept":"application/json"})
                        if r.status_code == 401:
                            logging.info(f"TONE3000 requires auth, skipping")
                            return st
                        if r.status_code != 200: continue
                        
                        data = r.json()
                        tones = data.get("data",[]) if isinstance(data,dict) else data
                        if not tones:
                            return st  # No more
                        
                        for tone in tones:
                            dl_url = tone.get("download_url") or tone.get("model_url") or tone.get("file_url")
                            if not dl_url: continue
                            if c.seen(dl_url): st["skip"]+=1; continue
                            
                            try:
                                dr = s.get(dl_url, timeout=60)
                                if dr.status_code != 200: c.mark(dl_url); continue
                                
                                title = tone.get("title","") or tone.get("name",f"t3k_{page}")
                                ext = Path(urlparse(dl_url).path).suffix.lower()
                                if ext not in VALID_EXT:
                                    ext = ".wav" if "wav" in dr.headers.get("Content-Type","") else ".nam"
                                if ext not in VALID_EXT: c.mark(dl_url); continue
                                
                                fname = re.sub(r'[<>:"/\\|?*]','_',title)[:60] + ext
                                tp = Path("/tmp/t3k")/fname; tp.parent.mkdir(parents=True,exist_ok=True)
                                tp.write_bytes(dr.content)
                                
                                if valid(tp) and not c.dup(tp):
                                    d = o.dest(tp, f"tone3000/{gear}/{title}")
                                    shutil.move(str(tp),d); st["files"]+=1; st["ok"]+=1
                                else:
                                    tp.unlink(missing_ok=True)
                                c.mark(dl_url)
                            except: st["err"]+=1
                        
                        if st["ok"]%50==0 and st["ok"]>0: c.save()
                        break  # Found working endpoint
                    except: continue
                
                time.sleep(0.5)
            except: break
    
    c.save()
    return st

# ===========================================================================
def gen_docs():
    total=0; cats={}
    for ch in BASE_DIR.iterdir():
        if ch.is_dir() and not ch.name.startswith("."):
            c=sum(1 for f in ch.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXT)
            if c>0: cats[ch.name]=c; total+=c
    md=f"# 🎸 IR DEF Repository\n\n> **{total:,}** archivos (.wav + .nam)\n\n| Cat | Files |\n|---|---|\n"
    for k,v in sorted(cats.items()): md+=f"| {k} | {v:,} |\n"
    md+=f"| **TOTAL** | **{total:,}** |\n"
    (BASE_DIR/"README.md").write_text(md,"utf-8")
    logging.info(f"Docs: {total:,}"); return total

# ===========================================================================
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--tier",default="all",choices=["github","soundwoofer","direct","tone3000","docs","all"])
    p.add_argument("--validate-only",action="store_true")
    p.add_argument("--output-dir",default="/tmp/ir_repository")
    a=p.parse_args()

    global BASE_DIR,CACHE_FILE,LOG_FILE
    BASE_DIR=Path(a.output_dir); CACHE_FILE=BASE_DIR/".download_cache.json"; LOG_FILE=BASE_DIR/".download.log"
    setup()
    logging.info("="*60)
    logging.info(f"IR DEF v5 ULTRA | tier={a.tier} | out={BASE_DIR}")
    logging.info("="*60)

    s=sess(); ca=C(); o=O(); st={}

    if a.validate_only:
        v=inv=0
        for rt,ds,fs in os.walk(BASE_DIR):
            ds[:]=[d for d in ds if not d.startswith(".")]
            for f in fs:
                fp=Path(rt)/f
                if fp.suffix.lower() in VALID_EXT:
                    if valid(fp): v+=1
                    else: fp.unlink(); inv+=1
        logging.info(f"Valid={v} Invalid={inv}"); return

    if a.tier in ("github","all"):
        logging.info(">>> GITHUB REPOS")
        st["gh"]=dl_github(s,ca,o)
        logging.info(f"GitHub: {st['gh']}")
        logging.info(">>> GITHUB RELEASES")
        st["rel"]=dl_releases(s,ca,o)
        logging.info(f"Releases: {st['rel']}")
    if a.tier in ("soundwoofer","all"):
        logging.info(">>> SOUNDWOOFER (1200+ free cab IRs)")
        st["sw"]=dl_soundwoofer(s,ca,o)
        logging.info(f"Soundwoofer: {st['sw']}")

    if a.tier in ("tone3000","all"):
        logging.info(">>> TONE3000 PUBLIC")
        st["t3k"]=dl_tone3000_public(s,ca,o)
        logging.info(f"TONE3000: {st['t3k']}")

    if a.tier in ("direct","all"):
        logging.info(">>> DIRECT ZIPs")
        st["dir"]=dl_direct(s,ca,o)
        logging.info(f"Direct: {st['dir']}")

    if a.tier in ("docs","all"):
        st["docs"]={"total":gen_docs()}

    (BASE_DIR/".stats.json").write_text(json.dumps(st,indent=2),"utf-8")
    logging.info("="*60)
    logging.info("DONE! "+json.dumps(st))
    logging.info("="*60)

if __name__=="__main__":
    main()
