# Git Change Keeper

> **Track your uncommitted work** — automatically saves every new diff to a folder so you never lose a work-in-progress state.

Git Change Keeper monitors a Git repository for changes and saves the detected diffs into timestamped folders, without requiring you to commit anything.  It compares SHA-256 hashes of each diff to avoid writing duplicate snapshots.

---

## Features

| Feature | Description |
|---|---|
| **GUI launcher** | Settings window lets you pick paths with a file-browser dialog |
| **Background operation** | After you click *Start Monitoring* the window hides and monitoring runs silently |
| **System-tray icon** | A green icon appears near the Windows clock; right-click for the context menu |
| **Tray context menu** | Show Settings · Stop Monitoring · Exit |
| **Hash-based deduplication** | Only genuinely new diffs are saved |
| **Configurable interval** | Any positive integer up to 100 000 seconds |

---

## Requirements

- **Python 3.10+**
- **Windows** (system tray is tested on Windows 10/11; Linux/macOS may need extra system libs for `pystray`)

---

## Installation

```bash
pip install gitpython pillow pystray
```

---

## Usage

### Start the GUI

```bash
python Git_Change_Keeper.py
```

The settings window opens:

1. **Repository Path** — click *Browse…* or type the full path to your local Git repository.
2. **Output Directory** — folder where diff snapshots are saved (default: `Keeper_Of_Changes`).
3. **Check Interval** — how often to check for changes, in seconds (default: `600`).
4. Click **Start Monitoring**.

The window disappears and a small green icon appears in the system tray (near the clock in the bottom-right corner of the screen).

### System-Tray Controls

Right-click the tray icon to open the context menu:

| Menu item | Action |
|---|---|
| **Show Settings** | Brings the settings window back |
| **Stop Monitoring** | Pauses monitoring (icon stays; you can restart from Settings) |
| **Exit** | Stops monitoring and removes the tray icon |

> **Tip:** If the icon is hidden, click the **^** (Show hidden icons) arrow in the taskbar notification area.

---

## Output Structure

Each time new changes are detected a timestamped sub-folder is created:

```
Keeper_Of_Changes/
├── hashes.txt               ← internal hash store (do not edit)
├── changes_20240501_120000/
│   ├── main.py.diff
│   └── utils.py.diff
└── changes_20240501_130015/
    └── README.md.diff
```

Each `.diff` file contains the raw output of `git diff` for that file at the moment the change was detected.

---

## Example

```
python Git_Change_Keeper.py
# → Settings window opens
# → Select C:\Projects\my-repo  as the repository
# → Leave output directory as Keeper_Of_Changes
# → Set interval to 300 (5 minutes)
# → Click Start Monitoring
# → Window hides; green tray icon appears
# → Every 5 minutes new diffs (if any) are saved automatically
```

