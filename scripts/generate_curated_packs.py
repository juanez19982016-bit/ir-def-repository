import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Config
RCLONE_REMOTE = "GoogleDrive:IR_DEF_REPO"
PACKS_REMOTE = f"{RCLONE_REMOTE}/_CURATED_RIGS"
TEMP_DIR = Path("temp_packs")
MAX_FILES_PER_PACK = 150 # Max files per pack to keep it curated

# Curated Packs Definitions
PACKS = {
    "01_Modern_Metal_Starter_Pack": ["5150", "evh", "rectifier", "mesa", "engl", "diesel", "v30", "ts9", "precision drive", "fortin"],
    "02_Classic_Rock_Legends": ["marshall", "plexi", "jcm800", "greenback", "creamback", "ac30", "vox"],
    "03_Pristine_Clean_Ambient": ["fender", "twin reverb", "deluxe reverb", "jc120", "roland", "matchless", "lonestar"],
    "04_Bass_Foundations": ["ampeg", "svt", "darkglass", "b7k", "sansamp", "gallien", "bass", "trace elliot"]
}

def run_rclone(cmd, capture=False):
    # Quiet execution for bulk downloads to prevent huge logs
    if not capture and "copyto" in cmd:
        cmd = cmd + ["-q"]
        
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
        return result.stdout
    else:
        subprocess.run(cmd, check=True)

def get_all_files():
    print("Fetching all files from Drive (This may take a minute)...")
    output = run_rclone(["rclone", "lsjson", RCLONE_REMOTE, "-R", "--files-only"], capture=True)
    try:
        data = json.loads(output)
        return [f["Path"] for f in data if ("NAM" in f["Path"] or "IR" in f["Path"] or f["Path"].endswith((".wav", ".nam")))]
    except Exception as e:
        print(f"Error parsing rclone output: {e}")
        return []

def create_packs():
    files = get_all_files()
    if not files:
        print("No files discovered. Exiting.")
        return

    print(f"Discovered {len(files)} potential tone files.")
    
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()

    for pack_name, keywords in PACKS.items():
        print(f"\n--- Generating Pack: {pack_name} ---")
        pack_dir = TEMP_DIR / pack_name
        pack_dir.mkdir()
        
        # Filter files
        matched_files = []
        for file_path in files:
            # Skip existing curated rigs
            if "_CURATED_RIGS" in file_path:
                continue
            
            lower_path = file_path.lower()
            if any(k.lower() in lower_path for k in keywords):
                matched_files.append(file_path)
                
        # Limit to max files for curation
        import random
        random.seed(42) # Deterministic selection
        if len(matched_files) > MAX_FILES_PER_PACK:
            matched_files = random.sample(matched_files, MAX_FILES_PER_PACK)
            
        print(f"Selected {len(matched_files)} files for {pack_name}.")
        
        # Download files
        for i, file_path in enumerate(matched_files):
            # Print occasionally to show progress without filling terminal
            if i % 10 == 0 or i == len(matched_files)-1:
                print(f"[{i+1}/{len(matched_files)}] Syncing to {pack_name}...")
                
            remote_path = f"{RCLONE_REMOTE}/{file_path}"
            # Evitar colisiones de nombres
            filename = Path(file_path).name
            local_path = pack_dir / f"{i:03d}_{filename}"
            run_rclone(["rclone", "copyto", remote_path, str(local_path)])
            
        # Create Readme
        readme_path = pack_dir / "README_TONEHUB_PRO.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"ToneHub Pro - {pack_name.replace('_', ' ')}\n")
            f.write("="*50 + "\n")
            f.write("A curated selection of premium Impulse Responses and NAM captures.\n")
            f.write("Perfect for instant playing without digging through 35,000 files.\n\n")
            f.write("Contents focus:\n")
            for k in keywords:
                f.write(f"- {k.title()}\n")
            f.write("\nEnjoy your tone!\n- ToneHub Pro\n")
            
        # Zip
        zip_path = TEMP_DIR / f"{pack_name}.zip"
        print(f"Zipping {pack_name}...")
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', pack_dir)
        
        # Upload
        print(f"Uploading {pack_name}.zip to Drive...")
        run_rclone(["rclone", "copy", str(zip_path), PACKS_REMOTE])
        print(f"Pack {pack_name} uploaded successfully!")
        
    print("\nCleaning up temp files...")
    shutil.rmtree(TEMP_DIR)
    print("All Premium Curated Packs generated and uploaded!")

if __name__ == "__main__":
    create_packs()
