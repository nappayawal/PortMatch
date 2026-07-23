from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Dict, List, Optional, Tuple

from portmatch.db import (
    delete_ship_year,
    delete_year,
    find_dry_docks,
    find_ships_with_me,
    list_imported_ships,
    query_calls,
)
from portmatch.importer import import_schedule
from portmatch.paths import ships_json_path, app_root


def _clean(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in {"nan", "none"}:
        return ""
    return s

def _clip(v: Any, width: int) -> str:
    s = _clean(v)
    return s if len(s) <= width else (s[: max(0, width - 1)] + "…")

def _fmt_time(eta: Any, etd: Any) -> str:
    e1 = _clean(eta)
    e2 = _clean(etd)
    if e1 and e2:
        return f"{e1}-{e2}"
    return e1 or e2 or ""


def _ship_slug(name: str) -> str:
    return "_".join(name.strip().lower().replace("-", " ").split())


def _set_icon(root: tk.Tk) -> None:
    # expects: assets/portmatchlite.ico
    icon_path = app_root() / "assets" / "portmatchlite.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(default=str(icon_path))
        except Exception:
            # some environments don’t like iconbitmap; safe to ignore
            pass


class PortMatchApp(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master

        master.title("PortMatch Lite v2.0")
        master.geometry("900x520")

        self._ships: List[str] = self._load_ships_names()
        self._build_ui()

    def _load_ships_names(self) -> List[str]:
        p = ships_json_path()
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        ships: List[str] = []
        for item in data:
            if isinstance(item, str):
                ships.append(item)
            elif isinstance(item, dict) and "name" in item:
                ships.append(str(item["name"]))
        return ships

    def _build_ui(self):
        nb = ttk.Notebook(self.master)
        nb.pack(fill="both", expand=True)

        self.tab_import = ttk.Frame(nb)
        self.tab_query = ttk.Frame(nb)
        self.tab_maint = ttk.Frame(nb)

        nb.add(self.tab_import, text="Import")
        nb.add(self.tab_query, text="Query")
        nb.add(self.tab_maint, text="Maintenance")

        self._build_import_tab()
        self._build_query_tab()
        self._build_maint_tab()

    # -------------------- Import tab --------------------
    def _build_import_tab(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self.tab_import, text="Ship").grid(row=0, column=0, sticky="w", **pad)
        self.import_ship = ttk.Combobox(self.tab_import, values=self._ships, state="readonly", width=35)
        self.import_ship.grid(row=0, column=1, sticky="w", **pad)
        if self._ships:
            self.import_ship.set(self._ships[0])

        ttk.Label(self.tab_import, text="Year").grid(row=1, column=0, sticky="w", **pad)
        self.import_year = ttk.Entry(self.tab_import, width=10)
        self.import_year.grid(row=1, column=1, sticky="w", **pad)
        self.import_year.insert(0, "2026")

        ttk.Label(self.tab_import, text="Schedule File").grid(row=2, column=0, sticky="w", **pad)
        self.import_file = ttk.Entry(self.tab_import, width=110)
        self.import_file.grid(row=2, column=1, sticky="w", **pad)

        ttk.Button(self.tab_import, text="Browse...", command=self._browse_import).grid(row=2, column=2, sticky="w", **pad)
        ttk.Button(self.tab_import, text="Import to Database", command=self._do_import).grid(row=3, column=1, sticky="w", **pad)

        self.import_log = tk.Text(self.tab_import, height=18, width=105, font=("Consolas", 10))
        self.import_log.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        self.tab_import.grid_rowconfigure(4, weight=1)
        self.tab_import.grid_columnconfigure(1, weight=1)

    def _browse_import(self):
        fp = filedialog.askopenfilename(
            title="Select schedule file",
            filetypes=[("Schedule files", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if fp:
            self.import_file.delete(0, "end")
            self.import_file.insert(0, fp)

    def _do_import(self):
        ship_name = self.import_ship.get().strip()
        year_txt = self.import_year.get().strip()
        fp = self.import_file.get().strip()

        if not ship_name:
            messagebox.showerror("Missing", "Please select a ship.")
            return
        if not year_txt.isdigit():
            messagebox.showerror("Invalid", "Year must be a number (e.g., 2026).")
            return
        if not fp:
            messagebox.showerror("Missing", "Please select a schedule file.")
            return

        year = int(year_txt)

        self.import_log.delete("1.0", "end")
        self.import_log.insert("end", f"Reading: {Path(fp).name}\n")

        try:
            inserted, skipped = import_schedule(fp, ship_name=ship_name, year=year)
            self.import_log.insert("end", f"Imported rows: {inserted}\n")
            if skipped:
                self.import_log.insert("end", f"Skipped rows: {skipped}\n")

            messagebox.showinfo("Import complete", f"Imported {inserted} rows for {ship_name} ({year}).")
            self._refresh_query_ships()

        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    # -------------------- Query tab --------------------
    def _build_query_tab(self):
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self.tab_query, text="Date from (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", **pad)
        self.q_from = ttk.Entry(self.tab_query, width=14)
        self.q_from.grid(row=0, column=1, sticky="w", **pad)
        self.q_from.insert(0, "2026-01-01")

        ttk.Label(self.tab_query, text="Date to (YYYY-MM-DD)").grid(row=0, column=2, sticky="w", **pad)
        self.q_to = ttk.Entry(self.tab_query, width=14)
        self.q_to.grid(row=0, column=3, sticky="w", **pad)
        self.q_to.insert(0, "2026-01-15")

        ttk.Label(self.tab_query, text="My Ship").grid(row=1, column=0, sticky="w", **pad)
        self.q_ship = ttk.Combobox(self.tab_query, values=[], state="readonly", width=32)
        self.q_ship.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self.tab_query, text="Port Code (optional)").grid(row=1, column=2, sticky="w", **pad)
        self.q_port = ttk.Entry(self.tab_query, width=10)
        self.q_port.grid(row=1, column=3, sticky="w", **pad)

        ttk.Label(self.tab_query, text="Dry Dock Year").grid(row=2, column=0, sticky="w", **pad)
        self.q_dry_dock_year = ttk.Entry(self.tab_query, width=10)
        self.q_dry_dock_year.grid(row=2, column=1, sticky="w", **pad)
        self.q_dry_dock_year.insert(0, "2026")

        ttk.Button(self.tab_query, text="Show schedule", command=self._do_query_schedule).grid(row=3, column=0, sticky="w", **pad)
        ttk.Button(self.tab_query, text="Find ships with me", command=self._do_query_with_me).grid(row=3, column=1, sticky="w", **pad)
        ttk.Button(self.tab_query, text="Find dry docks", command=self._do_query_dry_docks).grid(row=3, column=2, sticky="w", **pad)

        self.q_rows_label = ttk.Label(self.tab_query, text="Rows: 0")
        self.q_rows_label.grid(row=4, column=0, sticky="w", padx=10, pady=4)

        self.q_out = tk.Text(self.tab_query, height=18, width=105, font=("Consolas", 10))
        self.q_out.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

        self.tab_query.grid_rowconfigure(5, weight=1)
        self.tab_query.grid_columnconfigure(1, weight=1)

        self._refresh_query_ships()

    def _refresh_query_ships(self):
        imported = list_imported_ships()
        if imported:
            values = [name for _, name in imported]
            self.q_ship["values"] = values
            self.q_ship.set(values[0])
        else:
            self.q_ship["values"] = self._ships
            if self._ships:
                self.q_ship.set(self._ships[0])

    def _do_query_schedule(self):
        d1 = self.q_from.get().strip()
        d2 = self.q_to.get().strip()
        port = self.q_port.get().strip() or None

        ship_name = self.q_ship.get().strip()
        ship_key = _ship_slug(ship_name) if ship_name else None

        rows = query_calls(d1, d2, ship_key=ship_key, port_code=port)
        self._render_schedule(rows)

    def _do_query_dry_docks(self):
        year_text = self.q_dry_dock_year.get().strip()
        if not year_text.isdigit():
            messagebox.showerror("Invalid", "Dry Dock Year must be numeric (e.g., 2026).")
            return

        rows = find_dry_docks(int(year_text))
        self._render_dry_docks(rows, int(year_text))

    def _do_query_with_me(self):
        d1 = self.q_from.get().strip()
        d2 = self.q_to.get().strip()
        port = self.q_port.get().strip() or None

        ship_name = self.q_ship.get().strip()
        if not ship_name:
            messagebox.showerror("Missing", "Select 'My Ship' first.")
            return
        ship_key = _ship_slug(ship_name)

        rows = find_ships_with_me(ship_key, d1, d2, port_code=port)
        self._render_with_me(rows)

    def _render_schedule(self, rows: List[Dict[str, Any]]):
        self.q_out.delete("1.0", "end")
        self.q_rows_label.config(text=f"Rows: {len(rows)}")

        # Column widths (tune as you like)
        W_DATE, W_SHIP, W_LOC, W_PORT, W_TIME = 10, 18, 42, 5, 11

        header = (
            f"{'DATE':<{W_DATE}} | {'SHIP':<{W_SHIP}} | {'LOCATION':<{W_LOC}} | "
            f"{'PORT':<{W_PORT}} | {'TIME':<{W_TIME}}\n"
        )
        sep = (
            f"{'-' * W_DATE}-+-{'-' * W_SHIP}-+-{'-' * W_LOC}-+-"
            f"{'-' * W_PORT}-+-{'-' * W_TIME}\n"
        )
        self.q_out.insert("end", header)
        self.q_out.insert("end", sep)

        for r in rows:
            dt = _clip(r.get("sail_date"), W_DATE)
            ship = _clip(r.get("ship_name"), W_SHIP)
            loc = _clip(r.get("location"), W_LOC)
            port = _clip(r.get("port_code"), W_PORT)
            t = _clip(_fmt_time(r.get("eta"), r.get("etd")), W_TIME)

            line = (
                f"{dt:<{W_DATE}} | {ship:<{W_SHIP}} | {loc:<{W_LOC}} | "
                f"{port:<{W_PORT}} | {t:<{W_TIME}}\n"
            )
            self.q_out.insert("end", line)



    def _render_dry_docks(self, rows: List[Dict[str, Any]], year: int):
        self.q_out.delete("1.0", "end")
        self.q_rows_label.config(text=f"Dry-dock rows: {len(rows)}")

        W_DATE, W_SHIP, W_LOC, W_PORT, W_TIME = 10, 22, 42, 5, 11
        self.q_out.insert("end", f"SHIPS WITH DRY DOCK IN {year}\n\n")
        header = (
            f"{'DATE':<{W_DATE}} | {'SHIP':<{W_SHIP}} | {'LOCATION':<{W_LOC}} | "
            f"{'PORT':<{W_PORT}} | {'TIME':<{W_TIME}}\n"
        )
        sep = (
            f"{'-' * W_DATE}-+-{'-' * W_SHIP}-+-{'-' * W_LOC}-+-"
            f"{'-' * W_PORT}-+-{'-' * W_TIME}\n"
        )
        self.q_out.insert("end", header)
        self.q_out.insert("end", sep)

        for r in rows:
            dt = _clip(r.get("sail_date"), W_DATE)
            ship = _clip(r.get("ship_name"), W_SHIP)
            loc = _clip(r.get("location"), W_LOC)
            port = _clip(r.get("port_code"), W_PORT)
            time_text = _clip(_fmt_time(r.get("eta"), r.get("etd")), W_TIME)
            self.q_out.insert(
                "end",
                f"{dt:<{W_DATE}} | {ship:<{W_SHIP}} | {loc:<{W_LOC}} | "
                f"{port:<{W_PORT}} | {time_text:<{W_TIME}}\n",
            )

    def _refresh_maint_ships(self):
        imported = list_imported_ships()
        values = [name for _, name in imported]
        self.m_ship["values"] = values
        if values:
            self.m_ship.set(values[0])

    def _do_delete_ship_year(self):
        ship_name = self.m_ship.get().strip()
        year_txt = self.m_ship_year.get().strip()

        if not ship_name:
            messagebox.showerror("Missing", "Select a ship to delete.")
            return
        if not year_txt.isdigit():
            messagebox.showerror("Invalid", "Year must be numeric.")
            return

        ship_key = _ship_slug(ship_name)
        year = int(year_txt)

        count = delete_ship_year(ship_key, year)
        self.m_log.insert("end", f"Deleted rows for {ship_name} ({year}): {count}\n")

        # refresh dropdowns everywhere
        self._refresh_query_ships()
        self._refresh_maint_ships()




    def _render_with_me(self, rows: List[Dict[str, Any]]):
        self.q_out.delete("1.0", "end")
        self.q_rows_label.config(text=f"Rows: {len(rows)}")

        W_DATE, W_PORT, W_LOC, W_OTHER = 10, 5, 38, 22  # adjust W_LOC if you want wider

        header = f"{'DATE':<{W_DATE}} | {'PORT':<{W_PORT}} | {'LOCATION':<{W_LOC}} | {'OTHER SHIP':<{W_OTHER}}\n"
        sep = f"{'-' * W_DATE}-+-{'-' * W_PORT}-+-{'-' * W_LOC}-+-{'-' * W_OTHER}\n"
        self.q_out.insert("end", header)
        self.q_out.insert("end", sep)

        for r in rows:
            dt = _clip(r.get("sail_date"), W_DATE)
            port = _clip(r.get("port_code"), W_PORT)
            loc = _clip(r.get("location"), W_LOC)
            other = _clip(r.get("other_ship_name"), W_OTHER)

            line = f"{dt:<{W_DATE}} | {port:<{W_PORT}} | {loc:<{W_LOC}} | {other:<{W_OTHER}}\n"
            self.q_out.insert("end", line)




    # -------------------- Maintenance tab --------------------
    def _build_maint_tab(self):
        pad = {"padx": 10, "pady": 6}

        # --- Delete whole year ---
        ttk.Label(self.tab_maint, text="Delete whole year (e.g., 2026)").grid(row=0, column=0, sticky="w", **pad)
        self.m_year = ttk.Entry(self.tab_maint, width=10)
        self.m_year.grid(row=0, column=1, sticky="w", **pad)
        self.m_year.insert(0, "2026")

        ttk.Button(self.tab_maint, text="Delete Year", command=self._do_delete_year).grid(row=0, column=2, sticky="w",
                                                                                          **pad)

        # --- Delete one ship for a year ---
        ttk.Separator(self.tab_maint, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="ew", padx=10,
                                                                pady=10)

        ttk.Label(self.tab_maint, text="Delete one ship for a year").grid(row=2, column=0, sticky="w", **pad)

        ttk.Label(self.tab_maint, text="Ship").grid(row=3, column=0, sticky="w", **pad)
        self.m_ship = ttk.Combobox(self.tab_maint, values=[], state="readonly", width=32)
        self.m_ship.grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(self.tab_maint, text="Year").grid(row=3, column=2, sticky="w", padx=10, pady=6)
        self.m_ship_year = ttk.Entry(self.tab_maint, width=10)
        self.m_ship_year.grid(row=3, column=2, sticky="e", padx=10, pady=6)
        self.m_ship_year.insert(0, "2026")

        ttk.Button(self.tab_maint, text="Delete Ship+Year", command=self._do_delete_ship_year).grid(row=3, column=3,
                                                                                                    sticky="w", padx=10,
                                                                                                    pady=6)

        self.m_log = tk.Text(self.tab_maint, height=18, width=105, font=("Consolas", 10))
        self.m_log.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

        self.tab_maint.grid_rowconfigure(4, weight=1)
        self.tab_maint.grid_columnconfigure(1, weight=1)

        self._refresh_maint_ships()

    def _do_delete_year(self):
        y = self.m_year.get().strip()
        if not y.isdigit():
            messagebox.showerror("Invalid", "Year must be numeric.")
            return

        year = int(y)
        count = delete_year(year)
        self.m_log.insert("end", f"Deleted rows for year {year}: {count}\n")
        self._refresh_query_ships()
        self._refresh_maint_ships()


def run():
    root = tk.Tk()
    _set_icon(root)

    app = PortMatchApp(root)
    app.pack(fill="both", expand=True)

    # --- Bottom-right contact label ---
    email = "npayawal@carnival.com"
    footer = tk.Label(
        root,
        text=f"Questions? {email}",
        fg="gray40",
        bg=root.cget("background"),
        cursor="hand2",
    )
    footer.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-8)

    def copy_email(_=None):
        root.clipboard_clear()
        root.clipboard_append(email)
        root.update()  # keep clipboard content
        # Optional: quick feedback
        # messagebox.showinfo("Copied", f"{email} copied to clipboard.")

    footer.bind("<Button-1>", copy_email)
    # ---------------------------------

    root.mainloop()