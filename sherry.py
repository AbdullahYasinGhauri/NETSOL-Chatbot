from __future__ import annotations
import json, re, sys, time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
from bs4 import BeautifulSoup
import markdownify
 
# ---------------------------- CONFIG ----------------------------------------
BASE            = "https://netsoltech.com"
SITEMAP_INDEX   = "https://netsoltech.com/sitemap-index.xml"
ALLOWED_DOMAINS = {"netsoltech.com", "www.netsoltech.com"}
OUTPUT_DIR      = Path("scrape_output")
WRITE_MARKDOWN  = True
RESPECT_ROBOTS  = False
MAX_PAGES       = 1000
 
# --- URL scoping ---
LOCALE_RE = re.compile(r"^[a-z]{2}(-[a-z]{2,3})?$")   # ar, fr, en-gb, zh-cn ... = locale dupes
INCLUDE_BLOG = False
BLOG_PREFIXES = ("blog",)
BLOG_WHITELIST = (
    
)
BLOG_DENY = ("hackathon","-is-at-","-is-a-","-conference","-summit","-convention",
             "womens-week","mental-health","fireside-chat","gearing-up","silver-sponsor")
 
REQUEST_DELAY   = 1.0
TIMEOUT         = 30
USER_AGENT      = "RAG-ingest-bot/1.0 (internal knowledge base)"
 
SCRAPE          = True
CHUNK           = True
CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP   = 200
DEDUP_MAX_REPEAT = 5
MIN_CHUNK_CHARS  = 40
 
# --- rendering / language forcing ---
FORCE_PLAYWRIGHT   = True
RENDER_WAIT_MS     = 3000
FORCE_ENGLISH      = True
ENGLISH_PREFIX     = "en-gb"          # explicit English route the site actually serves
I18N_COOKIE_VALUE  = "en-us"          # Nuxt i18n default locale code (not "en")
 
# Requests that carry country/locale detection. Aborting them keeps the English SSR default.
GEO_BLOCK = re.compile(
    r"(ip-?api|ipapi|ipinfo|ipgeolocation|ipdata|geoip|geo-?location|"
    r"cdn-cgi/trace|/api/geo|/api/locale|/api/country|country-?code|/geoip|/detect)",
    re.I,
)
 
EXTRA_URLS = []
# ----------------------------------------------------------------------------
 
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_PATH  = OUTPUT_DIR / "pages.jsonl"
CHUNKS_PATH = OUTPUT_DIR / "chunks.jsonl"
 
def log(m): print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)
 
def normalize(url):
    url, _ = urldefrag(url)
    p = urlparse(url)
    host = p.netloc.lower().removeprefix("www.")
    return f"{p.scheme}://{host}{p.path.rstrip('/') or '/'}"
 
def same_site(url):
    h = urlparse(url).netloc.lower().removeprefix("www.")
    return h in {d.removeprefix("www.") for d in ALLOWED_DOMAINS}
 
def in_scope(url):
    path = urlparse(url).path.strip("/")
    segs = path.split("/")
    first = segs[0] if segs and segs[0] else ""
    if LOCALE_RE.match(first):
        return False
    if not INCLUDE_BLOG and first in BLOG_PREFIXES:
        if any(d in path for d in BLOG_DENY): return False
        return any(k in path for k in BLOG_WHITELIST)
    return True
 
def english_url(url):
    """Insert the explicit English locale prefix, e.g. /products/x -> /en-gb/products/x."""
    p = urlparse(url)
    path = p.path if p.path.startswith("/") else "/" + p.path
    newpath = f"/{ENGLISH_PREFIX}{path}".rstrip("/") or f"/{ENGLISH_PREFIX}"
    return f"{p.scheme}://{p.netloc}{newpath}"
 
def load_robots(client):
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = client.get(urljoin(BASE, "/robots.txt"))
        if r.status_code == 200: rp.parse(r.text.splitlines()); log("robots.txt loaded")
        else: rp.allow_all = True
    except Exception: rp.allow_all = True
    return rp
 
def parse_sitemap(text):
    soup = BeautifulSoup(text, "lxml-xml")
    return soup.find("sitemapindex") is not None, [l.get_text(strip=True) for l in soup.find_all("loc")]
 
def discover(client):
    urls, to_do, seen = [], [SITEMAP_INDEX], set()
    while to_do:
        sm = to_do.pop()
        if sm in seen: continue
        seen.add(sm)
        try:
            r = client.get(sm)
            if r.status_code != 200: continue
            is_index, locs = parse_sitemap(r.text)
        except Exception as e:
            log(f"sitemap {sm} error: {e}"); continue
        if is_index: to_do += locs
        else: urls += [normalize(u) for u in locs if same_site(normalize(u)) and in_scope(normalize(u))]
    return sorted(set(urls))
 
