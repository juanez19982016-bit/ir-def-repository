import os
import json
import requests
import zipfile
import shutil
import argparse
import time
import re

# GitHub junk files/folders to DELETE
GITHUB_JUNK = {
    ".github", ".git", ".gitignore", ".gitattributes",
    "CONTRIBUTING.md", "CONTRIBUTORS.md", "CODE_OF_CONDUCT.md",
    "SECURITY.md", ".editorconfig", ".prettierignore",
    ".eslintignore", ".husky", ".vscode", ".idea",
    "CHANGELOG.md", ".npmignore", ".dockerignore",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".travis.yml", ".circleci", "Makefile",
    "renovate.json", ".changeset", "turbo.json",
    "CODEOWNERS", ".yarnrc.yml", ".pnp.cjs",
}

def clean_project_name(repo_name):
    """Transform 'mickasmt_next-saas-stripe-starter' into 'Next SaaS Stripe Starter'"""
    parts = repo_name.split("_", 1)
    name = parts[1] if len(parts) > 1 else parts[0]
    name = re.sub(r'[-_](main|master)$', '', name)
    name = name.replace("-", " ").replace("_", " ")
    name = name.title()
    for term in ["Ui", "Ai", "Css", "Js", "Api", "Crm", "Saas", "Cms", "Sdk", "Cli", "Seo"]:
        name = name.replace(term, term.upper())
    name = name.replace("Next.JS", "Next.js").replace("React.JS", "React.js")
    return name.strip()

def flatten_extracted(target_dir):
    """Fix double-nesting: if extraction created a single subfolder, move everything UP."""
    items = os.listdir(target_dir)
    # Filter out PROJECT_INFO.md which we create
    dirs = [d for d in items if os.path.isdir(os.path.join(target_dir, d))]
    files = [f for f in items if os.path.isfile(os.path.join(target_dir, f))]
    
    # If there's exactly 1 subfolder and no files (typical GitHub extract pattern)
    if len(dirs) == 1 and len(files) == 0:
        inner = os.path.join(target_dir, dirs[0])
        # Move all contents from inner folder UP to target_dir
        for item in os.listdir(inner):
            src = os.path.join(inner, item)
            dst = os.path.join(target_dir, item)
            if not os.path.exists(dst):
                shutil.move(src, dst)
        # Remove now-empty inner folder
        shutil.rmtree(inner, ignore_errors=True)
        return True
    return False

def remove_github_junk(target_dir):
    """Remove GitHub-specific files that expose raw clones."""
    removed = 0
    for root, dirs, files in os.walk(target_dir, topdown=True):
        depth = root.replace(target_dir, "").count(os.sep)
        if depth > 1:
            continue
        for name in dirs[:]:
            if name in GITHUB_JUNK or name == "node_modules" or name == ".next" or name == "dist":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
                removed += 1
        for name in files:
            if name in GITHUB_JUNK:
                try:
                    os.remove(os.path.join(root, name))
                    removed += 1
                except:
                    pass
    return removed

def detect_stack(proj_path):
    """Detect tech stack from project files."""
    stack = []
    for item in os.listdir(proj_path):
        il = item.lower()
        if il in ("next.config.js", "next.config.ts", "next.config.mjs"): stack.append("Next.js")
        elif il in ("tailwind.config.js", "tailwind.config.ts"): stack.append("Tailwind CSS")
        elif il == "tsconfig.json": stack.append("TypeScript")
    pkg = os.path.join(proj_path, "package.json")
    if os.path.exists(pkg):
        try:
            with open(pkg, 'r', errors='ignore') as f:
                c = f.read()
            if "supabase" in c: stack.append("Supabase")
            if "stripe" in c: stack.append("Stripe")
            if "prisma" in c: stack.append("Prisma")
            if "framer-motion" in c: stack.append("Framer Motion")
            if "@radix" in c or "shadcn" in c: stack.append("Shadcn/Radix")
            if "openai" in c: stack.append("OpenAI")
            if "next-auth" in c or "@auth/" in c: stack.append("Auth.js")
            if "react" in c and "React" not in stack: stack.append("React")
        except:
            pass
    return list(dict.fromkeys(stack))[:6]

