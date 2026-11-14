import urllib.request, ssl, re, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
req = urllib.request.Request("https://pgda.gsfc.nasa.gov/products/78", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
    html = r.read().decode("utf-8", errors="ignore")

# Find all hrefs
links = re.findall(r'href=[\'"]?([^\'" >]+\.tif)[\'"]?', html, re.IGNORECASE)
main_links = [l for l in links if "clone" not in l.lower()]
print(f"Total main GeoTIFFs (excluding clones): {len(main_links)}")
for l in sorted(set(main_links)):
    print(l)
