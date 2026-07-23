from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ..db import connect, init_db, simple_query

class QueryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.date_from = tk.StringVar(value="2026-01-01")
        self.date_to = tk.StringVar(value="2026-01-31")
        self.port_code = tk.StringVar(value="")

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self, text="Date from (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.date_from, width=14).grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(self, text="Date to (YYYY-MM-DD)").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.date_to, width=14).grid(row=0, column=3, sticky="w", **pad)

        ttk.Label(self, text="Port Code (optional)").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.port_code, width=10).grid(row=1, column=1, sticky="w", **pad)

        ttk.Button(self, text="Run Query", command=self._run).grid(row=1, column=3, sticky="e", **pad)

        self.out = tk.Text(self, height=18, width=100)
        self.out.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def _run(self):
        conn = connect()
        init_db(conn)

        df = self.date_from.get().strip()
        dt = self.date_to.get().strip()
        pc = self.port_code.get().strip() or None

        try:
            rows = simple_query(conn, df, dt, pc)
        except Exception as e:
            messagebox.showerror("Query failed", str(e))
            return

        self.out.delete("1.0", "end")
        self.out.insert("end", f"Rows: {len(rows)}\n\n")
        for r in rows[:500]:
            self.out.insert("end", f"{r['sail_date']} | {r['ship_id']} | {r['location']} | {r['port_code'] or ''} | {r['eta'] or ''}-{r['etd'] or ''}\n")
        if len(rows) > 500:
            self.out.insert("end", "\n(Showing first 500 rows)\n")
