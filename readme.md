# Attendance Logs Project

This project is used to log attendance and store it in files. It interacts with an attendance device, uses environment variables for sensitive data, and saves logs in two important files: `current_day_logs.txt` and `last_processed_log_date.txt`.

## Prerequisites

Make sure you have the following:

- **Python 3**: This project is designed to run with Python 3. You can check your Python version by running:
  ```bash
  python3 --version
  ```

- **Dependencies**: You need to install the following Python packages to run the script:
  - `requests` – For making HTTP requests.
  - `pyzk` – For interacting with ZK devices.
  - `python-dotenv` – For loading environment variables from a `.env` file.
  - `pymongo` – For working with MongoDB.

## Setup Instructions

### 1. Create a Virtual Environment (Recommended)

To avoid conflicts with other Python projects, it's highly recommended to use a **virtual environment**.

- **Create a virtual environment**:
  ```bash
  python3 -m venv venv
  ```

- **Activate the virtual environment**:
  - On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```
  - On Windows:
    ```bash
    venv\Scripts\activate
    ```

### 2. Install the Dependencies

Once the virtual environment is activated, install the necessary dependencies by running:

```bash
pip install requests
pip install -U pyzk
pip install python-dotenv
pip install pymongo
```

Alternatively, you can create a `requirements.txt` file containing these dependencies and run:

```bash
pip install -r requirements.txt
```

### 3. Setup `.env` File

Create a `.env` file in the root of the project directory to store sensitive information such as database URIs and API keys. 

**Required environment variables in the `.env` file:**

```env
# Device IP is the IP address of the attendance machine
DEVICE_IP=192.168.1.123

# Branch ID (your unique branch identifier)
BRANCH_ID=67xxxxxxxxxxxxxxx684

# Company ID (your unique company identifier)
COMPANY_ID=66xxxxxxxxxxxxxxx23e

# API URL for sending attendance logs
API_URL=http://localhost:8001/api/attendance-logs/insert
```

**Important:**  
- `DEVICE_IP` is critical for accessing the attendance device to pull logs. Ensure this IP is correctly set to the machine where the attendance device is located.
- When running the script, make sure your device (from which you're running the script) and the attendance machine are connected to the **same Wi-Fi network**. This is necessary for the script to communicate with the device.

Make sure the `.env` file **is not committed to version control** (e.g., Git). You can ensure this by adding `.env` to your `.gitignore`.

### 4. Run the Script

Once you’ve installed all the dependencies and set up the `.env` file, you can run the main script:

```bash
python3 attendance_logs.py
```

This will start the process and create/modify the following important files:
- `current_day_logs.txt`: Stores the attendance logs for the current day.
- `last_processed_log_date.txt`: Tracks the date and time of the last time the script was run, to ensure only new logs are processed.

### Important Files

- **`current_day_logs.txt`**: This file stores the attendance logs for the current day. It is updated each time the script is run.
- **`last_processed_log_date.txt`**: This file stores the timestamp of the last time the script was run. It helps keep track of the logs that have already been processed, ensuring that only new logs are saved in `current_day_logs.txt`.

### Project Directory Structure

Your project directory should look something like this:

```
my_project/
├── venv/                    # Virtual environment (not committed to version control)
├── requirements.txt         # List of dependencies
├── .env                     # Environment variables file (not committed to version control)
├── attendance_logs.py       # Main Python script
├── current_day_logs.txt     # Stores today's attendance logs
└── last_processed_log_date.txt  # Tracks last script run time
```

## Summary

This project requires Python 3 and the following dependencies:
- `requests`
- `pyzk`
- `python-dotenv`
- `pymongo`

Once the dependencies are installed and the `.env` file is configured, you can run the script with:

```bash
python3 attendance_logs.py
```

The script will create `current_day_logs.txt` and `last_processed_log_date.txt` to keep track of attendance logs and the last time the script was run.

**Important:**  
- Ensure that your device and the attendance machine are connected to the **same Wi-Fi network** for the script to work properly.
