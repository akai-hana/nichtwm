#!/bin/sh

# If error (non-zero value returned), exit immediately
set -e
#xinit ~/.xinitrc -- :0 -screen 2560x1600 # run as the main x server

# xinit ./.xinitrc -- $(command -v Xephyr) :1 -screen 640x400  # run on a nested server (Xephyr) and on a different display.
# xinit ./.xinitrc -- $(command -v Xephyr) :1 -screen 1280x800  # run on a nested server (Xephyr) and on a different display.
xinit ./.xinitrc -- $(command -v Xephyr) :1 -screen 2560x1600 # run on a nested server (Xephyr) and on a different display.
