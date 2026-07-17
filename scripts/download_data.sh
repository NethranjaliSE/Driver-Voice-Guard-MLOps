#!/bin/bash
# Download RAVDESS dataset from Zenodo
# Usage: bash scripts/download_data.sh

set -e

DATA_DIR="data/raw"
mkdir -p "$DATA_DIR"

echo "📥 Downloading RAVDESS Emotional Speech Audio..."
echo "   This is ~600MB. Please wait..."

# Download the audio speech part of RAVDESS from Zenodo
# Full dataset DOI: 10.5281/zenodo.1188976
BASE_URL="https://zenodo.org/record/1188976/files"

for i in $(seq -w 1 24); do
  ACTOR="Actor_$(printf '%02d' $i)"
  URL="${BASE_URL}/${ACTOR}.zip"
  OUT="${DATA_DIR}/${ACTOR}.zip"
  if [ -f "${DATA_DIR}/${ACTOR}" ]; then
    echo "✅ $ACTOR already exists, skipping."
    continue
  fi
  echo "   Downloading $ACTOR..."
  curl -L "$URL" -o "$OUT" --progress-bar
  unzip -q "$OUT" -d "$DATA_DIR"
  rm "$OUT"
done

echo ""
echo "✅ Dataset downloaded to $DATA_DIR"
echo "   Found $(find $DATA_DIR -name '*.wav' | wc -l) .wav files"