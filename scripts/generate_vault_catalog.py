"""
DevVault Pro V3: Generates INDICE.md files inside each category folder
and a master CATALOG.md at the root of the vault.
"""
import os
import json
import sys

def generate_indices(vault_dir, json_file):
    # Load repo metadata
    repos = []
    if os.path.exists(json_file):
        with open(json_file) as f:
            repos = json.load(f)
    
    # Build lookup: repo_name -> metadata
    lookup = {}
    for r in repos:
        key = r["repo_name"].replace("/", "_")
        lookup[key] = r
    
    # Walk each category folder
    categories = {}
    if not os.path.exists(vault_dir):
        print(f"Vault dir {vault_dir} not found!")
        return
    
    for cat_folder in sorted(os.listdir(vault_dir)):
        cat_path = os.path.join(vault_dir, cat_folder)
        if not os.path.isdir(cat_path):
            continue
        
        cat_name = cat_folder.strip("[]")
        projects = []
        
        for proj_folder in sorted(os.listdir(cat_path)):
            proj_path = os.path.join(cat_path, proj_folder)
            if not os.path.isdir(proj_path) or proj_folder == "__pycache__":
                continue
            
            meta = lookup.get(proj_folder, {})
            stars = meta.get("stars", "N/A")
            orig_name = meta.get("repo_name", proj_folder.replace("_", "/", 1))
            
            # Detect tech stack from files
            stack = detect_stack(proj_path)
            
            projects.append({
                "folder": proj_folder,
                "name": orig_name,
                "stars": stars,
                "stack": stack,
            })
        
        if projects:
            categories[cat_name] = projects
            # Write INDICE.md inside category folder
            write_category_index(cat_path, cat_name, projects)
    
    # Write master CATALOG.md
    write_master_catalog(vault_dir, categories)
    print(f"Generated indices for {len(categories)} categories.")

def detect_stack(proj_path):
    """Detect tech stack by looking at key files."""
    stack = []
    # Walk only top 2 levels to save time
    for root, dirs, files in os.walk(proj_path):
        depth = root.replace(proj_path, "").count(os.sep)
        if depth > 2:
            dirs.clear()
            continue
        for f in files:
            fl = f.lower()
            if fl == "next.config.js" or fl == "next.config.ts" or fl == "next.config.mjs":
                if "Next.js" not in stack: stack.append("Next.js")
            elif fl == "tailwind.config.js" or fl == "tailwind.config.ts":
                if "Tailwind" not in stack: stack.append("Tailwind")
            elif fl == "tsconfig.json":
                if "TypeScript" not in stack: stack.append("TypeScript")
            elif fl == "package.json":
                if "Node.js" not in stack: stack.append("Node.js")
                # Quick check for key deps
                try:
                    with open(os.path.join(root, f), 'r', errors='ignore') as pf:
                        content = pf.read()
                        if "supabase" in content and "Supabase" not in stack:
                            stack.append("Supabase")
                        if "stripe" in content and "Stripe" not in stack:
                            stack.append("Stripe")
                        if "prisma" in content and "Prisma" not in stack:
                            stack.append("Prisma")
                        if "framer-motion" in content and "Framer Motion" not in stack:
                            stack.append("Framer Motion")
                        if "shadcn" in content or "@radix" in content:
                            if "Shadcn/Radix" not in stack: stack.append("Shadcn/Radix")
                        if "openai" in content and "OpenAI" not in stack:
                            stack.append("OpenAI")
                        if "next-auth" in content or "auth" in content.lower():
                            if "Auth" not in stack: stack.append("Auth")
                except:
                    pass
    return stack[:6]  # Limit to 6 tags

def write_category_index(cat_path, cat_name, projects):
    """Write INDICE.md inside a category folder."""
    lines = [
        f"# 📂 {cat_name.replace('_', ' ')}\n",
        f"**{len(projects)} proyectos profesionales en esta categoría.**\n",
        "---\n",
        "| # | Proyecto | ⭐ Stars | Stack Tecnológico |",
        "|---|---------|---------|-------------------|",
    ]
    for i, p in enumerate(projects, 1):
        stack_str = ", ".join(p["stack"]) if p["stack"] else "Varios"
        lines.append(f"| {i} | `{p['name']}` | {p['stars']} | {stack_str} |")
    
    lines.append("\n---")
    lines.append("*Todos los proyectos tienen Licencia MIT (uso comercial libre).*\n")
    
    with open(os.path.join(cat_path, "INDICE.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def write_master_catalog(vault_dir, categories):
    """Write the master CATALOG.md at vault root."""
    total = sum(len(p) for p in categories.values())
    lines = [
        "# 🏆 DevVault Pro 2026 — Catálogo Oficial\n",
        f"**{total} proyectos profesionales** organizados en **{len(categories)} categorías**.\n",
        "Todos con Licencia MIT para uso comercial sin restricciones.\n",
        "---\n",
        "## 📊 Resumen por Categoría\n",
        "| Categoría | Proyectos |",
        "|-----------|-----------|",
    ]
    for cat, projs in sorted(categories.items()):
        lines.append(f"| {cat.replace('_', ' ')} | {len(projs)} |")
    
    lines.append(f"| **TOTAL** | **{total}** |")
    lines.append("\n---\n")
    
    for cat, projs in sorted(categories.items()):
        lines.append(f"## 📂 {cat.replace('_', ' ')}\n")
        for i, p in enumerate(projs, 1):
            stack_str = " · ".join(p["stack"]) if p["stack"] else ""
            lines.append(f"**{i}. {p['name']}** — ⭐ {p['stars']}  ")
            if stack_str:
                lines.append(f"`{stack_str}`\n")
            else:
                lines.append("")
        lines.append("---\n")
    
    lines.append("*DevVault Pro 2026 — La librería privada más completa para desarrolladores web.*\n")
    
    with open(os.path.join(vault_dir, "CATALOG.md"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Master catalog written: {total} projects across {len(categories)} categories.")

if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else "God_Tier_Dev_Vault"
    json_f = sys.argv[2] if len(sys.argv) > 2 else "github_dev_assets.json"
    generate_indices(vault, json_f)
