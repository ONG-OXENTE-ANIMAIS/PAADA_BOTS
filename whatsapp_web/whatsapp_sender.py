"""
WhatsApp Web Message Sender
============================
Automates sending messages through WhatsApp Web using Selenium.

Usage:
    python whatsapp_sender.py --phone "+5511999999999" --message "Hello!"
    python whatsapp_sender.py --phone "+5511999999999" --message "Hello!" --wait 30
    python whatsapp_sender.py --contact "John" --message "Hi John!"

First run: you must scan the QR code with your phone.
Subsequent runs: the session is persisted so no QR scan is needed.
"""

import argparse
import os
import sys
import time
import logging
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WHATSAPP_URL = "https://web.whatsapp.com"
USER_DATA_DIR = Path(__file__).parent / "chrome_profile"
DEFAULT_QR_WAIT = 60  # seconds to wait for QR scan on first login
DEFAULT_LOAD_WAIT = 30  # seconds to wait for chats to load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("whatsapp_sender")

# ---------------------------------------------------------------------------
# Browser helpers
# ---------------------------------------------------------------------------


def create_driver() -> webdriver.Chrome:
    """Create a Chrome WebDriver with a persistent profile so the QR code
    only needs to be scanned once."""
    opts = Options()
    opts.add_argument(f"--user-data-dir={USER_DATA_DIR.resolve()}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    # Keep the browser visible so the user can scan the QR code
    # opts.add_argument("--headless=new")  # uncomment after first login

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.maximize_window()
    return driver


def wait_for_login(driver: webdriver.Chrome, timeout: int = DEFAULT_QR_WAIT):
    """Wait until WhatsApp Web is fully loaded (QR scanned or session restored)."""
    log.info("Waiting for WhatsApp Web to load (scan the QR code if prompted)…")
    try:
        # The side panel (chat list) appears once logged in
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#pane-side'))
        )
        log.info("✅ WhatsApp Web loaded successfully.")
    except TimeoutException:
        log.error(
            "❌ Timed out waiting for login. "
            "Make sure you scanned the QR code within %d seconds.",
            timeout,
        )
        driver.quit()
        sys.exit(1)


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


def send_message_to_phone(
    driver: webdriver.Chrome,
    phone: str,
    message: str,
    wait: int = DEFAULT_LOAD_WAIT,
):
    """Send a message to a phone number (with country code, e.g. +5511999999999).

    Uses the wa.me deep-link so the contact does NOT need to be saved.
    """
    phone_clean = phone.replace(" ", "").replace("-", "").replace("+", "")
    encoded_msg = quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone_clean}&text={encoded_msg}"
    log.info("Opening chat with +%s …", phone_clean)
    driver.get(url)

    _click_send(driver, wait)


def send_message_to_contact(
    driver: webdriver.Chrome,
    contact_name: str,
    message: str,
    wait: int = DEFAULT_LOAD_WAIT,
):
    """Send a message to a saved contact by searching for their name."""
    log.info("Searching for contact '%s' …", contact_name)

    # Click the search box — try multiple selectors
    search_selectors = [
        'div[contenteditable="true"][data-tab="3"]',
        'div[contenteditable="true"][title="Search input textbox"]',
        'div[contenteditable="true"][title="Caixa de texto de pesquisa"]',
        '#side div[contenteditable="true"]',
    ]
    search_box = None
    for sel in search_selectors:
        try:
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            break
        except TimeoutException:
            continue
    if search_box is None:
        log.error("❌ Could not find the search box.")
        return
    search_box.clear()
    search_box.click()
    search_box.send_keys(contact_name)
    time.sleep(2)  # let results populate

    # Click the first matching result
    try:
        first_result = WebDriverWait(driver, wait).until(
            EC.presence_of_element_located(
                (By.XPATH, f'//span[@title and contains(translate(@title,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"), "{contact_name.lower()}")]')
            )
        )
        first_result.click()
        time.sleep(1)
    except TimeoutException:
        log.error("❌ Contact '%s' not found.", contact_name)
        return

    # Type the message into the message input box — try multiple selectors
    msg_input_selectors = [
        'div[contenteditable="true"][data-tab="10"]',
        'div[contenteditable="true"][data-tab="6"]',
        'div[contenteditable="true"][data-tab="1"]',
        'footer div[contenteditable="true"]',
        'div[title="Type a message"]',
        'div[title="Digite uma mensagem"]',
        '#main footer div[contenteditable="true"]',
    ]
    msg_box = None
    for sel in msg_input_selectors:
        try:
            msg_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            break
        except TimeoutException:
            continue
    if msg_box is None:
        log.error("❌ Could not find the message input box.")
        return
    msg_box.click()
    msg_box.send_keys(message)

    _click_send(driver, wait)


