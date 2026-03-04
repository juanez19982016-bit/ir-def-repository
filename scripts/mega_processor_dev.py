import os
import json
import requests
import zipfile
import shutil
import argparse
import time

def process_repos(json_file, output_base):
    with open(json_file, 'r') as f:
        repos = json.load(f)
        
    print(f"Processing {len(repos)} elite repositories...")
    
    success_count = 0
    total_size_mb = 0
    
    for repo in repos:
        category = repo.get("category", "Misc")
        repo_name = repo.get("repo_name", "").replace("/", "_")
        url1 = repo.get("download_url")
        url2 = repo.get("fallback_url")
        
        target_dir = os.path.join(output_base, f"[{category}]", repo_name)
        
        if os.path.exists(target_dir):
            continue
            
        temp_zip = f"{repo_name}.zip"
        
        print(f"Downloading God-Tier Asset: {repo_name}...")
        try:
            r = requests.get(url1, stream=True, timeout=30)
            if r.status_code == 404:
                r = requests.get(url2, stream=True, timeout=30)
                
            r.raise_for_status()
            
            with open(temp_zip, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            size_mb = os.path.getsize(temp_zip) / (1024 * 1024)
            total_size_mb += size_mb
            
            # Extract and clean
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(temp_zip, 'r') as z:
                z.extractall(target_dir)
                
            os.remove(temp_zip)
            
            # Remove node_modules
            for root, dirs, files in os.walk(target_dir, topdown=False):
                for name in dirs:
                    if name == "node_modules":
                        shutil.rmtree(os.path.join(root, name))
                        
            success_count += 1
            print(f"  -> Extracted successfully ({size_mb:.2f} MB).")
            
        except Exception as e:
            print(f"  -> Failed: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
                
        time.sleep(2) # Respectful delay
        
    print(f"\nDone. Successfully processed {success_count} hyper-premium assets.")
    print(f"Estimated Raw Size Added: {total_size_mb:.2f} MB.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', default="github_dev_assets.json")
    parser.add_argument('--output', default="God_Tier_Dev_Vault") # Upgraded folder name
    
    args = parser.parse_args()
    if os.path.exists(args.json):
        process_repos(args.json, args.output)
    else:
        print("JSON data not found.")
