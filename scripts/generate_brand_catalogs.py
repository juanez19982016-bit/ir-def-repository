"""
ToneHub Pro - PDF Brand Catalog Generator
==========================================
Scans the Drive repository structure and generates a professional
PDF catalog document for each brand folder, then uploads them
back to the Drive root as _BRAND_CATALOGS/.
"""
import os, sys, json, subprocess, textwrap
from pathlib import Path
from datetime import datetime

RCLONE_REMOTE = "gdrive2:IR_DEF_REPOSITORY"
CATALOGS_REMOTE = f"{RCLONE_REMOTE}/_BRAND_CATALOGS"
TEMP_DIR = Path("/tmp/brand_catalogs")

def rclone(args, capture=False):
    cmd = ["rclone"] + args
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return r.stdout, r.returncode
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_folder_structure():
    print("📡 Scanning Drive folder structure...")
    out, rc = rclone(["lsjson", RCLONE_REMOTE, "-R", "--files-only", "--no-modtime", "--no-mimetype"], capture=True)
    if rc != 0 or not out.strip():
        print(f"❌ Failed (rc={rc})")
        return {}
    try:
        data = json.loads(out)
    except:
        print("❌ JSON parse error")
        return {}

    # Group files by top-level folder (Brand)
    brands = {}
    for f in data:
        p = f["Path"]
        if p.startswith("_"):  # Skip meta folders
            continue
        parts = p.split("/")
        if len(parts) < 2:
            continue
        brand = parts[0]
        fname = parts[-1]
        ext = Path(fname).suffix.lower()
        if ext not in (".wav", ".nam"):
            continue
        if brand not in brands:
            brands[brand] = {"files": [], "types": {"wav": 0, "nam": 0}, "size_bytes": 0}
        brands[brand]["files"].append(fname)
        brands[brand]["types"]["wav" if ext == ".wav" else "nam"] += 1
        brands[brand]["size_bytes"] += f.get("Size", 0)

    print(f"✅ Found {len(brands)} brand folders")
    return brands

def format_size(b):
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def generate_catalog_txt(brand, info):
    """Generate a rich-text catalog (TXT format, universally readable)."""
    files = sorted(info["files"])
    wavs = info["types"]["wav"]
    nams = info["types"]["nam"]
    total = len(files)
    size = format_size(info["size_bytes"])

    lines = []
    lines.append("╔" + "═"*58 + "╗")
    lines.append("║" + f"  ToneHub Pro — {brand} Catalog".center(58) + "║")
    lines.append("╠" + "═"*58 + "╣")
    lines.append("║" + f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}".ljust(58) + "║")
    lines.append("║" + f"  Total Files: {total}".ljust(58) + "║")
    lines.append("║" + f"  Impulse Responses (IR/WAV): {wavs}".ljust(58) + "║")
    lines.append("║" + f"  Neural Amp Models (NAM): {nams}".ljust(58) + "║")
    lines.append("║" + f"  Total Size: {size}".ljust(58) + "║")
    lines.append("╚" + "═"*58 + "╝")
    lines.append("")
    lines.append("─" * 60)
    lines.append("  FILE LISTING")
    lines.append("─" * 60)
    lines.append("")

    # Group by sub-type
    ir_files = [f for f in files if f.lower().endswith(".wav")]
    nam_files = [f for f in files if f.lower().endswith(".nam")]

    if ir_files:
        lines.append(f"  ▸ Impulse Responses ({len(ir_files)} files)")
        lines.append("  " + "·" * 50)
        for i, f in enumerate(ir_files, 1):
            lines.append(f"    {i:4d}. {f}")
        lines.append("")

    if nam_files:
        lines.append(f"  ▸ Neural Amp Models ({len(nam_files)} files)")
        lines.append("  " + "·" * 50)
        for i, f in enumerate(nam_files, 1):
            lines.append(f"    {i:4d}. {f}")
        lines.append("")

    lines.append("─" * 60)
    lines.append("  ToneHub Pro — The Ultimate Tone Collection")
    lines.append("  35,000+ Studio-Grade Captures & Models")
    lines.append("─" * 60)

    return "\n".join(lines)

def main():
    brands = get_folder_structure()
    if not brands:
        print("No brands found. Exiting.")
        return

    if TEMP_DIR.exists():
        import shutil
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True)

    total_brands = len(brands)
    for idx, (brand, info) in enumerate(sorted(brands.items()), 1):
        print(f"[{idx}/{total_brands}] 📄 Generating catalog for {brand} ({len(info['files'])} files)...")
        content = generate_catalog_txt(brand, info)
        out_file = TEMP_DIR / f"{brand}_Catalog.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)

    # Also generate a MASTER catalog
    print(f"\n📄 Generating MASTER catalog...")
    master_lines = []
    master_lines.append("╔" + "═"*58 + "╗")
    master_lines.append("║" + "  ToneHub Pro — MASTER CATALOG".center(58) + "║")
    master_lines.append("╠" + "═"*58 + "╣")
    master_lines.append("║" + f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}".ljust(58) + "║")
    master_lines.append("║" + f"  Total Brands: {total_brands}".ljust(58) + "║")
    total_files = sum(len(b["files"]) for b in brands.values())
    master_lines.append("║" + f"  Total Files: {total_files}".ljust(58) + "║")
    total_wavs = sum(b["types"]["wav"] for b in brands.values())
    total_nams = sum(b["types"]["nam"] for b in brands.values())
    total_size = sum(b["size_bytes"] for b in brands.values())
    master_lines.append("║" + f"  IR/WAV: {total_wavs} | NAM: {total_nams}".ljust(58) + "║")
    master_lines.append("║" + f"  Total Size: {format_size(total_size)}".ljust(58) + "║")
    master_lines.append("╚" + "═"*58 + "╝")
    master_lines.append("")
    master_lines.append("─" * 60)
    master_lines.append("  BRAND INDEX (sorted by file count)")
    master_lines.append("─" * 60)
    master_lines.append("")
    master_lines.append(f"  {'Brand':<30} {'Files':>8} {'IR/WAV':>8} {'NAM':>8}")
    master_lines.append("  " + "─"*56)
    for brand, info in sorted(brands.items(), key=lambda x: len(x[1]["files"]), reverse=True):
        master_lines.append(f"  {brand:<30} {len(info['files']):>8} {info['types']['wav']:>8} {info['types']['nam']:>8}")
    master_lines.append("")
    master_lines.append("─" * 60)
    master_lines.append("  ToneHub Pro — The Ultimate Tone Collection")
    master_lines.append("─" * 60)

    master_file = TEMP_DIR / "00_MASTER_CATALOG.txt"
    with open(master_file, "w", encoding="utf-8") as f:
        f.write("\n".join(master_lines))

    # Upload all catalogs
    print(f"\n☁️  Uploading {total_brands + 1} catalogs to Drive...")
    rclone(["copy", str(TEMP_DIR), CATALOGS_REMOTE])

    print("\n🧹 Cleaning up...")
    import shutil
    shutil.rmtree(TEMP_DIR)
    print(f"🎉 {total_brands} brand catalogs + 1 master catalog generated and uploaded!")

if __name__ == "__main__":
    main()
