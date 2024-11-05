#!/usr/bin/env python3

import xcffib.xproto as xproto
import logging

"""Manages tiling layouts and operations for nichtwm."""
class TilingManager:
    def __init__(self, conn, screen, root_window) -> None:
        self.conn = conn
        self.screen = screen
        self.root_window = root_window
        self.windows = []

    """Adds a window and rearranges the layout."""
    def add_window(self, window) -> None:
        if window not in self.windows:
            self.windows.append(window)
            self.arrange_windows()
    """Removes a window and updates the layout."""
    def remove_window(self, window) -> None:
        if window in self.windows:
            self.windows.remove(window)

    """Recalculate and apply the tiling layout."""
    def arrange_windows(self) -> None:
        if not self.windows:
            logging.debug("No windows to arrange.")
            return

        screen_width = self.screen.width_in_pixels
        screen_height = self.screen.height_in_pixels

        while True:
            num_windows = len(self.windows)

            if len(self.windows) == 1:
                # One window takes the full screen
                self._tile_single_window(self.windows[0], screen_width, screen_height)
                return
            if len(self.windows) != 1:
                # First window on the left (50% width), remaining windows stacked on the right
                first_window_width = screen_width // 2
                first_window_height = screen_height
                remaining_window_width = screen_width // 2
                remaining_window_height = screen_height // (len(self.windows) - 1)

                self._tile_first_window(self.windows[0], first_window_width, first_window_height)

                # Stacked windows on the right
                for i, window in enumerate(self.windows[1:], start=1):
                    y = (i - 1) * remaining_window_height
                    x = first_window_width  # Update x coordinate for windows on the right
                    self._tile_right_stack(window, x, y, remaining_window_width, remaining_window_height)
                return

            self.conn.flush()

    def _tile_single_window(self, window, screen_width, screen_height):
        """Configure a single window to take up the full screen."""
        self.conn.core.ConfigureWindow(
            window,
            xproto.ConfigWindow.X |
            xproto.ConfigWindow.Y |
            xproto.ConfigWindow.Width |
            xproto.ConfigWindow.Height,
            [0, 0, screen_width, screen_height]
        )

    def _tile_first_window(self, window, width, height):
        """Configure the first window to take up the left half of the screen."""
        self.conn.core.ConfigureWindow(
            window,
            xproto.ConfigWindow.X |
            xproto.ConfigWindow.Y |
            xproto.ConfigWindow.Width |
            xproto.ConfigWindow.Height,
            [0, 0, width, height]
        )

    def _tile_right_stack(self, window, x, y, width, height):
        """Configure the right stack of windows."""
        self.conn.core.ConfigureWindow(
            window,
            xproto.ConfigWindow.X |
            xproto.ConfigWindow.Y |
            xproto.ConfigWindow.Width |
            xproto.ConfigWindow.Height,
            [x, y, width, height]
        )

    def focus_window(self, window) -> None:
        """Focus a specific window."""
        if window in self.windows:
            self.conn.core.RaiseWindow(window)
            self.conn.flush()

    def handle_window_close(self, event):
        """Handles a window close event."""
        window = event.window
        self.remove_window(window)
        self.conn.flush()
