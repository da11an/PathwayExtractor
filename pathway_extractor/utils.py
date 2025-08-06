from pathlib import Path

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
