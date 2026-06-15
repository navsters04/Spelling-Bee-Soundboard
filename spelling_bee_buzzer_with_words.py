import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import threading
import time
import glob

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

        # Build UI
        self.create_ui()

        # Hotkeys
        self.root.bind('<c>', lambda e: self.play_correct())
        self.root.bind('<C>', lambda e: self.play_correct())
        self.root.bind('<w>', lambda e: self.play_wrong())
        self.root.bind('<W>', lambda e: self.play_wrong())
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

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
                              bg="#181825", fg="#444466")
        self.status.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0), ipady=8)

        # Hint at bottom
        hint = tk.Label(self.root, text="Press 'C' for Correct  |  Press 'W' for Wrong  |  F11 = Fullscreen",
                       font=('Segoe UI', 9), bg="#1a1a2e", fg="#555577")
        hint.pack(pady=(5, 0))

    def render_word_buttons(self):
        """Create buttons for each word audio file"""
        if not self.word_files:
            empty_msg = tk.Label(self.scrollable_frame, text="Put MP3 files in a 'words' folder\nnext to this .exe",
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

def main():
    root = tk.Tk()
    app = SoundBoard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
