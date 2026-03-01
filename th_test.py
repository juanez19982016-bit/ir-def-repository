import requests
import json

base_api = "https://tonehunt.org/api/v1"
r = requests.get(f"{base_api}/models?page=1&perPage=50&sortBy=newest")
data = r.json()
items = data.get("models", data)
print(f"Got {len(items)} items")

print(type(items), str(items)[:500])

    mid = item.get("id")
    dl = f"{base_api}/models/{mid}/download"
    print("Testing DL:", dl)
    dr = requests.get(dl, timeout=5)
    print("Code:", dr.status_code)
    print("Content-Disposition:", dr.headers.get("content-disposition", ""))
    print("Length:", len(dr.content))
    print("Content head:", dr.content[:100])
