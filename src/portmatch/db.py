from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from portmatch.paths import db_path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS port_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_key TEXT NOT NULL,
                ship_name TEXT NOT NULL,
                sail_date TEXT NOT NULL,          -- YYYY-MM-DD
                location TEXT,
                berth_type TEXT,
                port_code TEXT,
                country_code TEXT,
                eta TEXT,
                etd TEXT,
                voyage TEXT,
                itinerary TEXT,
                source_file TEXT,
                imported_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_ship_date ON port_calls(ship_key, sail_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_date_port ON port_calls(sail_date, port_code)")


def insert_calls(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    init_db()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO port_calls (
                ship_key, ship_name, sail_date, location, berth_type, port_code, country_code,
                eta, etd, voyage, itinerary, source_file
            )
            VALUES (
                :ship_key, :ship_name, :sail_date, :location, :berth_type, :port_code, :country_code,
                :eta, :etd, :voyage, :itinerary, :source_file
            )
            """,
            rows,
        )
        return len(rows)


def delete_year(year: int) -> int:
    init_db()
    y = str(year)
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM port_calls WHERE substr(sail_date, 1, 4) = ?",
            (y,),
        )
        return cur.rowcount

def delete_ship_year(ship_key: str, year: int) -> int:
    init_db()
    y = str(year)
    with connect() as conn:
        cur = conn.execute(
            """
            DELETE FROM port_calls
            WHERE ship_key = ?
              AND substr(sail_date, 1, 4) = ?
            """,
            (ship_key, y),
        )
        return cur.rowcount


def list_imported_ships() -> List[Tuple[str, str]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT ship_key, ship_name FROM port_calls GROUP BY ship_key, ship_name ORDER BY ship_name"
        ).fetchall()
        return [(r["ship_key"], r["ship_name"]) for r in rows]


def query_calls(
    date_from: str,
    date_to: str,
    ship_key: Optional[str] = None,
    port_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()

    sql = """
        SELECT sail_date, ship_key, ship_name, location, port_code, eta, etd
        FROM port_calls
        WHERE sail_date BETWEEN ? AND ?
    """
    params: List[Any] = [date_from, date_to]

    if ship_key:
        sql += " AND ship_key = ?"
        params.append(ship_key)

    if port_code:
        sql += " AND UPPER(port_code) = UPPER(?)"
        params.append(port_code.strip())

    sql += " ORDER BY sail_date, ship_name"

    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]



def find_dry_docks(year: int) -> List[Dict[str, Any]]:
    """Return all schedule rows whose Location contains a dry-dock reference.

    Matching is case-insensitive and ignores spaces, hyphens, and underscores,
    so values such as DRYDOCK, Dry Dock, Dry-Dock, and
    "Freeport - DRYDOCK" are all included.
    """
    init_db()
    year_text = str(int(year))

    sql = """
        SELECT DISTINCT
            sail_date, ship_key, ship_name, location, port_code, eta, etd
        FROM port_calls
        WHERE substr(sail_date, 1, 4) = ?
          AND REPLACE(
                REPLACE(
                    REPLACE(LOWER(IFNULL(location, '')), ' ', ''),
                    '-', ''
                ),
                '_', ''
              ) LIKE '%drydock%'
        ORDER BY sail_date, ship_name, location
    """

    with connect() as conn:
        rows = conn.execute(sql, (year_text,)).fetchall()
        return [dict(r) for r in rows]

def find_ships_with_me(
    my_ship_key: str,
    date_from: str,
    date_to: str,
    port_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    For each (date, port) where my ship is in-port, list other ships at same (date, port).
    Excludes At Sea and blank port_code.
    """
    init_db()

    sql = """
    WITH mine AS (
        SELECT sail_date, port_code, location
        FROM port_calls
        WHERE ship_key = ?
          AND sail_date BETWEEN ? AND ?
          AND port_code IS NOT NULL AND TRIM(port_code) <> ''
          AND LOWER(IFNULL(location,'')) <> 'at sea'
    )
    SELECT
        m.sail_date AS sail_date,
        m.port_code AS port_code,
        m.location  AS location,
        o.ship_key  AS other_ship_key,
        o.ship_name AS other_ship_name
    FROM mine m
    JOIN port_calls o
      ON o.sail_date = m.sail_date
     AND UPPER(IFNULL(o.port_code,'')) = UPPER(m.port_code)
    WHERE o.ship_key <> ?
    """

    params: List[Any] = [my_ship_key, date_from, date_to, my_ship_key]

    if port_code:
        sql += " AND UPPER(m.port_code) = UPPER(?)"
        params.append(port_code.strip())

    sql += " ORDER BY m.sail_date, m.port_code, o.ship_name"

    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]