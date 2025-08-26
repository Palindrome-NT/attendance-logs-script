import os
import time
import json
import requests
from datetime import datetime, timedelta
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

    # Define your desired start and end dates (with time)
    start_date = datetime(2025, 4, 20, 10,30, 0)
    end_date = datetime(2025, 4, 29, 15, 0, 0)
    # Use the stored last_processed_time or default to the start_date.
    last_processed_time = fetch_last_processed_time() or start_date

    current_day_logs = load_current_day_logs()
    today_date = datetime.now().date()

    # Commented out the reset line because we're using bounded dates.
    # if current_day_logs and today_date != datetime.strptime(list(current_day_logs.values())[0]['log_date'], "%Y-%m-%d").date():
    #     current_day_logs = {}

    try:
        conn = ZK(device_ip, port=4370).connect()
        print("Connected to the device.")
        
        attendance_logs = conn.get_attendance()
        logs_to_send = []
        current_time = datetime.now()

        for log in attendance_logs:
            log_time = log.timestamp
            # Process only if log_time is within our desired window.
            if log_time < start_date or log_time > end_date:
                continue

            employee_id = log.user_id
            log_date = log_time.date()
            check_time = log_time.strftime("%H:%M:%S")

            if log_time >= last_processed_time:
                if str(log_date) == str(today_date):
                    if employee_id in current_day_logs:
                        last_log_time = datetime.strptime(current_day_logs[employee_id]['log_time'], "%Y-%m-%d %H:%M:%S")
                        last_status = current_day_logs[employee_id]['checklog']
                        time_diff = (log_time - last_log_time).total_seconds()
                        if time_diff <= 30:
                            continue
                        else:
                            checklog = "out" if last_status == "in" else "in"
                            if log_date > last_log_time.date():
                                checklog = "in"
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
                    else:
                        checklog = "in"
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
                else:
                    checklog = "in"
                    if employee_id in current_day_logs:
                        last_log_time = datetime.strptime(current_day_logs[employee_id]['log_time'], "%Y-%m-%d %H:%M:%S")
                        last_status = current_day_logs[employee_id]['checklog']
                        
                        if log_date > last_log_time.date():
                            checklog = "in"
                        else:
                            time_diff = (log_time - last_log_time).total_seconds()
                            if time_diff <= 30:
                                continue
                            else:
                                checklog = "out" if last_status == "in" else "in"
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
        time.sleep(2 * 60)  # change next cycle time according to need
