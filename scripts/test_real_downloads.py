import os, zipfile, shutil, requests
from pathlib import Path

BASE_DIR = Path(r"C:\Users\Admin\Desktop\IR DEF\ir-repository\03_PRESETS_AND_MODELERS")

VALID_EXT = {
    ".kipr", ".hlx", ".pgp", ".syx", ".rig", ".tsl", 
    ".txp", ".prst", ".patch", ".mo", ".preset"
}

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

def organize_file(src_path):
    fn = Path(src_path).name
    cat = EXT_MAP.get(Path(fn).suffix.lower(), "Misc")
    dest_dir = BASE_DIR / cat
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    clean = fn.replace(' ', '_')
    dest = dest_dir / clean
    if not dest.exists():
        shutil.copy2(src_path, dest)
        return True
    return False

def test_repo(repo):
    print("Testing repo:", repo)
    tmp_dir = Path("temp_extract")
    tmp_dir.mkdir(exist_ok=True)
    
    count = 0
    for branch in ["main", "master"]:
        url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
        try:
            r = requests.get(url, stream=True, timeout=10)
            if r.status_code == 200:
                zip_path = tmp_dir / "test.zip"
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(1024 * 1024): f.write(chunk)
                
                with zipfile.ZipFile(zip_path) as zf: 
                    zf.extractall(tmp_dir)
                
                for root, dirs, files in os.walk(tmp_dir):
                    for fn in files:
                        p = Path(root) / fn
                        if p.suffix.lower() in VALID_EXT:
                            if p.stat().st_size > 50:
                                if organize_file(p):
                                    count += 1
                
                print(f"Great success! Added {count} from {repo}")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return
        except Exception as e:
            print("Error", e)
    print("Failed to download or find valid files in", repo)
    shutil.rmtree(tmp_dir, ignore_errors=True)

repos = [
    "alexander-makarov/Fractal-AxeFx2-Presets",
    "MoisesM/Helix-Presets",
    "niksoper/helix-presets",
    "sj-williams/pod-go-patches",
    "engageintellect/pod-go-patches",
    "Tonalize/HelixNativePresets",
    "jyanes83/Line6-Helix-Bundle-Parser",
    "bloodysummers/headrushfx-editor",
    "pdec5504/MX5-rig-manager",
    "bohoffi/boss-gt-1000-patch-editor",
    "lamparom2025/GT1000-UNLEASHED",
    "fourth44/boss-gt1000",
    "ray-su/Ampero-presets",
    "G6-Presets/zoom",
    "valeton/gp100-patches",
    "AxeFxDocs/Presets", 
    "Line6/Helix",
    "Kempler/Profiles"
]

for r in repos:
    test_repo(r)
