import urllib.request, ssl, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
req = urllib.request.Request("https://pgda.gsfc.nasa.gov/products/78", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
    html = r.read().decode("utf-8", errors="ignore")
    for line in html.splitlines():
        if any(w in line.lower() for w in ["download", "href", "http", "ftp", "shackleton", "lola"]):
            print(line.strip())
