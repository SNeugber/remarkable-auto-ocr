# Remarkable Auto OCR

1. Syncs a remarkable tablet over SSH
1. Uploads files to [google OCR](/#TODO_link)
1. Saves in gdrive

## TODO

1. Set up `ruff` ✅
1. Set up `mdformat` ✅
1. Set up devcontainer ✅
1. Start with remarkable integration
   - Fetch data over ssh
   - Upload to google OCR
   - Merge OCRed text with PDF somehow
   - Upload to gdrive
   - Save SQLite DB file in gdrive with info on synced files
1. PoC of running `main.py` as service
1. How to distribute all the necessary libs from `uv` to service?
   - Use [nuitka](https://github.com/astral-sh/uv/issues/5802#issuecomment-2273058176)

## ChatGPT instructions

To create a Python project that runs as a system service using `systemd` and manages the project with the "uv" package manager, follow the steps below.

### Prerequisites

- Python 3.12 installed
- `uv` package manager installed
- A Linux system with `systemd` available
- A basic understanding of Linux system services

### Step 1: Initialize the Project with `uv`

First, we'll set up the Python project using the `uv` package manager. If `uv` is not installed, you can install it using `pip`:

```bash
pip install uv
```

Then, create the project:

```bash
uv init my_python_service
cd my_python_service
```

### Step 2: Create the Python Script for the Service

Inside the project folder, create a Python script that will be run as the service. Let's call it `main.py`.

Create the file `main.py` with the following basic structure:

```python
import time
import logging

logging.basicConfig(filename='/var/log/my_python_service.log', level=logging.INFO)

def main():
    while True:
        logging.info("Service is running...")
        time.sleep(60)

if __name__ == "__main__":
    main()
```

This script will log every minute that the service is running. You can modify the script for your own service logic.

### Step 3: Create the Systemd Service File

Now, we need to create a `systemd` service file to make the Python script run as a service.

Create a file named `my_python_service.service` in the `/etc/systemd/system/` directory. You can use a text editor like `nano` or `vim`:

```bash
sudo nano /etc/systemd/system/my_python_service.service
```

Add the following content to the file:

```ini
[Unit]
Description=My Python Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/your/project/my_python_service/main.py
WorkingDirectory=/path/to/your/project/my_python_service
Restart=always
User=nobody
Group=nogroup

[Install]
WantedBy=multi-user.target
```

Replace `/path/to/your/project/my_python_service` with the actual path to your project directory.

### Step 4: Register and Start the Service

Now, let's enable and start the service using `systemd` commands:

1. Reload `systemd` to recognize the new service:

   ```bash
   sudo systemctl daemon-reload
   ```

1. Enable the service to start on boot:

   ```bash
   sudo systemctl enable my_python_service.service
   ```

1. Start the service:

   ```bash
   sudo systemctl start my_python_service.service
   ```

1. Check the status of the service:

   ```bash
   sudo systemctl status my_python_service.service
   ```

1. To stop the service:

   ```bash
   sudo systemctl stop my_python_service.service
   ```

1. To restart the service:

   ```bash
   sudo systemctl restart my_python_service.service
   ```

### Step 5: Add Instructions to the README.md

Create or modify a `README.md` file in the project directory with the following setup instructions:

````markdown
# My Python Service

This is a simple Python service running as a Linux system service using systemd.

## Setup Instructions

### Prerequisites

- Python 3.12
- `uv` package manager installed

### Installation

1. Clone the repository or create the project:
   ```bash
   uv init my_python_service
   cd my_python_service
````

2. Create a `systemd` service file at `/etc/systemd/system/my_python_service.service`:

   ```ini
   [Unit]
   Description=My Python Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /path/to/your/project/my_python_service/main.py
   WorkingDirectory=/path/to/your/project/my_python_service
   Restart=always
   User=nobody
   Group=nogroup

   [Install]
   WantedBy=multi-user.target
   ```

1. Register and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable my_python_service.service
   sudo systemctl start my_python_service.service
   ```

1. Check the status of the service:

   ```bash
   sudo systemctl status my_python_service.service
   ```

### Logging

The service logs will be written to `/var/log/my_python_service.log`. You can view the log with:

```bash
tail -f /var/log/my_python_service.log
```

### Stopping and Restarting the Service

To stop the service:

```bash
sudo systemctl stop my_python_service.service
```

To restart the service:

```bash
sudo systemctl restart my_python_service.service
```

````

### Step 6: Test the Service

After starting the service, check if it's logging properly to the log file `/var/log/my_python_service.log`.

```bash
tail -f /var/log/my_python_service.log
````

This should show messages like "Service is running..." every minute.

### Conclusion

You’ve now set up a Python project that runs as a system service using `systemd`. The `README.md` contains the setup instructions, and the project uses `uv` for managing the Python environment.
