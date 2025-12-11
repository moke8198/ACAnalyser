import tkinter as tk
from tkinter import messagebox, ttk

# Import functions from other modules
from analysis import format_ms_to_time
# UPDATED: Import the delete function
from database import get_unique_cars_and_tracks, get_sessions, get_laps_for_session, delete_session_by_id

class DatabaseViewer:
    def __init__(self, master, back_command):
        self.master = master
        self.back_command = back_command
        self.selected_car = tk.StringVar(value='All Cars')
        self.selected_track = tk.StringVar(value='All Tracks')

        self.main_frame = ttk.Frame(master, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(3, weight=1)
        self.main_frame.rowconfigure(5, weight=1)

        # --- Header ---
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        tk.Label(header_frame, text="Saved Sessions Database", font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        ttk.Button(header_frame, text="< Back to Main Menu", command=self.back_command).pack(side=tk.RIGHT)

        # --- Filters ---
        filter_frame = ttk.LabelFrame(self.main_frame, text="Filters", padding=5)
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(filter_frame, text="Car:").pack(side=tk.LEFT, padx=(5, 5))
        self.car_combobox = ttk.Combobox(filter_frame, textvariable=self.selected_car, state="readonly", width=25)
        self.car_combobox.pack(side=tk.LEFT, padx=5)
        self.car_combobox.bind('<<ComboboxSelected>>', self.refresh_session_list)
        ttk.Label(filter_frame, text="Track:").pack(side=tk.LEFT, padx=(20, 5))
        self.track_combobox = ttk.Combobox(filter_frame, textvariable=self.selected_track, state="readonly", width=25)
        self.track_combobox.pack(side=tk.LEFT, padx=5)
        self.track_combobox.bind('<<ComboboxSelected>>', self.refresh_session_list)

        # --- Session List (Top Table) ---
        tk.Label(self.main_frame, text="1. Select a Session:", font=('Arial', 10, 'bold'), anchor='w').grid(row=2, column=0, sticky=tk.W, pady=(10,0))
        session_cols = ('ID', 'Car', 'Track', 'Best Lap', 'Theoretical', 'Date')
        self.session_tree = ttk.Treeview(self.main_frame, columns=session_cols, show='headings', height=6)
        self.session_tree.heading('ID', text='ID')
        self.session_tree.heading('Car', text='Car Model')
        self.session_tree.heading('Track', text='Track')
        self.session_tree.heading('Best Lap', text='Best Lap')
        self.session_tree.heading('Theoretical', text='Theoretical')
        self.session_tree.heading('Date', text='Session Date')
        self.session_tree.column('ID', width=40, anchor=tk.CENTER)
        self.session_tree.column('Car', width=150)
        self.session_tree.column('Track', width=150)
        self.session_tree.column('Best Lap', width=80, anchor=tk.CENTER)
        self.session_tree.column('Theoretical', width=80, anchor=tk.CENTER)
        self.session_tree.column('Date', width=140, anchor=tk.CENTER)
        self.session_tree.grid(row=3, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        sess_scroll = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=sess_scroll.set)
        sess_scroll.grid(row=3, column=1, sticky=(tk.N, tk.S))
        
        # ADDED BINDINGS FOR DELETION
        self.session_tree.bind('<<TreeviewSelect>>', self.on_session_select)
        self.session_tree.bind('<Delete>', self.confirm_delete_session)      # Bind Delete Key
        self.session_tree.bind('<Button-3>', self.show_context_menu)         # Bind Right Click (Button-3)

        # --- Lap List (Bottom Table) ---
        tk.Label(self.main_frame, text="2. Lap Details for Selected Session:", font=('Arial', 10, 'bold'), anchor='w').grid(row=4, column=0, sticky=tk.W, pady=(20,0))
        lap_cols = ('Lap', 'Time', 'S1', 'S2', 'S3', 'Cuts', 'Status')
        self.lap_tree = ttk.Treeview(self.main_frame, columns=lap_cols, show='headings', height=8)
        self.lap_tree.heading('Lap', text='Lap #')
        self.lap_tree.heading('Time', text='Lap Time')
        self.lap_tree.heading('S1', text='Sector 1')
        self.lap_tree.heading('S2', text='Sector 2')
        self.lap_tree.heading('S3', text='Sector 3')
        self.lap_tree.heading('Cuts', text='Cuts')
        self.lap_tree.heading('Status', text='Status')
        self.lap_tree.column('Lap', width=50, anchor=tk.CENTER)
        self.lap_tree.column('Time', width=90, anchor=tk.CENTER)
        self.lap_tree.column('S1', width=90, anchor=tk.CENTER)
        self.lap_tree.column('S2', width=90, anchor=tk.CENTER)
        self.lap_tree.column('S3', width=90, anchor=tk.CENTER)
        self.lap_tree.column('Cuts', width=50, anchor=tk.CENTER)
        self.lap_tree.column('Status', width=80, anchor=tk.CENTER)
        self.lap_tree.grid(row=5, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        lap_scroll = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.lap_tree.yview)
        self.lap_tree.configure(yscrollcommand=lap_scroll.set)
        lap_scroll.grid(row=5, column=1, sticky=(tk.N, tk.S))

        # Initial Load
        self.populate_filters()
        self.refresh_session_list()


    def populate_filters(self):
        """Fetches unique car models and tracks to populate the comboboxes using database module."""
        cars, tracks = get_unique_cars_and_tracks()
        self.car_combobox['values'] = tuple(cars)
        self.track_combobox['values'] = tuple(tracks)

    def refresh_session_list(self, event=None):
        """Updates the top table based on filters using database module."""
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        for item in self.lap_tree.get_children():
            self.lap_tree.delete(item)

        # Use imported database function
        records = get_sessions(
            car_filter=self.selected_car.get(),
            track_filter=self.selected_track.get()
        )

        for row in records:
            # row: (id, car_model, track_name, best_lap_time, theoretical_lap_time, date_time)
            formatted = (
                row[0], row[1], row[2],
                format_ms_to_time(row[3]),
                format_ms_to_time(row[4]),
                row[5]
            )
            self.session_tree.insert('', tk.END, values=formatted)

    def on_session_select(self, event):
        """Triggered when user clicks a row in the top table."""
        selected_items = self.session_tree.selection()
        if not selected_items:
            return
        # Ensure focus is set on the clicked item for immediate deletion
        self.session_tree.focus(selected_items[0])
        
        item_values = self.session_tree.item(selected_items[0])['values']
        session_id = item_values[0]
        self.load_laps_for_session(session_id)

    def load_laps_for_session(self, session_id):
        """Queries the database for laps belonging to the session and updates bottom table."""
        for item in self.lap_tree.get_children():
            self.lap_tree.delete(item)

        # Use imported database function
        laps = get_laps_for_session(session_id)

        for lap in laps:
            # lap: (lap_number, lap_time, sector_1, sector_2, sector_3, cuts, is_valid)
            lap_number, lap_time, s1, s2, s3, cuts, is_valid = lap

            valid_status = "VALID" if is_valid == 1 else "INVALID"
            if cuts > 0:
                valid_status = f"CUTS ({cuts})"

            formatted = (
                lap_number,
                format_ms_to_time(lap_time),
                format_ms_to_time(s1),
                format_ms_to_time(s2),
                format_ms_to_time(s3),
                cuts,
                valid_status
            )
            self.lap_tree.insert('', tk.END, values=formatted)

    # --- NEW DELETION LOGIC ---
    def get_selected_session_id(self):
        """Helper to get the ID of the currently selected session."""
        selected_items = self.session_tree.selection()
        if selected_items:
            # The ID is the first value in the row
            return self.session_tree.item(selected_items[0], 'values')[0]
        return None

    def confirm_delete_session(self, event=None):
        """Prompts user and executes deletion if confirmed (triggered by Delete key or context menu)."""
        session_id = self.get_selected_session_id()
        if not session_id:
            messagebox.showwarning("Warning", "Please select a session to delete.")
            return

        # Get session details for confirmation message
        selected_item = self.session_tree.selection()[0]
        values = self.session_tree.item(selected_item, 'values')
        # Display ID, Car, Track, and Date (index 0, 1, 2, 5)
        session_info = f"Session ID: {values[0]}\nCar: {values[1]}\nTrack: {values[2]}\nDate: {values[5]}"

        if messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to permanently delete this session and all its lap data?\n\n{session_info}"
        ):
            # Call the imported database function
            if delete_session_by_id(session_id):
                messagebox.showinfo("Success", f"Session {session_id} successfully deleted.")
                self.refresh_session_list() # Reload the session list
                # Clear the lap details tree
                for i in self.lap_tree.get_children():
                    self.lap_tree.delete(i)
            # If deletion fails, delete_session_by_id handles the error message

    def show_context_menu(self, event):
        """Displays a right-click context menu for deletion."""
        # Check if an item was clicked directly
        item_id = self.session_tree.identify_row(event.y)
        
        # If an item was clicked, select it
        if item_id:
            self.session_tree.selection_set(item_id)
            
            menu = tk.Menu(self.main_frame, tearoff=0)
            menu.add_command(label="Delete Selected Session", command=self.confirm_delete_session)
            
            try:
                # Display the menu at the cursor position
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()