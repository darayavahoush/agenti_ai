#!/bin/bash
set -e
IMG_DIR="backend/data/flashcard_images"
BASE="https://cdn.jsdelivr.net/gh/hfg-gmuend/openmoji/color/72x72"

PAIRS="doctor:1F9D1-200D-2695-FE0F police:1F46E firefighter:1F9D1-200D-1F692 farmer:1F9D1-200D-1F33E \
lamp:1F4A1 clock:23F0 teddybear:1F9F8"

for pair in $PAIRS; do
  word="${pair%%:*}"
  code="${pair##*:}"
  echo "Downloading $word ($code)..."
  curl -sf -o "$IMG_DIR/$word.png" "$BASE/$code.png" || echo "  FAILED: $word"
done

echo ""
echo "Done. Checking results:"
for pair in $PAIRS; do
  word="${pair%%:*}"
  if [ -s "$IMG_DIR/$word.png" ]; then
    echo "  OK:     $word.png"
  else
    echo "  MISSING: $word.png"
  fi
done
