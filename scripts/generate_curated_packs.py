"""
ToneHub Pro - Curated Rig Pack Generator
=========================================
Scans the entire Drive repository, identifies tone files by keyword,
and uploads curated ZIP packs to _CURATED_RIGS/ on Drive.
"""
import os, sys, json, shutil, subprocess, random
from pathlib import Path

RCLONE_REMOTE = "gdrive2:IR_DEF_REPOSITORY"
PACKS_REMOTE = f"{RCLONE_REMOTE}/_CURATED_RIGS"
TEMP_DIR = Path("/tmp/curated_packs")
MAX_FILES_PER_PACK = 120

PACKS = {
    "01_Modern_Metal_Starter_Pack": {
        "keywords": ["5150", "evh", "rectifier", "mesa", "engl", "diezel", "v30", "ts9", "fortin", "revv", "peavey"],
        "desc": "High-gain monsters: 5150s, Rectifiers, ENGLs, Diezels, and their matching cabs."
    },
    "02_Classic_Rock_Legends": {
        "keywords": ["marshall", "plexi", "jcm800", "jcm900", "greenback", "creamback", "ac30", "vox", "superlead", "jtm"],
        "desc": "The British Invasion: Marshall stacks, Vox chimney, and vintage crunch."
    },
    "03_Pristine_Clean_Ambient": {
        "keywords": ["fender", "twin reverb", "deluxe reverb", "jc120", "roland", "matchless", "lonestar", "princeton", "jazz chorus"],
        "desc": "Crystal-clean platforms for ambient, worship, and studio recording."
    },
    "04_Bass_Foundations": {
        "keywords": ["ampeg", "svt", "darkglass", "b7k", "sansamp", "gallien", "bass", "trace elliot", "b15"],
        "desc": "Thunderous bass tones: Ampeg SVTs, Darkglass crunch, and vintage warmth."
    },
    "05_Boutique_Premium_Collection": {
        "keywords": ["bogner", "friedman", "soldano", "two rock", "dumble", "matchless", "divided", "suhr", "morgan", "tone king"],
        "desc": "Ultra-premium boutique captures: Friedman, Bogner, Soldano, and more."
    },
    "06_Pedals_and_Overdrives": {
        "keywords": ["pedal", "overdrive", "distortion", "fuzz", "boost", "screamer", "klon", "rat", "muff", "drive", "stomp"],
        "desc": "Every iconic pedal captured: Tube Screamers, Klon, RAT, Big Muff, and beyond."
    },
}

def rclone(args, capture=False):
    cmd = ["rclone"] + args
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return r.stdout, r.returncode
    else:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_all_files():
    print("📡 Scanning entire Drive repository...")
    out, rc = rclone(["lsjson", RCLONE_REMOTE, "-R", "--files-only", "--no-modtime", "--no-mimetype"], capture=True)
    if rc != 0 or not out.strip():
        print(f"❌ Failed to list files (rc={rc}). Check rclone config.")
        return []
    try:
        data = json.loads(out)
        files = [f["Path"] for f in data if f["Path"].lower().endswith((".wav", ".nam"))]
        print(f"✅ Found {len(files)} tone files (.wav/.nam)")
        return files
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
        return []

def create_packs():
    files = get_all_files()
    if not files:
        return

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True)

    for pack_name, info in PACKS.items():
        keywords = info["keywords"]
        desc = info["desc"]
        print(f"\n{'='*60}")
        print(f"📦 Generating: {pack_name}")
        print(f"   {desc}")
        print(f"{'='*60}")

        pack_dir = TEMP_DIR / pack_name
        pack_dir.mkdir()

        # Match files by keyword
        matched = []
        for fp in files:
            if "_CURATED_RIGS" in fp:
                continue
            low = fp.lower()
            if any(k.lower() in low for k in keywords):
                matched.append(fp)

        random.seed(42)
        if len(matched) > MAX_FILES_PER_PACK:
            matched = random.sample(matched, MAX_FILES_PER_PACK)

        print(f"   Selected {len(matched)} files")

        if not matched:
            print(f"   ⚠️  No matches found, skipping.")
            continue

        # Download matched files
        for i, fp in enumerate(matched):
            if i % 20 == 0:
                print(f"   ⬇️  [{i+1}/{len(matched)}] downloading...")
            fname = Path(fp).name
            local = pack_dir / f"{i:03d}_{fname}"
            rclone(["copyto", f"{RCLONE_REMOTE}/{fp}", str(local), "-q"])

        # Write README
        readme = pack_dir / "README.txt"
        with open(readme, "w", encoding="utf-8") as f:
            f.write(f"ToneHub Pro — {pack_name.replace('_', ' ')}\n")
            f.write("=" * 55 + "\n\n")
            f.write(f"{desc}\n\n")
            f.write(f"Contains {len(matched)} curated files.\n")
            f.write("Keywords: " + ", ".join(keywords) + "\n\n")
            f.write("Part of the ToneHub Pro 35,000+ Tone Collection.\n")

        # Create ZIP
        zip_base = TEMP_DIR / pack_name
        print(f"   📁 Zipping...")
        shutil.make_archive(str(zip_base), "zip", pack_dir)

        # Upload
        zip_file = f"{zip_base}.zip"
        print(f"   ☁️  Uploading to Drive...")
        rclone(["copy", zip_file, PACKS_REMOTE])
        print(f"   ✅ {pack_name}.zip uploaded!")

    # Also upload individual pack folders (unzipped) for browsing
    print("\n☁️  Uploading unzipped folders for direct browsing...")
    rclone(["copy", str(TEMP_DIR), PACKS_REMOTE, "--exclude", "*.zip"])

    print("\n🧹 Cleaning up...")
    shutil.rmtree(TEMP_DIR)
    print("\n🎉 All Curated Rig Packs generated and uploaded to _CURATED_RIGS!")

if __name__ == "__main__":
    create_packs()
