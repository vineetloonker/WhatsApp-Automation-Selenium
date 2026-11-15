"""
WhatsApp Web helper using Selenium 4.

Safety defaults:
- Dry-run unless --send is supplied.
- Asks for confirmation before every individual message.
- Logs submission attempts; it cannot verify delivery or read receipts.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


LOG_FILE = Path("message_log.csv")
SEND_BUTTON_SELECTORS = (
    (By.CSS_SELECTOR, '[data-testid="compose-btn-send"]'),
    (By.CSS_SELECTOR, 'button[aria-label="Send"]'),
    (By.CSS_SELECTOR, 'button[aria-label="send"]'),
)


def normalise_phone(value: str, country_code: str) -> str:
    """Return digits only; add the default country code when needed."""
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        raise ValueError("Phone number is blank or invalid.")
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    if len(digits) <= 10 and country_code:
        digits = country_code + digits
    if not 8 <= len(digits) <= 15:
        raise ValueError(f"Phone number has an invalid length: {value!r}")
    return digits


def read_contacts(path: Path, country_code: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Contacts file not found: {path}")

    contacts: list[dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV must have a header row.")

        phone_column = next(
            (column for column in ("phone_no", "phone", "mobile") if column in reader.fieldnames),
            None,
        )
        if not phone_column:
            raise ValueError("CSV needs a phone_no, phone, or mobile column.")

        for row_number, row in enumerate(reader, start=2):
            try:
                phone = normalise_phone(row.get(phone_column, ""), country_code)
            except ValueError as exc:
                logging.warning("Skipping CSV row %s: %s", row_number, exc)
                continue
            contacts.append({
                "phone": phone,
                "name": (row.get("name") or "").strip() or "there",
            })
    return contacts


def find_send_button(driver):
    for by, selector in SEND_BUTTON_SELECTORS:
        matches = driver.find_elements(by, selector)
        for element in matches:
            if element.is_displayed() and element.is_enabled():
                return element
    return False


def append_log(phone: str, name: str, status: str, detail: str = "") -> None:
    file_exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(["timestamp_utc", "phone", "name", "status", "detail"])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            phone,
            name,
            status,
            detail,
        ])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or send individual WhatsApp Web messages from a CSV."
    )
    parser.add_argument("--contacts", type=Path, default=Path("contacts.csv"))
    parser.add_argument(
        "--message",
        default="Hello {name}, this is a reminder from our office.",
        help="Message template. You can use {name}.",
    )
    parser.add_argument("--country-code", default="91", help="Default country code, e.g. 91 for India.")
    parser.add_argument("--send", action="store_true", help="Open WhatsApp Web and allow sending.")
    parser.add_argument("--max-messages", type=int, default=20, help="Maximum contacts processed in one run.")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to wait for WhatsApp controls.")
    args = parser.parse_args()

    if args.max_messages < 1:
        parser.error("--max-messages must be at least 1")

    try:
        contacts = read_contacts(args.contacts, args.country_code)
    except (OSError, ValueError) as exc:
        logging.error("%s", exc)
        return 1

    if not contacts:
        logging.error("No valid contacts found.")
        return 1

    contacts = contacts[: args.max_messages]
    logging.info("Loaded %s valid contact(s).", len(contacts))

    if not args.send:
        print("\nDRY RUN — no WhatsApp messages will be sent.\n")
        for contact in contacts:
            message = args.message.format(name=contact["name"])
            print(f"To: {contact['name']} (+{contact['phone']})")
            print(f"Message: {message}\n")
            append_log(contact["phone"], contact["name"], "dry_run")
        print("To proceed, run again with --send. You will still confirm each message.")
        return 0

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Selenium Manager (included with Selenium) resolves the matching driver.
    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as exc:
        logging.error("Could not start Chrome: %s", exc)
        return 1

    try:
        driver.get("https://web.whatsapp.com/")
        input("Scan the WhatsApp Web QR code if required. Once your chats are visible, press Enter here... ")

        for index, contact in enumerate(contacts, start=1):
            message = args.message.format(name=contact["name"])
            url = (
                "https://web.whatsapp.com/send"
                f"?phone={contact['phone']}&text={quote(message)}"
            )
            print(f"\n[{index}/{len(contacts)}] {contact['name']} (+{contact['phone']})")
            driver.get(url)

            try:
                send_button = WebDriverWait(driver, args.wait).until(find_send_button)
            except TimeoutException:
                logging.warning("Send control not found for %s; skipping.", contact["phone"])
                append_log(contact["phone"], contact["name"], "not_sent", "Send control not found")
                continue

            print(f"Message preview: {message}")
            approval = input("Send this message? Type YES to confirm: ").strip()
            if approval != "YES":
                append_log(contact["phone"], contact["name"], "skipped", "Not confirmed by user")
                print("Skipped.")
                continue

            try:
                send_button.click()
                append_log(
                    contact["phone"],
                    contact["name"],
                    "submitted_to_whatsapp_web",
                    "Send button clicked; delivery not verified",
                )
                print("Submitted to WhatsApp Web. Delivery is not verified.")
                time.sleep(2)
            except WebDriverException as exc:
                logging.exception("Could not submit message to %s", contact["phone"])
                append_log(contact["phone"], contact["name"], "error", str(exc)[:300])

    finally:
        input("\nPress Enter to close the browser...")
        driver.quit()

    print(f"\nActivity log: {LOG_FILE.resolve()}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
