"""
DevVault Pro V4: Generates INDICE.md per category and CATALOG.md.
Works with CLEAN folder names by walking the actual directory structure.
"""
import os
import json
import sys

def detect_stack(proj_path):
    stack = []
    try:
        items = os.listdir(proj_path)
    except:
        return stack
    for item in items:
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
            if "react" in c and "React" not in stack: stack.append("React")
        except:
            pass
    return list(dict.fromkeys(stack))[:6]

def generate_indices(vault_dir, mapping_file):
    # Load name mapping if exists
    mapping = {}
    if os.path.exists(mapping_file):
        with open(mapping_file) as f:
            mapping = json.load(f)
    
    categories = {}
    
    for cat_folder in sorted(os.listdir(vault_dir)):
        cat_path = os.path.join(vault_dir, cat_folder)
        if not os.path.isdir(cat_path) or cat_folder.startswith("[BONUS]"):
            continue
        
        cat_name = cat_folder.strip("[]")
        projects = []
        
        for proj_folder in sorted(os.listdir(cat_path)):
            proj_path = os.path.join(cat_path, proj_folder)
            if not os.path.isdir(proj_path):
                continue
            
            # Look up metadata from mapping (uses clean name as key)
            meta = mapping.get(proj_folder, {})
            stars = meta.get("stars", "—")
            
            # Detect stack from actual files
            stack = detect_stack(proj_path)
            
            projects.append({
                "folder": proj_folder,
                "stars": stars,
                "stack": stack,
            })
        
        if projects:
            categories[cat_name] = projects
            write_category_index(cat_path, cat_name, projects)
    
    write_master_catalog(vault_dir, categories)
    print(f"Generated indices for {len(categories)} categories.")

def write_category_index(cat_path, cat_name, projects):
    lines = [
        f"# 📂 {cat_name.replace('_', ' ')}\n",
        f"**{len(projects)} projects in this category.**\n",
        "---\n",
        "| # | Project | ⭐ Stars | Tech Stack |",
        "|---|---------|---------|------------|",
    ]
    for i, p in enumerate(projects, 1):
        stack_str = ", ".join(p["stack"]) if p["stack"] else "—"
        lines.append(f"| {i} | **{p['folder']}** | {p['stars']} | {stack_str} |")
    
    lines.append("\n---")
    lines.append("*All projects are MIT licensed for commercial use.*\n")
    
    with open(os.path.join(cat_path, "INDICE.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def write_master_catalog(vault_dir, categories):
    total = sum(len(p) for p in categories.values())
    lines = [
        "# 🏆 DevVault Pro 2026 — Official Catalog\n",
        f"**{total} professional projects** across **{len(categories)} categories**.\n",
        "All MIT licensed for unrestricted commercial use.\n",
        "---\n",
        "## 📊 Summary\n",
        "| Category | Projects |",
        "|----------|----------|",
    ]
    for cat, projs in sorted(categories.items()):
        lines.append(f"| {cat.replace('_', ' ')} | {len(projs)} |")
    lines.append(f"| **TOTAL** | **{total}** |\n")
    lines.append("---\n")
    
    for cat, projs in sorted(categories.items()):
        lines.append(f"## 📂 {cat.replace('_', ' ')}\n")
        for i, p in enumerate(projs, 1):
            stack_str = " · ".join(p["stack"]) if p["stack"] else ""
            star_str = f"⭐ {p['stars']}" if p['stars'] != "—" else ""
            lines.append(f"**{i}. {p['folder']}** {star_str}  ")
            if stack_str:
                lines.append(f"`{stack_str}`\n")
            else:
                lines.append("")
        lines.append("---\n")
    
    lines.append("*DevVault Pro 2026 — The most complete private library for web developers.*\n")
    
    with open(os.path.join(vault_dir, "CATALOG.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Master catalog: {total} projects, {len(categories)} categories.")

if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else "God_Tier_Dev_Vault"
    mapping = sys.argv[2] if len(sys.argv) > 2 else "name_mapping.json"
    generate_indices(vault, mapping)
