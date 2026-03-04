import requests
import json
import os
import time

# =============================================================================
# CURATED LIST: The 100+ most famous MIT/Open-Source repos for web developers
# These are downloaded DIRECTLY, no search needed. Guaranteed high quality.
# =============================================================================
CURATED_REPOS = [
    # --- SHADCN / UI SYSTEMS (all MIT) ---
    {"repo_name": "shadcn-ui/ui", "category": "Shadcn_UI_Blocks_and_Kits", "stars": 80000},
    {"repo_name": "shadcn-ui/taxonomy", "category": "Premium_SaaS_Boilerplates", "stars": 18000},
    {"repo_name": "shadcn-ui/next-template", "category": "Premium_SaaS_Boilerplates", "stars": 5000},
    {"repo_name": "mickasmt/next-saas-stripe-starter", "category": "Premium_SaaS_Boilerplates", "stars": 4000},
    {"repo_name": "sadmann7/shadcn-table", "category": "Shadcn_UI_Blocks_and_Kits", "stars": 3000},
    {"repo_name": "tremorlabs/tremor", "category": "React_Admin_Dashboards", "stars": 16000},
    {"repo_name": "pacocoursey/cmdk", "category": "Shadcn_UI_Blocks_and_Kits", "stars": 9000},
    # --- NEXT.JS BOILERPLATES (MIT only) ---
    {"repo_name": "steven-tey/dub", "category": "Premium_SaaS_Boilerplates", "stars": 18000},
    {"repo_name": "vercel/commerce", "category": "Ecommerce_Starter_Kits", "stars": 11000},
    {"repo_name": "vercel/platforms", "category": "Premium_SaaS_Boilerplates", "stars": 5000},
    {"repo_name": "vercel/ai-chatbot", "category": "AI_SaaS_and_Chatbots", "stars": 7000},
    {"repo_name": "mckaywrigley/chatbot-ui", "category": "AI_SaaS_and_Chatbots", "stars": 28000},
    {"repo_name": "leerob/leerob.io", "category": "Portfolio_and_Blog_Templates", "stars": 7000},
    {"repo_name": "timlrx/tailwind-nextjs-starter-blog", "category": "Portfolio_and_Blog_Templates", "stars": 8000},
    {"repo_name": "chronark/highstorm", "category": "Premium_SaaS_Boilerplates", "stars": 3000},
    {"repo_name": "sadmann7/skateshop", "category": "Ecommerce_Starter_Kits", "stars": 3500},
    {"repo_name": "ixartz/SaaS-Boilerplate", "category": "Premium_SaaS_Boilerplates", "stars": 4000},
    {"repo_name": "ixartz/Next-js-Boilerplate", "category": "Premium_SaaS_Boilerplates", "stars": 9000},
    {"repo_name": "Blazity/next-enterprise", "category": "Premium_SaaS_Boilerplates", "stars": 6000},
    {"repo_name": "t3-oss/create-t3-app", "category": "Premium_SaaS_Boilerplates", "stars": 25000},
    # --- DASHBOARDS (MIT) ---
    {"repo_name": "horizon-ui/horizon-ui-chakra", "category": "React_Admin_Dashboards", "stars": 2500},
    {"repo_name": "marmelab/react-admin", "category": "React_Admin_Dashboards", "stars": 25000},
    {"repo_name": "refinedev/refine", "category": "React_Admin_Dashboards", "stars": 28000},
    {"repo_name": "TanStack/table", "category": "React_Admin_Dashboards", "stars": 25000},
    # --- FRAMER MOTION / ANIMATIONS (MIT) ---
    {"repo_name": "framer/motion", "category": "Framer_Motion_UI_Kits", "stars": 24000},
    {"repo_name": "ibelick/motion-primitives", "category": "Framer_Motion_UI_Kits", "stars": 3000},
    {"repo_name": "magicuidesign/magicui", "category": "Framer_Motion_UI_Kits", "stars": 5000},
    # --- TAILWIND COMPONENT LIBRARIES (MIT) ---
    {"repo_name": "saadeghi/daisyui", "category": "Tailwind_Component_Libraries", "stars": 33000},
    {"repo_name": "preline/preline", "category": "Tailwind_Component_Libraries", "stars": 5000},
    {"repo_name": "themesberg/flowbite", "category": "Tailwind_Component_Libraries", "stars": 8000},
    {"repo_name": "konstaui/konsta", "category": "Tailwind_Component_Libraries", "stars": 3000},
    {"repo_name": "sailboatui/sailboatui", "category": "Tailwind_Component_Libraries", "stars": 1500},
    {"repo_name": "creativetimofficial/material-tailwind", "category": "Tailwind_Component_Libraries", "stars": 4000},
    # --- E-COMMERCE (MIT only) ---
    {"repo_name": "medusajs/medusa", "category": "Ecommerce_Starter_Kits", "stars": 25000},
    {"repo_name": "vercel/commerce", "category": "Ecommerce_Starter_Kits", "stars": 11000},
    # --- PORTFOLIO / BLOG (MIT) ---
    {"repo_name": "craftzdog/craftzdog-homepage", "category": "Portfolio_and_Blog_Templates", "stars": 5000},
    {"repo_name": "dillionverma/portfolio", "category": "Portfolio_and_Blog_Templates", "stars": 2000},
    {"repo_name": "chronark/chronark.com", "category": "Portfolio_and_Blog_Templates", "stars": 1500},
    # --- CRM / BUSINESS (MIT) ---
    {"repo_name": "twentyhq/twenty", "category": "CRM_and_Business_Tools", "stars": 20000},
    {"repo_name": "documenso/documenso", "category": "CRM_and_Business_Tools", "stars": 8000},
    # --- AUTH (MIT/ISC) ---
    {"repo_name": "nextauthjs/next-auth", "category": "Auth_and_Payment_Modules", "stars": 24000},
    {"repo_name": "lucia-auth/lucia", "category": "Auth_and_Payment_Modules", "stars": 9000},
    # --- LANDING PAGES (MIT) ---
    {"repo_name": "cruip/open-react-template", "category": "Landing_Pages_High_Conversion", "stars": 2500},
    {"repo_name": "cruip/tailwind-landing-page-template", "category": "Landing_Pages_High_Conversion", "stars": 3000},
]

