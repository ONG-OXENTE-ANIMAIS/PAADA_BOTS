# WhatsApp Web Message Sender 📱

A Python script that automates sending messages through **WhatsApp Web** using Selenium.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Make sure Google Chrome is installed

The script uses Chrome via Selenium. [ChromeDriver](https://chromedriver.chromium.org/) is managed automatically by `webdriver-manager`.

## Usage

### Send to a phone number (no need to save the contact)

```bash
python whatsapp_sender.py --phone "+5511999999999" --message "Hello from Python!"
```

### Send to a saved contact by name

```bash
python whatsapp_sender.py --contact "John" --message "Hey John, what's up?"
```

### Bulk send to multiple numbers

```bash
python whatsapp_sender.py --bulk "+5511999999999" "+5511888888888" "+5511777777777" --message "Hi everyone!" --delay 10
```

### Options

| Flag | Description |
|------|-------------|
| `--phone` | Single phone number with country code |
| `--contact` | Name of a saved contact |
| `--bulk` | Space-separated list of phone numbers |
| `--message` / `-m` | The message to send (**required**) |
| `--wait` | Seconds to wait for QR code login (default: 60) |
| `--delay` | Seconds between bulk messages (default: 5) |

## First Run — QR Code

On the **first run**, Chrome will open WhatsApp Web and display a QR code. Scan it with your phone (**WhatsApp → Linked Devices → Link a Device**). The session is saved in `chrome_profile/` so you won't need to scan again.

## Notes

- The phone number **must include the country code** (e.g. `+55` for Brazil).
- WhatsApp may flag or ban accounts that send too many automated messages. Use bulk sending responsibly.
- The script keeps the browser visible so you can see what's happening. After verifying it works, you can uncomment the `--headless` line in the code.