def _click_send(driver: webdriver.Chrome, wait: int):
    """Wait for the send button to appear and click it, with multiple
    fallback strategies to handle WhatsApp Web UI changes."""

    # Strategy 1: Try several known selectors for the send button
    send_selectors = [
        'span[data-icon="send"]',
        'button[aria-label="Send"]',
        'button[aria-label="Enviar"]',          # Portuguese
        'span[data-icon="send-light"]',
        'span[data-icon="msg-send"]',
        '[data-testid="send"]',
        '[data-testid="compose-btn-send"]',
        'button[aria-label="Send message"]',
        'button[aria-label="Enviar mensagem"]',  # Portuguese
    ]

    for selector in send_selectors:
        try:
            send_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            send_btn.click()
            log.info("✅ Message sent! (via button: %s)", selector)
            time.sleep(2)
            return
        except TimeoutException:
            continue

    # Strategy 2: Find the message input box and press Enter
    log.warning("⚠️  Send button not found, trying Enter key fallback…")
    input_selectors = [
        'div[contenteditable="true"][data-tab="10"]',
        'div[contenteditable="true"][data-tab="6"]',
        'div[contenteditable="true"][data-tab="1"]',
        'footer div[contenteditable="true"]',
        'div[title="Type a message"]',
        'div[title="Digite uma mensagem"]',      # Portuguese
        '#main footer div[contenteditable="true"]',
    ]

    for selector in input_selectors:
        try:
            msg_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            msg_box.send_keys(Keys.ENTER)
            log.info("✅ Message sent! (via Enter key on: %s)", selector)
            time.sleep(2)
            return
        except TimeoutException:
            continue

    log.error("❌ Could not send the message. Neither send button nor input box were found.")


# ---------------------------------------------------------------------------
# Bulk messaging
# ---------------------------------------------------------------------------


def send_bulk_messages(
    driver: webdriver.Chrome,
    phones: list[str],
    message: str,
    delay: int = 5,
):
    """Send the same message to multiple phone numbers with a delay between each."""
    total = len(phones)
    for i, phone in enumerate(phones, 1):
        log.info("Sending message %d/%d …", i, total)
        send_message_to_phone(driver, phone, message)
        if i < total:
            log.info("Waiting %d seconds before next message…", delay)
            time.sleep(delay)
    log.info("🎉 Bulk send complete (%d messages).", total)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Send WhatsApp messages via WhatsApp Web automation."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--phone",
        help="Recipient phone number with country code (e.g. +5511999999999).",
    )
    group.add_argument(
        "--contact",
        help="Name of a saved contact to search for.",
    )
    group.add_argument(
        "--bulk",
        nargs="+",
        metavar="PHONE",
        help="Multiple phone numbers for bulk send.",
    )
    parser.add_argument(
        "--message", "-m",
        required=True,
        help="The message text to send.",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=DEFAULT_QR_WAIT,
        help=f"Seconds to wait for QR login (default: {DEFAULT_QR_WAIT}).",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Seconds between bulk messages (default: 5).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    driver = create_driver()
    try:
        driver.get(WHATSAPP_URL)
        wait_for_login(driver, timeout=args.wait)

        if args.phone:
            send_message_to_phone(driver, args.phone, args.message)
        elif args.contact:
            send_message_to_contact(driver, args.contact, args.message)
        elif args.bulk:
            send_bulk_messages(driver, args.bulk, args.message, delay=args.delay)
    finally:
        log.info("Closing browser…")
        driver.quit()


if __name__ == "__main__":
    main()
