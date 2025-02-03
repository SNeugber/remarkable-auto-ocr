# Remarkable Auto OCR

This is a utility service intended to automatically sync and convert handwritten Remarkable documents:

1. Fetches files from remarkable tablet over SSH.
1. Converts files to pdf using [rmc](https://github.com/ricklupton/rmc)
1. Converts those files to markdown using the [Google AI Studio](https://aistudio.google.com/)

## Dev Setup

1. Install VSCode
1. Install devcontainers extension
1. Set up your tablet for [ssh key authentication](https://remarkable.guide/guide/access/ssh.html).
1. Create a whitelist, blacklist, and custom prompts: [Which Files to Process](#which-files-to-process)
1. Create a Google AI Studio API key: [Google AI Studio](https://aistudio.google.com/apikey)
1. Create a file `env.toml` in your home directory: [Config](#config)
1. Launch project in the dev container
1. Run app through vscode using the configurations in `launch.json`

## User Setup

TBD...

## Config

The config file should be in the home directory under `env.toml` and contain the following keys:

```toml
[remarkable-auto-ocr-app]


remarkable_ip_address = "192.168.1.xxx"   # TBD: fetch this automatically
ssh_key_path = "/root/.ssh/id_rsa"        # for example
check_interval = 120                      # how often to check for files to sync
google_api_key = "your google api key"    # see below
whitelist_path = "./data/whitelist.csv"   # see below
blacklist_path = "./data/blacklist.csv"   # see below
prompts_dir = "./data/prompts"            # see below
default_prompt = "Turn this document into markdown"
```

Further configuration parameters can be found in [config.py](/src/config.py).

## Which Files To Process

To select which files should be processed and how to do so, you can create two files: `whitelist.csv` and `blacklist.csv`.

⚠️ **Without a `whitelist.csv`, all files on the tablet will be processed!** ⚠️

### whitelist.csv

The whitelist is a list of paths that select which files to process. This can be paths to entire directories, or specific file paths. It should be structured as follows:

```markdown
| path   | prompt_path    | pdf_only |
|--------|----------------|----------|
| A/B    | prompt_ab.txt  | False    |
| A/B/C  | prompt_abc.txt | False    |
| C      |                | True     |
| D      | D/prompt.txt   | True     |
```

- The `path` column specifies which files on the tablet to process.
- The `prompt_path` column specifies whether a [prompt](#custom-prompts) different to the default prompt in the [config](#config) should be used.
- The `pdf_only` column indicates whether files should be rendered as pdf only, instead of turning them into markdown by default.

If the path is a directory then all files in that directory will be processed with the given configuration.

➡️ More specific paths take precendence: in the example above `A/B/C` will use the prompt `prompt_abc.txt`, while all other files in `A/B/` will use the prompt in `prompt_ab.txt`

⚠️ **If a prompt file referenced in `whitelist.csv` can not be found, all files that match this path in the whitelist will be skipped!** ⚠️

### blacklist.csv

The blacklist is a list of paths that matched in the whitelist, should be ignored for processing, e.g. if only one file in an entire directory should be ignored.

```markdown
| path   |
|--------|
| A/B/D  |
| A/B/F  |
```

## Custom Prompts

Custom prompts should be stored as text files relative to the `prompts_dir` set in the [config](#config).

##### *example_prompt.txt*

```txt
Render this document as a markdown table. Ensure that the table contains columns `A`, `B`, and `C`.
Do not include any text other than the raw markdown in the output.
```

## TODO

### Prios

1. Replace sqlite db with dataframes
1. Save hash of prompt to check if document needs to be re-rendered
1. Better place for user config
1. Try to fetch IP automatically, might need to run this outside of docker
1. Add files to gdrive folder, see [here](https://askubuntu.com/a/1336612)
   - This works, the path just needs to include the full thing, e.g. `cp -R ./* /run/user/<UID>/gvfs/google-drive\:host\=gmail.com\,user\=<gmail.user.name>/My\ Drive/<TargetDir>/`
1. Build & deploy as service in the background
1. Create relases by building it in CI
1. Tests

### Dev Setup

1. Create VSCode task to create `~/.env.toml`
1. VSCode & UV seem to not be 100% happy yet
1. Looks like WSL + devcontianer means I can't find the IP address automatically?

### General App

1. Save sqlite DB somewhere as well, e.g. GDrive
1. Run the whole thing as a service in the background
   - Use [nuitka](https://github.com/astral-sh/uv/issues/5802#issuecomment-2273058176) to make it distributable

### Remarkable Integration

1. Find IP address based on MAC address

### Document Parsing

1. Explore other methods/models

   - NotebookLLM API available yet?
   - Run small Deepseek locally

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
