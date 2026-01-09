import tkinter as tk
from src.gui.app import App

def main():
    root = tk.Tk()
    # Set icon if available later
    # root.iconbitmap('icon.ico') 
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
