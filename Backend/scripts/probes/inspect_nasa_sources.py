import re
import ssl
import urllib.request
import certifi

CTX = ssl.create_default_context(cafile=certifi.where())
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MoonscapeInspector/2.0"}


def get_links(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
            pattern = re.compile(r'href=["\']([^"\']+)["\']')
            return sorted(set(pattern.findall(html)))
    except Exception as e:
        print(f"Error {url}: {e}")
        return []


if __name__ == "__main__":
    print("=== LOLA 5mpp Directory (Product 78) ===")
    p78_files = get_links("https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/")
    print(f"Total entries: {len(p78_files)}")
    for f in p78_files:
        if any(w in f.lower() for w in ["shackleton", "connect", "nobile", "gerlache", "malapert", ".tif", ".zip"]):
            print(" ", f)

    print("\n=== Diviner Polar Data (PDS) ===")
    div_files = get_links("https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/data/gcp/")
    print(f"Diviner GCP directory count: {len(div_files)}")
    for f in div_files:
        if any(w in f.lower() for w in ["sp", "south", "polar", "tbol", "tb"]):
            print(" ", f)

    print("\n=== LROC WAC Polar Mosaics ===")
    wac_files = get_links("https://data.lroc.im-ldi.com/lroc/view_rdr/WAC_GLOBAL/")
    for f in wac_files:
        if any(w in f.lower() for w in ["sp", "south", "pole", "polar"]):
            print(" ", f)
