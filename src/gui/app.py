import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import logging
import queue
from ..organizer.mod_organizer import ModOrganizer

class LogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sims 4 Mod Organizer by Ygor Amaral")
        self.root.geometry("600x500")
        
        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.delete_originals = tk.BooleanVar(value=False)  # Default: keep files
        self.status_var = tk.StringVar(value="Ready")
        
        self.organizer = None
        self.log_queue = queue.Queue()
        
        self.create_widgets()
        self.setup_logging()
        self.root.after(100, self.process_logs)

    def setup_logging(self):
        self.logger = logging.getLogger('Sims4ModOrganizer')
        self.logger.setLevel(logging.DEBUG)  # Changed to DEBUG to see detailed info
        handler = LogHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also enable debug logging for parser modules
        logging.getLogger('src.parser.cas_part').setLevel(logging.DEBUG)
        logging.getLogger('src.parser.cas_part').addHandler(handler)

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
        self.root.after(100, self.process_logs)

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Source Selection
        src_frame = ttk.LabelFrame(main_frame, text="Source Folder (Downloads)", padding="5")
        src_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(src_frame, textvariable=self.source_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(src_frame, text="Browse", command=self.browse_source).pack(side=tk.RIGHT)

        # Destination Selection
        dest_frame = ttk.LabelFrame(main_frame, text="Destination Folder (Mods)", padding="5")
        dest_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(dest_frame, textvariable=self.dest_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dest_frame, text="Browse", command=self.browse_dest).pack(side=tk.RIGHT)

        # Options
        opts_frame = ttk.Frame(main_frame)
        opts_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(opts_frame, text="Delete original files after organizing", variable=self.delete_originals).pack(side=tk.LEFT)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.run_btn = ttk.Button(btn_frame, text="Organize Mods", command=self.start_organizing)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_organizing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Progress
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, textvariable=self.status_var).pack(anchor=tk.W)

        # Log Window
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, state='normal')
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_path.set(path)

    def browse_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_path.set(path)

    def start_organizing(self):
        src = self.source_path.get()
        dest = self.dest_path.get()
        
        if not src or not dest:
            messagebox.showerror("Error", "Please select both source and destination folders.")
            return

        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.progress['value'] = 0
        
        self.organizer = ModOrganizer(src, dest, not self.delete_originals.get(), self.logger)
        
        thread = threading.Thread(target=self.run_bg_task)
        thread.daemon = True
        thread.start()

    def stop_organizing(self):
        if self.organizer:
            self.organizer.stop()
            self.status_var.set("Stopping...")

    def run_bg_task(self):
        try:
            self.organizer.organize(self.update_progress)
        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}")
            self.status_var.set("Error occurred")
        finally:
            self.root.after(0, self.reset_ui)

    def update_progress(self, message, percent):
        self.root.after(0, lambda: self._update_ui(message, percent))

    def _update_ui(self, message, percent):
        self.status_var.set(message)
        self.progress['value'] = percent * 100

    def reset_ui(self):
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.organizer.stop_requested:
             self.status_var.set("Stopped by user")
