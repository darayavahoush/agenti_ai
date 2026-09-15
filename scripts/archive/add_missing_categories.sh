#!/bin/bash
set -e
IMG_DIR="backend/data/flashcard_images"
BASE="https://cdn.jsdelivr.net/gh/hfg-gmuend/openmoji/color/72x72"

PAIRS="octopus:1F419 shark:1F988 dolphin:1F42C whale:1F40B crab:1F980 \
ant:1F41C bee:1F41D ladybug:1F41E mosquito:1F99F \
guitar:1F3B8 piano:1F3B9 drum:1F941 trumpet:1F3BA violin:1F3BB \
toilet:1F6BD bathtub:1F6C1 toothbrush:1FAA5 shower:1F6BF soap:1F9FC \
six:0036-FE0F-20E3 seven:0037-FE0F-20E3 eight:0038-FE0F-20E3 nine:0039-FE0F-20E3 ten:1F51F \
circle:1F534 square:1F7E5 triangle:1F53A star:2B50 diamond:1F536"

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