def get_description(proj_path):
    """Extract first meaningful description from README."""
    for rname in ["README.md", "readme.md", "Readme.md", "README.rst"]:
        rpath = os.path.join(proj_path, rname)
        if os.path.exists(rpath):
            try:
                with open(rpath, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("!") and not line.startswith("<") and not line.startswith("[") and len(line) > 20:
                            return line[:250]
            except:
                pass
    return "Professional web development project with production-ready code."

def generate_project_info(proj_path, clean_name, repo_meta):
    """Generate PROJECT_INFO.md inside each project."""
    stars = repo_meta.get("stars", "N/A")
    category = repo_meta.get("category", "").replace("_", " ")
    stack = detect_stack(proj_path)
    stack_str = " · ".join(stack) if stack else "Web Development"
    desc = get_description(proj_path)
    
    info = f"""# {clean_name}

**Category:** {category}  
**Stack:** `{stack_str}`  
**GitHub Stars:** ⭐ {stars}  
**License:** MIT (Free for commercial use)

## Description
{desc}

## Quick Start
```bash
npm install
npm run dev
```

## Tech Stack
{chr(10).join(f"- {s}" for s in stack) if stack else "- See package.json"}

---
*DevVault Pro 2026*
"""
    with open(os.path.join(proj_path, "PROJECT_INFO.md"), 'w', encoding='utf-8') as f:
        f.write(info)

def process_repos(json_file, output_base):
    with open(json_file, 'r') as f:
        repos = json.load(f)
    
    print(f"Processing {len(repos)} repositories...")
    
    # Build mapping for catalog generator: clean_name -> metadata
    name_map = {}
    success = 0
    total_mb = 0
    total_junk = 0
    
    for repo in repos:
        category = repo.get("category", "Misc")
        repo_name = repo.get("repo_name", "").replace("/", "_")
        url1 = repo.get("download_url")
        url2 = repo.get("fallback_url")
        
        clean_name = clean_project_name(repo_name)
        target_dir = os.path.join(output_base, f"[{category}]", clean_name)
        
        # Save mapping for catalog
        name_map[clean_name] = repo
        
        if os.path.exists(target_dir):
            continue
        
        temp_zip = f"{repo_name}.zip"
        print(f"  Downloading: {clean_name}...")
        
        try:
            r = requests.get(url1, stream=True, timeout=60)
            if r.status_code == 404:
                r = requests.get(url2, stream=True, timeout=60)
            r.raise_for_status()
            
            with open(temp_zip, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size_mb = os.path.getsize(temp_zip) / (1024 * 1024)
            total_mb += size_mb
            
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(temp_zip, 'r') as z:
                z.extractall(target_dir)
            os.remove(temp_zip)
            
            # FIX 1: Flatten double-nesting
            flatten_extracted(target_dir)
            
            # FIX 2: Remove GitHub junk
            junk = remove_github_junk(target_dir)
            total_junk += junk
            
            # FIX 3: Generate PROJECT_INFO.md
            generate_project_info(target_dir, clean_name, repo)
            
            success += 1
            print(f"    ✅ OK ({size_mb:.1f} MB, {junk} junk removed)")
            
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            # Remove empty dir if failed
            if os.path.exists(target_dir) and not os.listdir(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
        
        time.sleep(1)
    
    # Remove empty category folders
    for cat_folder in os.listdir(output_base):
        cat_path = os.path.join(output_base, cat_folder)
        if os.path.isdir(cat_path) and not os.listdir(cat_path):
            shutil.rmtree(cat_path)
            print(f"  Removed empty category: {cat_folder}")
    
    # Save name mapping for catalog generator
    with open("name_mapping.json", 'w') as f:
        json.dump({k: v for k, v in name_map.items()}, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Done. {success}/{len(repos)} projects processed.")
    print(f"Total: {total_mb:.0f} MB downloaded, {total_junk} junk files removed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', default="github_dev_assets.json")
    parser.add_argument('--output', default="God_Tier_Dev_Vault")
    args = parser.parse_args()
    if os.path.exists(args.json):
        process_repos(args.json, args.output)
    else:
        print("JSON data not found.")
