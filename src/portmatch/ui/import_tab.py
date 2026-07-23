from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from ..config import load_ships
from ..db import connect, init_db, create_import, insert_schedule_rows, set_import_rows_loaded
from ..importer import read_schedule_file, normalize_rows

class ImportTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.ships = load_ships()

        self.ship_var = tk.StringVar(value=self.ships[0].name if self.ships else "")
        self.year_var = tk.StringVar(value="2026")
        self.file_var = tk.StringVar(value="")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self, text="Ship").grid(row=0, column=0, sticky="w", **pad)
        ship_names = [s.name for s in self.ships]
        self.ship_dd = ttk.Combobox(self, textvariable=self.ship_var, values=ship_names, state="readonly", width=40)
        self.ship_dd.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(self, text="Year").grid(row=1, column=0, sticky="w", **pad)
        self.year_entry = ttk.Entry(self, textvariable=self.year_var, width=10)
        self.year_entry.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Schedule File").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.file_var, width=60).grid(row=2, column=1, sticky="w", **pad)
        ttk.Button(self, text="Browse…", command=self._browse).grid(row=2, column=2, sticky="w", **pad)

        ttk.Button(self, text="Import to Database", command=self._import).grid(row=3, column=1, sticky="w", **pad)

        self.status = tk.Text(self, height=12, width=100)
        self.status.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select schedule file",
            filetypes=[("Excel files", "*.xlsx *.xlsm *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def _log(self, msg: str):
        self.status.insert("end", msg + "\n")
        self.status.see("end")

    def _import(self):
        if not self.file_var.get():
            messagebox.showwarning("Missing file", "Please choose a schedule file.")
            return

        try:
            year = int(self.year_var.get().strip())
        except Exception:
            messagebox.showwarning("Invalid year", "Please enter a valid year (e.g., 2026).")
            return

        ship = next((s for s in self.ships if s.name == self.ship_var.get()), None)
        if ship is None:
            messagebox.showwarning("Missing ship", "Please select a ship.")
            return

        file_path = Path(self.file_var.get())
        self._log(f"Reading: {file_path.name}")
        try:
            df = read_schedule_file(file_path)
        except Exception as e:
            messagebox.showerror("Read failed", f"Could not read file:\n{e}")
            return

        conn = connect()
        init_db(conn)

        import_id = create_import(conn, ship.id, year, str(file_path))
        rows = normalize_rows(df, ship.id, year, import_id, str(file_path))

        inserted = insert_schedule_rows(conn, rows)
        set_import_rows_loaded(conn, import_id, inserted)

        self._log(f"Imported rows: {inserted}")
        messagebox.showinfo("Import complete", f"Imported {inserted} rows for {ship.name} ({year}).")
