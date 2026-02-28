#!/usr/bin/env python3

"""
POZNOTE CLI TOOL
================
A minimalist utility to interact with a Poznote instance directly from the 
Linux terminal via pipes and flags.

INPUT EXPECTATIONS:
- This script EXPECTS piped input for Posting and Updating.
- Advanced Feature (-c) allows posting directly from the clipboard.
- Example: `ls -la | poznote-cli.py` or `poznote-cli.py -c`

CONFIGURATION:
- Requires a file at ~/.poznote.conf with:
    POZNOTE_URL="https://your-server.com"
    POZNOTE_USER="your_username"
    POZNOTE_PASS="your_password"
    POZNOTE_USER_ID="your_id"
    POZNOTE_WORKSPACE="Clip"
    POZNOTE_ADVANCED_FEATURES="true" (Enables -L, -s, -U, and -D)

NOTE ON SEARCH (-s):
The Poznote API currently returns a list of IDs for results. While the browser 
displays all notes with the pattern, this CLI fetches and displays the full 
content of the first result found for quick access.

CORE ACTIONS:
- POST:   Capture stdin (or clipboard via -c) and save as a new note.
- READ:   Retrieve the most recent note (-L) or search by keyword (-s).
- UPDATE: Edit existing notes by ID (-U) using new piped input.
- DELETE: Remove notes by ID (-D).
- BURN:   Post a note and interactively delete it after a keypress (-b).
"""

import sys
import os
import subprocess
import shutil
import argparse
import time
import json

# 1. Dependency Guard: Ensure required non-standard libraries are installed
try:
    import requests
    from requests.auth import HTTPBasicAuth
    from dotenv import load_dotenv
    from pathlib import Path
except ImportError:
    print("Error: Missing dependencies.")
    print("Please run: sudo apt install python3-requests python3-dotenv")
    sys.exit(10)

# 2. Clipboard Integration: Supports Copying (for URLs) and Pasting (for -c flag)
def copy_to_clipboard(text):
    if shutil.which("xclip"):
        subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE).communicate(input=text.encode())
    elif shutil.which("wl-copy"):
        subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE).communicate(input=text.encode())

def get_clipboard_text():
    """Reads text from the system clipboard using xclip or wl-paste."""
    try:
        if shutil.which("xclip"):
            return subprocess.check_output(['xclip', '-selection', 'clipboard', '-o']).decode().strip()
        elif shutil.which("wl-paste"):
            return subprocess.check_output(['wl-paste']).decode().strip()
    except Exception:
        return None
    return None

# 3. Config Manager: Reads the ~/.poznote.conf file and extracts credentials/feature toggles
def get_config():
    config_path = Path("~/.poznote.conf").expanduser()
    if config_path.exists():
        load_dotenv(dotenv_path=config_path)
    
    url = os.getenv('POZNOTE_URL')
    user = os.getenv('POZNOTE_USER')
    password = os.getenv('POZNOTE_PASS')
    user_id = os.getenv('POZNOTE_USER_ID', '1')
    workspace = os.getenv('POZNOTE_WORKSPACE', 'Poznote')
    adv_feat = os.getenv('POZNOTE_ADVANCED_FEATURES', 'false').lower() == 'true'
    
    if not all([url, user, password]):
        print(f"Error: Credentials missing in {config_path}")
        sys.exit(12)
    return url.rstrip('/'), user, password, user_id, workspace, adv_feat

# 4. Debug Curl Helper: Prints the equivalent curl command
def print_debug_curl(method, url, headers, auth, payload=None):
    auth_str = f"{auth.username}:{auth.password}"
    cmd = [f"curl -X {method} '{url}'", f"-u '{auth_str}'"]
    for k, v in headers.items():
        cmd.append(f"-H '{k}: {v}'")
    if payload:
        cmd.append(f"-d '{json.dumps(payload)}'")
    print("\n--- DEBUG: CURL COMMAND ---")
    print(" ".join(cmd))
    print("---------------------------\n")

