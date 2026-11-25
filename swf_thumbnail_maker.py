#!/usr/bin/env python3
"""Batch SWF window captures for Linux X11; no shell interpolation."""
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


def times_from(text):
    values = sorted(set(float(s.strip()) for s in text.split(',')))
    if not values or any(not 0 <= n <= 3600 for n in values):
        raise ValueError('Enter comma-separated seconds between 0 and 3600.')
    return values


def run(args, timeout=10):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('SWF Thumbnail Maker — Linux X11')
        self.geometry('980x740')
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.manual = threading.Event()
        self.worker = None
        self.images = []
        self.folder = tk.StringVar()
        self.player = tk.StringVar(value=shutil.which('ruffle') or shutil.which('flashplayer') or '')
        self.delays = tk.StringVar(value='3, 8, 15')
        self.recursive = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Choose a folder and a player executable. Existing matching PNGs are skipped.')
        box = ttk.Frame(self, padding=12)
        box.pack(fill='both', expand=True)
        box.columnconfigure(1, weight=1)
        for row, (label, var, pick) in enumerate([
            ('SWF folder', self.folder, self.pick_folder),
            ('Player executable', self.player, self.pick_player),
        ]):
            ttk.Label(box, text=label).grid(row=row, column=0, sticky='w', pady=5)
            ttk.Entry(box, textvariable=var).grid(row=row, column=1, sticky='ew', padx=8)
            ttk.Button(box, text='Browse…', command=pick).grid(row=row, column=2)
        ttk.Label(box, text='Capture seconds').grid(row=2, column=0, sticky='w')
        ttk.Entry(box, textvariable=self.delays).grid(row=2, column=1, sticky='ew', padx=8, pady=5)
        ttk.Checkbutton(box, text='Include subfolders', variable=self.recursive).grid(row=3, column=1, sticky='w')
        ttk.Label(box, text='Times start when the player window appears. Last timed picture becomes game.png.\nAll captures remain available below so you can choose a better one.').grid(row=4, column=0, columnspan=3, sticky='w', pady=8)
        controls = ttk.Frame(box)
        controls.grid(row=5, column=0, columnspan=3, sticky='w')
        self.start_button = ttk.Button(controls, text='Start batch', command=self.start)
        self.start_button.pack(side='left', padx=3)
        ttk.Button(controls, text='Capture now', command=self.manual.set).pack(side='left', padx=3)
        ttk.Button(controls, text='Stop', command=self.stop.set).pack(side='left', padx=3)
        ttk.Button(controls, text='Load saved captures', command=self.load_captures).pack(side='left', padx=3)
        ttk.Label(box, textvariable=self.status, wraplength=920).grid(row=6, column=0, columnspan=3, sticky='w', pady=8)
        pane = ttk.Panedwindow(box, orient='horizontal')
        pane.grid(row=7, column=0, columnspan=3, sticky='nsew')
        box.rowconfigure(7, weight=1)
        left = ttk.Frame(pane)
        self.listing = tk.Listbox(left, width=40, exportselection=False)
        scroll = ttk.Scrollbar(left, command=self.listing.yview)
        self.listing.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.listing.pack(fill='both', expand=True)
        self.listing.bind('<<ListboxSelect>>', self.preview)
        pane.add(left, weight=1)
        right = ttk.Frame(pane)
        self.picture = ttk.Label(right, text='Capture preview', anchor='center')
        self.picture.pack(fill='both', expand=True)
        ttk.Button(right, text='Use selected picture as matching PNG', command=self.promote).pack(pady=6)
        pane.add(right, weight=2)
        self.log = tk.Text(box, height=7, state='disabled')
        self.log.grid(row=8, column=0, columnspan=3, sticky='ew', pady=8)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def pick_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.folder.set(p)

    def pick_player(self):
        p = filedialog.askopenfilename(title='Select flashplayer.bin or the Ruffle executable')
        if p:
            self.player.set(p)

    def write_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def add_image(self, path, target):
        if (path, target) not in self.images:
            self.images.append((path, target))
            self.listing.insert('end', f'{target.stem} / {path.name}')

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'log':
                    self.write_log(value)
                    self.status.set(value)
                elif kind == 'image':
                    self.add_image(*value)
                elif kind == 'done':
                    self.start_button.configure(state='normal')
                    self.status.set(value)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
                raise ValueError('This version needs an X11 desktop session. Log into Xfce/X11 first.')
            if not os.environ.get('DISPLAY'):
                raise ValueError('Run this on your desktop PC, not an SSH-only terminal.')
            for dep in ('xdotool', 'import'):
                if not shutil.which(dep):
                    raise ValueError('Install dependencies: sudo apt install python3-tk python3-pil.imagetk xdotool imagemagick')
            folder = Path(self.folder.get()).expanduser()
            if not folder.is_dir():
                raise ValueError('Select an existing local or mounted Samba folder.')
            executable = shutil.which(self.player.get())
            if not executable:
                raise ValueError('Select an executable Flash player or Ruffle. A .desktop launcher is not an executable.')
            delays = times_from(self.delays.get())
            recursive = self.recursive.get()
        except Exception as exc:
            messagebox.showerror('Check settings', str(exc))
            return
        self.stop.clear()
        self.manual.clear()
        self.start_button.configure(state='disabled')
        self.worker = threading.Thread(target=self.batch, args=(folder, executable, delays, recursive), daemon=True)
        self.worker.start()

    def batch(self, folder, executable, delays, recursive):
        captured = skipped = failed = 0
        try:
            files = sorted(p for p in (folder.rglob('*') if recursive else folder.iterdir()) if p.is_file() and p.suffix.lower() == '.swf')
            self.events.put(('log', f'Found {len(files)} SWF files. Keep player windows visible; do not minimize them.'))
            for index, swf in enumerate(files, 1):
                if self.stop.is_set():
                    break
                target = swf.with_suffix('.png')
                if target.exists():
                    skipped += 1
                    continue
                proc = None
                try:
                    self.events.put(('log', f'{index}/{len(files)} Opening {swf.name}'))
                    # A separate process group lets us close only the player we launched.
                    with open(os.devnull, 'wb') as quiet:
                        proc = subprocess.Popen([executable, str(swf.resolve())], stdout=quiet, stderr=quiet, start_new_session=True)
                    window = None
                    until = time.monotonic() + 25
                    while time.monotonic() < until and not self.stop.is_set():
                        result = run(['xdotool', 'search', '--onlyvisible', '--pid', str(proc.pid)], 3)
                        ids = result.stdout.split()
                        if ids:
                            window = ids[-1]
                            break
                        if proc.poll() is not None:
                            raise RuntimeError('Player exited or reused another instance. Close existing players and retry.')
                        self.stop.wait(.25)
                    if self.stop.is_set():
                        break
                    if not window:
                        raise RuntimeError('No player window found within 25 seconds.')
                    run(['xdotool', 'windowsize', window, '900', '650'])
                    run(['xdotool', 'windowactivate', '--sync', window], 3)
                    output = swf.parent / '_swf_captures' / swf.name
                    output.mkdir(parents=True, exist_ok=True)
                    started = time.monotonic()
                    last = None
                    shot = 0
                    self.manual.clear()
                    for delay in delays:
                        while not self.stop.is_set() and time.monotonic() - started < delay:
                            if self.manual.is_set():
                                self.manual.clear()
                                shot += 1
                                self.capture(window, output / f'manual_{time.time_ns()}.png', target)
                            self.stop.wait(.1)
                        if self.stop.is_set():
                            break
                        shot += 1
                        last = output / f'{time.time_ns()}_{delay:g}s.png'
                        self.capture(window, last, target)
                    if last and not self.stop.is_set():
                        # Never overwrite an existing matching PNG, even if one appears mid-batch.
                        with target.open('xb') as dest, last.open('rb') as source:
                            shutil.copyfileobj(source, dest)
                        captured += 1
                        self.events.put(('log', f'Saved {target.name}'))
                except Exception as exc:
                    failed += 1
                    self.events.put(('log', f'FAILED {swf.name}: {exc}'))
                finally:
                    if proc:
                        try:
                            os.killpg(proc.pid, signal.SIGTERM)
                            try:
                                proc.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                os.killpg(proc.pid, signal.SIGKILL)
                                proc.wait(timeout=2)
                        except ProcessLookupError:
                            pass
            word = 'Stopped' if self.stop.is_set() else 'Finished'
            self.events.put(('done', f'{word}: {captured} PNGs saved, {skipped} existing skipped, {failed} failed.'))
        except Exception as exc:
            self.events.put(('log', str(exc)))
            self.events.put(('done', 'Batch ended with an error; see log.'))

    def capture(self, window, path, target):
        result = run(['import', '-window', window, str(path)], 15)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Screenshot failed')
        with Image.open(path) as img:
            img.verify()
        self.events.put(('image', (path, target)))

    def load_captures(self):
        root = Path(self.folder.get()).expanduser()
        if not self.folder.get() or not root.is_dir():
            messagebox.showinfo('Choose folder', 'Choose the SWF folder first.')
            return
        for image in root.rglob('_swf_captures/*.swf/*.png'):
            target = image.parent.parent.parent / (Path(image.parent.name).stem + '.png')
            self.add_image(image, target)
        self.status.set(f'{len(self.images)} captures available for review.')

    def selected(self):
        selected = self.listing.curselection()
        return self.images[selected[0]] if selected else None

    def preview(self, event=None):
        pair = self.selected()
        if pair:
            try:
                with Image.open(pair[0]) as source:
                    img = source.convert('RGB')
                    img.thumbnail((550, 350))
                self.photo = ImageTk.PhotoImage(img)
                self.picture.configure(image=self.photo, text='')
            except Exception as exc:
                self.status.set(str(exc))

    def promote(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('Batch running', 'Stop or finish the batch before choosing replacement PNGs.')
            return
        pair = self.selected()
        if not pair:
            return
        source, target = pair
        if target.exists() and not messagebox.askyesno('Replace picture?', f'Replace {target.name} with this capture?'):
            return
        try:
            shutil.copyfile(source, target)
            self.status.set(f'Selected picture saved as {target}')
        except Exception as exc:
            messagebox.showerror('Save failed', str(exc))

    def close(self):
        self.stop.set()
        if self.worker and self.worker.is_alive():
            self.status.set('Closing the current player…')
            self.after(200, self.close)
        else:
            self.destroy()


if __name__ == '__main__':
    App().mainloop()
