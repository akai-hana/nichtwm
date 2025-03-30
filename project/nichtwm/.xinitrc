#!/bin/sh

. ./.Xprofile
xrdb -merge ./.Xresources
xsetroot -cursor_name left_ptr

exec dbus-launch --sh-syntax --exit-with-session ./bin/nichtwm.py
