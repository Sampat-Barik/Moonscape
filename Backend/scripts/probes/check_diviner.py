import urllib.request, ssl, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
url = "https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/catalog/dataset.cat"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        text = r.read().decode("utf-8", errors="ignore")
        print("Diviner dataset.cat found! Length:", len(text))
        for line in text.splitlines()[:20]:
            print(line)
except Exception as e:
    print("Diviner probe error:", e)
