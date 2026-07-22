"""
YouTube Auto Upload
--------------------
A small desktop app that:
  1. Watches one or more input folders for video files
  2. Uploads each video to YouTube (official Data API v3, OAuth login)
  3. Moves successfully-uploaded files into a "Finished" folder

Settings (input folders, output folder, privacy) are remembered between runs,
so the user just opens the app and clicks Run again.
"""

import os
import sys
import json
import queue
import shutil
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

APP_NAME = "YouTube Auto Upload"

# Everything persistent lives in %APPDATA%\YouTubeAutoUpload so it survives the
# .exe being moved around.
CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "YouTubeAutoUpload"
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATH = os.path.join(CONFIG_DIR, "token.json")
CLIENT_SECRET_PATH = os.path.join(CONFIG_DIR, "client_secret.json")

# Uploading requires the full youtube.upload scope.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

VIDEO_EXTS = {
    ".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
}

PRIVACY_CHOICES = ["private", "unlisted", "public"]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    default = {
        "input_folders": [],
        "output_folder": "",
        "privacy": "private",
    }
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        default.update({k: data[k] for k in default if k in data})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    if default["privacy"] not in PRIVACY_CHOICES:
        default["privacy"] = "private"
    return default


def save_config(cfg):
    ensure_config_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# YouTube auth + upload
# ---------------------------------------------------------------------------

def get_credentials():
    """Load stored credentials, refreshing or running the OAuth flow as needed.

    Raises FileNotFoundError if no client_secret.json has been provided yet.
    """
    ensure_config_dir()
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                TOKEN_PATH, SCOPES
            )
        except (ValueError, OSError):
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            return creds
        except Exception:
            creds = None  # fall through to full re-login

    # Need a fresh login.
    if not os.path.exists(CLIENT_SECRET_PATH):
        raise FileNotFoundError(
            "No client_secret.json found. Use the 'Set client_secret.json' "
            "button to select your Google OAuth credentials file first."
        )

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_PATH, SCOPES
    )
    # Opens the user's browser, spins up a tiny local server for the redirect.
    creds = flow.run_local_server(port=0, prompt="consent")
    _save_token(creds)
    return creds


def _save_token(creds):
    ensure_config_dir()
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def build_service(creds):
    return build("youtube", "v3", credentials=creds)


