import os
import json
import requests
import zipfile
import shutil
import argparse
import time
import re

# GitHub junk files/folders to DELETE (dead giveaway of raw clone)
GITHUB_JUNK = [
    ".github", ".git", ".gitignore", ".gitattributes",
    "CONTRIBUTING.md", "CONTRIBUTORS.md", "CODE_OF_CONDUCT.md",
    "SECURITY.md", ".editorconfig", ".prettierignore",
    ".eslintignore", ".husky", ".vscode", ".idea",
    "CHANGELOG.md", ".npmignore", ".dockerignore",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".travis.yml", ".circleci", "Makefile",
    "renovate.json", ".changeset", "turbo.json",
    "CODEOWNERS", ".yarnrc.yml", ".pnp.cjs",
]

def clean_project_name(repo_name):
    """Transform 'mickasmt_next-saas-stripe-starter' into 'Next SaaS Stripe Starter'"""
    # Remove owner prefix (everything before first _)
    parts = repo_name.split("_", 1)
    name = parts[1] if len(parts) > 1 else parts[0]
    # Remove trailing '-main' or '-master'
    name = re.sub(r'[-_](main|master)$', '', name)
    # Replace dashes/underscores with spaces and title case
    name = name.replace("-", " ").replace("_", " ")
    name = name.title()
    # Keep common tech terms uppercase
    for term in ["Ui", "Ai", "Css", "Js", "Api", "Crm", "Saas", "Cms", "Sdk", "Cli", "Seo"]:
        name = name.replace(term, term.upper())
    for term in ["Nextjs", "Reactjs", "Vuejs", "Nodejs"]:
        name = name.replace(term, term.replace("js", ".js"))
    name = name.replace("Next.JS", "Next.js").replace("React.JS", "React.js")
    return name.strip()

def remove_github_junk(target_dir):
    """Remove GitHub-specific files that expose the product as raw clones."""
    removed = 0
    for root, dirs, files in os.walk(target_dir, topdown=True):
        # Only clean top 2 levels
        depth = root.replace(target_dir, "").count(os.sep)
        if depth > 2:
            continue
        for name in dirs[:]:
            if name in GITHUB_JUNK:
                path = os.path.join(root, name)
                shutil.rmtree(path, ignore_errors=True)
                dirs.remove(name)
                removed += 1
        for name in files:
            if name in GITHUB_JUNK:
                path = os.path.join(root, name)
                try:
                    os.remove(path)
                    removed += 1
                except:
                    pass
    return removed

def detect_stack_quick(proj_path):
    """Quick stack detection from top-level files."""
    stack = []
    for item in os.listdir(proj_path):
        il = item.lower()
        if il in ("next.config.js", "next.config.ts", "next.config.mjs"):
            stack.append("Next.js")
        elif il in ("tailwind.config.js", "tailwind.config.ts"):
            stack.append("Tailwind CSS")
        elif il == "tsconfig.json":
            stack.append("TypeScript")
    # Check package.json for key deps
    pkg = os.path.join(proj_path, "package.json")
    if os.path.exists(pkg):
        try:
            with open(pkg, 'r', errors='ignore') as f:
                content = f.read()
            if "supabase" in content: stack.append("Supabase")
            if "stripe" in content: stack.append("Stripe")
            if "prisma" in content: stack.append("Prisma")
            if "framer-motion" in content: stack.append("Framer Motion")
            if "@radix" in content or "shadcn" in content: stack.append("Shadcn/Radix")
            if "openai" in content: stack.append("OpenAI")
            if "next-auth" in content or "@auth/" in content: stack.append("Auth.js")
        except:
            pass
    return list(dict.fromkeys(stack))[:6]