def extract_clean(html, url):
    """BeautifulSoup + markdownify: preserves lists/tables/grids trafilatura drops."""
    soup = BeautifulSoup(html, "lxml")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    for tag in soup(["script","style","noscript","header","footer","nav","svg","button"]):
        tag.decompose()
    content_area = soup.find("main") or soup.find("body") or soup
    text = markdownify.markdownify(str(content_area), heading_style="ATX", strip=["a","img"])
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s*\|\s*(?=\n|$)", "", text)
    return title, text.strip()
 
def fetch_static(url, client):
    try:
        r = client.get(url)
        if r.status_code == 200 and "html" in r.headers.get("content-type", ""): return r.text
    except Exception as e: log(f"  static error: {e}")
    return None
 
# --- Playwright rendering -----------------------------------------------------
def _route_handler(route):
    if GEO_BLOCK.search(route.request.url):
        return route.abort()
    return route.continue_()
 
def _render_once(context, url):
    """Render one URL, return (html, html_lang_lowercased)."""
    pg = context.new_page()
    # low-probability lever, but free: pin navigator language before hydration
    pg.add_init_script(
        "Object.defineProperty(navigator,'language',{get:()=>'en-US'});"
        "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});"
    )
    # domcontentloaded (NOT networkidle: this site runs GTM and would hang)
    pg.goto(url, wait_until="networkidle", timeout=TIMEOUT*1000)
    # scroll to trigger lazy components
    pg.evaluate("""async () => { await new Promise(res => {
        let y=0; const d=500; const t=setInterval(()=>{ const h=document.body.scrollHeight;
        window.scrollBy(0,d); y+=d; if(y>=h-window.innerHeight){clearInterval(t);res();} },150); }); }""")
    # expand accordions/tabs
    pg.evaluate("""() => {
        document.querySelectorAll('button[aria-expanded="false"]').forEach(b=>{try{b.click()}catch(e){}});
        document.querySelectorAll('.accordion-button,.tab-title,.faq-question').forEach(el=>{try{el.click()}catch(e){}});
    }""")
    pg.wait_for_timeout(RENDER_WAIT_MS)
    lang = (pg.get_attribute("html", "lang") or "").lower()
    html = pg.content()
    pg.close()
    return html, lang
 
def fetch_rendered(url, browser):
    """
    Render with networkidle (full JS-loaded data). If the page comes back
    non-English (IP-based locale switch), re-render the EXPLICIT /en-gb/ route,
    which is the only lever that reliably forces English. If /en-gb/ ALSO returns
    non-English, that is an egress-IP problem: log it, keep canonical, move on.
    """
    try:
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        html, lang = _render_once(context, url)                 # networkidle => full data
        p = urlparse(url).path.strip("/")
        first = p.split("/")[0] if p else ""
        already_prefixed = bool(LOCALE_RE.match(first))
        if lang and not lang.startswith("en") and not already_prefixed:
            en_url = english_url(url)                            # e.g. /products/x -> /en-gb/products/x
            log(f"  lang='{lang}' -> re-rendering English route {en_url}")
            try:
                html2, lang2 = _render_once(context, en_url)
                if lang2.startswith("en") and len(html2) > 500:
                    html = html2                                # English AND full data
                else:
                    log(f"  LANG WARNING: /en-gb/ returned lang='{lang2}' for {url} "
                        f"-> egress IP is forcing the locale; only a proxy / different "
                        f"run location fixes this, no code change will.")
            except Exception as e:
                log(f"  LANG WARNING: /en-gb/ render failed for {url} ({e}); kept canonical")
        context.close()
        return html
    except Exception as e:
        log(f"  playwright error: {e}")
        return None
 
