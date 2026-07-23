from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ..config import load_ships
from ..db import connect, init_db, count_year, delete_year

class MaintenanceTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.ships = load_ships()

        self.year_var = tk.StringVar(value="2026")
        self.ship_only_var = tk.BooleanVar(value=False)
        self.ship_var = tk.StringVar(value=self.ships[0].name if self.ships else "")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self, text="Year").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.year_var, width=10).grid(row=0, column=1, sticky="w", **pad)

        ttk.Checkbutton(self, text="Only selected ship", variable=self.ship_only_var, command=self._toggle_ship).grid(row=0, column=2, sticky="w", **pad)

        ttk.Label(self, text="Ship").grid(row=1, column=0, sticky="w", **pad)
        ship_names = [s.name for s in self.ships]
        self.ship_dd = ttk.Combobox(self, textvariable=self.ship_var, values=ship_names, state="readonly", width=40)
        self.ship_dd.grid(row=1, column=1, columnspan=2, sticky="w", **pad)

        ttk.Button(self, text="Preview rows to delete", command=self._preview).grid(row=2, column=1, sticky="w", **pad)
        ttk.Button(self, text="Delete year", command=self._delete).grid(row=2, column=2, sticky="w", **pad)

        self.info = tk.Text(self, height=12, width=100)
        self.info.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        self._toggle_ship()
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(2, weight=1)

    def _toggle_ship(self):
        state = "readonly" if self.ship_only_var.get() else "disabled"
        self.ship_dd.configure(state=state)

    def _resolve_ship_id(self):
        if not self.ship_only_var.get():
            return None
        ship = next((s for s in self.ships if s.name == self.ship_var.get()), None)
        return ship.id if ship else None

    def _preview(self):
        try:
            year = int(self.year_var.get().strip())
        except Exception:
            messagebox.showwarning("Invalid year", "Please enter a valid year (e.g., 2026).")
            return

        ship_id = self._resolve_ship_id()

        conn = connect()
        init_db(conn)
        c = count_year(conn, year, ship_id)

        scope = f"ship={ship_id}" if ship_id else "all ships"
        self.info.insert("end", f"Preview: {c} rows for {year} ({scope})\n")
        self.info.see("end")

    def _delete(self):
        try:
            year = int(self.year_var.get().strip())
        except Exception:
            messagebox.showwarning("Invalid year", "Please enter a valid year (e.g., 2026).")
            return

        ship_id = self._resolve_ship_id()
        conn = connect()
        init_db(conn)
        c = count_year(conn, year, ship_id)

        scope = f"ONLY {ship_id}" if ship_id else "ALL SHIPS"
        ok = messagebox.askyesno(
            "Confirm delete",
            f"This will delete {c} schedule rows for year {year} ({scope}).\n\nContinue?"
        )
        if not ok:
            return

        deleted = delete_year(conn, year, ship_id)
        self.info.insert("end", f"Deleted: {deleted} rows for {year} ({scope})\n")
        self.info.see("end")
        messagebox.showinfo("Done", f"Deleted {deleted} rows.")
