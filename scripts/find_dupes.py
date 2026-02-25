import subprocess, json
from collections import defaultdict

def run_rclone(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

print("Fetching file list with hashes...")
output = run_rclone(["rclone", "lsjson", "gdrive2:IR_DEF_REPOSITORY", "-R", "--files-only", "--hash"])
files = json.loads(output)

hashes = defaultdict(list)
names = defaultdict(list)

for f in files:
    h = f.get('Hashes', {}).get('md5')
    if h:
        hashes[h].append(f['Path'])
    name = f['Path'].split('/')[-1]
    names[name].append(f['Path'])

dupe_hashes = {h: paths for h, paths in hashes.items() if len(paths) > 1}
dupe_names = {n: paths for n, paths in names.items() if len(paths) > 1}

print(f"Total files: {len(files)}")
print(f"Files with identical MD5 hashes: {sum(len(paths) for paths in dupe_hashes.values())} (in {len(dupe_hashes)} unique hashes)")
print(f"Files with identical names: {sum(len(paths) for paths in dupe_names.values())} (in {len(dupe_names)} unique names)")

with open("dupes_report.json", "w", encoding="utf-8") as f:
    json.dump({
        "hash_duplicates": dupe_hashes,
        "name_duplicates": dupe_names
    }, f, indent=2)
print("Saved dupes_report.json")