def chunk_markdown(text, max_chars=CHUNK_MAX_CHARS, overlap=CHUNK_OVERLAP):
    lines = text.split("\n"); sections=[]; cur=[]; head=""
    def flush():
        body="\n".join(cur).strip()
        if body: sections.append((head, body))
    for ln in lines:
        if re.match(r"^#{1,6}\s", ln): flush(); cur=[]; head=ln.lstrip("#").strip()
        else: cur.append(ln)
    flush()
    def window(s, size, ov):
        out=[]; i=0
        while i < len(s):
            out.append(s[i:i+size])
            if i+size >= len(s): break
            i += max(1, size-ov)
        return out
    chunks=[]
    for h, body in sections:
        prefix=f"{h}\n\n" if h else ""; budget=max(50, max_chars-len(prefix)); atoms=[]
        for para in [x for x in body.split("\n\n") if x.strip()]:
            atoms += [para] if len(para)<=budget else window(para, budget, overlap)
        buf=""
        for a in atoms:
            if buf and len(buf)+len(a)+2 > budget: chunks.append((prefix+buf).strip()); buf=a
            else: buf=(buf+"\n\n"+a) if buf else a
        if buf.strip(): chunks.append((prefix+buf).strip())
    return [c for c in chunks if c.strip()]
 
def run_scrape():
    browser=_pw=None
    if FORCE_PLAYWRIGHT:
        try:
            from playwright.sync_api import sync_playwright
            _pw = sync_playwright().start(); browser = _pw.chromium.launch(headless=True)
            log("playwright browser ready")
        except Exception as e:
            log(f"playwright unavailable ({e}); static only"); browser=None
    try:
        with httpx.Client(timeout=TIMEOUT,
                          headers={"User-Agent":USER_AGENT,"Accept-Language":"en-US,en;q=0.9"},
                          follow_redirects=True) as c:
            rp = load_robots(c) if RESPECT_ROBOTS else None
            urls = discover(c)
            urls = sorted(set(urls) | {normalize(u) for u in EXTRA_URLS})
            log(f"{len(urls)} URLs ({len(EXTRA_URLS)} manual)")
            if RESPECT_ROBOTS:
                before=len(urls); urls=[u for u in urls if rp.can_fetch(USER_AGENT,u)]
                if before-len(urls): log(f"robots blocked {before-len(urls)}")
            urls=urls[:MAX_PAGES]; n=0; nonenglish=0
            with open(JSONL_PATH,"w",encoding="utf-8") as out:
                for i,url in enumerate(urls,1):
                    log(f"({i}/{len(urls)}) {url}")
                    title=text=""; method=""
                    if browser:
                        html=fetch_rendered(url, browser); method="playwright"
                        if not html: html=fetch_static(url,c); method="static"
                    else:
                        html=fetch_static(url,c); method="static"
                    if html: title,text=extract_clean(html,url)
                    if not text: log("  no text; skip"); time.sleep(REQUEST_DELAY); continue
                    out.write(json.dumps({"url":url,"title":title,"text":text,
                        "word_count":len(text.split()),"method":method,
                        "fetched_at":datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+"\n"); n+=1
                    if WRITE_MARKDOWN:
                        slug=re.sub(r"[^\w\-]+","_",urlparse(url).path.strip("/")) or "index"
                        (OUTPUT_DIR/f"{slug}.md").write_text(f"# {title}\n\nSource: {url}\n\n{text}",encoding="utf-8")
                    time.sleep(REQUEST_DELAY)
            log(f"scrape done: {n} pages -> {JSONL_PATH}")
    finally:
        if browser: browser.close()
        if _pw: _pw.stop()
 
def run_chunk():
    from collections import Counter
    if not JSONL_PATH.exists(): log("no pages.jsonl; scrape first"); return
    cand=[]
    for line in open(JSONL_PATH,encoding="utf-8"):
        r=json.loads(line)
        slug=re.sub(r"[^\w\-]+","_",urlparse(r["url"]).path.strip("/")) or "index"
        for j,ch in enumerate(chunk_markdown(r["text"])):
            cand.append((slug,r["url"],r["title"],j,ch.strip()))
    freq=Counter(c[4] for c in cand)
    kept=0; dd=0; ds=0
    with open(CHUNKS_PATH,"w",encoding="utf-8") as out:
        for slug,url,title,j,ch in cand:
            if freq[ch] > DEDUP_MAX_REPEAT: dd+=1; continue
            if len(ch) < MIN_CHUNK_CHARS:   ds+=1; continue
            out.write(json.dumps({"id":f"{slug}#{j}","url":url,"title":title,
                "chunk_index":j,"text":ch,"char_count":len(ch)},ensure_ascii=False)+"\n"); kept+=1
    log(f"chunking done: {kept} chunks kept ({dd} boilerplate + {ds} short dropped) -> {CHUNKS_PATH}")
 
if __name__ == "__main__":
    try:
        if SCRAPE: run_scrape()
        if CHUNK:  run_chunk()
    except KeyboardInterrupt:
        log("interrupted"); sys.exit(1)