# WhatsApp Automation — modernised Selenium version

This folder adds a maintained Python 3 / Selenium 4 implementation alongside the original notebooks. The original files are not deleted or overwritten.

## What it does

- Reads opted-in contacts from a CSV file.
- Accepts `phone_no`, `phone`, or `mobile` as the phone column.
- Personalises a message with the contact's `{name}`.
- Opens WhatsApp Web in Chrome using Selenium.
- Requires a clear `YES` confirmation for each message.
- Records dry runs, skipped contacts, errors, and messages submitted through the WhatsApp Web send control.

**Important:** A successful click only means the message was submitted to WhatsApp Web. This script does not verify delivery, read receipts, or recipient activity.

## Requirements

- Windows, macOS, or Linux
- Python 3.10 or later
- Google Chrome
- A WhatsApp account that can use WhatsApp Web

Selenium Manager is included in Selenium and normally resolves the matching browser driver automatically. You do not need to download ChromeDriver manually.

## Setup (Windows)

Open Command Prompt in this folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `contacts_template.csv` to `contacts.csv` and enter your own contacts. Do not commit real client contact data to a public GitHub repository.

## First run — preview only

```bat
python whatsapp_automation.py --contacts contacts.csv --message "Hello {name}, this is a reminder from our office."
```

This is a dry run. It does not open WhatsApp or send anything.

## Send after reviewing

```bat
python whatsapp_automation.py --contacts contacts.csv --message "Hello {name}, please share the pending documents." --send
```

The browser opens WhatsApp Web. Scan the QR code if prompted. The script asks you to type `YES` before each individual message. It processes at most 20 contacts by default; change this with `--max-messages`.

## Notes and limitations

- WhatsApp Web's page structure can change. If WhatsApp changes its send-button selectors, the script may need another update.
- Keep the browser visible; this implementation is not headless.
- Use only contacts who have agreed to receive your messages, follow WhatsApp's terms and applicable privacy / anti-spam requirements, and keep volumes reasonable.
- Do not use this for unsolicited bulk messaging.
- The CSV activity log is local and should be protected as client information.
- The old notebooks in the repository are historical examples. This folder is the recommended starting point for the modernised WhatsApp workflow.
