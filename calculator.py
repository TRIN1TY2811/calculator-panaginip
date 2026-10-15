import ctypes
import math
import os
import sys
import tkinter as tk
from tkinter import font


class Calculator:
    # Lyrical Easter Egg sequence with customized durations per line:
    # - Parang panaginip = 7 sec
    # - 'Pag ika'y aking kapiling = 7 sec
    # - Huwag kang tumingin sa'kin = 6 sec
    # - Ako ay nahuhumaling = 8 sec
    # - Ako ay nahuhumaling = 8 sec
    # - Sa 'yo (x3) = 2 sec each
    LYRICS = [
        ("Parang panaginip", 7000),
        ("'Pag ika'y aking kapiling", 7000),
        ("Huwag kang tumingin sa'kin", 6000),
        ("Ako ay nahuhumaling", 8000),
        ("Ako ay nahuhumaling", 8000),
        ("Sa 'yo", 2000),
        ("Sa 'yo", 2000),
        ("Sa 'yo", 2000),
    ]

    # Target window dimensions: 500 wide
    DEFAULT_WIDTH = 500
    DEFAULT_MIN_HEIGHT = 520

    # ==========================================================================
    # 1. WINDOW SETUP & INITIALIZATION
    # ==========================================================================
    def __init__(self, root):
        self.root = root

        # Start hidden while rendering widgets to prevent initial flicker on the left side
        self.root.withdraw()

        # Window properties (title, non-resizable, dark theme background)
        self.root.title("Calculator")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.root.minsize(self.DEFAULT_WIDTH, self.DEFAULT_MIN_HEIGHT)

        # State variables for calculator input and display
        self.expression = ""
        self.display_var = tk.StringVar(value="0")
        self.sub_display_var = tk.StringVar(value="")

        # Cache of button widgets by label for keyboard ripple animations
        self.button_widgets = {}

        # Easter Egg state variables
        self._is_lyric_active = False
        self._is_final_message_active = False
        self._lyric_timer_id = None
        self._fade_timer_id = None
        self._fade_phase = 0.0
        self._current_lyric_index = 0

        # Styles dictionary cache
        self.styles = {}

        # Audio playback setup
        self.AUDIO_ALIAS = "panaginip_audio"

        # Build UI components, CSS-like styles, and position window on screen
        self._build_ui()
        self._position_window()

        # Handle window close gracefully so audio doesn't keep playing
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _position_window(self):
        """Positions the 500px wide window slightly up and to the right of screen center."""
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), self.root.winfo_reqwidth(), self.DEFAULT_WIDTH)
        height = max(self.root.winfo_height(), self.root.winfo_reqheight(), self.DEFAULT_MIN_HEIGHT)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Base center coordinates
        center_x = max(0, (screen_width - width) // 2)
        center_y = max(0, (screen_height - height) // 2)

        # Move a little to the right (+80px) and a little up (-30px) from center
        offset_x = 80
        offset_y = -30

        x = max(0, center_x + offset_x)
        y = max(10, center_y + offset_y)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.deiconify()  # Reveal the window now that it is positioned

    def _build_ui(self):
        # ======================================================================
        # 2. CSS-STYLE THEME CONFIGURATION (Colors, Pseudo-Classes & Typography)
        # ======================================================================
        self.styles = {
            "num": {
                "bg": "#3e3e3e",
                "fg": "#aaaaaa",
                "hover_bg": "#4d4d4d",
                "hover_fg": "#ffffff",
                "active_bg": "#2f2f2f",
                "active_fg": "#ffffff",
                "border": "#2c2c36",
                "hover_border": "#555566",
            },
            "func": {
                "bg": "#4a4a4a",
                "fg": "#aaaaaa",
                "hover_bg": "#595959",
                "hover_fg": "#ffffff",
                "active_bg": "#383838",
                "active_fg": "#ffffff",
                "border": "#333340",
                "hover_border": "#666677",
            },
            "op": {
                "bg": "#7a4a55",
                "fg": "#ccaaaa",
                "hover_bg": "#925866",
                "hover_fg": "#ffffff",
                "active_bg": "#5e3740",
                "active_fg": "#ffffff",
                "border": "#4f2e36",
                "hover_border": "#a86979",
            },
            "back": {
                "bg": "#581c1c",
                "fg": "#d4a5a5",
                "hover_bg": "#732424",
                "hover_fg": "#ffffff",
                "active_bg": "#401414",
                "active_fg": "#ffffff",
                "border": "#3d1313",
                "hover_border": "#943838",
            },
            "eq": {
                "bg": "#3e3e3e",
                "fg": "#aaaaaa",
                "hover_bg": "#4d4d4d",
                "hover_fg": "#ffffff",
                "active_bg": "#2f2f2f",
                "active_fg": "#ffffff",
                "border": "#2c2c36",
                "hover_border": "#555566",
            },
        }

        # Monospaced font choice with crisp LCD digital rendering
        available_fonts = font.families()
        lcd_font_family = "Consolas" if "Consolas" in available_fonts else "Courier New"

        # ======================================================================
        # 3. SCREEN / DISPLAY CONFIGURATION (Locked Size & Ratio LCD Panel)
        # ======================================================================

        # Screen Container Frame: Fixed height container with pack_propagate(False)
        # to ensure the size and aspect ratio NEVER change when switching to lyrics.
        self.screen_frame = tk.Frame(
            self.root,
            bg="#141414",          # User-configured dark LCD background
            bd=4,
            relief="sunken",
            highlightbackground="#E7E7E7",  # User-configured border highlight
            highlightthickness=2,
            height=128,            # Fixed height to freeze ratio and size
        )
        self.screen_frame.pack_propagate(False)  # Lock size: Never shrink or expand with child widgets
        self.screen_frame.grid(
            row=0, column=0, columnspan=4,
            sticky="nsew", padx=16, pady=(16, 8)
        )

        # Screen Component 1: Sub-Display (shows running formula / expression history)
        sub_font = font.Font(family=lcd_font_family, size=13)
        self.sub_display_label = tk.Label(
            self.screen_frame,
            textvariable=self.sub_display_var,
            font=sub_font,
            bg="#141414",
            fg="#aaaaaa",          # Dimmed text color for history
            anchor="e",
            padx=10,
            pady=4,
        )
        self.sub_display_label.pack(fill="x")

        # Screen Component 2: Main Display (shows numbers input and calculation/lyrics output)
        self.main_display_font = font.Font(family=lcd_font_family, size=36, weight="bold")
        self.main_display_label = tk.Label(
            self.screen_frame,
            textvariable=self.display_var,
            font=self.main_display_font,
            bg="#141414",
            fg="#ffffff",          # Bright white text for main number
            anchor="e",
            padx=10,
            pady=8,
        )
        self.main_display_label.pack(fill="both", expand=True)

        # ======================================================================
        # 4. BUTTONS CONFIGURATION (Layout, Styling, Micro-Interactions & Grid)
        # ======================================================================

        buttons = [
            # Row 1: Top function bar
            ("C",   1, 0, 1, "back"),
            ("+/-", 1, 1, 1, "func"),
            ("%",   1, 2, 1, "func"),
            ("⌫",   1, 3, 1, "back"),

            # Row 2
            ("7",   2, 0, 1, "num"),
            ("8",   2, 1, 1, "num"),
            ("9",   2, 2, 1, "num"),
            ("÷",   2, 3, 1, "op"),

            # Row 3
            ("4",   3, 0, 1, "num"),
            ("5",   3, 1, 1, "num"),
            ("6",   3, 2, 1, "num"),
            ("×",   3, 3, 1, "op"),

            # Row 4
            ("1",   4, 0, 1, "num"),
            ("2",   4, 1, 1, "num"),
            ("3",   4, 2, 1, "num"),
            ("−",   4, 3, 1, "op"),

            # Row 5: Wide zero and addition
            ("0",   5, 0, 2, "num"),    # Spans 2 columns
            (".",   5, 2, 1, "num"),
            ("+",   5, 3, 1, "op"),

            # Row 6: Full-width equals bar
            ("=",   6, 0, 4, "eq"),     # Spans all 4 columns
        ]

        btn_font = font.Font(family="Segoe UI", size=18, weight="bold")

        # Instantiate Button Widgets with CSS-like Hover & Press Event Listeners
        for (label, row, col, colspan, style_key) in buttons:
            st = self.styles[style_key]
            btn = tk.Button(
                self.root,
                text=label,
                font=btn_font,
                bg=st["bg"],
                fg=st["fg"],
                activebackground=st["active_bg"],
                activeforeground=st["active_fg"],
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=st["border"],
                cursor="hand2",
                command=lambda l=label: self._on_button(l),
            )
            btn.grid(
                row=row,
                column=col,
                columnspan=colspan,
                sticky="nsew",
                padx=6,
                pady=4,
                ipady=12,
            )

            # Attach CSS-like :hover and :active micro-animations
            self._attach_button_animations(btn, st)

            # Store reference for keyboard animation binding
            self.button_widgets[label] = (btn, st)

        # Grid Sizing & Weight Configuration: Ensure rows and columns expand proportionally
        for i in range(4):
            self.root.columnconfigure(i, weight=1, minsize=100)
        for i in range(1, 7):
            self.root.rowconfigure(i, weight=1)

        # Keyboard Bindings: Allow physical keyboard inputs with animated visual feedback
        for digit in "0123456789":
            self.root.bind(digit, lambda e: self._on_button(e.char))

        self.root.bind("<Return>",    lambda e: self._on_button("="))
        self.root.bind("<KP_Enter>",  lambda e: self._on_button("="))
        self.root.bind("<BackSpace>", lambda e: self._on_button("⌫"))
        self.root.bind("<Escape>",    lambda e: self._on_button("C"))
        self.root.bind("<Key>",       self._on_key)

    def _attach_button_animations(self, btn, st):
        """Attaches CSS-like :hover and :active micro-interactions to buttons."""
        def on_enter(e):
            btn.config(
                bg=st["hover_bg"],
                fg=st["hover_fg"],
                highlightbackground=st["hover_border"]
            )

        def on_leave(e):
            btn.config(
                bg=st["bg"],
                fg=st["fg"],
                highlightbackground=st["border"]
            )

        def on_press(e):
            btn.config(
                bg=st["active_bg"],
                fg=st["active_fg"],
                highlightbackground=st["hover_border"]
            )

        def on_release(e):
            btn.config(
                bg=st["hover_bg"],
                fg=st["hover_fg"],
                highlightbackground=st["hover_border"]
            )

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<ButtonPress-1>", on_press)
        btn.bind("<ButtonRelease-1>", on_release)

    def _animate_keypress(self, label):
        """Flashes the corresponding button when typed via physical keyboard."""
        if label in self.button_widgets and not self._is_lyric_active:
            btn, st = self.button_widgets[label]
            btn.config(
                bg=st["hover_bg"],
                fg=st["hover_fg"],
                highlightbackground=st["hover_border"]
            )
            self.root.after(
                120,
                lambda: btn.config(
                    bg=st["bg"],
                    fg=st["fg"],
                    highlightbackground=st["border"]
                )
            )

    def _pulse_screen(self, color="#ffffff", duration=120):
        """CSS-like glow pulse on the LCD border highlight during actions."""
        if self._is_lyric_active or self._is_final_message_active:
            return
        self.screen_frame.config(highlightbackground=color)
        self.root.after(duration, lambda: self.screen_frame.config(highlightbackground="#E7E7E7"))

    # ==========================================================================
    # 5. LYRICAL EASTER EGG (1600 x 3 "Nahuhumaling") & AUDIO PLAYBACK
    # ==========================================================================

    def _get_audio_path(self):
        """Finds the 'Panaginip - nicole (Lyrics).mp3' file or any fallback MP3."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exact_match = os.path.join(base_dir, "Panaginip - nicole (Lyrics).mp3")
        if os.path.isfile(exact_match):
            return exact_match

        # Search for any mp3 containing 'panaginip' or 'nicole'
        try:
            for file in os.listdir(base_dir):
                lower = file.lower()
                if lower.endswith(".mp3") and ("panaginip" in lower or "nicole" in lower):
                    return os.path.join(base_dir, file)
        except Exception:
            pass

        # Search for any .mp3 file in directory
        try:
            for file in os.listdir(base_dir):
                if file.lower().endswith(".mp3"):
                    return os.path.join(base_dir, file)
        except Exception:
            pass

        # Fallback to current working directory
        cwd = os.getcwd()
        cwd_exact = os.path.join(cwd, "Panaginip - nicole (Lyrics).mp3")
        if os.path.isfile(cwd_exact):
            return cwd_exact

        try:
            for file in os.listdir(cwd):
                if file.lower().endswith(".mp3"):
                    return os.path.join(cwd, file)
        except Exception:
            pass

        return None

    def _play_audio(self):
        """Plays the Easter egg MP3 audio file synchronized with the lyrics."""
        audio_path = self._get_audio_path()
        if not audio_path or not os.path.exists(audio_path):
            return

        if sys.platform == "win32" or os.name == "nt":
            try:
                winmm = ctypes.windll.winmm
                # Ensure any previous playback is completely stopped and closed
                winmm.mciSendStringW(f"stop {self.AUDIO_ALIAS}", None, 0, 0)
                winmm.mciSendStringW(f"close {self.AUDIO_ALIAS}", None, 0, 0)

                # Use 8.3 short path name if possible to safely handle spaces and special chars in MCI
                buf = ctypes.create_unicode_buffer(500)
                ret = ctypes.windll.kernel32.GetShortPathNameW(audio_path, buf, 500)
                mci_path = buf.value if ret > 0 else audio_path
                mci_cmd = f'open "{mci_path}" type mpegvideo alias {self.AUDIO_ALIAS}'
                res = winmm.mciSendStringW(mci_cmd, None, 0, 0)
                if res == 0:
                    winmm.mciSendStringW(f"play {self.AUDIO_ALIAS} from 0", None, 0, 0)
            except Exception as e:
                print(f"[Audio Playback Error] {e}")

    def _stop_audio(self):
        """Stops and closes the Easter egg MP3 audio playback."""
        if sys.platform == "win32" or os.name == "nt":
            try:
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW(f"stop {self.AUDIO_ALIAS}", None, 0, 0)
                winmm.mciSendStringW(f"close {self.AUDIO_ALIAS}", None, 0, 0)
            except Exception:
                pass

    def _on_close(self):
        """Handles window closing: cleanly stops any playing audio and exits."""
        self._stop_audio()
        self.root.destroy()

    @staticmethod
    def _interpolate_color(hex1, hex2, t):
        """Interpolates smoothly between two hex colors (0.0 <= t <= 1.0)."""
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _start_lyrical_easter_egg(self):
        """Starts the lyrical sequence immediately upon '=' without any 1-second delay."""
        if self._is_lyric_active:
            return

        self._is_lyric_active = True
        self._is_final_message_active = False
        self._current_lyric_index = 0
        self._fade_phase = 0.0

        # Completely unmap top sub-display so the main lyric label is dead-center vertically & horizontally
        self.sub_display_var.set("")
        try:
            self.sub_display_label.pack_forget()
        except Exception:
            pass

        self.main_display_label.config(anchor="center", justify="center")

        # Play audio at the exact same time as showing the lyrics
        self._play_audio()

        # Show first lyric immediately
        self._display_current_lyric()

        # Start timer matching the first lyric duration ("Parang panaginip" = 7000ms)
        first_duration = self.LYRICS[0][1]
        self._lyric_timer_id = self.root.after(first_duration, self._step_lyric)

        # Start smooth gray-to-white fading transition loop on the screen
        self._animate_background_fade()

    def _display_current_lyric(self):
        """Renders the current lyric line with larger, centered, responsive font sizing."""
        if self._current_lyric_index < len(self.LYRICS):
            text, _ = self.LYRICS[self._current_lyric_index]
            self.display_var.set(text)

            # Prominent, bold font sizes tailored for the 500px window
            if len(text) <= 8:
                font_size = 36
            elif len(text) <= 17:
                font_size = 28
            elif len(text) <= 20:
                font_size = 25
            else:
                font_size = 22

            self.main_display_font.config(size=font_size)

    def _step_lyric(self):
        """Advances to the next lyric or presents the final message 'I Miss You :(('."""
        if not self._is_lyric_active:
            return

        self._current_lyric_index += 1

        if self._current_lyric_index < len(self.LYRICS):
            self._display_current_lyric()
            # Schedule next lyric line using current lyric line's duration
            duration = self.LYRICS[self._current_lyric_index][1]
            self._lyric_timer_id = self.root.after(duration, self._step_lyric)
        else:
            # All 8 lyrics complete: display "I Miss You :((" with black font and white background
            self._show_final_message()

    def _show_final_message(self):
        """Displays the concluding text 'I Miss You :((' with black font on a pure white background."""
        if self._fade_timer_id:
            try:
                self.root.after_cancel(self._fade_timer_id)
            except Exception:
                pass
            self._fade_timer_id = None

        self._is_lyric_active = False
        self._is_final_message_active = True

        # Keep sub-display unmapped so message stays centered
        self.sub_display_var.set("")
        try:
            self.sub_display_label.pack_forget()
        except Exception:
            pass

        # Apply pure white background with sharp black font
        self.screen_frame.configure(bg="#ffffff", highlightbackground="#cccccc")
        self.main_display_label.configure(
            bg="#ffffff",
            fg="#000000",
            anchor="center",
            justify="center",
        )
        self.main_display_font.config(size=30, weight="bold")
        self.display_var.set("I Miss You :((")
        self.expression = "4800"

    def _animate_background_fade(self):
        """Fades ONLY the screen background between gray and white simultaneously in a smooth loop."""
        if not self._is_lyric_active:
            return

        self._fade_phase += 0.05
        # Smooth oscillation between 0.0 and 1.0
        t = (math.sin(self._fade_phase) + 1.0) / 2.0

        # LCD Screen background shifts smoothly between deep gray (#2a2b36) and bright white (#ffffff)
        screen_bg = self._interpolate_color("#2a2b36", "#ffffff", t)

        # Text and border dynamically adapt for crystal-clear readability
        border_color = self._interpolate_color("#ffffff", "#6e6e7c", t)
        text_fg = self._interpolate_color("#ffffff", "#121218", t)
        sub_fg = self._interpolate_color("#aaaaaa", "#555566", t)

        # Apply shifting colors strictly to the screen elements (body and buttons remain untouched)
        self.screen_frame.configure(bg=screen_bg, highlightbackground=border_color)
        self.sub_display_label.configure(bg=screen_bg, fg=sub_fg)
        self.main_display_label.configure(bg=screen_bg, fg=text_fg)

        # Next animation frame at ~33 fps (30ms interval)
        self._fade_timer_id = self.root.after(30, self._animate_background_fade)

    def _stop_lyrical_easter_egg(self, keep_text=False):
        """Cancels lyric and fading timers, stops audio, and restores the screen to its original state."""
        self._stop_audio()

        if self._lyric_timer_id:
            try:
                self.root.after_cancel(self._lyric_timer_id)
            except Exception:
                pass
            self._lyric_timer_id = None

        if self._fade_timer_id:
            try:
                self.root.after_cancel(self._fade_timer_id)
            except Exception:
                pass
            self._fade_timer_id = None

        self._is_lyric_active = False
        self._is_final_message_active = False

        # Restore sub-display on top before the main display label
        try:
            self.sub_display_label.pack(fill="x", before=self.main_display_label, pady=4)
        except Exception:
            pass

        # Restore original screen theme and right-aligned number format
        self.screen_frame.configure(bg="#141414", highlightbackground="#E7E7E7")
        self.sub_display_label.configure(bg="#141414", fg="#aaaaaa")
        self.main_display_label.configure(bg="#141414", fg="#ffffff", anchor="e", justify="right")
        self.main_display_font.config(size=36)

        if not keep_text:
            self.expression = ""
            self.display_var.set("0")
            self.sub_display_var.set("")
        else:
            self.sub_display_var.set("")
            self.display_var.set("I Miss You :((")
            self.expression = "4800"

    # ==========================================================================
    # 6. CALCULATOR LOGIC & EVENT HANDLERS
    # ==========================================================================

    def _on_key(self, event):
        """Logic: Handles operator keys entered via the physical keyboard."""
        # Supports +, -, *, /, as well as 'x' or 'X' for multiplication
        mapping = {"+": "+", "-": "−", "*": "×", "x": "×", "X": "×", "/": "÷", ".": "."}
        ch = event.char
        if ch in mapping:
            self._on_button(mapping[ch])

    def _on_button(self, label):
        """Logic: Central dispatcher for all button clicks and key events."""
        # If lyrical easter egg or final message is active and user presses an action button, reset it
        if self._is_lyric_active or self._is_final_message_active:
            self._stop_lyrical_easter_egg()

        # Trigger button pulse animation and subtle screen glow
        self._animate_keypress(label)
        self._pulse_screen(color="#ffffff", duration=100)

        # --- Logic: Clear All ('C') ---
        if label == "C":
            self._stop_audio()
            self.expression = ""
            self.display_var.set("0")
            self.sub_display_var.set("")

        # --- Logic: Backspace ('⌫') ---
        elif label == "⌫":
            self.expression = self.expression[:-1]
            self.display_var.set(self.expression if self.expression else "0")
            pretty = (
                self.expression
                .replace("/", "÷")
                .replace("*", "×")
                .replace("-", "−")
            )
            self.sub_display_var.set(pretty)

        # --- Logic: Calculate Result ('=') ---
        elif label == "=":
            self._calculate()

        # --- Logic: Toggle Sign ('+/-') ---
        elif label == "+/-":
            try:
                val = float(self._last_number())
                toggled = str(-val if val != 0 else 0)
                without_last = self.expression[: len(self.expression) - len(self._last_number())]
                self.expression = without_last + toggled
                self.display_var.set(self._format(toggled))
            except Exception:
                pass

        # --- Logic: Percentage ('%') ---
        elif label == "%":
            try:
                val = float(self._last_number())
                pct = str(val / 100)
                without_last = self.expression[: len(self.expression) - len(self._last_number())]
                self.expression = without_last + pct
                self.display_var.set(self._format(pct))
            except Exception:
                pass

        # --- Logic: Digits & Operators Handling ---
        else:
            symbol_map = {"÷": "/", "×": "*", "−": "-"}
            raw = symbol_map.get(label, label)

            # Prevent consecutive operator duplicates
            if raw in "+-*/" and self.expression and self.expression[-1] in "+-*/":
                self.expression = self.expression[:-1]

            self.expression += raw

            pretty = (
                self.expression
                .replace("/", "÷")
                .replace("*", "×")
                .replace("-", "−")
            )
            self.sub_display_var.set(pretty)

            last = self._last_number()
            self.display_var.set(self._format(last) if last else label)

    def _calculate(self):
        """Logic: Evaluates the arithmetic expression and displays the result."""
        # --- Check for 1600 x 3 Lyrical Easter Egg Trigger ---
        clean_expr = self.expression.replace(" ", "").replace("×", "*")
        if clean_expr in ("1600*3", "1600.0*3", "1600*3.0", "1600.0*3.0", "3*1600", "3.0*1600", "3*1600.0"):
            self._start_lyrical_easter_egg()
            return

        try:
            pretty = (
                self.expression
                .replace("/", "÷")
                .replace("*", "×")
                .replace("-", "−")
            )
            self.sub_display_var.set(pretty + " =")

            result = eval(self.expression)  # noqa: S307
            result_str = self._format(str(result))
            self.display_var.set(result_str)
            self.expression = str(result)
            self._pulse_screen(color="#ffffff", duration=150)
        except ZeroDivisionError:
            self.display_var.set("Error")
            self.expression = ""
            self._pulse_screen(color="#ff5555", duration=250)  # Red warning pulse
        except Exception:
            self.display_var.set("Error")
            self.expression = ""
            self._pulse_screen(color="#ff5555", duration=250)  # Red warning pulse

    def _last_number(self) -> str:
        """Logic Helper: Extracts the trailing number from the current expression string."""
        import re
        matches = re.findall(r"-?\d+\.?\d*", self.expression)
        return matches[-1] if matches else ""

    @staticmethod
    def _format(value: str) -> str:
        """Logic Helper: Removes redundant trailing zeros from decimal results."""
        try:
            f = float(value)
            if f == int(f) and "." not in value:
                return str(int(f))
            formatted = f"{f:.10g}"
            return formatted
        except ValueError:
            return value


# ==============================================================================
# 7. APPLICATION ENTRY POINT
# ==============================================================================
def main():
    root = tk.Tk()
    Calculator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
