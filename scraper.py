from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

EXCLUDED_PATHS = [
    "/blog", "/blogs", "/insights", "/careers", "/career",
    "/press", "/media", "/podcasts", "/podcast",
    "/webinars", "/webinar", "/investor",
    "/downloads", "/whitepapers",
    "/ebooks",
]


def normalize_url(url):
    """
    Normalize a URL while preserving the original hostname.
    Removes query params, fragments, and trailing slash -- including the
    bare-domain vs trailing-slash root case (e.g. "example.com" and
    "example.com/" now normalize to the same string).
    """
    parsed = urlparse(url)
    parsed = parsed._replace(query="", fragment="")

    path = parsed.path
    if path in ("", "/"):
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")

    parsed = parsed._replace(path=path)
    return urlunparse(parsed)


def extract_links(soup, base_url):

    urls = set()

    for link in soup.find_all("a"):

        href = link.get("href")

        if not href:
            continue

        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue

        absolute_url = urljoin(base_url, href)

        parsed = urlparse(absolute_url)

        # Fix www-less URLs
        if parsed.netloc == "netsoltech.com":
            parsed = parsed._replace(netloc="www.netsoltech.com")
            absolute_url = urlunparse(parsed)

        absolute_url = normalize_url(absolute_url)
        parsed = urlparse(absolute_url)
        path = parsed.path.lower()

        if any(path.startswith(prefix) for prefix in EXCLUDED_PATHS):
            continue

        if path.endswith((".pdf", ".xml", ".zip", ".xlsx", ".doc", ".docx", ".htm")):
            continue

        # Only crawl the main website
        if parsed.netloc != "www.netsoltech.com":
            continue

        urls.add(absolute_url)

    return urls


def scrape_page(page, url):
    """
    Loads `url` in the given Playwright page (a tab reused across the whole
    crawl), waits for client-side rendering to settle, then extracts clean
    text + outbound links from the fully hydrated DOM.
    """

    try:
        response = page.goto(url, wait_until="networkidle", timeout=20000)
    except PlaywrightTimeoutError:
        # Some pages never go fully idle (trackers, polling widgets, etc.)
        # -- fall back to whatever's rendered after DOM content loads.
        response = page.goto(url, wait_until="domcontentloaded", timeout=20000)

    if response is None or response.status != 200:
        status = response.status if response else "no response"
        raise Exception(f"Failed to fetch {url} (status: {status})")

    # Use the final post-redirect URL as the base for resolving relative
    # links, in case this URL redirected somewhere.
    final_url = page.url

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    links = extract_links(soup, final_url)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = [line.strip() for line in text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)

    return clean_text, links