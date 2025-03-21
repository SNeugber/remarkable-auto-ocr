# Remarkable Auto OCR

This is a utility service intended to automatically sync and convert handwritten Remarkable documents:

1. Fetches files from remarkable tablet over SSH.
1. Converts files to pdf using [rmc](https://github.com/ricklupton/rmc)
1. Converts those files to markdown using the [Google AI Studio](https://aistudio.google.com/)

# Limitations

- As of right now, this is more of a POC that I'm happy with for my own workflow. It could do with tests and cleaning
  up.
- Since I own a Paper Pro tablet, that is what everything is tested with and geared towards right now. I'm planning on
  making it more generic in due course...

# Contents

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Setup](#setup)
- [Dev Setup](#dev-setup)
- [Service Loop](#service-loop)
- [Config](#config)
- [Which Files To Process](#which-files-to-process)
  - [whitelist.csv](#whitelistcsv)
  - [blacklist.csv](#blacklistcsv)
  - [Custom Prompts](#custom-prompts)
- [Saving Data to External Resources](#saving-data-to-external-resources)
  - [`md_repo_path`](#md_repo_path)
  - [`pdf_copy_path`](#pdf_copy_path)
  - [Ubuntu Google Drive Integration](#ubuntu-google-drive-integration)
  - [Windows Google Drive Integration](#windows-google-drive-integration)
- [Known Issues](#known-issues)
  - [Rotated PDFs](#rotated-pdfs)
  - [Finding the tablet IP automatically](#finding-the-tablet-ip-automatically)
- [TODO](#todo)

<!-- mdformat-toc end -->

## Setup

1. [Install Docker](https://docs.docker.com/engine/install/)
1. Set up your tablet for [ssh key authentication](https://remarkable.guide/guide/access/ssh.html).
1. Create a Google AI Studio API key: [Google AI Studio](https://aistudio.google.com/apikey)
1. Create a `data` directory containing:
   1. A whitelist, blacklist, and custom prompts: [Which Files to Process](#which-files-to-process)
   1. A `config.toml` file: [Config](#config)
1. Set up a repository & google drive directory to save the data to:
   [Saving Data to External Resources](#saving-data-to-external-resources)
1. Update [docker-compose.yml](./docker-compose.yml) to mount your paths:
   - The `data` directory at `/data`, containing the whitelist, blacklist, custom prompts, and `config.toml` (by default
     set to `./data`)
   - The docker volume for the google drive integration (if applicable)
   - The path to the repo to save markdown files to (if applicable)
   - The path to your `.gitconfig` file, so that it can save markdown files in the repo (if applicable)
1. Ensure the paths in the `config.toml` match the mounted paths!
1. Start the service: `docker compose up --build -d rao`

## Dev Setup

1. [Install VSCode](https://code.visualstudio.com/download)
1. Install the [devcontainers extension](https://code.visualstudio.com/docs/devcontainers/containers)
1. Update [dev.docker-compose.yml](./dev.docker-compose.yml) instead of [docker-compose.yml](./docker-compose.yml) above
1. Open project in the dev container
1. Run app through vscode using the configurations in `launch.json`

## Service Loop

The app runs every `Config.check_interval` seconds. At each iteration it:

1. reloads `config.toml`, `whitelist.csv`, `blacklist.csv`, to enable changes while the service is running
1. fetches the list of documents from the tablet
1. loads any documents which have been modified since last time
1. parses the documents to pdf
1. parses any documents not marked as `pdf_only` to markdown
1. saves the `.pdf`/`.md` files (and pushes the files to the git repo and/or google drive folder, if set)
1. updates the database to mark the files as processed

## Config

The config file should be in the home directory under `env.toml` and contain the following keys:

```toml
[remarkable-auto-ocr-app]

remarkable_ip_address = "192.168.1.xxx"   # TBD: fetch this automatically
ssh_key_path = "/root/.ssh/id_rsa"        # for example
check_interval = 120                      # how often to check for files to sync
google_api_key = "your google api key"    # see below
whitelist_path = "/data/whitelist.csv"    # see below
blacklist_path = "/data/blacklist.csv"    # see below
render_path = "/data/renders"             # where to save rendered pdf/md files to, before copying them elsewhere
md_repo_path = ""                         # see below
pdf_copy_path = ""                        # see below
prompts_dir = "/data/prompts"             # see below
db_data_dir = "/data/"                    # see below
model = "gemini-1.5-flash"                # the model to use for markdown conversion
default_prompt = "Turn this document into markdown"
```

⚠️ **Paths must be relative to their mount paths in the `[dev.]docker-compose.yml` file!**

Further configuration parameters can be found in [config.py](/src/config.py).

## Which Files To Process

To select which files should be processed and how to do so, you can create two files: `whitelist.csv` and
`blacklist.csv`.

⚠️ **Without a `whitelist.csv`, all files on the tablet will be processed!**

### whitelist.csv

The whitelist is a list of paths that select which files to process. This can be paths to entire directories, or
specific file paths. It should be structured as follows:

| path  | prompt_path    | pdf_only | force_reprocess |
| ----- | -------------- | -------- | --------------- |
| A/B   | prompt_ab.txt  | False    |                 |
| A/B/C | prompt_abc.txt | False    |                 |
| C     |                | True     | always          |
| D     | D/prompt.txt   | True     | once            |

- The `path` column specifies which files on the tablet to process.
- The `prompt_path` column specifies whether a [prompt](#custom-prompts) different to the default prompt in the
  [config](#config) should be used.
- The `pdf_only` column indicates whether files should be rendered as pdf only, instead of turning them into markdown by
  default.
- The `force_reprocess` column indicates whether file(s) should be reprocessed, regardless of whether they are outdated
  or not. Must be one of \[`once`, `always`\].
  - If it's `once` the value will be automatically cleared for the next sync run

If the path is a directory then all files in that directory will be processed with the given configuration.

➡️ More specific paths take precendence: in the example above `A/B/C` will use the prompt `prompt_abc.txt`, while all
other files in `A/B/` will use the prompt in `prompt_ab.txt`

⚠️ **If a prompt file referenced in `whitelist.csv` can not be found, all files that match this path in the whitelist
will be skipped!** ⚠️

### blacklist.csv

The blacklist is a list of paths that matched in the whitelist, should be ignored for processing, e.g. if only one file
in an entire directory should be ignored.

```markdown
| path   |
|--------|
| A/B/D  |
| A/B/F  |
```

### Custom Prompts

Custom prompts should be stored as text files relative to the `prompts_dir` set in the [config](#config).

**example_prompt.txt**

```txt
Render this document as a markdown table. Ensure that the table contains columns `A`, `B`, and `C`.
```

## Saving Data to External Resources

The config options `md_repo_path` and `pdf_copy_path` allow for exporting the generated markdown/pdf files:

### `md_repo_path`

This path should be set to the root directory of a git repo to push the generated markdown files to. It will
create/update a `README.md` file as well as a `documents` subdirectory. The markdown files will be copied to the
`documents` subdirectory, in the same directory structure as found on the tablet. When the copying is complete, it will
commit and push the files/changes.

### `pdf_copy_path`

This path should be set to the directory where all generated pdfs should be copied to. This is used primarily for
auto-syncing to e.g. google drive.

### Ubuntu Google Drive Integration

For integration with googe drive on ubuntu, the `pdf_copy_path` path should be in the format described
[here](https://askubuntu.com/a/1336612), pointing at the directory where the google drive folder is mounted to.

For example:

```text
/run/user/<UID>/gvfs/google-drive\:host\=gmail.com\,user\=<gmail.user.name>/My\ Drive/<TargetDir>/
```

You just need to replace `<UID>` with your user id and `<TargetDir>` with the name of the folder in google drive you
want to save the pdfs in.

⚠️ Since the app is running in a container, we need to ensure that this folder is mounted:

❗Due to
[a limitation regarding colons in volumes in `docker compose`](https://forums.docker.com/t/docker-compose-bind-mount-with-colon-comma-in-path-not-working/146533/3),
we can't use the normal `volumes` option, but need to the slightly more invovled `bind` syntax:

```yaml
services:
rao:
   ...
   volumes:
      - gdrive:/data/gdrive

volumes:
   gdrive:
      driver: local
      driver_opts:
         type: none
         o: bind
         device: "/run/user/1000/gvfs/google-drive:host=gmail.com,user=samuel.neugber/"
```

### Windows Google Drive Integration

In `docker desktop`, ensure that the drive created by the google drive application is shared. Then you can mount it as a
volume in `docker-compose.yml`, e.g. for drive letter `G:`:

```yaml
services:
rao:
   ...
   volumes:
      - gdrive:/data/gdrive

volumes:
   gdrive:
      driver: local
      driver_opts:
         type: none
         o: bind
         device: "G:\\"
```

## Known Issues

### Rotated PDFs

`remarks` doesn't appear to deal with rotated PDFs well it seems.

### Finding the tablet IP automatically

I'd ideally like to find the IP of the tablet automatically using the MAC address and `arp-scan`. But I'm using rootless
docker, and in there I can't run `arp-scan`. So either I use rootfull docker for deploying the final package, or I have
to make certain apt packages mandatory during installation and limit the app to run in ubuntu/linux.

## TODO

1. Tests & Code Cleanup
1. Pass in scaling factor to `remarks.process_document` to scale templates to paper pro dimensions

# Acknowledgements

[rmc](https://github.com/ricklupton/rmc) and [remarks](https://github.com/Azeirah/remarks) do all the the heavy lifting
of parsing the remarkable files to PDF.
