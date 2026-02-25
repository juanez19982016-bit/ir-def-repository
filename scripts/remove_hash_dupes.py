import json
import subprocess
import os

print("Loading duplicate report...")
with open("dupes_report.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dupe_hashes = data.get("hash_duplicates", {})
to_delete = []

for h, paths in dupe_hashes.items():
    # Filter only .wav and .nam just to be safe
    audio_paths = [p for p in paths if p.lower().endswith(('.wav', '.nam'))]
    if len(audio_paths) > 1:
        # Sort paths by length so we prefer keeping the one in the shallowest folder
        audio_paths.sort(key=lambda x: (len(x), x))
        
        # Keep the first, delete the rest
        for dele in audio_paths[1:]:
            to_delete.append(dele)

print(f"Planning to delete {len(to_delete)} exact duplicate audio files.")

if to_delete:
    with open("delete_list.txt", "w", encoding="utf-8") as f:
        for p in to_delete:
            f.write(f"{p}\n")
    
    print("Executing batch deletion with rclone...")
    subprocess.run(["rclone", "delete", "gdrive2:IR_DEF_REPOSITORY", "--files-from", "delete_list.txt", "-v"])
    print("Deletion complete.")
    
    # Regenerate README
    print("Regenerating total count via README...")
    subprocess.run(["python", "scripts/generate_drive_readme.py"])
else:
    print("No duplicates found to delete.")
