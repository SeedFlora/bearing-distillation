#!/usr/bin/env bash
# Resumable, provenance-recording downloader.
#
# Usage:
#   bash scripts/download.sh <list.tsv> <dest_dir> <provenance.tsv>
#
# <list.tsv> columns (tab-separated, '#' starts a comment line):
#   url  filename  expected_sha256(optional, '-' if unknown)
#
# Behaviour:
#   * HEAD request first; a file whose local size equals the remote
#     Content-Length is not downloaded again.
#   * Partial files are resumed with `curl -C -`.
#   * After completion the local SHA-256 is computed and, when the source
#     publishes one, compared with the expected value.
#   * One provenance row per file is appended to <provenance.tsv>.
# Raw files are never modified after download.
set -u
LIST="$1"; DEST="$2"; PROV="$3"
UA="Mozilla/5.0 (compatible; research-data-download)"
mkdir -p "$DEST"
if [ ! -f "$PROV" ]; then
  printf 'filename\turl\tbytes\tsha256_local\tsha256_expected\tsha256_match\tlast_modified\tcontent_length\taccess_utc\n' > "$PROV"
fi

while IFS=$'\t' read -r url fname expected || [ -n "${url:-}" ]; do
  [ -z "${url:-}" ] && continue
  case "$url" in \#*) continue;; esac
  expected="${expected:--}"
  out="$DEST/$fname"
  if grep -q -P "^\Q$fname\E\t" "$PROV" 2>/dev/null; then
    echo "[skip] $fname already recorded in provenance"; continue
  fi
  head_out=$(curl -sIL --connect-timeout 30 -A "$UA" "$url" | tr -d '\r')
  remote_len=$(echo "$head_out" | grep -i '^content-length:' | tail -1 | awk '{print $2}')
  last_mod=$(echo "$head_out" | grep -i '^last-modified:' | tail -1 | cut -d' ' -f2-)
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    local_len=$(stat -c %s "$out" 2>/dev/null || echo 0)
    if [ -n "$remote_len" ] && [ "$local_len" = "$remote_len" ]; then break; fi
    echo "[get] $fname attempt=$attempt have=$local_len of=${remote_len:-?} $(date -u +%FT%TZ)"
    curl -sS -L --fail --connect-timeout 30 --speed-time 120 --speed-limit 1024 \
         -C - -A "$UA" -o "$out" "$url"
    rc=$?
    [ $rc -eq 0 ] && { [ -z "$remote_len" ] && break; continue; }
    echo "[retry] $fname rc=$rc"; sleep 20
  done
  local_len=$(stat -c %s "$out" 2>/dev/null || echo 0)
  if [ -n "$remote_len" ] && [ "$local_len" != "$remote_len" ]; then
    echo "[FAIL] $fname incomplete: $local_len / $remote_len"; continue
  fi
  sha=$(sha256sum "$out" | cut -d' ' -f1)
  if [ "$expected" = "-" ]; then match="not_published"
  elif [ "$sha" = "$expected" ]; then match="yes"; else match="NO"; fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$fname" "$url" "$local_len" "$sha" \
     "$expected" "$match" "${last_mod:-}" "${remote_len:-}" "$(date -u +%FT%TZ)" >> "$PROV"
  echo "[done] $fname bytes=$local_len sha256=$sha match=$match"
done < "$LIST"
echo "[all-finished] $(date -u +%FT%TZ)"
