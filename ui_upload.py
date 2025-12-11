import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from tkinterdnd2 import DND_FILES

# Import functions from other modules
from analysis import analyze_ac_session
from database import save_session_data

class LapAnalyzerApp:
    def __init__(self, master, back_command):
        self.master = master
        self.back_command = back_command

        self.file_path = tk.StringVar()
        self.summary_data = None # Store summary data for saving (includes 'all_laps' and 'session_datetime')

        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # UI Layout setup
        self.back_button = ttk.Button(self.frame, text="< Back to Main Menu", command=self.back_command)
        self.back_button.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(self.frame, text="Analyze Session Data", font=('Arial', 14, 'bold')).grid(row=0, column=1, columnspan=2, pady=5, sticky=tk.E)

        # File selection area
        ttk.Label(self.frame, text="JSON File Path:").grid(row=1, column=0, sticky=tk.W, pady=(15, 5))
        
        # Drop target is the Entry widget
        self.file_entry = ttk.Entry(self.frame, textvariable=self.file_path, width=70)
        self.file_entry.grid(row=1, column=1, padx=5, pady=(15, 5), sticky=(tk.W, tk.E))

        self.browse_button = ttk.Button(self.frame, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=1, column=2, padx=5, pady=(15, 5), sticky=tk.W)

        self.action_frame = ttk.Frame(self.frame)
        self.action_frame.grid(row=2, column=1, pady=10)

        self.save_button = ttk.Button(self.action_frame, text="Save Session to Database", command=self.save_session, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=10)

        self.output_text = tk.Text(self.frame, wrap=tk.WORD, height=20, width=80, bg="#EAEAEA")
        self.output_text.grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.scrollbar = ttk.Scrollbar(self.frame, command=self.output_text.yview)
        self.output_text['yscrollcommand'] = self.scrollbar.set
        self.scrollbar.grid(row=3, column=3, sticky=(tk.N, tk.S, tk.W))

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(3, weight=1)

        # Drag-and-Drop setup: Already bound to self.file_entry
        self.frame.drop_target_register(DND_FILES)
        self.frame.dnd_bind('<<Drop>>', self.on_drop)

        self.display_output(["Welcome! Drag and drop an Assetto Corsa session JSON file into the window or use the Browse button to begin."])

    def browse_file(self):
        filename = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("Assetto Corsa Session JSON", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
            self.analyze_session()

    def on_drop(self, event):
        """Handler for file drop on the entry box."""
        # Clean up the path string which often includes surrounding braces/quotes
        file_path = event.data.strip('{}').strip()
        
        # Handle cases where multiple files are dropped (only take the first)
        if ' ' in file_path and not os.path.exists(file_path):
             # This handles space-separated paths typically from D&D on Windows
             file_path = file_path.split()[0]
             
        if os.path.exists(file_path):
            self.file_path.set(file_path)
            self.analyze_session()
        else:
            self.display_output([f"Error: Dropped file path is invalid or file does not exist: {file_path}"])


    def analyze_session(self):
        """Analyzes the session file and displays the report."""
        file_path = self.file_path.get()
        if not file_path:
            self.display_output(["Please select a file first."])
            return

        # Use imported analysis function
        # analyze_ac_session returns (report_lines, summary_data)
        report, summary_data = analyze_ac_session(file_path)
        self.display_output(report)

        # Check for a valid session (best lap time > 0)
        if summary_data and summary_data.get('best_lap_ms', -1) > 0:
            self.save_button['state'] = tk.NORMAL
            self.summary_data = summary_data
        else:
            self.save_button['state'] = tk.DISABLED
            self.summary_data = None


    def save_session(self):
        """Calls the function to write data to SQLite."""
        if self.summary_data:
            # Use imported save function
            success = save_session_data(
                raw_data=self.summary_data['raw_data'],
                best_lap_ms=self.summary_data['best_lap_ms'],
                theoretical_ms=self.summary_data['theoretical_ms'],
                # Pass the 'all_laps' data
                all_laps_data=self.summary_data['all_laps'], 
                # Pass the extracted 'session_datetime'
                session_datetime=self.summary_data.get('session_datetime') 
            )

            if success:
                messagebox.showinfo("Success", "Session successfully saved to database!")
                self.save_button['state'] = tk.DISABLED
                self.back_command()
            # Note: database.py handles error message for failed save
        else:
            messagebox.showwarning("Error", "No valid session data is currently loaded to save.")

    def display_output(self, lines):
        self.output_text.delete(1.0, tk.END)
        for line in lines:
            self.output_text.insert(tk.END, line + "\n")