pyinstaller --noconfirm --clean --onedir --windowed `
  --name PortMatchLite `
  --icon assets\portmatchlite.ico `
  --paths src `
  --add-data "ships.json;." `
  --add-data "assets\portmatchlite.ico;assets" `
  src\portmatch\main.py

# --- Ensure editable config + icon are next to the EXE ---
$dist = Join-Path $PSScriptRoot "dist\PortMatchLite"

Copy-Item (Join-Path $PSScriptRoot "ships.json") $dist -Force

$assetsDir = Join-Path $dist "assets"
New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot "assets\portmatchlite.ico") $assetsDir -Force