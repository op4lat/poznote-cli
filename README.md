# Poznote CLI Tool

A minimalist, high-speed terminal utility for interacting with a [Poznote](https://github.com/timothepoznanski/poznote) instance. Designed for developers who live in the terminal and need to capture logs, snippets, or temporary notes via pipes and flags.

## Features

* **Pipe-Oriented:** Designed to work seamlessly with Unix pipes (e.g., `ls -la | poznote-cli.py`).
* **Burn Mode (`-b`):** Create a note, share the URL, and interactively delete it immediately after use—perfect for temporary credentials or one-time snippets.
* **Clipboard Integration:** Automatically copies the resulting Note URL to your system clipboard. Can also post *from* your clipboard using the `-c` flag.
* **Developer Debugging:** Includes a `--debug` flag that prints the exact `curl` command equivalent for every action.
* **Exit-Code Ready:** Returns specific codes for success, missing dependencies, or API errors for use in larger automation scripts.

---

## Installation

### 1. Prerequisites
Ensure you have Python 3 installed along with the necessary system dependencies:

```bash
# For X11 (Common Linux)
sudo apt install python3-requests python3-dotenv xclip

# For Wayland (Modern Linux)
sudo apt install python3-requests python3-dotenv wl-clipboard

```

### 2. Configuration

Create a configuration file at `~/.poznote.conf`:

```bash
POZNOTE_URL="https://your-poznote-instance.com"
POZNOTE_USER="your_username"
POZNOTE_PASS="your_password"
POZNOTE_USER_ID="1"
POZNOTE_WORKSPACE="Clip"
POZNOTE_ADVANCED_FEATURES="false" # Set to true to unlock search, list, and modify features

```

---

## Usage

| Command | Action |
| --- | --- |
| `echo "Capture this" \| ./poznote-cli.py` | Post piped text as a new note |
| `./poznote-cli.py -c` | Post content currently in your clipboard |
| `./poznote-cli.py -t "tag1,tag2"` | Post with comma-separated tags |
| `echo "secret" \| ./poznote-cli.py -b` | **Burn Mode:** Post and delete after a keypress |
| `./poznote-cli.py --debug` | Run command and show equivalent `curl` syntax |

---

## Hidden Advanced Features

For **security reasons**, features that read your history or modify existing notes are **hidden from the help menu and disabled by default**. This prevents accidental data leaks or unintentional modifications in environments where the script might be used on shared machines.

To unlock these, you must explicitly set `POZNOTE_ADVANCED_FEATURES="true"` in your `.poznote.conf`.

| Flag | Action |
| --- | --- |
| `-L` | **List Last:** Fetches the most recent note, displays it, and copies the URL. |
| `-s "query"` | **Search:** Performs a server-side search and displays the first match. |
| `-U [ID]` | **Update:** Replaces the content of note [ID] using piped input. |
| `-D [ID]` | **Delete:** Permanently removes note [ID] from the server. |

---

## Technical Reference

### Exit Codes

* `0`: Success
* `10`: Missing Python Libraries (`requests` or `dotenv`)
* `11`: No Piped Input detected (Standard Input is a TTY)
* `12`: Configuration Error (Missing credentials or Advanced Features disabled)
* `13`: API or Network Error (Timeout, 401 Unauthorized, etc.)

### AI Collaboration

This tool was developed through an iterative, collaborative process between the author and **Google Gemini**. While Python was used for its robust handling of HTTP streams and system pipes, the interface is designed to maintain the speed and simplicity of a BASH utility.

---

## Quick Start (Alias)

To run the tool simply by typing `poz` from anywhere in your terminal, add this to your `~/.bashrc` or `~/.zshrc`:

```bash
alias poz='python3 /path/to/your/script/poznote-cli.py'

```

## License

This project is licensed under the MIT License.
