#!/bin/bash

# Usage: ./organize.sh "Object Name"

set -e

OBJECT_NAME="$1"

if [[ -z "$OBJECT_NAME" ]]; then
    echo "Usage: $0 \"Object Name\""
    exit 1
fi

# Resolve script's directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Relative path to consolidated directory
BASE_DIR="$SCRIPT_DIR/consolidated"
OBJECT_PATH="$BASE_DIR/$OBJECT_NAME"
FLATS_PATH="$BASE_DIR/Flat"
OUTPUT_DIR="$SCRIPT_DIR/organized/${OBJECT_NAME}"

FILTERS=(L R G B S H O)

if [[ ! -d "$OBJECT_PATH" ]]; then
    echo "Error: Object folder '$OBJECT_PATH' does not exist."
    exit 1
fi

echo "Organizing data for object: $OBJECT_NAME"
echo "Using consolidated directory: $BASE_DIR"
echo "Output directory: $OUTPUT_DIR"

# Create base output directory
mkdir -p "$OUTPUT_DIR"

# Step 1: Collect and sort all unique observation dates
DATES=()
for FILTER in "${FILTERS[@]}"; do
    FILTER_DIR="$OBJECT_PATH/$FILTER"
    if [[ -d "$FILTER_DIR" ]]; then
        for DATE_DIR in "$FILTER_DIR"/*; do
            [[ -d "$DATE_DIR" ]] || continue
            DATE=$(basename "$DATE_DIR")
            DATES+=("$DATE")
        done
    fi
done

# Remove duplicates and sort
IFS=$'\n' DATES=($(sort -u <<<"${DATES[*]}"))
unset IFS

if [[ ${#DATES[@]} -eq 0 ]]; then
    echo "No observation dates found for object '$OBJECT_NAME'."
    exit 0
fi

# Step 2: For each unique date, make night_N folder and copy lights/flats
NIGHT_COUNT=1
for DATE in "${DATES[@]}"; do
    NIGHT_DIR="$OUTPUT_DIR/night $NIGHT_COUNT"
    LIGHTS_DIR="$NIGHT_DIR/lights"
    FLATS_DIR="$NIGHT_DIR/flats"

    mkdir -p "$LIGHTS_DIR"
    mkdir -p "$FLATS_DIR"

    echo "Creating $NIGHT_DIR for date $DATE"

    # Copy light files
    for FILTER in "${FILTERS[@]}"; do
        FILTER_DATE_DIR="$OBJECT_PATH/$FILTER/$DATE"
        if [[ -d "$FILTER_DATE_DIR" ]]; then
            for EXPTIME_DIR in "$FILTER_DATE_DIR"/*; do
                [[ -d "$EXPTIME_DIR" ]] || continue
                cp "$EXPTIME_DIR"/* "$LIGHTS_DIR/" 2>/dev/null || true
            done
        fi
    done

    # Copy flat files
    for FILTER in "${FILTERS[@]}"; do
        FLAT_DATE_DIR="$FLATS_PATH/$FILTER/$DATE"
        if [[ -d "$FLAT_DATE_DIR" ]]; then
            cp "$FLAT_DATE_DIR"/* "$FLATS_DIR/" 2>/dev/null || true
        fi
    done

    ((NIGHT_COUNT++))
done

echo "Done. Output directory: $OUTPUT_DIR"
