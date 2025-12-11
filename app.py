import tkinter as tk
from tkinterdnd2 import TkinterDnD

# Import functions from the modular files
from database import setup_database, get_session_count
from ui_upload import LapAnalyzerApp
from ui_viewer import DatabaseViewer

# ==============================================================================
# MAIN APPLICATION STRUCTURE & NAVIGATION
# ==============================================================================

def clear_screen(root):
    """Destroys all widgets on the current screen."""
    for widget in root.winfo_children():
        widget.destroy()

def open_upload_screen(root):
    """Opens the LapAnalyzerApp screen."""
    clear_screen(root)
    LapAnalyzerApp(root, back_command=lambda: show_main_menu(root))

def open_database_screen(root):
    """Opens the DatabaseViewer screen."""
    clear_screen(root)
    DatabaseViewer(root, back_command=lambda: show_main_menu(root))

def show_main_menu(root):
    """Builds and displays the main menu screen."""

    clear_screen(root)

    # Application Title
    tk.Label(
        root,
        text="Sim Racing Data Analyzer",
        font=('Arial', 28, 'bold'),
        fg='#004D40'
    ).pack(pady=(60, 30))

    # Option 1: Upload Practice
    upload_button = tk.Button(
        root,
        text="Upload Practice Session (Analyze & Save)",
        command=lambda: open_upload_screen(root),
        width=40,
        height=2,
        font=('Arial', 12)
    )
    upload_button.pack(pady=15)

    # Option 2: Database Viewer
    db_button = tk.Button(
        root,
        text="View Saved Sessions (Database)",
        command=lambda: open_database_screen(root),
        width=40,
        height=2,
        font=('Arial', 12)
    )
    db_button.pack(pady=15)

    # Setup Status
    count = get_session_count() # Get count from database module
    if count >= 0:
        status_text = f"Database Ready. {count} session(s) saved."
        status_color = 'green'
    else:
        status_text = "Database Error: Could not connect."
        status_color = 'red'

    tk.Label(
        root,
        text=status_text,
        fg=status_color,
        font=('Arial', 10)
    ).pack(pady=(40, 10))


def start_app():
    """Initializes the database and runs the main application loop."""

    setup_database() # Call setup from database module

    root = TkinterDnD.Tk()
    root.title("Sim Racing Data Analyzer")
    root.geometry("950x600")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    show_main_menu(root)

    root.mainloop()

if __name__ == "__main__":
    start_app()