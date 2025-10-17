#!/bin/bash

COMMAND=$1
shift

case "$COMMAND" in
  consolidate)
    ./helper.py consolidate --src "$@" ;;
  organize)
    ./helper.py organize --object "$@" ;;
  *)
    echo "Usage: $0 {consolidate|organize} [options]"
    exit 1
    ;;
esac
