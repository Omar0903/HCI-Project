import tkinter as tk
from tkinter import font as tkfont
import numpy as np
from scipy.signal import butter, filtfilt
import pywt
import joblib

class FlatButton(tk.Frame):
    def __init__(self, parent, text, bg_color, hover_color, text_color, command, on_hover=None, **kwargs):
        super().__init__(parent, bg=bg_color, relief="flat", borderwidth=0, **kwargs)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.command = command
        self.text = text
        self.on_hover = on_hover
        self.text_color = text_color
        
        # Shrink font to fit the new size
        self.label = tk.Label(self, text=text, font=("Segoe UI", 12, "bold"), 
                              bg=bg_color, fg=text_color, cursor="hand2")
        self.label.pack(expand=True, fill="both")
        
        self.label.bind("<Button-1>", self.on_click)
        self.label.bind("<Enter>", self.on_enter)
        self.label.bind("<Leave>", self.on_leave)
        
    def on_click(self, event):
        self.label.config(bg="#ffffff", fg="#000000")
        self.after(100, lambda: self.label.config(bg=self.hover_color, fg=self.text_color))
        self.command()
        
    def on_enter(self, event):
        self.config(bg=self.hover_color)
        self.label.config(bg=self.hover_color)
        if self.on_hover:
            self.on_hover(self.text)
        
    def on_leave(self, event):
        self.config(bg=self.bg_color)
        self.label.config(bg=self.bg_color)
        if self.on_hover:
            self.on_hover("")

class EOGCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("EOG Calculator - 4 Groups")
        
        # Expanded geometry to fit the 13x13 grid comfortably
        self.root.geometry("600x650")
        self.root.configure(bg="#202020")
        
        self.state = 'WAIT_FIRST'
        self.first_digit = None
        self.operation = None
        self.second_digit = None
        
        # EOG Processing Initialization
        self.signal_buffer = []
        try:
            self.model = joblib.load('eog_model.pkl')
        except:
            self.model = None
            
        self.main_center_pos = (6, 6)
        self.current_pos = self.main_center_pos
        self.buttons_by_pos = {}
        
        # Signal Processing Delay (Cooldown) in milliseconds
        self.signal_delay_ms = 1000
        self.can_process_signal = True
        
        # Fonts
        self.display_font = tkfont.Font(family="Segoe UI Semibold", size=24, weight="bold")
        self.history_font = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        self.focus_font = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        
        self.display_frame = tk.Frame(self.root, bg="#202020", bd=0)
        self.display_frame.grid(row=0, column=0, columnspan=13, sticky="nsew", pady=(10, 5))
        
        self.history_var = tk.StringVar()
        self.history_var.set("")
        
        self.display_var = tk.StringVar()
        self.display_var.set("0")
        
        self.history_label = tk.Label(
            self.display_frame,
            textvariable=self.history_var,
            font=self.history_font,
            bg="#202020",
            fg="#A0A0A0",
            anchor="e",
            padx=10
        )
        self.history_label.pack(fill="x", side="top")
        
        self.display_label = tk.Label(
            self.display_frame, 
            textvariable=self.display_var, 
            font=self.display_font, 
            bg="#202020", 
            fg="#FFFFFF",
            anchor="e",
            padx=10
        )
        self.display_label.pack(fill="x", side="top", pady=(0, 5))
        
        self.focus_var = tk.StringVar()
        self.focus_label = tk.Label(
            self.display_frame, 
            textvariable=self.focus_var, 
            font=self.focus_font, 
            bg="#202020", 
            fg="#ff9f0a",
            anchor="w",
            padx=10
        )
        self.focus_label.place(relx=0, rely=0.5, anchor="w")

        # Configure 13x13 grid
        for i in range(13):
            self.root.grid_columnconfigure(i, weight=1, uniform="sq")
            if i == 0:
                self.root.grid_rowconfigure(i, weight=1) 
            else:
                self.root.grid_rowconfigure(i, weight=1, uniform="sq")
            
        self.create_buttons()
        self.build_navigation_graph()

        # Bind Spacebar for testing the two specific signals
        self.root.bind("<space>", lambda e: self.load_test_signals())
        self.highlight_current_pos()

    def get_hover_name(self, text):
        names = {
            '+': "Add", '-': "Subtract", 'x': "Multiply", '/': "Divide",
            'E': "Exit", 'C': "Clear", 'CURSOR': "Main Center",
            '%': "Modulus", 'n!': "Factorial", 'p': "Power", '√': "Root"
        }
        if text in names:
            return names[text]
        elif text.isdigit():
            return f"Number {text}"
        return text

    def update_focus(self, text):
        if text:
            name = self.get_hover_name(text)
            self.focus_var.set(f"👁️ {name}")
        else:
            self.focus_var.set("")

    def create_buttons(self):
        num_c, num_h, num_fg = "#3B3B3B", "#4C4C4C", "#FFFFFF"
        op_c, op_h, op_fg = "#FF9500", "#FFB340", "#FFFFFF"
        sys_c, sys_h, sys_fg = "#A5A5A5", "#D9D9D9", "#000000"
        cur_c, cur_h, cur_fg = "#4CC2FF", "#2AA6DF", "#000000"
        
        buttons = {
            # Top Group (Center 5)
            '8': (1, 6, num_c, num_h, num_fg),
            '9': (2, 5, num_c, num_h, num_fg), '5': (2, 6, num_c, num_h, num_fg), '7': (2, 7, num_c, num_h, num_fg),
            '6': (3, 6, num_c, num_h, num_fg),
            
            # Left Group (Center n!)
            'E': (5, 2, sys_c, sys_h, sys_fg),
            'C': (6, 1, sys_c, sys_h, sys_fg), 'n!': (6, 2, op_c, op_h, op_fg), '%': (6, 3, op_c, op_h, op_fg),
            'p': (7, 2, op_c, op_h, op_fg),
            
            # Right Group (Center 0)
            '3': (5, 10, num_c, num_h, num_fg),
            '4': (6, 9, num_c, num_h, num_fg), '0': (6, 10, num_c, num_h, num_fg), '2': (6, 11, num_c, num_h, num_fg),
            '1': (7, 10, num_c, num_h, num_fg),
            
            # Bottom Group (Center +)
            '/': (9, 6, op_c, op_h, op_fg),
            '√': (10, 5, op_c, op_h, op_fg), '+': (10, 6, op_c, op_h, op_fg), '-': (10, 7, op_c, op_h, op_fg),
            'x': (11, 6, op_c, op_h, op_fg),
        }
        
        pad = 2 
        
        for text, config in buttons.items():
            row, col, bg, hover, fg = config
            btn = FlatButton(self.root, text=text, bg_color=bg, hover_color=hover, text_color=fg,
                             command=lambda t=text: self.button_click(t),
                             on_hover=self.update_focus)
            btn.grid(row=row, column=col, padx=pad, pady=pad, sticky="nsew")
            self.buttons_by_pos[(row, col)] = btn

        # Main Center
        self.cursor_frame = tk.Frame(self.root, bg="#202020")
        self.cursor_frame.grid(row=6, column=6, sticky="nsew", padx=pad, pady=pad)
        
        self.cursor_label = tk.Label(self.cursor_frame, text="Center", font=("Segoe UI", 10, "bold"), 
                                     bg=cur_c, fg=cur_fg, relief="flat", cursor="hand2")
        self.cursor_label.pack(expand=True, fill="both")
        
        self.cursor_label.bind("<Enter>", lambda e: [self.cursor_label.config(bg=cur_h), self.update_focus("CURSOR")])
        self.cursor_label.bind("<Leave>", lambda e: [self.cursor_label.config(bg=cur_c), self.update_focus("")])

    def build_navigation_graph(self):
        MAIN = self.main_center_pos
        TOP_C = (2, 6)
        BOT_C = (10, 6)
        LEFT_C = (6, 2)
        RIGHT_C = (6, 10)

        # Defines explicit robust state machine for the 2-step navigation
        self.nav = {
            MAIN: {'Up': TOP_C, 'Down': BOT_C, 'Left': LEFT_C, 'Right': RIGHT_C},
            
            # Top Group
            TOP_C: {'Up': (1,6), 'Down': (3,6), 'Left': (2,5), 'Right': (2,7)},
            (1,6): {'Down': TOP_C},
            (3,6): {'Up': TOP_C, 'Down': MAIN},
            (2,5): {'Right': TOP_C},
            (2,7): {'Left': TOP_C},
            
            # Bottom Group
            BOT_C: {'Up': (9,6), 'Down': (11,6), 'Left': (10,5), 'Right': (10,7)},
            (9,6): {'Down': BOT_C, 'Up': MAIN},
            (11,6): {'Up': BOT_C},
            (10,5): {'Right': BOT_C},
            (10,7): {'Left': BOT_C},

            # Left Group
            LEFT_C: {'Up': (5,2), 'Down': (7,2), 'Left': (6,1), 'Right': (6,3)},
            (5,2): {'Down': LEFT_C},
            (7,2): {'Up': LEFT_C},
            (6,1): {'Right': LEFT_C},
            (6,3): {'Left': LEFT_C, 'Right': MAIN},
            
            # Right Group
            RIGHT_C: {'Up': (5,10), 'Down': (7,10), 'Left': (6,9), 'Right': (6,11)},
            (5,10): {'Down': RIGHT_C},
            (7,10): {'Up': RIGHT_C},
            (6,9): {'Right': RIGHT_C, 'Left': MAIN},
            (6,11): {'Left': RIGHT_C},
        }

    def highlight_current_pos(self):
        # Reset all buttons to their normal color
        for pos, btn in self.buttons_by_pos.items():
            btn.config(bg=btn.bg_color)
            btn.label.config(bg=btn.bg_color)
        
        self.cursor_label.config(bg="#4CC2FF") 
        
        # Highlight current
        if self.current_pos in self.buttons_by_pos:
            btn = self.buttons_by_pos[self.current_pos]
            btn.config(bg=btn.hover_color)
            btn.label.config(bg=btn.hover_color)
            self.update_focus(btn.text)
            print(f"📍 Currently hovered on button: {btn.text}")
        elif self.current_pos == self.main_center_pos:
            self.cursor_label.config(bg="#2AA6DF")
            self.update_focus("CURSOR")
            print("📍 Currently hovered on: Main Center")
        else:
            self.update_focus("")

    def highlight_waiting(self, is_waiting):
        wait_color = "#FF3B30" # Red color
        
        if is_waiting:
            if self.current_pos in self.buttons_by_pos:
                btn = self.buttons_by_pos[self.current_pos]
                btn.config(bg=wait_color)
                btn.label.config(bg=wait_color)
            elif self.current_pos == self.main_center_pos:
                self.cursor_label.config(bg=wait_color)
        else:
            # Restore hover color
            if self.current_pos in self.buttons_by_pos:
                btn = self.buttons_by_pos[self.current_pos]
                btn.config(bg=btn.hover_color)
                btn.label.config(bg=btn.hover_color)
            elif self.current_pos == self.main_center_pos:
                self.cursor_label.config(bg="#2AA6DF")

    def load_test_signals(self):
        import os
        # Loading simulated signal pairs to trigger the GUI movements
        trials = [
             {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\yukari1h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\yukari1v.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2v.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sol14h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sol14V.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sag10h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sag10v.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2v.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sag10h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sag10v.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sol14h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\sol14V.txt"},
            {"h": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2h.txt",
             "v": r"D:\Projects\Semster 8\HCI\HCI Project\3-class\kirp2v.txt"},
        ]
        
        test_signals_array = []
        for trial in trials:
            if os.path.exists(trial['h']) and os.path.exists(trial['v']):
                with open(trial['h'], 'r') as fh, open(trial['v'], 'r') as fv:
                    h_sig = [int(line.strip()) for line in fh if line.strip()]
                    v_sig = [int(line.strip()) for line in fv if line.strip()]
                    test_signals_array.append((h_sig, v_sig))
            else:
                print(f"File not found for trial: {trial}")
                
        self.test_signals_queue = test_signals_array
        print(f"Loaded {len(test_signals_array)} trials into the array.")
        self.feed_next_test_signal()

    def feed_next_test_signal(self):
        if hasattr(self, 'test_signals_queue') and self.test_signals_queue:
            h_sig, v_sig = self.test_signals_queue.pop(0)
            print("\n🔄 Processing next test signal...")
            self.process_signal(h_sig, v_sig)
            
            # Feed the next one after the cooldown
            self.root.after(self.signal_delay_ms + 100, self.feed_next_test_signal)

    def extract_wavelet_features(self, signal):
        coeffs = pywt.wavedec(signal, 'db1', level=2)
        return coeffs[0]

    def process_signal(self, h_signal, v_signal):
        if not self.can_process_signal:
            return  # Ignore if still in cooldown
            
        h_array = np.array(h_signal)
        v_array = np.array(v_signal)
        
        h_features = self.extract_wavelet_features(h_array)
        v_features = self.extract_wavelet_features(v_array)
        
        combined_features = np.concatenate([h_features, v_features]).reshape(1, -1)
        
        if self.model:
            prediction = self.model.predict(combined_features)[0]
        else:
            print("No model loaded. Returning None.")
            prediction = None
            
        if prediction:
            self.move_gui(prediction)
            
            self.can_process_signal = False
            self.highlight_waiting(True)
            self.root.after(self.signal_delay_ms, self.enable_signal_processing)

    def enable_signal_processing(self):
        self.can_process_signal = True
        self.highlight_waiting(False)
            
    def move_gui(self, action):
        print(f"\n🎯 Model decided action: {action}")
        
        if action == 'Blink':
            # Execute button click if on a button
            if self.current_pos in self.buttons_by_pos:
                print(f"✅ Clicked (Blink) on button: {self.buttons_by_pos[self.current_pos].text}")
                self.buttons_by_pos[self.current_pos].on_click(None)
            elif self.current_pos == self.main_center_pos:
                print("✅ Clicked (Blink) in the Main Center.")
                
            # Always return to Main Center after Blink
            self.current_pos = self.main_center_pos
            self.highlight_current_pos()
            return
            
        # Graph-based precise navigation for 2-step process
        if self.current_pos in self.nav and action in self.nav[self.current_pos]:
            self.current_pos = self.nav[self.current_pos][action]
            
        self.highlight_current_pos()

    def button_click(self, text):
        if text == 'E':
            self.root.destroy()
            return
        elif text == 'C':
            self.reset()
            return
            
        if self.state == 'DONE':
            self.reset()
            
        if text in '0123456789':
            if self.state == 'WAIT_FIRST':
                self.first_digit = text
                self.display_var.set(self.first_digit)
                self.history_var.set("")
                self.state = 'WAIT_OP'
            elif self.state == 'WAIT_SECOND':
                self.second_digit = text
                # Execute calculation immediately!
                self.calculate()
                
        elif text in ['+', '-', 'x', '/', '%', 'p', '√']:
            if self.state == 'WAIT_OP':
                self.operation = text
                self.history_var.set(f"{self.first_digit} {self.operation}")
                self.state = 'WAIT_SECOND'
                
        elif text == 'n!':
            if self.state in ['WAIT_OP', 'WAIT_SECOND']:
                import math
                try:
                    num = int(float(self.first_digit))
                    res = math.factorial(num)
                    self.history_var.set(f"{num}!")
                    self.display_var.set(str(res))
                    self.first_digit = str(res)
                    self.state = 'DONE'
                except Exception as e:
                    self.display_var.set("Error")
                    self.state = 'DONE'

    def calculate(self):
        try:
            a = float(self.first_digit)
            b = float(self.second_digit) if self.second_digit else 0
            op = self.operation
            
            if op == '+': res = a + b
            elif op == '-': res = a - b
            elif op == 'x': res = a * b
            elif op == 'p': res = a ** b
            elif op == '√':
                if b == 0: res = "Error"
                else: res = a ** (1 / b)
            elif op == '%': res = a % b
            elif op == '/':
                if b == 0:
                    res = "Error"
                else:
                    res = a / b
                    
            if res != "Error":
                if isinstance(res, float) and res.is_integer():
                    res = int(res)
                else:
                    res = round(res, 2)
            
            self.history_var.set(f"{a} {op} {b} =")
            self.display_var.set(str(res))
            self.state = 'DONE'
        except Exception as e:
            self.display_var.set("Error")
            self.state = 'DONE'

    def reset(self):
        self.state = 'WAIT_FIRST'
        self.first_digit = None
        self.operation = None
        self.second_digit = None
        self.display_var.set("0")
        self.history_var.set("")

if __name__ == "__main__":
    root = tk.Tk()
    app = EOGCalculator(root)
    root.mainloop()
