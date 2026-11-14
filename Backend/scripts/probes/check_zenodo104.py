import json, ssl, urllib.request, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
url = "https://zenodo.org/api/records/17954508"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        data = json.loads(r.read().decode("utf-8"))
        files = data.get("files", [])
        print(f"Zenodo Record 17954508: Total files = {len(files)}")
        for f in files[:10]:
            print(f"  {f.get('key'):<40} {f.get('size', 0)/(1024*1024):>8.2f} MB")
except Exception as e:
    print("Zenodo probe error:", e)
