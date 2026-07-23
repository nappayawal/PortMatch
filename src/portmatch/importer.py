from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd

from portmatch.db import insert_calls


def _slug(name: str) -> str:
    return "_".join(name.strip().lower().replace("-", " ").split())


def _is_na(v: Any) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except Exception:
        return False


def _clean(v: Any) -> Optional[str]:
    if _is_na(v):
        return None
    s = str(v).strip()
    if not s:
        return None
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    return s


def _month_to_num(m: Any) -> int:
    m = _clean(m)
    if m is None:
        raise ValueError("Missing month")
    s = m.strip()
    for i in range(1, 13):
        if s.lower() in {calendar.month_name[i].lower(), calendar.month_abbr[i].lower()}:
            return i
    raise ValueError(f"Unknown month: {s}")


def _col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for name in candidates:
        key = name.strip().lower()
        if key in lookup:
            return lookup[key]
    return None


def _read_text_with_fallback(path: Path) -> Tuple[str, str]:
    """
    Return (text, encoding_used). Try common encodings for CSV exports.
    """
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_err: Optional[Exception] = None
    for enc in encodings:
        try:
            return path.read_text(encoding=enc), enc
        except Exception as e:
            last_err = e
            continue
    raise last_err  # type: ignore


def _detect_header_and_sep(lines: List[str], max_scan: int = 80) -> Tuple[Optional[int], Optional[str]]:
    need = {"month", "day", "location"}
    seps = [",", "\t", ";", "|"]

    scan = min(max_scan, len(lines))
    for i in range(scan):
        line = lines[i].strip()
        if not line:
            continue
        for sep in seps:
            parts = [p.strip().strip('"') for p in line.split(sep)]
            tokens = {p.lower() for p in parts if p}
            if need.issubset(tokens):
                return i, sep
    return None, None


def _read_schedule_df(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()

    if ext in {".xlsx", ".xls"}:
        df_raw = pd.read_excel(path, header=None)
        need = {"month", "day", "location"}
        header_row = None
        for i in range(min(80, len(df_raw))):
            row = df_raw.iloc[i].tolist()
            tokens = {str(x).strip().lower() for x in row if not _is_na(x)}
            if need.issubset(tokens):
                header_row = i
                break

        if header_row is None:
            df = pd.read_excel(path)
            df.columns = [str(c).strip() for c in df.columns]
            return df

        header_vals = df_raw.iloc[header_row].tolist()
        df = df_raw.iloc[header_row + 1 :].copy()
        df.columns = [str(c).strip() for c in header_vals]
        df = df.reset_index(drop=True)
        return df

    # CSV-like: read text with encoding fallback first (for header detection)
    text, enc_used = _read_text_with_fallback(path)
    lines = text.splitlines()

    hdr, sep = _detect_header_and_sep(lines)

    if hdr is None or sep is None:
        # fallback: let pandas try with the detected encoding
        df = pd.read_csv(path, encoding=enc_used, engine="python", index_col=False)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    df = pd.read_csv(
        path,
        skiprows=hdr,
        sep=sep,
        encoding=enc_used,
        engine="python",
        index_col=False,
        skipinitialspace=True,
    )
    df.columns = [str(c).strip() for c in df.columns]
    return df


def import_schedule(file_path: str, ship_name: str, year: int) -> Tuple[int, int]:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(file_path)

    ship_key = _slug(ship_name)
    df = _read_schedule_df(p)

    col_month = _col(df, "Month")
    col_day = _col(df, "Day")
    col_loc = _col(df, "Location")

    missing = [name for name, col in [("Month", col_month), ("Day", col_day), ("Location", col_loc)] if col is None]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. Found columns: {list(df.columns)}")

    col_port = _col(df, "Port Code", "PortCode", "Port")
    col_eta = _col(df, "ETA")
    col_etd = _col(df, "ETD")
    col_berth = _col(df, "Berth Type", "BerthType")
    col_country = _col(df, "Country Code", "CountryCode")
    col_voy = _col(df, "Voyage#", "Voyage")
    col_itin = _col(df, "Itinerary#", "Itinerary")

    imported: List[Dict[str, Any]] = []
    skipped = 0
    first_error: Optional[str] = None

    for _, r in df.iterrows():
        try:
            mnum = _month_to_num(r[col_month])
            d_raw = _clean(r[col_day])
            if d_raw is None:
                skipped += 1
                continue

            dnum = int(float(str(d_raw).strip()))
            dt = date(int(year), int(mnum), int(dnum)).isoformat()

            imported.append(
                {
                    "ship_key": ship_key,
                    "ship_name": ship_name,
                    "sail_date": dt,
                    "location": _clean(r[col_loc]),
                    "berth_type": _clean(r[col_berth]) if col_berth else None,
                    "port_code": _clean(r[col_port]) if col_port else None,
                    "country_code": _clean(r[col_country]) if col_country else None,
                    "eta": _clean(r[col_eta]) if col_eta else None,
                    "etd": _clean(r[col_etd]) if col_etd else None,
                    "voyage": _clean(r[col_voy]) if col_voy else None,
                    "itinerary": _clean(r[col_itin]) if col_itin else None,
                    "source_file": p.name,
                }
            )

        except Exception as e:
            skipped += 1
            if first_error is None:
                first_error = f"{type(e).__name__}: {e}"
            continue

    inserted = insert_calls(imported)

    if inserted == 0 and len(df) > 0:
        raise ValueError(
            f"Imported 0 rows (skipped {skipped}). "
            f"Likely a parsing/format issue. First error: {first_error or 'unknown'}"
        )

    return inserted, skipped