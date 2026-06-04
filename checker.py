import os
import json
import hashlib
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# ── Configuration ────────────────────────────────────────────────────────────
TARGET_URL          = "https://the-trackr.com"   # ← fill in the exact listings page URL
LISTINGS_SELECTOR   = "tr.border"                # each internship row
TITLE_SELECTOR      = "td.min-w-\\[420px\\] a"  # the job title link
LINK_SELECTOR       = "td.min-w-\\[420px\\] a"  # same element has the href
STATE_FILE = "seen_internships.json"             # Tracks what we've already seen
# ─────────────────────────────────────────────────────────────────────────────


def load_seen() -> set:
    """Load previously seen internship IDs from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    """Persist the current set of seen IDs."""
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def make_id(text: str) -> str:
    """Create a stable ID from a listing's text content."""
    return hashlib.md5(text.strip().encode()).hexdigest()


def scrape_listings() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(TARGET_URL, wait_until="networkidle")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Debug: print how many rows were found at each stage
    all_rows = soup.select(LISTINGS_SELECTOR)
    print(f"DEBUG: Total rows matching '{LISTINGS_SELECTOR}': {len(all_rows)}")

    open_rows = [el for el in all_rows if el.select_one("td.bg-blue-300")]
    print(f"DEBUG: Rows with opening date (bg-blue-300): {len(open_rows)}")

    items = []
    for el in open_rows:
        title_el = el.select_one(TITLE_SELECTOR)
        link_el  = el.select_one(LINK_SELECTOR)
        title = title_el.get_text(strip=True) if title_el else el.get_text(strip=True)
        href  = link_el["href"] if link_el and link_el.get("href") else TARGET_URL
        print(f"DEBUG: Found listing: {title}")
        items.append({"id": make_id(title), "title": title, "url": href})

    return items


def send_email(new_listings: list[dict]):
    """Send a notification email listing all new internships."""
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    subject = f"🎉 {len(new_listings)} New Internship(s) Found!"

    # Plain-text body
    text_lines = ["New internships were posted:\n"]
    for item in new_listings:
        text_lines.append(f"• {item['title']}\n  {item['url']}\n")
    text_body = "\n".join(text_lines)

    # HTML body
    html_rows = "".join(
        f'<tr><td style="padding:8px 4px;border-bottom:1px solid #eee;">'
        f'<a href="{item["url"]}" style="color:#2563eb;text-decoration:none;">{item["title"]}</a>'
        f"</td></tr>"
        for item in new_listings
    )
    html_body = f"""
    <html><body style="font-family:sans-serif;color:#111;max-width:600px;margin:auto;">
      <h2 style="color:#2563eb;">🎉 {len(new_listings)} New Internship(s) Found</h2>
      <p>The following new listings appeared on <a href="{TARGET_URL}">{TARGET_URL}</a>:</p>
      <table style="width:100%;border-collapse:collapse;">{html_rows}</table>
      <p style="color:#888;font-size:12px;margin-top:24px;">
        Sent by your internship tracker · <a href="{TARGET_URL}">View all listings</a>
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"✉️  Email sent with {len(new_listings)} new listing(s).")


def main():
    seen = load_seen()
    listings = scrape_listings()

    new = [item for item in listings if item["id"] not in seen]

    if new:
        print(f"Found {len(new)} new listing(s).")
        send_email(new)
        seen.update(item["id"] for item in new)
        save_seen(seen)
    else:
        print("No new listings found.")

    # Always update seen with everything currently on the page
    # (removes stale IDs after listings rotate off)
    current_ids = {item["id"] for item in listings}
    save_seen(current_ids)


if __name__ == "__main__":
    main()