# 5. Helper for API Requests: Standardizes headers and authentication
def poznote_request(method, endpoint, payload=None, params=None, debug=False):
    base_url, user, password, user_id, _, _ = get_config()
    url = f"{base_url}{endpoint}"
    headers = {"X-User-ID": str(user_id), "Content-Type": "application/json"}
    auth = HTTPBasicAuth(user, password)
    
    if debug:
        print_debug_curl(method, url, headers, auth, payload)

    try:
        response = requests.request(method, url, json=payload, params=params, headers=headers, auth=auth, timeout=10)
        response.raise_for_status()
        return response.json() if response.content else {"success": True}
    except requests.exceptions.RequestException as e:
        print(f"Error: API Request failed: {e}")
        sys.exit(13)

# 6. Read Action: Fetches the ID then does a deep fetch for content
def list_last_note(debug=False):
    base_url, _, _, _, workspace, _ = get_config()
    data = poznote_request("GET", "/api/v1/notes", params={"workspace": workspace}, debug=debug)
    notes = data.get("notes", [])
    
    if not notes:
        print(f"No notes found in workspace: {workspace}")
        return

    last_id = notes[0].get("id")
    detail_data = poznote_request("GET", f"/api/v1/notes/{last_id}", debug=debug)
    note = detail_data.get("note", {})
    
    print(f"--- Latest Note in {workspace} [ID: {last_id}] ---")
    print(f"{note.get('heading', 'No Title')}")
    print(f"{note.get('content', '')}")
    print("-" * 40)
    
    full_url = f"{base_url}/index.php?workspace={workspace}&note={last_id}"
    print(f"URL: {full_url}")
    copy_to_clipboard(full_url)

# 6b. Search Action: Finds ID via search, then deep fetches content for the first hit
def search_notes(query, debug=False):
    base_url, _, _, _, workspace, _ = get_config()
    data = poznote_request("GET", "/api/v1/notes", params={"workspace": workspace, "search": query}, debug=debug)
    notes = data.get("notes", [])
    
    if not notes:
        print(f"No notes found matching '{query}' in workspace: {workspace}")
        return

    first_id = notes[0].get("id")
    detail_data = poznote_request("GET", f"/api/v1/notes/{first_id}", debug=debug)
    note = detail_data.get("note", {})
    
    print(f"First match for '{query}' in {workspace} [ID: {first_id}]")
    print(f"{note.get('heading', 'No Title')}")
    print(f"{note.get('content', '')}")
    print("-" * 40)
    
    full_url = f"{base_url}/index.php?workspace={workspace}&note={first_id}"
    print(f"View in browser: {full_url}")
    copy_to_clipboard(full_url)

# 7. Delete Action: Permanently removes a note by its numeric ID
def delete_note(note_id, silent=False, debug=False):
    poznote_request("DELETE", f"/api/v1/notes/{note_id}", debug=debug)
    if not silent:
        print(f"Success: Note {note_id} deleted.")

# 8. Update Action: Replaces note content using a PATCH request and piped input
def update_note(note_id, debug=False):
    if sys.stdin.isatty():
        print("Error: No piped input detected for update.")
        sys.exit(11)
    
    input_data = sys.stdin.read().strip()
    if not input_data: return

    payload = {"content": input_data}
    poznote_request("PATCH", f"/api/v1/notes/{note_id}", payload=payload, debug=debug)
    print(f"Success: Note {note_id} updated via PATCH.")