def generate_project_info(proj_path, clean_name, repo_meta):
    """Generate a PROJECT_INFO.md inside each project folder."""
    stars = repo_meta.get("stars", "N/A")
    category = repo_meta.get("category", "").replace("_", " ")
    orig_name = repo_meta.get("repo_name", "")
    
    # Detect stack
    # Walk into the first subfolder (GitHub extracts as repo-main/)
    actual_path = proj_path
    subdirs = [d for d in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, d))]
    if len(subdirs) == 1:
        actual_path = os.path.join(proj_path, subdirs[0])
    
    stack = detect_stack_quick(actual_path)
    stack_str = " · ".join(stack) if stack else "Web Development"
    
    # Find README content from original repo
    readme_content = ""
    for readme_name in ["README.md", "readme.md", "Readme.md"]:
        readme_path = os.path.join(actual_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', errors='ignore') as f:
                    readme_content = f.read()[:500]  # First 500 chars
            except:
                pass
            break
    
    # Extract first meaningful description line from README
    description = "Professional web development project."
    if readme_content:
        for line in readme_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("!") and not line.startswith("<") and len(line) > 20:
                description = line[:200]
                break
    
    info = f"""# {clean_name}

**Categoría:** {category}  
**Stack:** `{stack_str}`  
**Estrellas GitHub:** ⭐ {stars}  
**Licencia:** MIT (Uso comercial libre)

## Descripción
{description}

## Cómo Usar
1. Copia esta carpeta a tu workspace
2. Ejecuta `npm install` (o `pnpm install`)
3. Ejecuta `npm run dev`
4. Personaliza colores, textos y lógica según tu proyecto

## Stack Tecnológico
{chr(10).join(f"- {s}" for s in stack) if stack else "- Ver package.json para dependencias"}

---
*Parte de DevVault Pro 2026 — La librería privada más completa para desarrolladores web.*
"""
    info_path = os.path.join(proj_path, "PROJECT_INFO.md")
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(info)

def process_repos(json_file, output_base):
    with open(json_file, 'r') as f:
        repos = json.load(f)
        
    print(f"Processing {len(repos)} elite repositories...")
    
    success_count = 0
    total_size_mb = 0
    total_junk_removed = 0
    
    for repo in repos:
        category = repo.get("category", "Misc")
        repo_name = repo.get("repo_name", "").replace("/", "_")
        url1 = repo.get("download_url")
        url2 = repo.get("fallback_url")
        
        # CLEAN professional folder name
        clean_name = clean_project_name(repo_name)
        target_dir = os.path.join(output_base, f"[{category}]", clean_name)
        
        if os.path.exists(target_dir):
            continue
            
        temp_zip = f"{repo_name}.zip"
        
        print(f"Downloading: {clean_name}...")
        try:
            r = requests.get(url1, stream=True, timeout=60)
            if r.status_code == 404:
                r = requests.get(url2, stream=True, timeout=60)
                
            r.raise_for_status()
            
            with open(temp_zip, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            size_mb = os.path.getsize(temp_zip) / (1024 * 1024)
            total_size_mb += size_mb
            
            # Extract
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(temp_zip, 'r') as z:
                z.extractall(target_dir)
                
            os.remove(temp_zip)
            
            # CLEAN: Remove node_modules
            for root, dirs, files in os.walk(target_dir, topdown=False):
                for name in dirs:
                    if name == "node_modules" or name == ".next" or name == "dist":
                        shutil.rmtree(os.path.join(root, name), ignore_errors=True)
            
            # CLEAN: Remove GitHub junk files
            junk = remove_github_junk(target_dir)
            total_junk_removed += junk
            
            # GENERATE: PROJECT_INFO.md
            generate_project_info(target_dir, clean_name, repo)
                        
            success_count += 1
            print(f"  -> OK ({size_mb:.1f} MB, {junk} junk files removed)")
            
        except Exception as e:
            print(f"  -> Failed: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
                
        time.sleep(1)
        
    print(f"\nDone. Successfully processed {success_count} premium assets.")
    print(f"Total size: {total_size_mb:.1f} MB. Junk removed: {total_junk_removed} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', default="github_dev_assets.json")
    parser.add_argument('--output', default="God_Tier_Dev_Vault")
    
    args = parser.parse_args()
    if os.path.exists(args.json):
        process_repos(args.json, args.output)
    else:
        print("JSON data not found.")
