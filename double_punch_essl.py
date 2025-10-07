import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from zk import ZK

load_dotenv()

def fetch_last_processed_time():
    """Reads the last processed timestamp from a file."""
    try:
        with open("last_processed_log_date.txt", "r") as file:
            return datetime.strptime(file.read().strip(), "%Y-%m-%d %H:%M:%S")
    except (FileNotFoundError, ValueError):
        return None 

def save_last_processed_time(timestamp):
    """Saves the last processed timestamp to a file."""
    with open("last_processed_log_date.txt", "w") as file:
        file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S"))

def load_current_day_logs():
    """Loads the current day's logs from a file."""
    try:
        with open("current_day_logs.txt", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_current_day_logs(current_day_logs):
    """Saves the current day's logs to a file."""
    with open("current_day_logs.txt", "w") as file:
        json.dump(current_day_logs, file)

def send_logs_to_api(logs, api_url):
    """Sends log entries to the API."""
    for log in logs:
        if "createdAt" in log and isinstance(log["createdAt"], datetime):
            log["createdAt"] = log["createdAt"].isoformat()
        if "updatedAt" in log and isinstance(log["updatedAt"], datetime):
            log["updatedAt"] = log["updatedAt"].isoformat()
    response = requests.post(api_url, json=logs)
    if response.status_code == 200:
        api_response = response.json()
        if api_response.get("success"):
            print("Logs sent to API successfully.")
            return True
        else:
            print("API response: Duplicate or existing logs.")
            return False
    else:
        print("Failed to send logs:", response.text)
        return False

def fetch_and_process_logs():
    device_ip = os.getenv('DEVICE_IP')
    branch_id = os.getenv('BRANCH_ID')
    company_id = os.getenv('COMPANY_ID')
    api_url = os.getenv('API_URL')

    zk = ZK(device_ip, port=4370)
    last_processed_time = fetch_last_processed_time() or datetime(2025, 10, 1) # Specify the start date (in yyyy-mm-dd format) from which logs should be saved to the database.

    current_day_logs = load_current_day_logs()
    today_date = datetime.now().date()

    try:
        conn = zk.connect()
        print("Connected to the device.")
        
        attendance_logs = conn.get_attendance()
        logs_to_send = []

        current_time = datetime.now()

        for log in attendance_logs:
            log_time = log.timestamp
            employee_id = log.user_id
            log_date = log_time.date()
            check_time = log_time.strftime("%H:%M:%S")

            if log_time >= last_processed_time:
                checklog = "in" if log.punch == 0 else "out"

                current_day_logs[employee_id] = {
                    "log_time": log_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "checklog": checklog,
                    "log_date": str(log_date)
                }

                log_entry = {
                    "employee_id": employee_id,
                    "company_id": company_id,
                    "branch_id": branch_id,
                    "check_date": str(log_date),
                    "check_time": check_time,
                    "checklog": checklog,
                    "device_name": "Primary",
                    "createdAt": datetime.now(),
                    "updatedAt": datetime.now()
                }

                logs_to_send.append(log_entry)

        if logs_to_send:
            if send_logs_to_api(logs_to_send, api_url):
                save_last_processed_time(current_time)
                print(f"Updated last processed time to: {current_time}")
            else:
                print("Logs were not saved, retaining the previous last processed time.")
            save_current_day_logs(current_day_logs)

    except Exception as e:
        print("Process terminated:", e)
    finally:
        if conn:
            conn.disconnect()
            print("Disconnected from the device.")

if __name__ == "__main__":
    while True:
        fetch_and_process_logs()
        print("Waiting for the next cycle (2 minutes)...")
        time.sleep(2 * 60) # change next cycle time according to need
