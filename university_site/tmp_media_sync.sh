#!/bin/bash
# Sync Django media/ into public/media/ (what Apache serves via .htaccess)
set -e
cd /home/cp29524/apps/university_site
LOG=tmp/media_sync.log
{
  echo "START $(date -Is)"
  mkdir -p public/media
  # copy without deleting existing (safe)
  if command -v rsync >/dev/null 2>&1; then
    rsync -a media/ public/media/
  else
    cp -a media/. public/media/
  fi
  # counts
  echo "media_files=$(find media -type f 2>/dev/null | wc -l)"
  echo "public_media_files=$(find public/media -type f 2>/dev/null | wc -l)"
  touch tmp/restart.txt
  echo "DONE $(date -Is)"
} >"$LOG" 2>&1
