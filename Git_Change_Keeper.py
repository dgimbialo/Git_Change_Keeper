import os
import git
import hashlib
import threading
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageDraw
import pystray


# ─── Core monitoring logic ────────────────────────────────────────────────────

def calculate_hash(content):
    """Return SHA-256 hash of *content*."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def load_saved_hashes(hash_store_path):
    """Load previously stored file hashes from *hash_store_path*."""
    if os.path.exists(hash_store_path):
        with open(hash_store_path, 'r') as f:
            return dict(line.strip().split(' ', 1) for line in f if line.strip())
    return {}


def save_hashes(hashes, hash_store_path):
    """Persist *hashes* dict to *hash_store_path*."""
    with open(hash_store_path, 'w') as f:
        for file_path, file_hash in hashes.items():
            f.write(f'{file_path} {file_hash}\n')


def ensure_hash_store_exists(output_base_path, hash_store_path):
    """Create output directory and empty hash store if they do not exist."""
    if not os.path.exists(output_base_path):
        os.makedirs(output_base_path)
    if not os.path.exists(hash_store_path):
        open(hash_store_path, 'w').close()


def save_git_changes(repo_path, output_base_path, hash_store_path):
    """Detect new git diffs in *repo_path* and save them under *output_base_path*."""
    repo = git.Repo(repo_path)

    if not repo.is_dirty(untracked_files=True):
        print('No changes detected.')
        return

    diff_files = repo.git.diff(None, name_only=True).splitlines()
    saved_hashes = load_saved_hashes(hash_store_path)
    new_hashes = {}
    changes_saved = False
    output_path = None

    for file_path in diff_files:
        file_path = file_path.strip()
        if not file_path:
            continue
        full_file_path = os.path.join(repo_path, file_path)
        if not os.path.exists(full_file_path):
            print(f'File does not exist in the repository: {file_path}')
            continue
        try:
            diff_content = repo.git.diff('--', file_path)
            current_hash = calculate_hash(diff_content)
            if file_path not in saved_hashes or saved_hashes[file_path] != current_hash:
                if not changes_saved:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_path = os.path.join(output_base_path, f'changes_{timestamp}')
                    os.makedirs(output_path, exist_ok=True)
                with open(os.path.join(output_path, f'{os.path.basename(file_path)}.diff'), 'w') as f:
                    f.write(diff_content)
                new_hashes[file_path] = current_hash
                changes_saved = True
        except git.exc.GitCommandError as e:
            print(f'Error with file {file_path}: {e}')

    if changes_saved:
        print(f'Changes saved in folder: {output_path}')
        saved_hashes.update(new_hashes)
        save_hashes(saved_hashes, hash_store_path)
    else:
        print('No new changes to save.')


# ─── Background monitor thread ────────────────────────────────────────────────

class Monitor:
    """Runs save_git_changes periodically in a background daemon thread."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, repo_path, check_interval, output_base_path):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(repo_path, check_interval, output_base_path),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self, repo_path, check_interval, output_base_path):
        hash_store_path = os.path.join(output_base_path, 'hashes.txt')
        ensure_hash_store_exists(output_base_path, hash_store_path)
        while not self._stop_event.is_set():
            print(f'Checking for changes: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            try:
                save_git_changes(repo_path, output_base_path, hash_store_path)
            except Exception as e:
                print(f'Monitoring error: {e}')
            self._stop_event.wait(check_interval)


# ─── System-tray icon ─────────────────────────────────────────────────────────

def _create_tray_image():
    """Build a simple 64×64 green circle icon with three white bars (diff/patch symbol)."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dark-green circle background
    draw.ellipse([2, 2, size - 2, size - 2], fill=(34, 120, 34, 255))
    # Two thin white horizontal bars to suggest a diff/patch
    bar_w, bar_h = 32, 5
    x0 = (size - bar_w) // 2
    draw.rectangle([x0, 18, x0 + bar_w, 18 + bar_h], fill=(255, 255, 255, 220))
    draw.rectangle([x0, 30, x0 + bar_w - 8, 30 + bar_h], fill=(255, 255, 255, 160))
    draw.rectangle([x0, 42, x0 + bar_w, 42 + bar_h], fill=(255, 255, 255, 220))
    return img


# ─── Main application ─────────────────────────────────────────────────────────

class App:
    """Orchestrates the settings GUI, tray icon, and monitoring thread."""

    def __init__(self):
        self._monitor = Monitor()
        self._tray = None
        self._tray_started = False

        # Build tkinter root (kept alive but possibly hidden)
        self._root = tk.Tk()
        self._root.title('Git Change Keeper')
        self._root.resizable(False, False)
        self._root.protocol('WM_DELETE_WINDOW', self._on_window_close)
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = self._root
        pad = {'padx': 8, 'pady': 5}

        frame = ttk.Frame(root, padding=14)
        frame.grid(sticky='nsew')

        # Repository path
        ttk.Label(frame, text='Repository Path:').grid(row=0, column=0, sticky='w', **pad)
        self._repo_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._repo_var, width=42).grid(row=0, column=1, **pad)
        ttk.Button(frame, text='Browse…', command=self._browse_repo).grid(row=0, column=2, **pad)

        # Output directory
        ttk.Label(frame, text='Output Directory:').grid(row=1, column=0, sticky='w', **pad)
        self._output_var = tk.StringVar(value='Keeper_Of_Changes')
        ttk.Entry(frame, textvariable=self._output_var, width=42).grid(row=1, column=1, **pad)
        ttk.Button(frame, text='Browse…', command=self._browse_output).grid(row=1, column=2, **pad)

        # Check interval
        ttk.Label(frame, text='Check Interval (seconds):').grid(row=2, column=0, sticky='w', **pad)
        self._interval_var = tk.StringVar(value='600')
        ttk.Entry(frame, textvariable=self._interval_var, width=10).grid(row=2, column=1, sticky='w', **pad)

        # Status label
        self._status_var = tk.StringVar(value='Status: idle')
        ttk.Label(frame, textvariable=self._status_var, foreground='gray').grid(
            row=3, column=0, columnspan=3, pady=(6, 2))

        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(4, 2))
        ttk.Button(btn_frame, text='Start Monitoring', command=self._cmd_start).pack(side='left', padx=6)
        ttk.Button(btn_frame, text='Stop Monitoring', command=self._cmd_stop).pack(side='left', padx=6)

        hint = ttk.Label(
            frame,
            text='After starting, the window will hide.\nUse the tray icon near the clock to control the app.',
            foreground='#555555',
            justify='center',
        )
        hint.grid(row=5, column=0, columnspan=3, pady=(6, 4))

    # ── Directory browse helpers ─────────────────────────────────────────────

    def _browse_repo(self):
        path = filedialog.askdirectory(title='Select Git Repository Folder')
        if path:
            self._repo_var.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title='Select Output Directory')
        if path:
            self._output_var.set(path)

    # ── Button commands ──────────────────────────────────────────────────────

    def _cmd_start(self):
        repo_path = self._repo_var.get().strip()
        output_path = self._output_var.get().strip()
        interval_str = self._interval_var.get().strip()

        if not repo_path:
            messagebox.showerror('Error', 'Repository path cannot be empty.')
            return
        if not os.path.isdir(repo_path):
            messagebox.showerror('Error', f'Directory does not exist:\n{repo_path}')
            return
        try:
            interval = int(interval_str)
            if interval <= 0 or interval > 100000:
                raise ValueError
        except ValueError:
            messagebox.showerror('Error', 'Interval must be a positive integer ≤ 100000.')
            return

        if self._monitor.is_running():
            self._monitor.stop()

        self._monitor.start(repo_path, interval, output_path)
        self._status_var.set(f'Status: monitoring "{os.path.basename(repo_path)}" every {interval}s')

        # Start tray icon once
        if not self._tray_started:
            self._start_tray()

        # Hide main window – monitoring continues in the background
        self._root.withdraw()

    def _cmd_stop(self):
        self._monitor.stop()
        self._status_var.set('Status: stopped')

    # ── System-tray management ───────────────────────────────────────────────

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Show Settings', self._tray_show_settings),
            pystray.MenuItem('Stop Monitoring', self._tray_stop_monitoring),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', self._tray_exit),
        )
        self._tray = pystray.Icon(
            'Git Change Keeper',
            _create_tray_image(),
            'Git Change Keeper',
            menu,
        )
        # run_detached() starts the icon loop in its own daemon thread
        self._tray.run_detached()
        self._tray_started = True

    def _tray_show_settings(self, icon=None, item=None):
        # Must schedule UI updates on the main tkinter thread
        self._root.after(0, self._root.deiconify)

    def _tray_stop_monitoring(self, icon=None, item=None):
        self._monitor.stop()
        self._root.after(0, lambda: self._status_var.set('Status: stopped'))

    def _tray_exit(self, icon=None, item=None):
        self._monitor.stop()
        if self._tray:
            self._tray.stop()
        self._root.after(0, self._root.destroy)

    # ── Window close button ──────────────────────────────────────────────────

    def _on_window_close(self):
        if self._monitor.is_running():
            # Keep the process alive in the background
            self._root.withdraw()
        else:
            # Nothing running – exit cleanly
            if self._tray:
                self._tray.stop()
            self._root.destroy()

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        self._root.mainloop()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    app = App()
    app.run()


if __name__ == '__main__':
    main()

