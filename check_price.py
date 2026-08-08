#!/usr/bin/env python3
"""
check_price.py

Opens the Back Market NL iPhone 15 Pro page in a real headless browser
(so its JavaScript challenge actually gets solved, unlike a plain curl
request), reads the "Premium" condition price, and writes it to
premium_price.txt. Meant to run inside GitHub Actions on a schedule --
see .github/workflows/check_price.yml
"""
import re
import sys

from playwright.sync_api import sync_playwright

URL = "https://www.backmarket.nl/nl-nl/p/iphone-15-pro"
OUTPUT_FILE = "premium_price.txt"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=UA, locale="nl-NL")
        # Reduce obvious "this is an automated browser" fingerprints.
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()
        page.goto(URL, wait_until="load", timeout=60000)
        # Give client-side rendering a few seconds to finish filling in
        # the price -- "networkidle" isn't used here because this page
        # keeps background tracker/analytics requests going indefinitely,
        # so that condition would never actually be satisfied.
        page.wait_for_timeout(6000)
        html = page.content()
        browser.close()

    # Same anchor logic as the original curl attempt: the "Premium"
    # condition option is the only one marked with the small diamond
    # icon, right before its price -- this avoids matching the word
    # "Premium" elsewhere on the page (e.g. the review filter).
    match = re.search(r"outline-diamond[^€]*€[^0-9]*([0-9][0-9.,]*)", html)
    if not match:
        print("ERROR: Premium price not found in rendered page", file=sys.stderr)
        sys.exit(1)

    price = match.group(1)
    with open(OUTPUT_FILE, "w") as f:
        f.write(price + "\n")
    print(f"Premium price: {price}")


if __name__ == "__main__":
    main()
