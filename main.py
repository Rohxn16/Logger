import tkinter as tk
from pynput import keyboard

class KeystrokeNotepad:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Keystroke Notepad")
        self.root.geometry("800x500")

        # Simple text area
        self.text = tk.Text(self.root, font=("Courier New", 18), wrap='word')
        self.text.pack(expand=True, fill='both', padx=10, pady=10)

        # Global key listener
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()

    def on_press(self, key):
        try:
            char = key.char
            self.root.after(0, lambda: self.text.insert('end', char))
        except AttributeError:
            special = {
                keyboard.Key.space: ' ',
                keyboard.Key.enter: '\n',
                keyboard.Key.backspace: None,   # handled below
                keyboard.Key.tab: '    ',
            }
            if key == keyboard.Key.backspace:
                self.root.after(0, lambda: self.text.delete('end-2c', 'end-1c'))
            elif key in special:
                ch = special[key]
                self.root.after(0, lambda c=ch: self.text.insert('end', c))

    def quit(self):
        self.listener.stop()
        self.root.quit()

if __name__ == "__main__":
    KeystrokeNotepad()