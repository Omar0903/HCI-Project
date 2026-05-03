import tkinter as tk
from tkinter import font as tkfont

class FlatButton(tk.Frame):
    def __init__(self, parent, text, bg_color, hover_color, text_color, command, on_hover=None, **kwargs):
        super().__init__(parent, bg=bg_color, relief="flat", borderwidth=0, **kwargs)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.command = command
        self.text = text
        self.on_hover = on_hover
        self.text_color = text_color
        
        # تصغير الخط ليتناسب مع الحجم الجديد
        self.label = tk.Label(self, text=text, font=("Segoe UI", 12, "normal"), 
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
        self.root.title("Calculator - Compact")
        
        self.root.geometry("350x450")
        self.root.configure(bg="#202020")
        
        self.state = 'WAIT_FIRST'
        self.first_digit = None
        self.operation = None
        self.second_digit = None
        
        # تصغير الخطوط لتناسب النافذة الجديدة
        self.display_font = tkfont.Font(family="Segoe UI Semibold", size=24, weight="bold")
        self.history_font = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        self.focus_font = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        
        self.display_frame = tk.Frame(self.root, bg="#202020", bd=0)
        self.display_frame.grid(row=0, column=0, columnspan=7, sticky="nsew", pady=(10, 5))
        
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

        for i in range(7):
            self.root.grid_columnconfigure(i, weight=1, uniform="sq")
            
        for i in range(8):
            if i == 0:
                self.root.grid_rowconfigure(i, weight=1) 
            else:
                self.root.grid_rowconfigure(i, weight=1, uniform="sq")
            
        self.create_buttons()

    def get_hover_name(self, text):
        names = {
            '+': "Addition",
            '-': "Subtraction",
            'x': "Multiplication",
            '/': "Division",
            'E': "Exit",
            'C': "Clear",
            'CURSOR': "Center Cursor"
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
        num_c = "#3B3B3B"  
        num_h = "#4C4C4C"  
        num_fg = "#FFFFFF"
        op_c = "#FF9500"   
        op_h = "#FFB340"
        op_fg = "#FFFFFF"
        
        sys_c = "#A5A5A5"
        sys_h = "#D9D9D9"
        sys_fg = "#000000"
        
        cur_c = "#4CC2FF"  
        cur_h = "#2AA6DF"
        cur_fg = "#000000"
        
        buttons = {
            '-': (1, 3, op_c, op_h, op_fg),
            '/': (2, 2, op_c, op_h, op_fg), '+': (2, 3, op_c, op_h, op_fg), 'x': (2, 4, op_c, op_h, op_fg),
            
            'E': (3, 1, sys_c, sys_h, sys_fg), 
            'C': (4, 0, sys_c, sys_h, sys_fg), '9': (4, 1, num_c, num_h, num_fg),
            '8': (5, 1, num_c, num_h, num_fg),
            
            '7': (3, 5, num_c, num_h, num_fg),
            '5': (4, 5, num_c, num_h, num_fg), '6': (4, 6, num_c, num_h, num_fg),
            '4': (5, 5, num_c, num_h, num_fg),
            
            '0': (6, 2, num_c, num_h, num_fg), '1': (6, 3, num_c, num_h, num_fg), '2': (6, 4, num_c, num_h, num_fg),
            '3': (7, 3, num_c, num_h, num_fg),
        }
        
        pad = 1 
        
        for text, config in buttons.items():
            row, col, bg, hover, fg = config
            btn = FlatButton(self.root, text=text, bg_color=bg, hover_color=hover, text_color=fg,
                             command=lambda t=text: self.button_click(t),
                             on_hover=self.update_focus)
            btn.grid(row=row, column=col, padx=pad, pady=pad, sticky="nsew")

        self.cursor_frame = tk.Frame(self.root, bg="#202020")
        self.cursor_frame.grid(row=4, column=3, sticky="nsew", padx=pad, pady=pad)
        
        self.cursor_label = tk.Label(self.cursor_frame, text="Centre", font=("Segoe UI", 10, "normal"), 
                                     bg=cur_c, fg=cur_fg, relief="flat", cursor="hand2")
        self.cursor_label.pack(expand=True, fill="both")
        
        self.cursor_label.bind("<Enter>", lambda e: [self.cursor_label.config(bg=cur_h), self.update_focus("CURSOR")])
        self.cursor_label.bind("<Leave>", lambda e: [self.cursor_label.config(bg=cur_c), self.update_focus("")])

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
                self.calculate()
        elif text in '+-x/':
            if self.state == 'WAIT_OP':
                self.operation = text
                self.history_var.set(f"{self.first_digit} {self.operation}")
                self.state = 'WAIT_SECOND'

    def calculate(self):
        try:
            a = int(self.first_digit)
            b = int(self.second_digit)
            op = self.operation
            
            if op == '+': res = a + b
            elif op == '-': res = a - b
            elif op == 'x': res = a * b
            elif op == '/':
                if b == 0:
                    res = "Error"
                else:
                    res = a / b
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
