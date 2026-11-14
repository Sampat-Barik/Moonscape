import ssl
import urllib.request

ctx = ssl.create_default_context()
base = 'https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/'
files = [
    'LDEM_80S_80MPP_ADJ.TIF',
    'LDSM_80S_80MPP_ADJ.TIF',
    'LDEC_80S_80MPP_ADJ.TIF',
    'LDEM_80S_80MPP_ADJ_ERR.TIF',
    'LDEM_80S_80MPP_ADJ_EFFRES.TIF',
    'LDSM_80S_80MPP_ADJ_ERR.TIF',
]
total_bytes = 0
for f in files:
    url = base + f
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            cl = int(r.headers.get('Content-Length', 0))
            total_bytes += cl
            ranges = r.headers.get('Accept-Ranges', 'none')
            print(f"{f:<32} {r.status}  {cl / (1024*1024):>8.2f} MB  Ranges: {ranges}")
    except Exception as e:
        print(f"{f:<32} ERROR: {e}")
print(f"Total for all 6 files: {total_bytes / (1024*1024*1024):.2f} GB ({total_bytes} bytes)")
