#!/bin/bash

source .venv/bin/activate
COMMAND=$1
shift

case "$COMMAND" in
  consolidate)
    .~/stellar/code/helper.py consolidate --src "$@" ;;
  organize)
    .~/stellar/code/helper.py organize --object "$@" ;;
  *)
    echo "Usage: $0 {consolidate|organize} [options]"
    exit 1
    ;;
esac

deactivate