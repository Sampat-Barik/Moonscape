import urllib.request, ssl, certifi

ctx = ssl.create_default_context(cafile=certifi.where())
files = [
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif",
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slp.tif",
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_ldec.tif",
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_toterr.tif",
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_slperr.tif"
]
for u in files:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            cl = int(r.headers.get("Content-Length", 0))
            print(f"{u.split('/')[-1]:<35} {r.status} {cl / (1024*1024):>8.2f} MB  Ranges: {r.headers.get('Accept-Ranges')}")
    except Exception as e:
        print(f"Error {u}: {e}")
