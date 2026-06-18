import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import threading
import time
import glob
import math
import ctypes
from ctypes import wintypes

class SoundBoard:
    def __init__(self, root):
        self.root = root
        self.root.title("Spelling Bee Buzzer")
        self.root.geometry("700x600")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(650, 500)

        # Get directory where .exe or .py is located
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))

        self.buzzer_dir = os.path.join(self.app_dir, "buzzer")
        self.words_dir = os.path.join(self.app_dir, "words")
        self.correct_path = os.path.join(self.buzzer_dir, "correct.mp3")
        self.wrong_path = os.path.join(self.buzzer_dir, "wrong.mp3")

        # Check buzzer files
        self.check_buzzer_files()

        # Load word audio files
        self.word_files = self.load_word_files()

        # 9 toggle states (3 sets of P/A/Z in one row)
        self.toggle_states = [True] * 9

        # Colors for toggles (teal, red, gold) repeating
        self.toggle_colors = [
            {'active': '#0d7377', 'inactive': '#1a3a3b'},  # P - Teal
            {'active': '#c0392b', 'inactive': '#5c1e1a'},   # A - Red
            {'active': '#d4a017', 'inactive': '#5c4a1a'},  # Z - Gold
        ] * 3

        self.toggle_labels = ['P', 'A', 'Z'] * 3

        # === TIMER STATE ===
        self.timer_running = False
        self.timer_seconds = 0
        self.timer_total = 0
        self.timer_thread = None
        self.timer_stop_event = threading.Event()
        self.timer_window_visible = True

        # Build UI
        self.create_ui()

        # Hotkeys
        self.root.bind('<c>', lambda e: self.play_correct())
        self.root.bind('<C>', lambda e: self.play_correct())
        self.root.bind('<w>', lambda e: self.play_wrong())
        self.root.bind('<W>', lambda e: self.play_wrong())
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

        # Open timer display window
        self.open_timer_window()

        # Handle main window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_timer_window(self):
        self.timer_window = tk.Toplevel(self.root)
        self.timer_window.title("Timer Display")
        self.timer_window.geometry("500x500")       
        self.timer_window.configure(bg="#0a0a1a")
        self.timer_window.overrideredirect(True)
        self.timer_window.attributes('-topmost', True)

        # Center on screen
        screen_w = self.timer_window.winfo_screenwidth()
        screen_h = self.timer_window.winfo_screenheight()
        x = (screen_w - 500) // 2
        y = (screen_h - 500) // 2
        self.timer_window.geometry(f"500x500+{x}+{y}")

        self.timer_window.bind('<Button-1>', self.start_drag)
        self.timer_window.bind('<B1-Motion>', self.on_drag)
        self.timer_window.bind('<F11>', lambda e: self.toggle_timer_fullscreen())
        self.timer_window.bind('<Escape>', lambda e: self.exit_timer_fullscreen())
        self.timer_window.bind('<Button-3>', self.show_timer_menu)

        # NEW: Canvas for circular progress
        self.timer_canvas = tk.Canvas(
            self.timer_window,
            width=500, height=500,
            bg="#0a0a1a",
            highlightthickness=0
        )
        self.timer_canvas.pack(fill=tk.BOTH, expand=True)

        # Ring geometry
        self.center_x = 250
        self.center_y = 250
        self.radius = 180
        self.ring_width = 15

        # Background ring (dark gray)
        self.bg_ring = self.timer_canvas.create_oval(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            outline="#1a1a3a", width=self.ring_width
        )

        # Progress ring (colored arc)
        self.progress_ring = self.timer_canvas.create_arc(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            start=90, extent=0,
            outline="#00ff88", width=self.ring_width,
            style="arc"
        )

        # Timer text (centered on canvas)
        self.timer_display = self.timer_canvas.create_text(
            self.center_x, self.center_y,
            text="00:00",
            font=('Segoe UI', 72, 'bold'),
            fill="#00ff88",
            anchor="center"
        )

        # Close button
        self.close_btn = tk.Button(
            self.timer_window,
            text="✕",
            font=('Segoe UI', 10),
            bg="#0a0a1a",
            fg="#666",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.hide_timer_window
        )
        self.close_btn.place(x=470, y=5)

    def hide_timer_window(self):
        self.timer_window.withdraw()
        self.timer_window_visible = False
        self.toggle_timer_btn.config(text="SHOW TIMER")

    def show_timer_window(self):
        self.timer_window.deiconify()
        self.timer_window_visible = True
        self.toggle_timer_btn.config(text="HIDE TIMER")

    def toggle_timer_visibility(self):
        if self.timer_window_visible:
            self.hide_timer_window()
        else:
            self.show_timer_window()

    def get_monitor_at_position(self, x, y):
        """Get the monitor that contains the given point using Windows API"""
        user32 = ctypes.windll.user32
        hMonitor = user32.MonitorFromPoint(wintypes.POINT(x, y), 2)
        
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)
            ]
        
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            return {
                'left': mi.rcMonitor.left,
                'top': mi.rcMonitor.top,
                'right': mi.rcMonitor.right,
                'bottom': mi.rcMonitor.bottom,
                'width': mi.rcMonitor.right - mi.rcMonitor.left,
                'height': mi.rcMonitor.bottom - mi.rcMonitor.top
            }
        return None

    def toggle_timer_fullscreen(self):
        """Toggle fullscreen - manually fills screen to work on correct monitor"""
        # Track fullscreen state ourselves since we can't rely on -fullscreen attribute
        if not hasattr(self, '_timer_is_fullscreen'):
            self._timer_is_fullscreen = False

        if not self._timer_is_fullscreen:
            # Save current windowed state
            self.timer_window.update_idletasks()
            self._windowed_geometry = self.timer_window.geometry()

            # Hide close button when going fullscreen
            if hasattr(self, 'close_btn'):
                self.close_btn.place_forget()

            # Get current window center position
            wx = self.timer_window.winfo_x()
            wy = self.timer_window.winfo_y()
            ww = self.timer_window.winfo_width()
            wh = self.timer_window.winfo_height()
            center_x = wx + ww // 2
            center_y = wy + wh // 2

            # Get the actual monitor this window is on
            monitor = self.get_monitor_at_position(center_x, center_y)

            if monitor:
                mon_w = monitor['width']
                mon_h = monitor['height']
                mon_x = monitor['left']
                mon_y = monitor['top']
            else:
                mon_w = self.timer_window.winfo_screenwidth()
                mon_h = self.timer_window.winfo_screenheight()
                mon_x = wx
                mon_y = wy

            # Turn off borderless, then set geometry to fill the monitor
            self.timer_window.overrideredirect(False)
            self.timer_window.update_idletasks()

            # Set position first, then size (order matters for multi-monitor)
            self.timer_window.geometry(f"+{mon_x}+{mon_y}")
            self.timer_window.update_idletasks()
            self.timer_window.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
            self.timer_window.update_idletasks()

            # Use Windows API to maximize properly instead of -fullscreen
            # This respects the monitor position
            self._maximize_window()

            self._timer_is_fullscreen = True
            self.resize_timer_canvas()
        else:
            # Show close button when exiting fullscreen
            if hasattr(self, 'close_btn'):
                self.close_btn.place(x=470, y=5)


            # Restore windowed state
            self._restore_window()

            self.timer_window.overrideredirect(True)
            self.timer_window.update_idletasks()

            if hasattr(self, '_windowed_geometry'):
                self.timer_window.geometry(self._windowed_geometry)
            else:
                self.timer_window.geometry("500x500")

            self._timer_is_fullscreen = False
            self.resize_timer_canvas()

    def _maximize_window(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.ShowWindow(hwnd, 3)   # SW_MAXIMIZE = 3

    def _restore_window(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE = 9


    def exit_timer_fullscreen(self):
        self.timer_window.attributes('-fullscreen', False)
        self.timer_window.update_idletasks()
        self.timer_window.overrideredirect(True)
        if hasattr(self, '_windowed_geometry'):
            self.timer_window.geometry(self._windowed_geometry)
        else:
            self.timer_window.geometry("500x500")
        self.resize_timer_canvas()

    def resize_timer_canvas(self):
        self.timer_window.update_idletasks()
        w = self.timer_window.winfo_width()
        h = self.timer_window.winfo_height()
        
        self.timer_canvas.config(width=w, height=h)
        
        # Recalculate center and radius
        self.center_x = w // 2
        self.center_y = h // 2
        self.radius = min(w, h) // 2 - 40
        
        # Update ring positions
        self.timer_canvas.coords(
            self.bg_ring,
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius
        )
        self.timer_canvas.coords(
            self.progress_ring,
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius
        )
        
        # Update text position
        self.timer_canvas.coords(self.timer_display, self.center_x, self.center_y)
        
        # Update font size based on window size
        font_size = max(48, min(w, h) // 6)
        self.timer_canvas.itemconfig(self.timer_display, font=('Segoe UI', font_size, 'bold'))
        
        # Redraw progress
        self._update_ring()

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def on_drag(self, event):
        x = self.timer_window.winfo_x() + event.x - self.drag_x
        y = self.timer_window.winfo_y() + event.y - self.drag_y
        self.timer_window.geometry(f"+{x}+{y}")

    def show_timer_menu(self, event):
        menu = tk.Menu(self.timer_window, tearoff=0, bg="#1a1a2e", fg="#f0f0f0")
        menu.add_command(label="Toggle Fullscreen (F11)", command=self.toggle_timer_fullscreen)
        menu.add_command(label="Change Color...", command=self.change_timer_color)
        menu.add_separator()
        menu.add_command(label="Hide Timer Window", command=self.hide_timer_window)
        menu.post(event.x_root, event.y_root)

    def change_timer_color(self):
        colors = ["#00ff88", "#ff6b6b", "#4ecdc4", "#ffe66d", "#ffffff", "#ff9f43"] 
        current = self.timer_canvas.itemcget(self.timer_display, "fill") 
        try:
            idx = colors.index(current)
            next_color = colors[(idx + 1) % len(colors)]
        except ValueError:
            next_color = colors[0]
        self.timer_canvas.itemconfig(self.timer_display, fill=next_color)
        self.timer_canvas.itemconfig(self.progress_ring, outline=next_color)

    def check_buzzer_files(self):
        missing = []
        if not os.path.exists(self.correct_path):
            missing.append("buzzer\\correct.mp3")
        if not os.path.exists(self.wrong_path):
            missing.append("buzzer\\wrong.mp3")

        if missing:
            msg = "Missing buzzer sound files:\n\n" + "\n".join(missing)
            msg += "\n\nPlease create a 'buzzer' folder next to this .exe\n"
            msg += "and put correct.mp3 and wrong.mp3 inside it."
            messagebox.showerror("Sound Files Missing", msg)
            self.root.destroy()
            sys.exit(1)

    def load_word_files(self):
        """Load all mp3 files from words folder"""
        if not os.path.exists(self.words_dir):
            return []

        pattern = os.path.join(self.words_dir, "*.wav")
        files = glob.glob(pattern)
        # Sort alphabetically by filename (without extension)
        files.sort(key=lambda x: os.path.splitext(os.path.basename(x))[0].lower())
        return files

    def create_ui(self):
        # Title
        title = tk.Label(self.root, text="SPELLING BEE", font=('Segoe UI', 24, 'bold'),
                        bg="#1a1a2e", fg="#f0f0f0")
        title.pack(pady=(15, 2))

        subtitle = tk.Label(self.root, text="Sound Board", font=('Segoe UI', 12),
                           bg="#1a1a2e", fg="#8888aa")
        subtitle.pack(pady=(0, 10))

         # === TIMER SECTION ===
        timer_frame = tk.Frame(self.root, bg="#1a1a2e")
        timer_frame.pack(fill=tk.X, padx=30, pady=(0, 10))

        tk.Label(timer_frame, text="⏱ TIMER", font=('Segoe UI', 14, 'bold'),
                bg="#1a1a2e", fg="#89b4fa").pack(side=tk.LEFT)

        # Timer input
        input_frame = tk.Frame(timer_frame, bg="#1a1a2e")
        input_frame.pack(side=tk.LEFT, padx=(15, 0))

        self.min_entry = tk.Entry(input_frame, width=4, font=('Segoe UI', 14),
                                  bg="#313244", fg="#f0f0f0", relief=tk.FLAT,
                                  justify=tk.CENTER, insertbackground="#f0f0f0")
        self.min_entry.insert(0, "2")
        self.min_entry.pack(side=tk.LEFT)

        tk.Label(input_frame, text=":", font=('Segoe UI', 14),
                bg="#1a1a2e", fg="#f0f0f0").pack(side=tk.LEFT, padx=2)

        self.sec_entry = tk.Entry(input_frame, width=4, font=('Segoe UI', 14),
                                  bg="#313244", fg="#f0f0f0", relief=tk.FLAT,
                                  justify=tk.CENTER, insertbackground="#f0f0f0")
        self.sec_entry.insert(0, "00")
        self.sec_entry.pack(side=tk.LEFT)

        # Timer control buttons
        ctrl_frame = tk.Frame(timer_frame, bg="#1a1a2e")
        ctrl_frame.pack(side=tk.RIGHT)

        self.start_btn = tk.Button(ctrl_frame, text="▶ START", font=('Segoe UI', 11, 'bold'),
                                   bg="#10b981", fg="white", relief=tk.FLAT,
                                   padx=15, pady=5, cursor="hand2",
                                   command=self.start_timer)
        self.start_btn.pack(side=tk.LEFT, padx=3)

        self.stop_btn = tk.Button(ctrl_frame, text="⏹ STOP", font=('Segoe UI', 11, 'bold'),
                                  bg="#ef4444", fg="white", relief=tk.FLAT,
                                  padx=15, pady=5, cursor="hand2",
                                  command=self.stop_timer, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)

        self.reset_btn = tk.Button(ctrl_frame, text="↺ RESET", font=('Segoe UI', 11, 'bold'),
                                   bg="#3b82f6", fg="white", relief=tk.FLAT,
                                   padx=15, pady=5, cursor="hand2",
                                   command=self.reset_timer)
        self.reset_btn.pack(side=tk.LEFT, padx=3)

        self.toggle_timer_btn = tk.Button(ctrl_frame, text="HIDE TIMER", font=('Segoe UI', 11, 'bold'),
                                          bg="#7c3aed", fg="white", relief=tk.FLAT,
                                          padx=15, pady=5, cursor="hand2",
                                          command=self.toggle_timer_visibility)
        self.toggle_timer_btn.pack(side=tk.LEFT, padx=3)

        # Separator
        sep = tk.Frame(self.root, bg="#313244", height=2)
        sep.pack(fill=tk.X, padx=20, pady=5)

        # === BUZZER BUTTONS ===
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=8)

        self.correct_btn = tk.Button(btn_frame, text="CORRECT", font=('Segoe UI', 18, 'bold'),
                                     bg="#10b981", fg="white", activebackground="#059669",
                                     activeforeground="white", relief=tk.FLAT,
                                     padx=35, pady=20, cursor="hand2",
                                     command=self.play_correct)
        self.correct_btn.pack(side=tk.LEFT, padx=12)

        self.wrong_btn = tk.Button(btn_frame, text="WRONG", font=('Segoe UI', 18, 'bold'),
                                   bg="#ef4444", fg="white", activebackground="#dc2626",
                                   activeforeground="white", relief=tk.FLAT,
                                   padx=35, pady=20, cursor="hand2",
                                   command=self.play_wrong)
        self.wrong_btn.pack(side=tk.LEFT, padx=12)

        # === TOGGLES (9 in a row) ===
        toggle_frame = tk.Frame(self.root, bg="#1a1a2e")
        toggle_frame.pack(pady=12)

        self.toggle_buttons = []
        for i in range(9):
            btn = tk.Button(toggle_frame, text=self.toggle_labels[i], font=('Segoe UI', 14, 'bold'),
                           width=3, height=1,
                           bg=self.toggle_colors[i]['active'],
                           fg="white",
                           activebackground=self.toggle_colors[i]['inactive'],
                           relief=tk.FLAT, cursor="hand2",
                           command=lambda idx=i: self.toggle(idx))
            btn.pack(side=tk.LEFT, padx=4)
            self.toggle_buttons.append(btn)

        # === WORD AUDIO SECTION ===
        words_header = tk.Frame(self.root, bg="#1a1a2e")
        words_header.pack(fill=tk.X, padx=30, pady=(15, 5))

        tk.Label(words_header, text="📋 WORD AUDIO", font=('Segoe UI', 14, 'bold'),
                bg="#1a1a2e", fg="#89b4fa").pack(side=tk.LEFT)

        word_count = len(self.word_files)
        tk.Label(words_header, text=f"({word_count} words loaded)", font=('Segoe UI', 10),
                bg="#1a1a2e", fg="#6b7280").pack(side=tk.LEFT, padx=(10, 0))

        if word_count == 0:
            tk.Label(words_header, text="[No words folder found]", font=('Segoe UI', 9),
                    bg="#1a1a2e", fg="#ef4444").pack(side=tk.RIGHT)

        # Scrollable word buttons area
        words_container = tk.Frame(self.root, bg="#1a1a2e")
        words_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)

        self.canvas = tk.Canvas(words_container, bg="#1a1a2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(words_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1a1a2e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=620)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Render word buttons
        self.render_word_buttons()

        # Status bar
        self.status = tk.Label(self.root, text="Ready", font=('Segoe UI', 10),
                            bg="#1a1a2e", fg="#6b7280")
        self.status.pack(pady=(5, 0))

        # Hint at bottom
        hint = tk.Label(self.root, text="Press 'C' for Correct  |  Press 'W' for Wrong  |  F11 = Fullscreen",
                       font=('Segoe UI', 9), bg="#1a1a2e", fg="#555577")
        hint.pack(pady=(5, 0))

    # === TIMER METHODS ===
    def start_timer(self):
        if self.timer_running:
            return

        try:
            mins = int(self.min_entry.get() or 0)
            secs = int(self.sec_entry.get() or 0)
        except ValueError:
            self.status.config(text="Invalid time format", fg="#ef4444")
            return

        self.timer_total = mins * 60 + secs
        if self.timer_total <= 0:
            self.status.config(text="Please set a time > 0", fg="#ef4444")
            return

        self.timer_seconds = self.timer_total
        self.timer_running = True
        self.timer_stop_event.clear()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.min_entry.config(state=tk.DISABLED)
        self.sec_entry.config(state=tk.DISABLED)

        self.status.config(text="Timer running...", fg="#10b981")

        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _timer_loop(self):
        while self.timer_seconds > 0 and not self.timer_stop_event.is_set():
            self._update_display()
            time.sleep(1)
            self.timer_seconds -= 1

        if not self.timer_stop_event.is_set():
            self._update_display()
            self.timer_finished()

    def _update_display(self):
        mins, secs = divmod(self.timer_seconds, 60)
        time_str = f"{mins:02d}:{secs:02d}"

        self.root.after(0, lambda: self.timer_canvas.itemconfig(self.timer_display, text=time_str))
        self.root.after(0, self._update_ring)

        # Color changes — now using itemconfig for canvas
        if self.timer_seconds <= 10:
            self.root.after(0, lambda: self.timer_canvas.itemconfig(self.timer_display, fill="#ef4444"))
            self.root.after(0, lambda: self.timer_canvas.itemconfig(self.progress_ring, outline="#ef4444"))
        elif self.timer_seconds <= 30:
            self.root.after(0, lambda: self.timer_canvas.itemconfig(self.timer_display, fill="#d4a017"))
            self.root.after(0, lambda: self.timer_canvas.itemconfig(self.progress_ring, outline="#d4a017"))

    def _update_ring(self):
        """Update the circular progress ring based on remaining time"""
        if self.timer_total > 0:
            progress = (self.timer_total - self.timer_seconds) / self.timer_total
        else:
            progress = 0
        
        extent = progress * 360
        self.timer_canvas.itemconfig(self.progress_ring, extent=extent)

    def timer_finished(self):
        self.timer_running = False
        self.root.after(0, self._reset_ui_state)
        self.root.after(0, lambda: self.status.config(text="TIME'S UP!", fg="#ef4444"))
        
        self.root.after(0, lambda: self.timer_canvas.itemconfig(self.timer_display, text="00:00", fill="#ef4444"))
        self.root.after(0, lambda: self.timer_canvas.itemconfig(self.progress_ring, outline="#ef4444", extent=360))
        
        self.root.after(0, self.play_wrong)

    def stop_timer(self):
        if not self.timer_running:
            return
        self.timer_stop_event.set()
        self.timer_running = False
        self._reset_ui_state()
        self.status.config(text="Timer stopped", fg="#d4a017")

    def reset_timer(self):
        if self.timer_running:
            self.timer_stop_event.set()
            self.timer_running = False
            if self.timer_thread:
                self.timer_thread.join(timeout=0.5)

        self.timer_seconds = 0
        self.timer_total = 0
        self._reset_ui_state()
        
        self.timer_canvas.itemconfig(self.timer_display, text="00:00", fill="#00ff88")
        self.timer_canvas.itemconfig(self.progress_ring, outline="#00ff88", extent=0)
        
        self.status.config(text="Timer reset", fg="#6b7280")

    def _reset_ui_state(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.min_entry.config(state=tk.NORMAL)
        self.sec_entry.config(state=tk.NORMAL)

    def render_word_buttons(self):
        """Create buttons for each word audio file"""
        if not self.word_files:
            empty_msg = tk.Label(self.scrollable_frame, text="Put WAV files in a 'words' folder\nnext to this .exe",
                                font=('Segoe UI', 12), bg="#1a1a2e", fg="#6b7280",
                                justify=tk.CENTER)
            empty_msg.pack(pady=40)
            return

        # Grid layout: 3 columns of word buttons
        for idx, filepath in enumerate(self.word_files):
            word_name = os.path.splitext(os.path.basename(filepath))[0]
            row = idx // 3
            col = idx % 3

            word_card = tk.Frame(self.scrollable_frame, bg="#313244", padx=10, pady=8)
            word_card.grid(row=row, column=col, padx=5, pady=4, sticky="ew")
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)
            self.scrollable_frame.grid_columnconfigure(2, weight=1)

            # Word name
            tk.Label(word_card, text=word_name, font=('Segoe UI', 12, 'bold'),
                    bg="#313244", fg="#cdd6f4").pack(side=tk.LEFT, padx=(0, 10))

            # Play button
            play_btn = tk.Button(word_card, text="▶", font=('Segoe UI', 11, 'bold'),
                                bg="#89b4fa", fg="#1e1e2e", relief=tk.FLAT,
                                width=3, cursor="hand2",
                                command=lambda f=filepath, n=word_name: self.play_word(f, n))
            play_btn.pack(side=tk.RIGHT)

    def play_word(self, filepath, word_name):
        """Play a word audio file"""
        self.status.config(text=f"Playing: {word_name}", fg="#89b4fa")
        self.play_audio_file(filepath)

    def toggle(self, idx):
        """Toggle a button between active and inactive"""
        self.toggle_states[idx] = not self.toggle_states[idx]
        is_active = self.toggle_states[idx]

        btn = self.toggle_buttons[idx]
        letter = self.toggle_labels[idx]
        if is_active:
            btn.config(bg=self.toggle_colors[idx]['active'], fg="white")
        else:
            btn.config(bg=self.toggle_colors[idx]['inactive'], fg="black")

    def play_audio_file(self, filepath):
        """Play any audio file using multiple methods"""
        def run():
            played = False

            # Method 1: Windows Media Player COM
            try:
                import comtypes.client
                player = comtypes.client.CreateObject("WMPlayer.OCX")
                player.URL = filepath
                player.settings.volume = 100
                player.controls.play()
                while player.playState != 1:
                    time.sleep(0.1)
                player.close()
                played = True
            except:
                pass

            # Method 2: PowerShell MediaPlayer
            if not played:
                try:
                    import subprocess
                    ps_cmd = (
                        'Add-Type -AssemblyName presentationCore; '
                        '$player = New-Object System.Windows.Media.MediaPlayer; '
                        '$player.Open("' + filepath + '"); '
                        '$player.Play(); '
                        'Start-Sleep -s 5'
                    )
                    subprocess.run(
                        ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                    played = True
                except:
                    pass

            # Method 3: Default player
            if not played:
                try:
                    os.startfile(filepath)
                except Exception as e:
                    self.root.after(0, lambda: self.status.config(text="Error: " + str(e), fg="#ef4444"))

        threading.Thread(target=run, daemon=True).start()

    def play_sound(self, path, btn, original_color, flash_color, label_text):
        """Play buzzer sound with visual feedback"""
        self.play_audio_file(path)
        self.status.config(text=f"Playing: {label_text}", fg=original_color)
        self.flash_button(btn, original_color, flash_color)

    def play_correct(self):
        self.play_sound(self.correct_path, self.correct_btn, "#10b981", "#059669", "CORRECT")

    def play_wrong(self):
        self.play_sound(self.wrong_path, self.wrong_btn, "#ef4444", "#dc2626", "WRONG")

    def flash_button(self, btn, original, darker):
        btn.config(bg=darker)
        self.root.after(150, lambda: btn.config(bg=original))

    def toggle_fullscreen(self):
        is_full = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_full)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def on_close(self):
        """Clean up on window close"""
        if self.timer_running:
            self.timer_stop_event.set()
        if hasattr(self, 'timer_window') and self.timer_window.winfo_exists():
            self.timer_window.destroy()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = SoundBoard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
