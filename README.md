# YouTube Auto Upload

A small Windows desktop app that uploads videos from folders you choose to
YouTube, then moves the finished files into a "Finished" folder. It remembers
your folder choices and privacy setting, so next time you just open it and
click **Run**.

Uses the **official YouTube Data API v3** with OAuth login (no
username/password automation, so it won't break or get flagged the way
browser-scripting tools do).

---

## Download & run

1. Download **`YouTubeAutoUpload.exe`** from the
   [latest release](../../releases/latest).
2. Double-click it. That's the whole install — it's a single file.

> **Where does it store its settings?**
> Nothing is written next to the .exe or on your desktop. The app keeps its
> config, your login token, and your credentials file in
> `%APPDATA%\YouTubeAutoUpload` (a hidden per-user folder). You can run the
> .exe from anywhere — desktop, USB stick, Downloads — and it stays tidy.
> To completely reset the app, delete that folder.

---

## How the app works

1. Open `YouTubeAutoUpload.exe`
2. **Add folder** — pick one or more folders containing videos to upload
3. **Browse** — pick the *Finished* folder (uploaded videos get moved here)
4. Choose a **Privacy** setting (Private / Unlisted / Public)
5. Click **Run**

Each video's YouTube **title** is its filename (without the extension).
On success the file is moved to the Finished folder, so re-running never
double-uploads the same file. Your settings are saved automatically.

---

## One-time setup: getting your `client_secret.json`

The app needs a Google credentials file so it's allowed to upload to *your*
YouTube channel. You create this once, for free, in the Google Cloud Console.
It takes about 10 minutes. Follow these steps in order.

### 1. Create a project
1. Go to **<https://console.cloud.google.com/>** and sign in with the Google
   account that owns your YouTube channel.
2. At the top-left, click the project dropdown → **New Project**.
3. Name it anything (e.g. `YT Uploader`) → **Create**. Wait a few seconds,
   then make sure that new project is selected in the top-left dropdown.

### 2. Enable the YouTube Data API
1. Left menu (☰) → **APIs & Services** → **Library**.
2. Search for **YouTube Data API v3** and click it.
3. Click **Enable**.

### 3. Configure the consent screen
1. Left menu → **APIs & Services** → **OAuth consent screen**
   (in the newer console this is called **Google Auth Platform**).
2. If it says *"not configured yet"*, click **Get started** and fill in:
   - **App name:** anything (e.g. `YT Uploader`)
   - **User support email:** your email
   - **Audience:** choose **External**
   - **Contact information:** your email
   - Agree to the policy → **Create**

### 4. Publish the app (so you don't have to log in every 7 days)
1. Still under the consent screen / Google Auth Platform, open the
   **Audience** tab.
2. Under **Publishing status**, click **Publish app** → **Confirm**.
3. It should now say **In production**.

> You do **not** need to submit for Google verification. Because the app only
> requests permission to upload to your own account, publishing is enough.
> The first time you sign in you'll see a *"Google hasn't verified this app"*
> warning — click **Advanced → Go to (app name) (unsafe)**. That's normal for
> a personal app and only appears once.

### 5. Create the OAuth client and download the JSON
1. Open the **Clients** tab (or **APIs & Services → Credentials**).
2. Click **+ Create client** (or **Create credentials → OAuth client ID**).
3. **Application type: Desktop app** — this is important, it must be *Desktop
   app*.
4. Give it a name (e.g. `YT Uploader Desktop`) → **Create**.
5. In the dialog that appears, click **⬇ Download JSON**.
   (If you closed it, click the client's name in the list, then
   **Download JSON**.)

That downloaded file **is** your `client_secret.json`. The filename will be
long (like `client_secret_1234-abcd.apps.googleusercontent.com.json`) — that's
fine, you don't need to rename it. Keep it somewhere safe; it's private.

### 6. Load it into the app
1. Open the app → click **Set client_secret.json** → select the file you
   downloaded.
2. Click **Sign in / out** → a browser opens → log in and approve access.
   (Accept the "unverified app" warning as noted above.)

You're done. The login is remembered, so you won't be asked again.

---

## Upload quota (please read)

YouTube gives each API project a default quota of **10,000 units/day**, and
**each upload costs ~1,600 units** — so you can upload roughly **6 videos per
day** by default. Beyond that, uploads fail until the quota resets (midnight
Pacific time). You can request a higher quota from Google if you need more.

---

## Building the .exe yourself

You only need this if you want to change the code and rebuild.

1. Install **Python 3.9+** from <https://www.python.org/downloads/> — during
   install, tick **"Add python.exe to PATH"**.
2. Double-click **`build_exe.bat`**.
3. When it finishes, your program is at **`dist\YouTubeAutoUpload.exe`**.

### Run from source (for testing)

```bash
pip install -r requirements.txt
python youtube_auto_upload.py
```

---

## Files in this project

| File | What it is |
|------|-----------|
| `youtube_auto_upload.py` | The application (GUI + upload logic) |
| `requirements.txt` | Python packages it needs |
| `build_exe.bat` | One-click build script → `dist\YouTubeAutoUpload.exe` |
| `README.md` | This file |

---

## Privacy / security note

Your `client_secret.json` and your saved login token stay **only on your own
computer**, in `%APPDATA%\YouTubeAutoUpload`. They are never uploaded to
GitHub and are not part of this repository.
