import requests
import json
import os
import time

def search_github_code(token):
    """
    Searches GitHub for MIT licensed elite UI components and AI boilerplates.
    Deep pagination to maximize the 15GB payload.
    """
    print("Initiating God-Tier GitHub Search for Developer Vault 2026...")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    else:
        print("Warning: Running without a token, rate limits will be tight.")
        
    # The elite 2026 stack queries (MIT License)
    queries = [
        "shadcn blocks dashboard tailwind react license:mit size:>50",
        "nextjs 15 boilerplate stripe supabase auth tailwind license:mit size:>50",
        "framer motion UI kit react tailwind license:mit size:>50",
        "react admin dashboard modern license:mit size:>100",
        "ai saas starter kit nextjs license:mit size:>100"
    ]
    
    all_repos = []
    seen = set()
    
    for query in queries:
        print(f"\nSearching for: {query}")
        page = 1
        
        # Deep pagination to get MASSIVE volume (up to 10 pages per query = 1000 results each)
        while page <= 10: 
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=100&page={page}"
            
            try:
                response = requests.get(url, headers=headers)
                
                if response.status_code == 403:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                    sleep_time = max(10, reset_time - time.time())
                    print(f"Rate limited. Sleeping for {sleep_time} seconds to respect API limits...")
                    time.sleep(sleep_time)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                if not items:
                    print("No more items found for this query.")
                    break
                    
                for item in items:
                    repo_id = item.get("id")
                    if repo_id in seen:
                        continue
                        
                    seen.add(repo_id)
                    repo_name = item.get("full_name")
                    stars = item.get("stargazers_count", 0)
                    
                    # Hyper-premium 2026 categorization
                    category = "React_Admin_Dashboards"
                    if "shadcn" in query:
                        category = "Shadcn_UI_Blocks_and_Kits"
                    elif "nextjs 15" in query or "ai saas" in query:
                        category = "Premium_SaaS_Boilerplates"
                    elif "framer" in query:
                        category = "Framer_Motion_UI_Kits"
                        
                    all_repos.append({
                        "repo_name": repo_name,
                        "stars": stars,
                        "category": category,
                        "download_url": f"https://github.com/{repo_name}/archive/refs/heads/main.zip",
                        "fallback_url": f"https://github.com/{repo_name}/archive/refs/heads/master.zip"
                    })
                
                print(f"Page {page}: Found {len(items)} repositories.")
                page += 1
                time.sleep(3) # Polite scraping delay
                
            except requests.exceptions.RequestException as e:
                print(f"Error on page {page}: {e}")
                break
                
    print(f"\nTotal unique hyper-premium repos found: {len(all_repos)}")
    
    with open("github_dev_assets.json", 'w') as f:
        json.dump(all_repos, f, indent=4)
        
    print("Saved results to github_dev_assets.json")
    return all_repos

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    search_github_code(token)
