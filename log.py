import requests  # type: ignore
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import gspread  # type: ignore
from oauth2client.service_account import ServiceAccountCredentials  # type: ignore
import json

# --- 🔐 Google Sheets Setup ---
def setup_google_sheets(sheet_name: str, worksheet_name: str):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Load credentials from GitHub secret
    google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
    
    client = gspread.authorize(creds)
    spreadsheet = client.open(sheet_name)
    sheet = spreadsheet.worksheet(worksheet_name)
    return sheet

# --- 📝 Update Status in Sheet ---
def update_status(sheet, email, new_status, column_name):
    header = sheet.row_values(1)
    try:
        col_index = header.index(column_name) + 1
    except ValueError:
        print(f"❌ Column '{column_name}' not found.")
        return

    try:
        cell = sheet.find(email)
        if cell:
            sheet.update_cell(cell.row, col_index, new_status)
            print(f"✅ Updated row {cell.row} → {column_name}: {new_status}")
        else:
            raise ValueError("Email not found.")
    except Exception as e:
        print(f"❌ Failed to update for email '{email}': {e}")

# --- 🌐 Download Email Tracker Logs ---
def download_log_file(url: str, fallback_url: str, retry_delay=5):
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("✅ Successfully downloaded the log.")
                return response.text
            else:
                print(f"⚠️ Status {response.status_code}. Retrying fallback...")
                response = requests.get(fallback_url)
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}. Retrying...")
        time.sleep(retry_delay)

# --- 🧹 Filter Logs from Last N Hours ---
def filter_recent_logs(log_text: str, hours: int = 4, timezone: str = "America/New_York"):
    filtered = []
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    cutoff = now - timedelta(hours=hours)
    print(f"🕒 Filtering entries between: {cutoff} and {now}")
    for line in log_text.splitlines():
        try:
            timestamp_str = line.split(" - ")[0].strip()
            timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=tz)
            if cutoff <= timestamp <= now:
                filtered.append(line)
        except Exception as e:
            print(f"⚠️ Skipping line due to error: {e}")
    return filtered

# --- 📂 Save Lines to File ---
def save_lines_to_file(lines, filename: str):
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    print(f"✅ Saved {len(lines)} lines to {filename}")

# --- 📤 Extract User IDs from Log ---
def extract_recipient_ids(log_lines: list[str]):
    ids = []
    for line in log_lines:
        try:
            parts = line.split(" - ")
            if len(parts) >= 2:
                user = parts[1].strip().replace(" opened", "")
                ids.append(user)
        except Exception as e:
            print(f"⚠️ Error parsing line: {e}")
    unique_ids = sorted(set(ids))
    return unique_ids

# --- 🔁 Process One Sheet ---
def run_tracker_for_sheet(sheet_name, worksheet_name):
    print(f"▶️ Checking logs for {sheet_name} → {worksheet_name} at {datetime.now()}")
    
    LOG_URL = "https://emailtracker-2twv.onrender.com/download/log"
    FALLBACK_URL = "https://emailtracker-2twv.onrender.com/track/jeeveshreddy04@gmail.com.png"
    LOG_FILE = "filtered_logs.log"
    sheet = setup_google_sheets(sheet_name, worksheet_name)

    log_text = download_log_file(LOG_URL, FALLBACK_URL)
    filtered_logs = filter_recent_logs(log_text, hours=4)
    save_lines_to_file(filtered_logs, LOG_FILE)
    recipient_ids = extract_recipient_ids(filtered_logs)

    for email in recipient_ids:
        update_status(sheet, email, "Opened", "Click_Status")

# --- 🚀 Main Process ---
def main():
    with open("config.json") as f:
        config = json.load(f)
    
    for tracker in config:
        run_tracker_for_sheet(tracker["sheet_name"], tracker["worksheet_name"])

if __name__ == "__main__":
    main()
