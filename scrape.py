"""
scrape.py - Scrapes USask program pages into data/ as .txt files + metadata.csv

Run once:  python scrape.py
"""
import os, csv, time, re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://programs.usask.ca"
LIST_URL = "https://programs.usask.ca/programs/list-of-programs.php"
OUT_DIR = "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

os.makedirs(OUT_DIR, exist_ok=True)

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def clean_filename(name):
    name = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"\s+", "_", name)[:80]

def infer_college(url):
    # the path segment after the domain is usually the college
    m = re.search(r"programs\.usask\.ca/+([a-z0-9-]+)/", url)
    if not m:
        return "Unknown"
    slug = m.group(1)
    mapping = {
        "arts-and-science": "Arts and Science",
        "engineering": "Engineering",
        "edwards": "Edwards School of Business",
        "agriculture-and-bioresources": "Agriculture and Bioresources",
        "education": "Education",
        "nursing": "Nursing",
        "pharmacy-nutrition": "Pharmacy and Nutrition",
        "medicine": "Medicine",
        "dentistry": "Dentistry",
        "law": "Law",
        "kinesiology": "Kinesiology",
        "veterinary-medicine": "Veterinary Medicine",
        "sens": "School of Environment and Sustainability",
        "grad-studies": "Graduate and Postdoctoral Studies",
    }
    return mapping.get(slug, slug.replace("-", " ").title())

def infer_level(url):
    return "Graduate" if "grad-studies" in url else "Undergraduate"

# --- Stage 1: collect program links from the list page ---
print("Fetching program list page...")
soup = get_soup(LIST_URL)

links = {}
for a in soup.select("a[href]"):
    href = a.get("href", "")
    text = a.get_text(strip=True)
    # keep only real program pages: end in index.php, live under a college path,
    # skip nav/util links and the cascade.usask.ca preview links
    if not text or len(text) < 3:
        continue
    if "index.php" not in href:
        continue
    if "/programs/" in href:        # nav pages, not program pages
        continue
    if "cascade.usask.ca" in href:  # broken preview links
        continue
    full = urljoin(BASE, href.replace("//", "/").replace("https:/", "https://"))
    # normalize accidental double slashes in path
    full = re.sub(r"(?<!:)//", "/", full)
    if full.startswith(BASE) and "index.php" in full:
        links[full] = text

print(f"Found {len(links)} candidate program links.")

# --- Stage 2: fetch each, save text + metadata ---
metadata = []
count, skipped = 0, 0
for url, name in sorted(links.items(), key=lambda kv: kv[1]):
    try:
        s = get_soup(url)
        main = s.find("main") or s.find("body")
        # remove nav, footer, scripts to reduce junk
        for tag in main.select("nav, footer, script, style, header"):
            tag.decompose()
        text = main.get_text(separator="\n", strip=True)
        # collapse big blank runs
        text = re.sub(r"\n{3,}", "\n\n", text)
        if len(text) < 250:
            skipped += 1
            continue
        college = infer_college(url)
        level = infer_level(url)
        fname = clean_filename(name) + ".txt"
        # avoid overwriting duplicates
        if os.path.exists(os.path.join(OUT_DIR, fname)):
            fname = clean_filename(name) + "_" + str(count) + ".txt"
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\nCollege: {college}\nLevel: {level}\nSource: {url}\n\n{text}")
        metadata.append({"filename": fname, "title": name,
                         "college": college, "level": level, "url": url})
        count += 1
        print(f"[{count}] {name}  ({college}, {level})")
        time.sleep(0.4)   # be polite
    except Exception as e:
        skipped += 1
        print(f"  skip {name}: {e}")

with open("metadata.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["filename", "title", "college", "level", "url"])
    w.writeheader()
    w.writerows(metadata)

print(f"\nDone. Saved {count} documents to {OUT_DIR}/, skipped {skipped}. metadata.csv written.")