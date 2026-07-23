# PortMatch Lite v2.0

Portable, no-admin ship schedule importer + local SQLite database + query UI.

## What you get
- **Local SQLite DB** (no server install)
- **Import**: Ship dropdown (from `ships.json`) + Year + Excel/CSV file(s)
- **Query**: simple filters (starter)
- **Maintenance**: delete a whole year (e.g., delete all 2026)

## Run in PyCharm (dev)
1. Open this folder in PyCharm.
2. Right-click `src/` → **Mark Directory as → Sources Root**
3. Run: `src/portmatch/main.py`

## Portable distribution goal
Later, build a one-folder EXE and ship this structure:

```
PortMatchLite/
  PortMatchLite.exe
  assets/portmatchlite.ico
  ships.json
  portmatch_lite.db
```

Keep the folder in a user-writable location (Desktop/Documents) to avoid admin permissions.

## Icon
Replace `assets/portmatchlite.ico` with your preferred icon (e.g., St. Joseph symbol).
