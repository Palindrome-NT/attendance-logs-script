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

def load_last_logs():
    """Loads the last employee logs (previous in/out) from a file."""
    try:
        with open("current_day_logs.txt", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_last_logs(last_logs):
    """Saves the last employee logs to a file."""
    with open("current_day_logs.txt", "w") as file:
        json.dump(last_logs, file)

def load_employee_shift_data():
    """Load employee shift data from file."""
    try:
        with open("employee_shift_data.txt", "r") as file:
            data = json.load(file)
            if data.get("success") and "data" in data:
                return data["data"]
            return {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_employee_shift_data(shift_data):
    """Save employee shift data to file."""
    with open("employee_shift_data.txt", "w") as file:
        json.dump(shift_data, file)

def fetch_employee_shift_data():
    """Fetch employee shift configurations from API."""
    try:
        branch_id = os.getenv('BRANCH_ID')
        company_id = os.getenv('COMPANY_ID')
        api_key = os.getenv('X_API_KEY')
        shift_api_url = os.getenv('SHIFT_API_URL')
        
        if not all([branch_id, company_id, api_key]):
            return None
        
        # Prepare API request
        url = f"{shift_api_url}?branch_id={branch_id}&company_id={company_id}"
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            api_response = response.json()
            if api_response.get("success") and "data" in api_response:
                save_employee_shift_data(api_response)
                return api_response["data"]
            else:
                return None
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error while fetching shift data: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while fetching shift data: {e}")
        return None

def is_within_employee_shift_range(current_log_time, last_log_time, shift_config):
    """
    Check if log time falls within employee's specific shift range.
    """
    if not shift_config or not last_log_time:
        return False
        
    start_time_str = shift_config.get('SHIFT_START_TIME', '09:00:00')
    end_time_str = shift_config.get('SHIFT_END_TIME', '23:59:59')
    spans_midnight = shift_config.get('SHIFT_SPANS_MIDNIGHT', False)
    
    shift_start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
    shift_end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
    
    if not spans_midnight:
        if current_log_time.date() > last_log_time.date():
            return False
        else:
            current_time_only = current_log_time.time()
            return shift_start_time <= current_time_only <= shift_end_time
    else:
        shift_start_boundary = datetime.combine(last_log_time.date(), shift_start_time)
        shift_end_boundary = datetime.combine(last_log_time.date() + timedelta(days=1), shift_end_time)
        last_log_in_shift = shift_start_boundary <= last_log_time <= shift_end_boundary
        
        if not last_log_in_shift:
            shift_start_boundary = datetime.combine(last_log_time.date() - timedelta(days=1), shift_start_time)
            shift_end_boundary = datetime.combine(last_log_time.date(), shift_end_time)
            last_log_in_shift = shift_start_boundary <= last_log_time <= shift_end_boundary
        
        current_log_in_shift = shift_start_boundary <= current_log_time <= shift_end_boundary
        
        if last_log_in_shift and not current_log_in_shift:
            return False
        
        if current_log_in_shift:
            return True
        
        return False

def determine_checklog_with_employee_shift(employee_id, log_time, last_logs, employee_shift_data):
    """
    Determine checklog based on individual employee shift configuration.
    """
    if employee_id not in last_logs:
        return "in"
    
    last_checklog = last_logs[employee_id]['checklog']
    last_log_time = datetime.strptime(last_logs[employee_id]['log_time'], "%Y-%m-%d %H:%M:%S")
    
    shift_config = employee_shift_data.get(employee_id)
    
    if not shift_config:
        if log_time.date() > last_log_time.date():
            return "in"
        else:
            return "out" if last_checklog == "in" else "in"
    
    spans_midnight = shift_config.get('SHIFT_SPANS_MIDNIGHT', False)
    
    if not spans_midnight:
        if log_time.date() > last_log_time.date():
            return "in"
        else:
            return "out" if last_checklog == "in" else "in"
    else:
        if is_within_employee_shift_range(log_time, last_log_time, shift_config):
            new_checklog = "out" if last_checklog == "in" else "in"
            return new_checklog
        else:
            return "in"

def send_logs_to_api(logs, api_url):
    """Sends log entries to the API."""
    for log in logs:
        if isinstance(log.get("createdAt"), datetime):
            log["createdAt"] = log["createdAt"].isoformat()
        if isinstance(log.get("updatedAt"), datetime):
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
    
    employee_shift_data = fetch_employee_shift_data()
    
    if employee_shift_data is None:
        employee_shift_data = load_employee_shift_data()
    
    zk = ZK(device_ip, port=4370)
    last_processed_time = fetch_last_processed_time() or datetime(2025, 5, 1) # Specify the start date (in yyyy-mm-dd format) from which logs should be saved to the database.
    last_logs = load_last_logs()
    
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
                # Skip duplicate logs within 30 seconds
                if employee_id in last_logs:
                    last_log_time = datetime.strptime(last_logs[employee_id]['log_time'], "%Y-%m-%d %H:%M:%S")
                    if (log_time - last_log_time).total_seconds() <= 30:
                        continue
                
                # Determine 'in' or 'out' using employee-specific shift data
                checklog = determine_checklog_with_employee_shift(
                    employee_id, log_time, last_logs, employee_shift_data
                )
                
                # Update last_logs
                last_logs[employee_id] = {
                    "log_time": log_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "checklog": checklog,
                    "log_date": str(log_date)
                }
                
                # Prepare entry for API
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
                
                # Show shift info in log
                shift_info = employee_shift_data.get(employee_id, {})
                spans_midnight = shift_info.get('SHIFT_SPANS_MIDNIGHT', 'default')

        if logs_to_send:
            if send_logs_to_api(logs_to_send, api_url):
                save_last_processed_time(current_time)
                print(f"Updated last processed time to: {current_time}")
            else:
                print("Logs were not saved, retaining the previous last processed time.")
        
        save_last_logs(last_logs)

    except Exception as e:
        print("Process terminated:", e)
    finally:
        if 'conn' in locals() and conn:
            conn.disconnect()
            print("Disconnected from the device.")

if __name__ == "__main__":
    while True:
        fetch_and_process_logs()
        print("Waiting for the next cycle (2 minutes)...")
        time.sleep(2 * 60)