# 9. Post Action: Creates a new note from piped data or clipboard (-c)
def post_to_poznote(tags=None, from_clipboard=False, show_delete=False, show_update=False, burn=False, debug=False):
    base_url, _, _, _, workspace, _ = get_config()

    if from_clipboard:
        input_data = get_clipboard_text()
    else:
        if sys.stdin.isatty():
            print("Error: No piped input. Use -c to post from clipboard.")
            sys.exit(11)
        input_data = sys.stdin.read().strip()

    if not input_data: sys.exit(0)

    payload = {
        "heading": f"cli-{int(time.time())}",
        "content": input_data,
        "workspace": workspace,
        "type": "markdown"
    }
    if tags: payload["tags"] = tags.split(',')

    data = poznote_request("POST", "/api/v1/notes", payload=payload, debug=debug)
    note_id = data.get("note", {}).get("id")
    
    full_url = f"{base_url}/index.php?workspace={workspace}&note={note_id}"
    print(f"Success: {full_url}")
    copy_to_clipboard(full_url)

    script_name = os.path.basename(__file__)
    if show_delete and note_id:
        print(f"To delete this note run: {script_name} -D {note_id}")
    if show_update and note_id:
        print(f"To update this note run: [command] | {script_name} -U {note_id}")

    if burn and note_id:
        # I am leaving intentionally the emoji of fire because it actually looks cool. 
        # Even thought it might look like vibe code
        print(f"\n🔥 BURN MODE: Note will be deleted from {workspace} when you proceed.")
        try:
            with open('/dev/tty', 'r') as tty:
                print("Press [Enter] to delete...", end="", flush=True)
                tty.readline()
        except Exception:
            input("Press [Enter] to delete...")
        delete_note(note_id, silent=False, debug=debug)

# 10. CLI Entry Point: Parses flags and routes to the correct function
if __name__ == "__main__":
    _, _, _, _, workspace, adv_feat = get_config()

    # Define help text or suppress based on Advanced Features toggle
    l_help = "List the most recent note" if adv_feat else argparse.SUPPRESS
    s_help = "Search notes by keyword" if adv_feat else argparse.SUPPRESS
    D_help = "Delete a specific note by ID" if adv_feat else argparse.SUPPRESS
    U_help = "Update a specific note by ID" if adv_feat else argparse.SUPPRESS

    parser = argparse.ArgumentParser(
        description="Poznote CLI Tool: Post, update, or delete notes from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("-d", action="store_true", help="Show command to self-delete")
    parser.add_argument("-b", "--burn", action="store_true", help="Interactively delete note after posting")
    parser.add_argument("-u", action="store_true", help="Show command to self-update")
    parser.add_argument("-t", "--tags", help="Comma-separated tags")
    parser.add_argument("-c", "--clipboard", action="store_true", help="Post content from clipboard")
    parser.add_argument("--debug", action="store_true", help="Display equivalent curl command")
    
    # Advanced Features (Hidden/Suppressed if adv_feat is False)
    parser.add_argument("-D", "--delete", metavar="ID", help=D_help)
    parser.add_argument("-U", "--update", metavar="ID", help=U_help)
    parser.add_argument("-L", "--last", action="store_true", help=l_help)
    parser.add_argument("-s", "--search", metavar="QUERY", help=s_help)
    
    args = parser.parse_args()

    # Guard clause: Prevent execution of advanced features if disabled in config
    if any([args.last, args.search, args.delete, args.update]) and not adv_feat:
        print("Error: Advanced features are disabled in ~/.poznote.conf")
        sys.exit(12)

    if args.last:
        list_last_note(debug=args.debug)
    elif args.search:
        search_notes(args.search, debug=args.debug)
    elif args.delete:
        delete_note(args.delete, debug=args.debug)
    elif args.update:
        update_note(args.update, debug=args.debug)
    else:
        post_to_poznote(
            tags=args.tags, 
            from_clipboard=args.clipboard, 
            show_delete=args.d, 
            show_update=args.u, 
            burn=args.burn, 
            debug=args.debug
        )

# --- CREDITS & DOCUMENTATION ---
# Poznote Project: https://github.com/timothepoznanski/poznote
# Version Compatibility: Built for Poznote v1.x
# -------------------------------

# --- EXIT CODE REFERENCE ---
# 0:  Success
# 10: Missing Python Libraries (requests/dotenv)
# 11: No Piped Input (Standard Input is a TTY)
# 12: Missing Configuration (POZNOTE_URL, USER, or PASS)
# 13: API or Network Error (Timeout, 401 Unauthorized, etc.)
# -------------------------------