#!/usr/bin/env bash
# Download one Creative Commons file into assets/ (row in CREDITS.md) or wings/<id>/ (row in
# wings/<id>/CREDITS.md, created with its header if missing; core/credits.gd merges every file).
#   tools/fetch_cc.sh <url> <dest under assets/ or wings/<id>/> "<title>" "<author>" "<source page url>" <licence>
# licence must be CC0 or CC-BY (e.g. CC0-1.0, CC-BY-4.0, CC-BY-3.0). Anything else is refused.
# Example:
#   tools/fetch_cc.sh https://example.org/rain.ogg assets/audio/cc/rain.ogg "Rain on glass" \
#     "Jane Doe" https://freesound.org/s/12345/ CC-BY-4.0
set -euo pipefail
cd "$(dirname "$0")/.."
URL="$1"; DEST="$2"; TITLE="$3"; AUTHOR="$4"; PAGE="$5"; LIC="$6"
case "$LIC" in
  CC0*|CC-BY-[0-9]*) ;;
  *) echo "fetch_cc: licence '$LIC' not allowed (CC0 / CC-BY only)" >&2; exit 2 ;;
esac
case "$DEST" in
  assets/*) CREDITS=CREDITS.md ;;
  wings/*/*) CREDITS="wings/$(echo "$DEST" | cut -d/ -f2)/CREDITS.md" ;;
  *) echo "fetch_cc: destination must be under assets/ or wings/<id>/" >&2; exit 2 ;;
esac
if [[ ! -f "$CREDITS" ]]; then
  printf '# Credits\n\n| Path | Title | Author | Source | Licence |\n|---|---|---|---|---|\n' > "$CREDITS"
fi
if grep -qF "| $DEST |" "$CREDITS"; then
  echo "fetch_cc: $DEST already credited" >&2; exit 3
fi
mkdir -p "$(dirname "$DEST")"
TMP="$(mktemp)"
curl -fL --max-filesize 104857600 -o "$TMP" "$URL"
mv "$TMP" "$DEST"
printf '| %s | %s | %s | %s | %s |\n' "$DEST" "$TITLE" "$AUTHOR" "$PAGE" "$LIC" >> "$CREDITS"
echo "$DEST  ($(du -h "$DEST" | cut -f1))  credited in $CREDITS"
echo "next: python3 tools/fix_imports.py && Godot --headless --path . --import"
