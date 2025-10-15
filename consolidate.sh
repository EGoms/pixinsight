#!/bin/bash

set -e

SRC_DIR="$1"
BASE_DIR="$(dirname "$0")"
CONSOLIDATED_DIR="$BASE_DIR/consolidated"

if [ -z "$SRC_DIR" ]; then
	echo "Usage: $0 <source_directory>"
	exit 1
fi

mkdir -p "$CONSOLIDATED_DIR"

get_epoch() {
	local date="$1"
	local time="$2"
	gdate -d "${date:0:4}-${date:4:2}-${date:6:2} ${time:0:2}:${time:2:2}:${time:4:2}" +%s
}

find "$SRC_DIR" -type f -name '*.fit' | while read -r file; do
	fname="$(basename "$file")"
	fname_noext="${fname%.fit}"
	
	TYPE="$(echo "$fname_noext" | cut -d'_' -f1)"

	if [ "$TYPE" = "Flat" ]; then
		OBJECT="Flat"
		IFS='_' read -r _ EXPOSURE BIN CAMERA FILTER GAIN DATETIME TEMP NUMBER <<< "$fname_noext" 
	elif [ "$TYPE" = "Dark" ]; then
		OBJECT="Dark"
		FILTER="Dark"
		IFS='_' read -r _ EXPOSURE BIN CAMERA FILTER GAIN DATETIME TEMP NUMBER <<< "$fname_noext" 
	else
		IFS='_' read -r _ OBJECT EXPOSURE BIN CAMERA FILTER GAIN DATETIME TEMP NUMBER <<< "$fname_noext"
	fi
	
	DATE="$(echo "$DATETIME" | sed 's/-.*//')"
	TIME="$(echo "$DATETIME" | sed 's/.*-//')"

	case "$TYPE" in
	  Light|Flat|Dark|Bias) ;;
	  *) continue ;;
	esac

	case "$FILTER" in
	  L|R|G|B|S|H|O) ;;
	  *) continue ;;
	esac

	EXPOSURE_VAL="$(echo "$EXPOSURE" | sed 's/s$//')"
	GAIN_VAL="$(echo "$GAIN" | sed 's/gain//')"
	TEMP_VAL="$(echo "$TEMP" | sed 's/C$//')"

	FILE_EPOCH=$(get_epoch "$DATE" "$TIME")
	DAY1_NOON=$(get_epoch "$DATE" "120100")
	DAY2_NOON=$(get_epoch "$(gdate -d "${DATE} +1 day" +%Y%m%d)" "120000")

	if (( FILE_EPOCH >= DAY1_NOON && FILE_EPOCH < DAY2_NOON )); then
		GROUP_DATE="$DATE"
	else
		GROUP_DATE="$(gdate -d "${DATE} -1 day" +%Y%m%d)"
	fi

	if [ "$TYPE" = "Dark" ]; then
		TARGET_DIR="$CONSOLIDATED_DIR/Dark/$GAIN/$EXPOSURE"
	else
		TARGET_DIR="$CONSOLIDATED_DIR/$OBJECT/$FILTER/$GROUP_DATE/$EXPOSURE"
	fi
	mkdir -p "$TARGET_DIR"
	mv "$file" "$TARGET_DIR/"
done

echo "Consolidation Complete."
