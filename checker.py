import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Configuration ────────────────────────────────────────────────────────────
API_URLS = [
    # UK Finance
    "https://api.the-trackr.com/programmes?region=UK&industry=Finance&season=2027&type=summer-internships",
    "https://api.the-trackr.com/programmes?region=UK&industry=Finance&season=2027&type=events",
    # UK Tech
    "https://api.the-trackr.com/programmes?region=UK&industry=Tech&season=2026&type=summer-internships",
    "https://api.the-trackr.com/programmes?region=UK&industry=Tech&season=2026&type=events",
    # EU Finance
    "https://api.the-trackr.com/programmes?region=EU&industry=Finance&season=2026&type=summer-internships",
]

STATE_FILE = "seen_internships.json"
# ─────────────────────────────────────────────────────────────────────────────


def load_seen() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def fetch_all_listings() -> list[dict]:
    """Fetch listings from all configured API URLs and combine them."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; InternshipBot/1.0)"}
    all_listings = []
    for url in API_URLS:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        listings = resp.json()
        print(f"DEBUG: Fetched {len(listings)} listings from {url}")
        all_listings.extend(listings)
    return all_listings


def is_open(listing: dict) -> bool:
    """A listing is open if it has an openingDate set."""
    return listing.get("openingDate") is not None


def send_email(new_listings: list[dict]):
    sender    = os.environ["EMAIL_SENDER"]
    password  = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    smtp_host = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    subject = f"{len(new_listings)} New Internship(s) Open on Trackr!"

    text_lines = ["The following internships just opened on Trackr:\n"]
    for item in new_listings:
        company = item.get("company", {}).get("name", "Unknown")
        title   = item.get("name", "Untitled")
        url     = item.get("url") or item.get("company", {}).get("careersSite", "https://the-trackr.com")
        text_lines.append(f"• {company} — {title}\n  {url}\n")
    text_body = "\n".join(text_lines)

    html_rows = ""
    for item in new_listings:
        company  = item.get("company", {}).get("name", "Unknown")
        title    = item.get("name", "Untitled")
        url      = item.get("url") or item.get("company", {}).get("careersSite", "https://the-trackr.com")
        industry = item.get("industry", "")
        html_rows += (
            f'<tr>'
            f'<td style="padding:8px 4px;border-bottom:1px solid #eee;font-weight:600">{company}</td>'
            f'<td style="padding:8px 4px;border-bottom:1px solid #eee;">'
            f'<a href="{url}" style="color:#2563eb;text-decoration:none;">{title}</a>'
            f'</td>'
            f'<td style="padding:8px 4px;border-bottom:1px solid #eee;color:#888;font-size:12px;">{industry}</td>'
            f'</tr>'
        )

    html_body = f"""
    <html><body style="font-family:sans-serif;color:#111;max-width:640px;margin:auto;">
      <h2 style="color:#2563eb;">{len(new_listings)} New Internship(s) Now Open</h2>
      <p>The following listings just became available on
         <a href="https://the-trackr.com">the-trackr.com</a>:</p>
      <table style="width:100%;border-collapse:collapse;">{html_rows}</table>
      <p style="color:#888;font-size:12px;margin-top:24px;">
        Sent by your Trackr bot ·
        <a href="https://the-trackr.com">View all listings</a>
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_login, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"✉️  Email sent with {len(new_listings)} new listing(s).")


def main():
    seen         = load_seen()
    all_listings = fetch_all_listings()

    # Only care about listings that are currently open
    open_listings = [l for l in all_listings if is_open(l)]
    print(f"DEBUG: Total listings across all sources: {len(all_listings)}")
    print(f"DEBUG: Open listings (have openingDate): {len(open_listings)}")

    # Find ones we haven't seen before
    new = [l for l in open_listings if l["id"] not in seen]
    print(f"DEBUG: New listings: {len(new)}")

    if new:
        for l in new:
            print(f"  → [{l.get('industry')}] {l.get('company', {}).get('name')} — {l.get('name')}")
        send_email(new)
    else:
        print("No new listings found.")

    # Save ALL currently open IDs
    save_seen({l["id"] for l in open_listings})


if __name__ == "__main__":
    main()