def upload_video(service, file_path, privacy, log):
    """Upload one video. Returns the new video id on success."""
    title = os.path.splitext(os.path.basename(file_path))[0]
    body = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": "",
            "categoryId": "22",  # People & Blogs (a safe default)
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(file_path, chunksize=1024 * 1024 * 8, resumable=True)
    request = service.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    last_pct = -1
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct != last_pct:
                log(f"    ...{pct}%")
                last_pct = pct
    return response.get("id")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("720x620")
        self.minsize(640, 560)

        self.cfg = load_config()
        self.log_queue = queue.Queue()
        self.worker = None
        self.cancel_flag = threading.Event()

        self._build_ui()
        self._refresh_input_list()
        self.output_var.set(self.cfg.get("output_folder", ""))
        self.privacy_var.set(self.cfg.get("privacy", "private"))
        self._update_auth_status()

        self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- UI construction ----------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Input folders
        in_frame = ttk.LabelFrame(self, text="Input folders (videos to upload)")
        in_frame.pack(fill="both", expand=False, **pad)

        self.input_list = tk.Listbox(in_frame, height=6, selectmode=tk.EXTENDED)
        self.input_list.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=10)

        in_btns = ttk.Frame(in_frame)
        in_btns.pack(side="right", fill="y", padx=(0, 10), pady=10)
        ttk.Button(in_btns, text="Add folder", command=self._add_input).pack(fill="x", pady=2)
        ttk.Button(in_btns, text="Remove", command=self._remove_input).pack(fill="x", pady=2)

        # Output folder
        out_frame = ttk.LabelFrame(self, text="Finished folder (uploaded videos moved here)")
        out_frame.pack(fill="x", **pad)
        self.output_var = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=(10, 6), pady=10
        )
        ttk.Button(out_frame, text="Browse", command=self._pick_output).pack(
            side="right", padx=(0, 10), pady=10
        )

        # Options row
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", **pad)

        ttk.Label(opt_frame, text="Privacy:").pack(side="left", padx=(10, 4))
        self.privacy_var = tk.StringVar()
        self.privacy_combo = ttk.Combobox(
            opt_frame, textvariable=self.privacy_var, values=PRIVACY_CHOICES,
            state="readonly", width=12,
        )
        self.privacy_combo.pack(side="left")

        self.auth_label = ttk.Label(opt_frame, text="", foreground="#555")
        self.auth_label.pack(side="left", padx=20)

        ttk.Button(opt_frame, text="Set client_secret.json", command=self._pick_client_secret).pack(
            side="right", padx=(4, 10)
        )
        ttk.Button(opt_frame, text="Sign in / out", command=self._toggle_auth).pack(side="right")

        # Action buttons
        act_frame = ttk.Frame(self)
        act_frame.pack(fill="x", **pad)
        self.run_btn = ttk.Button(act_frame, text="Run", command=self._on_run)
        self.run_btn.pack(side="left", padx=10)
        self.cancel_btn = ttk.Button(act_frame, text="Cancel", command=self._on_cancel, state="disabled")
        self.cancel_btn.pack(side="left")

        # Log
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=12, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y", pady=10, padx=(0, 10))
        self.log_text.configure(yscrollcommand=scroll.set)

    # -- Small UI helpers ---------------------------------------------------

    def _refresh_input_list(self):
        self.input_list.delete(0, tk.END)
        for folder in self.cfg.get("input_folders", []):
            self.input_list.insert(tk.END, folder)

    def _add_input(self):
        folder = filedialog.askdirectory(title="Select a folder of videos")
        if folder:
            folder = os.path.normpath(folder)
            if folder not in self.cfg["input_folders"]:
                self.cfg["input_folders"].append(folder)
                self._refresh_input_list()
                self._persist()

    def _remove_input(self):
        sel = list(self.input_list.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            del self.cfg["input_folders"][idx]
        self._refresh_input_list()
        self._persist()

    def _pick_output(self):
        folder = filedialog.askdirectory(title="Select the Finished folder")
        if folder:
            self.output_var.set(os.path.normpath(folder))
            self._persist()

    def _pick_client_secret(self):
        path = filedialog.askopenfilename(
            title="Select your Google OAuth client_secret.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)  # sanity check it's valid JSON
            ensure_config_dir()
            shutil.copyfile(path, CLIENT_SECRET_PATH)
            self.log("Saved client_secret.json.")
            self._update_auth_status()
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showerror(APP_NAME, f"Could not read that file:\n{e}")

    def _toggle_auth(self):
        if os.path.exists(TOKEN_PATH):
            # Sign out
            try:
                os.remove(TOKEN_PATH)
            except OSError:
                pass
            self.log("Signed out.")
            self._update_auth_status()
        else:
            # Sign in (runs the browser flow on a thread so UI stays responsive)
            self.log("Opening browser to sign in to YouTube...")
            threading.Thread(target=self._sign_in_thread, daemon=True).start()

    def _sign_in_thread(self):
        try:
            get_credentials()
            self.log("Signed in successfully.")
        except Exception as e:
            self.log(f"Sign-in failed: {e}")
        self.after(0, self._update_auth_status)

    def _update_auth_status(self):
        if not os.path.exists(CLIENT_SECRET_PATH):
            self.auth_label.config(text="No credentials file set", foreground="#b00")
        elif os.path.exists(TOKEN_PATH):
            self.auth_label.config(text="Signed in", foreground="#080")
        else:
            self.auth_label.config(text="Not signed in", foreground="#b60")

    def _persist(self):
        self.cfg["output_folder"] = self.output_var.get().strip()
        self.cfg["privacy"] = self.privacy_var.get() or "private"
        save_config(self.cfg)

    # -- Logging ------------------------------------------------------------

    def log(self, msg):
        self.log_queue.put(msg)

    def _drain_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    # -- Run / cancel -------------------------------------------------------

    def _on_run(self):
        if self.worker and self.worker.is_alive():
            return
        self._persist()

        if not self.cfg["input_folders"]:
            messagebox.showwarning(APP_NAME, "Add at least one input folder first.")
            return
        out = self.cfg["output_folder"]
        if not out:
            messagebox.showwarning(APP_NAME, "Select a Finished folder first.")
            return
        if not os.path.exists(CLIENT_SECRET_PATH):
            messagebox.showwarning(
                APP_NAME,
                "No credentials set. Click 'Set client_secret.json' and choose "
                "your Google OAuth file first.",
            )
            return

        self.cancel_flag.clear()
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.cancel_flag.set()
            self.log("Cancel requested; finishing current file then stopping...")

    def _run_worker(self):
        try:
            self.log("Authenticating...")
            creds = get_credentials()
            service = build_service(creds)
            self.after(0, self._update_auth_status)

            out_folder = self.cfg["output_folder"]
            os.makedirs(out_folder, exist_ok=True)
            privacy = self.cfg["privacy"]

            files = self._collect_videos()
            if not files:
                self.log("No video files found in the input folders.")
                return

            self.log(f"Found {len(files)} video(s). Privacy = {privacy}.")
            ok = 0
            for path in files:
                if self.cancel_flag.is_set():
                    self.log("Stopped by user.")
                    break
                name = os.path.basename(path)
                self.log(f"Uploading: {name}")
                try:
                    vid = upload_video(service, path, privacy, self.log)
                    self.log(f"  Uploaded (id={vid}). Moving to Finished folder.")
                    self._move_to_output(path, out_folder)
                    ok += 1
                except HttpError as e:
                    self.log(f"  API error, skipped: {e}")
                except Exception as e:
                    self.log(f"  Failed, skipped: {e}")

            self.log(f"Done. {ok}/{len(files)} uploaded.")
        except FileNotFoundError as e:
            self.log(str(e))
        except Exception as e:
            self.log("Unexpected error:\n" + traceback.format_exc())
        finally:
            self.after(0, self._run_finished)

    def _run_finished(self):
        self.run_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

    def _collect_videos(self):
        found = []
        seen = set()
        for folder in self.cfg["input_folders"]:
            if not os.path.isdir(folder):
                self.log(f"  (skipping missing folder: {folder})")
                continue
            for entry in sorted(os.listdir(folder)):
                full = os.path.join(folder, entry)
                if not os.path.isfile(full):
                    continue
                if os.path.splitext(entry)[1].lower() in VIDEO_EXTS:
                    key = os.path.normcase(os.path.abspath(full))
                    if key not in seen:
                        seen.add(key)
                        found.append(full)
        return found

    def _move_to_output(self, path, out_folder):
        base = os.path.basename(path)
        dest = os.path.join(out_folder, base)
        # Avoid clobbering an existing file of the same name.
        if os.path.exists(dest):
            stem, ext = os.path.splitext(base)
            i = 1
            while os.path.exists(dest):
                dest = os.path.join(out_folder, f"{stem} ({i}){ext}")
                i += 1
        shutil.move(path, dest)

    # -- Close --------------------------------------------------------------

    def _on_close(self):
        self._persist()
        if self.worker and self.worker.is_alive():
            if not messagebox.askokcancel(
                APP_NAME, "An upload is in progress. Quit anyway?"
            ):
                return
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
