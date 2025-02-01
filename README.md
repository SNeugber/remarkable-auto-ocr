# Remarkable Auto OCR

1. Syncs a remarkable tablet over SSH
1. Uploads files to [google OCR](/#TODO_link)
1. Saves in gdrive

# Dev Setup

1. Install VSCode
1. Install devcontainers extension
1. Ensure `~/.ssh` exists
1. Ensure `~/env.toml` exists
1. Launch project in dev container
1. Run app through vscode using the configurations in `launch.json`

## TODO

### Prios

1. Whitelist/blacklist + custom prompts
1. Add files to git repo & commit
1. Add files to gdrive folder
1. Tests

### Dev Setup

1. Create VSCode task to create `~/.env.toml`
1. VSCode & ruff & UV seem to not be 100% happy yet
   - The whole `launch.json` setup doesn't seem to work properly with the debugger yet...
1. How to run and debug app properly with vscode? Seems to not debug quite right...
1. Looks like WSL has problems with ExpressVPN :(

### General App

1. Load some sort of configuration file
1. How to get secrets like google API keys and ssh key for tablet?
1. Save sqlite DB somewhere as well, e.g. GDrive
1. Run the whole thing as a service in the background
   - Use [nuitka](https://github.com/astral-sh/uv/issues/5802#issuecomment-2273058176) to make it distributable
1. Front-end? Low prio...

### Remarkable Integration

1. Fetch data via ssh/sftp using Paramiko ✅
1. Need to load file paths for documents via metadata
1. Provide a whitelist of documents/directories and potentially also specific prompts for each

### Document Parsing

1. Find best model to parse documents into markdown

   - Gemini API
   - NotebookLLM API available yet?
   - Run Deepseek R1 locally? -> Waaaay to big :D

## Setup Instructions

Set up the remarkable for ssh access by following [this guide](https://remarkable.guide/guide/access/ssh.html#setting-up-a-ssh-key)

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

logging.basicConfig(filename="/var/log/my_python_service.log", level=logging.INFO)


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
