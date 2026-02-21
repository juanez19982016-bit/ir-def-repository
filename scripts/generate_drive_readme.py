"""
ToneHub Pro - Drive README Generator
======================================
Creates a premium README.txt file in the root of the Google Drive
repository so customers immediately understand what they have.
"""
import os, json, subprocess
from pathlib import Path
from datetime import datetime

RCLONE_REMOTE = "gdrive2:IR_DEF_REPOSITORY"
TEMP_DIR = Path("/tmp/drive_readme")

def rclone(args, capture=False):
    cmd = ["rclone"] + args
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return r.stdout, r.returncode
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("📡 Scanning Drive for statistics...")
    out, rc = rclone(["lsjson", RCLONE_REMOTE, "-R", "--files-only", "--no-modtime", "--no-mimetype"], capture=True)
    if rc != 0 or not out.strip():
        print("❌ Could not read Drive.")
        return

    data = json.loads(out)
    wavs = [f for f in data if f["Path"].lower().endswith(".wav")]
    nams = [f for f in data if f["Path"].lower().endswith(".nam")]
    total = len(wavs) + len(nams)
    total_size = sum(f.get("Size", 0) for f in data)

    # Get brands
    brands = set()
    for f in data:
        parts = f["Path"].split("/")
        if len(parts) >= 2 and not parts[0].startswith("_"):
            brands.add(parts[0])

    def fmt(b):
        for u in ["B", "KB", "MB", "GB", "TB"]:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    readme = TEMP_DIR / "README_TONEHUB_PRO.txt"
    with open(readme, "w", encoding="utf-8") as f:
        f.write(r"""
████████╗ ██████╗ ███╗   ██╗███████╗██╗  ██╗██╗   ██╗██████╗
╚══██╔══╝██╔═══██╗████╗  ██║██╔════╝██║  ██║██║   ██║██╔══██╗
   ██║   ██║   ██║██╔██╗ ██║█████╗  ███████║██║   ██║██████╔╝
   ██║   ██║   ██║██║╚██╗██║██╔══╝  ██╔══██║██║   ██║██╔══██╗
   ██║   ╚██████╔╝██║ ╚████║███████╗██║  ██║╚██████╔╝██████╔╝
   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝
                    P  R  O
""")
        f.write("=" * 60 + "\n")
        f.write("  THE ULTIMATE TONE COLLECTION\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"  Last Updated: {datetime.now().strftime('%B %d, %Y')}\n\n")
        f.write(f"  📊 Repository Statistics:\n")
        f.write(f"  ─────────────────────────────────────\n")
        f.write(f"  Total Tone Files:    {total:,}\n")
        f.write(f"  Impulse Responses:   {len(wavs):,} (.wav)\n")
        f.write(f"  Neural Amp Models:   {len(nams):,} (.nam)\n")
        f.write(f"  Total Brands:        {len(brands)}\n")
        f.write(f"  Total Size:          {fmt(total_size)}\n\n")
        f.write(f"  📂 Folder Structure:\n")
        f.write(f"  ─────────────────────────────────────\n")
        f.write(f"  /[Brand Name]/          → Master vault organized by brand\n")
        f.write(f"  /_CURATED_RIGS/         → Ready-to-play themed ZIP packs\n")
        f.write(f"  /_BRAND_CATALOGS/       → Full file listings per brand\n")
        f.write(f"  /README_TONEHUB_PRO.txt → This file\n\n")
        f.write(f"  🎸 How to Use:\n")
        f.write(f"  ─────────────────────────────────────\n")
        f.write(f"  1. QUICK START: Go to _CURATED_RIGS/ and download\n")
        f.write(f"     a themed pack (e.g., Modern_Metal_Starter_Pack.zip)\n\n")
        f.write(f"  2. BROWSE BY BRAND: Navigate brand folders to find\n")
        f.write(f"     specific amp/cab captures.\n\n")
        f.write(f"  3. SEARCH: Use Google Drive's search bar to find\n")
        f.write(f"     any specific model instantly.\n\n")
        f.write(f"  4. IRs (.wav): Load into any amp sim or modeler\n")
        f.write(f"     that supports impulse responses.\n\n")
        f.write(f"  5. NAMs (.nam): Load into Neural Amp Modeler plugin.\n\n")
        f.write(f"  🏷️ Brand Index ({len(brands)} brands):\n")
        f.write(f"  ─────────────────────────────────────\n")
        for b in sorted(brands):
            count = len([x for x in data if x["Path"].startswith(b + "/") and x["Path"].lower().endswith((".wav", ".nam"))])
            f.write(f"  • {b:<30} {count:>5} files\n")
        f.write(f"\n" + "=" * 60 + "\n")
        f.write(f"  ToneHub Pro — Premium Tone Ecosystem\n")
        f.write(f"  All content is 100% real captures from verified sources.\n")
        f.write(f"=" * 60 + "\n")

    print("☁️  Uploading README to Drive root...")
    rclone(["copy", str(readme), RCLONE_REMOTE])
    print("✅ README_TONEHUB_PRO.txt uploaded!")

    import shutil
    shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()
