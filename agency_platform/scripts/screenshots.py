"""Screenshot every screen of a running platform: python agency_platform/scripts/screenshots.py [base_url]"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

SHOTS = [
    ("01-developments", "#", None),
    ("02-documents", "#/d/kelso-villa/documents", None),
    ("03-facts", "#/d/kelso-villa/facts", "viewport"),
    ("03b-facts-full", "#/d/kelso-villa/facts", None),
    ("04-fact-page-preview", "#/d/kelso-villa/facts", "preview"),
    ("05-contradictions", "#/d/kelso-villa/contradictions", "viewport"),
    ("05b-contradictions-full", "#/d/kelso-villa/contradictions", None),
    ("06-publish", "#/d/kelso-villa/publish", None),
    ("07-st-huberts-contradictions", "#/d/st-huberts-close/contradictions", None),
]

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    for name, hash_, extra in SHOTS:
        page.goto(f"{BASE}/{hash_}")
        page.wait_for_load_state("networkidle")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(600)
        if extra == "preview":
            page.locator("tbody tr").filter(has_text="Guide").first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
            page.screenshot(path=OUT / f"{name}.png")
            continue
        page.screenshot(path=OUT / f"{name}.png", full_page=extra != "viewport")
        print("saved", name)
    b.close()