def search_github_code(token):
    print("=== DevVault Pro V2: Ultra-Premium Scraper ===")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # 15 elite search queries (V2 expansion)
    queries = [
        "shadcn blocks dashboard tailwind react license:mit stars:>10",
        "nextjs 15 boilerplate stripe supabase auth license:mit stars:>10",
        "framer motion UI kit react tailwind license:mit stars:>10",
        "react admin dashboard modern license:mit stars:>10",
        "ai saas starter kit nextjs license:mit stars:>10",
        "nextjs ecommerce template tailwind license:mit stars:>10",
        "react portfolio template modern license:mit stars:>10",
        "nextjs blog template mdx tailwind license:mit stars:>10",
        "invoice generator react nextjs license:mit stars:>10",
        "crm dashboard react tailwind license:mit stars:>10",
        "ai chatbot nextjs openai license:mit stars:>10",
        "nextjs authentication starter license:mit stars:>10",
        "tailwind landing page template license:mit stars:>10",
        "react table dashboard analytics license:mit stars:>10",
        "nextjs multi-tenant saas license:mit stars:>10",
    ]
    
    all_repos = []
    seen = set()
    
    # Step 1: Add all curated repos first (guaranteed quality)
    print(f"\n--- Loading {len(CURATED_REPOS)} curated premium repos ---")
    for repo in CURATED_REPOS:
        repo_name = repo["repo_name"]
        seen.add(repo_name)
        all_repos.append({
            "repo_name": repo_name,
            "stars": repo["stars"],
            "category": repo["category"],
            "download_url": f"https://github.com/{repo_name}/archive/refs/heads/main.zip",
            "fallback_url": f"https://github.com/{repo_name}/archive/refs/heads/master.zip"
        })
    print(f"Loaded {len(all_repos)} curated repos.")
    
    # Step 2: Search GitHub API for more
    for query in queries:
        print(f"\nSearching: {query}")
        page = 1
        while page <= 5:
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=100&page={page}"
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 403:
                    reset = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                    sleep_t = max(10, reset - time.time())
                    print(f"Rate limited. Sleeping {sleep_t}s...")
                    time.sleep(sleep_t)
                    continue
                response.raise_for_status()
                items = response.json().get("items", [])
                if not items:
                    break
                for item in items:
                    name = item.get("full_name")
                    stars = item.get("stargazers_count", 0)
                    if name in seen or stars < 10:
                        continue
                    seen.add(name)
                    cat = "React_Admin_Dashboards"
                    q = query.lower()
                    if "shadcn" in q: cat = "Shadcn_UI_Blocks_and_Kits"
                    elif "nextjs 15" in q or "saas" in q or "multi-tenant" in q: cat = "Premium_SaaS_Boilerplates"
                    elif "framer" in q: cat = "Framer_Motion_UI_Kits"
                    elif "ecommerce" in q: cat = "Ecommerce_Starter_Kits"
                    elif "portfolio" in q: cat = "Portfolio_and_Blog_Templates"
                    elif "blog" in q: cat = "Portfolio_and_Blog_Templates"
                    elif "invoice" in q or "crm" in q: cat = "CRM_and_Business_Tools"
                    elif "chatbot" in q or "ai" in q: cat = "AI_SaaS_and_Chatbots"
                    elif "auth" in q: cat = "Auth_and_Payment_Modules"
                    elif "landing" in q: cat = "Landing_Pages_High_Conversion"
                    elif "table" in q or "analytics" in q: cat = "React_Admin_Dashboards"
                    all_repos.append({
                        "repo_name": name, "stars": stars, "category": cat,
                        "download_url": f"https://github.com/{name}/archive/refs/heads/main.zip",
                        "fallback_url": f"https://github.com/{name}/archive/refs/heads/master.zip"
                    })
                print(f"  Page {page}: +{len(items)} repos")
                page += 1
                time.sleep(3)
            except Exception as e:
                print(f"  Error: {e}")
                break
                
    print(f"\n=== TOTAL unique repos: {len(all_repos)} ===")
    with open("github_dev_assets.json", 'w') as f:
        json.dump(all_repos, f, indent=2)
    return all_repos

if __name__ == "__main__":
    search_github_code(os.environ.get("GITHUB_TOKEN"))
