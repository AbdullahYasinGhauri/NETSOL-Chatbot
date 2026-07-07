import time
import json
import os
from collections import deque
from playwright.sync_api import sync_playwright
from scraper import scrape_page, normalize_url


def save_dataset(pages, filename="data/website_data.json"):
    """
    Save crawled pages to JSON.
    """

    os.makedirs("data", exist_ok=True)

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            pages,
            f,
            indent=4,
            ensure_ascii=False
        )


def crawl_website(start_url):
    MAX_PAGES = 300
    start_url = normalize_url(start_url)

    visited = set()
    queued = set([start_url])
    queue = deque([start_url])
    pages = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        while queue and len(pages) < MAX_PAGES:

            current_url = queue.popleft()

            if current_url in visited:
                continue

            print(f"\nCrawling: {current_url}")

            visited.add(current_url)

            try:

                text, links = scrape_page(page, current_url)

                pages.append(
                    {
                        "url": current_url,
                        "content": text
                    }
                )

                print(f"[OK] Saved page ({len(text)} characters)")
                print(f"[OK] Found {len(links)} links")
                time.sleep(0.5)

                for link in links:

                    if link not in visited and link not in queued:
                        queue.append(link)
                        queued.add(link)

            except Exception as e:

                print(f"[ERROR] Failed: {current_url}")
                print(e)

        browser.close()

    return pages


def main():

    start_url = "https://www.netsoltech.com"

    pages = crawl_website(start_url)

    save_dataset(pages)

    print("\n=================================")
    print("Crawling Complete")
    print("=================================")
    print(f"Pages Crawled : {len(pages)}")
    print("Dataset Saved : data/website_data.json")


if __name__ == "__main__":
    main()