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
        
        file_var = StringVar(value=str(zip_files[0]))
        combo = ttk.Combobox(dialog, textvariable=file_var, values=[f.name for f in zip_files], state="readonly")
        combo.pack(pady=10, padx=10)
        
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
        # Find matching zip file from list
        for f in zip_files:
            print(f, selected_name)
            if str(f) == str(selected_name):
                zip_file = f
                break
    print("zip_file selected: ", zip_file)

    return zip_file
