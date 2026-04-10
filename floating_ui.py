import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import queue
import threading
import os
import time

class FloatingUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Borderless
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")  # Windows transparency
        self.root.configure(bg="black")

        self.queue = queue.Queue()

        # Get screen width and height to position bottom right
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.window_width = 350
        self.window_height = 120
        x = screen_width - self.window_width - 20
        y = screen_height - self.window_height - 60
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

        # Animation: fade-in
        self.fade_in()

        # Canvas and logo
        self.canvas = tk.Canvas(self.root, width=120, height=120, bg="black", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        img = Image.open("ironman.jpg").resize((90, 90), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_oval(15, 15, 105, 105, fill="black", outline="")
        self.canvas.create_image(60, 60, image=self.photo)

        # Dialogue bubble
        self.dialogue = tk.Label(
            self.root, text="Friday is Idle...", font=("Segoe UI", 12),
            bg="#222", fg="white", wraplength=200, justify="left", anchor="w",
            padx=12, pady=6, bd=2, relief="ridge"
        )
        self.dialogue.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        self.root.grid_columnconfigure(1, weight=1)

        self.visible = True

    def update_status(self, text):
        self.queue.put(text)

    def hide(self):
        self.root.withdraw()
        self.visible = False

    def show(self):
        self.root.deiconify()
        self.visible = True

    def fade_in(self):
        for i in range(0, 10):
            self.root.attributes("-alpha", i * 0.1)
            self.root.update()
            time.sleep(0.02)

    def fade_out(self):
        for i in reversed(range(0, 10)):
            self.root.attributes("-alpha", i * 0.1)
            self.root.update()
            time.sleep(0.02)

    def process_queue(self):
        try:
            while not self.queue.empty():
                status = self.queue.get_nowait()
                self.dialogue.config(text=status)
                if not self.visible:
                    self.show()
        except queue.Empty:
            pass
        self.root.after(200, self.process_queue)

    def run(self):
        self.process_queue()
        self.root.mainloop()

# Optional test run
if __name__ == "__main__":
    ui = FloatingUI()
    threading.Thread(target=ui.run, daemon=True).start()

    while True:
        ui.update_status("🎧 Listening...")
        time.sleep(2)
        ui.update_status("💬 Responding...")
        time.sleep(2)
        ui.fade_out()
        ui.hide()
        time.sleep(2)
        ui.fade_in()
        ui.show()
        time.sleep(2)