from pathlib import Path
import re
import unicodedata

def get_zip_file(download_dir: Path) -> Path:
    # Find zip files in Downloads that match expected naming pattern
    # - Single or double digit month: [0-9] or [0-9][0-9]
    # - Single or double digit day: [0-9] or [0-9][0-9]  
    # - 4-digit year: [0-9][0-9][0-9][0-9]
    zip_files = list(download_dir.glob("*_[0-9]*-[0-9]*-[0-9][0-9][0-9][0-9]*.zip"))

    if not zip_files:
        # If no matching files found, show full file dialog
        from tkinter import filedialog
        selected_path = filedialog.askopenfilename(
            title="Select ZIP file of EC3 PDF Reports",
            filetypes=[("ZIP files", "*.zip")]
        )
        if not selected_path:
            print("No file selected. Exiting.")
            exit()
        zip_file = Path(selected_path)
    else:
        # Show dialog with matching files
        from tkinter import Tk, ttk, StringVar
        root = Tk()
        root.withdraw()  # Hide main window
        
        dialog = Tk()
        dialog.title("Select EC3 Report ZIP")
        
        label = ttk.Label(dialog, text="Choose the ZIP file to process:")
        label.pack(pady=10, padx=10)
        
        file_var = StringVar(value=zip_files[0].name)
        combo = ttk.Combobox(dialog, textvariable=file_var, values=[f.name for f in zip_files], state="readonly")
        combo.pack(pady=10, padx=10)
        
        # Bind selection event to update the variable
        def on_combo_select(event):
            file_var.set(combo.get())
        
        combo.bind('<<ComboboxSelected>>', on_combo_select)
        
        def on_select():
            dialog.quit()
        
        btn = ttk.Button(dialog, text="Select", command=on_select)
        btn.pack(pady=10, padx=10)
        
        dialog.mainloop()
        dialog.destroy()
        
        # Get selected file path
        selected_name = file_var.get()
        if not selected_name:
            print("No file selected. Exiting.")
            exit()
        
        # Debug: print available files and selected name
        print(f"Selected name: '{selected_name}'")
        print("Available files:")
        for f in zip_files:
            print(f"  '{f.name}'")
        
        # Find matching zip file from list
        try:
            zip_file = next(f for f in zip_files if f.name == selected_name)
        except StopIteration:
            print(f"Error: Could not find file '{selected_name}' in the list of available files.")
            print("This might be due to a mismatch between the dropdown values and actual filenames.")
            exit()
    print("zip_file selected: ", zip_file)

    return zip_file


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename to be safe for Windows and other filesystems.
    
    Removes or replaces invalid characters, handles Unicode, and ensures
    the filename doesn't exceed length limits.
    
    Args:
        filename: The original filename (without extension)
        max_length: Maximum length for the filename (default 200 to leave room for extension)
    
    Returns:
        A sanitized filename safe for use in file paths
    """
    # Windows invalid characters: < > : " / \ | ? *
    # Also remove control characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    
    # Replace invalid characters with underscore
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Normalize Unicode characters (e.g., convert accented characters to their base form)
    # This helps with characters that might cause issues on Windows
    try:
        # Try to normalize to NFC form (canonical composition)
        sanitized = unicodedata.normalize('NFC', sanitized)
    except Exception:
        # If normalization fails, just use the string as-is after removing invalid chars
        pass
    
    # Remove leading/trailing spaces and periods (Windows doesn't allow these)
    sanitized = sanitized.strip(' .')
    
    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Handle reserved names on Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
    if sanitized.upper() in reserved_names:
        sanitized = f'_{sanitized}_'
    
    # Truncate if too long (leave room for extension)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed'
    
    return sanitized
