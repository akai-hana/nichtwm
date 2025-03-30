#!/usr/bin/env python3

#TODO LIST#
# code workspaces

##~~##  nichtwm!  ##~~##
# made by akai_hana :) #

# Main features:
# + Python & X server parallelization through concurrent.futures and xcb #WIP#
# + Safe typing, logging and traceback, graceful error handling
# + Uncomplicated, non-verbose yaml config file (by default "~/.config/nichtwm/config.yaml")
# + Tiling/Floating window behavior (bspwm-like?)
# + Workspaces (6 by default)
# + Highly modular & extensible

# modules
from utils import KeyUtil
from tiling import TilingManager

# xcb
import xcffib # Python bindings for the X11 protocol
import xcffib.xproto as xproto # Protocol types, constants, window management, event handling, etc

# System utilities
import subprocess    # Shell commands and external processes
import os   # Get home path, get cpu thread count
import yaml # Read config.yaml

# Debugging
import logging   # Log useful data
import traceback # Useful debug data

class WindowManager:
    """main"""
    def __init__(self) -> None:
        ## Initialize X server
        try:
            self.conn = xcffib.connect()                 # xcb connection
            self.screen = self.conn.get_setup().roots[0] # Get first available screen
            self.root_window = self.screen.root          # Initialize screen
            self.tiling_manager = TilingManager(self.conn, self.screen, self.root_window)

        except xcffib.ConnectionException as e:
            logging.error(f"Failed to connect to X server: {e}")

        except Exception as e:
            logging.error(f"Unexpected error connecting to X server: {type(e).__name__}, {e}")

        ## Config file
        # Set config path
        config_path = f'{os.environ["HOME"]}/.config/nichtwm/config.yaml'
        # Load config
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
                logging.debug(f"Loaded config: {self.config}")

        except FileNotFoundError:
            logging.error(f"Config file not found: {config_path}")
            self.config = {}

        except yaml.YAMLError as e:
            logging.error(f"Error loading YAML config: {e}")
            self.config = {}

        # Keycodes/Keysyms utils
        self.key_util = KeyUtil(self.conn)

        # Windows
        self.windows = []
        self.current_window = 0 # X root window is 0, then 1-indexed for spawned windows
        self.num_windows = 0

        # Workspaces
        self.workspaces = [{'windows': [], 'tiling_manager': TilingManager(self.conn, self.screen, self.root_window)} for _ in range(self.config['num-o-workspaces'])]
        self.current_workspace = 0

    """Event loop of the WM; setup && run nichtwm."""
    def run(self) -> None:
        # If root window fails to configure, exit gracefully
        if not self._setup_event_mask():
            logging.error("Failed to configure root window. Exiting gracefully.")
            raise RuntimeError("Root window configuration failed.")

        try:
            self._grab_keys()
            self._start_event_loop()

        except Exception as e:
            logging.exception(f"An error ocurred during nichtwm's event loop: {e}")
            self._graceful_shutdown()

    """Event mask listen for X events"""
    def _setup_event_mask(self) -> bool:
        logging.debug(f"Setting up event mask for root window: {self.root_window}")

        cookie = self.conn.core.ChangeWindowAttributesChecked(
            self.root_window,
            xproto.CW.EventMask, # Window attribute to set which events we want

            [
                # For substructure changes (window creation/deletion, resizes, etc.)
                xproto.EventMask.SubstructureNotify |
                # Redirect substructure notifications for children to the root window.
                xproto.EventMask.SubstructureRedirect |
                # Keypresses
                xproto.EventMask.KeyPress |
                # Cursor hover window focus
                xproto.EventMask.EnterWindow
            ]
        )

        # Check if request was valid
        try:
            cookie.check()
            return True

        except xproto.AccessError as e:
            logging.error("Failed to set event mask on the root window. Is another WM running?")
            logging.debug(traceback.format_exc()) # More detailed stack trace
            return False

    """Grab key events defined on config.yaml"""
    def _grab_keys(self) -> Nnnnsaone:
        if self.config['modifier'].lower() == 'alt':
            self.config['modifier'] = '_1'
        if self.config['modifier'].lower() == 'super':
            self.config['modifier'] = '_4'

        for action in self.config['actions']:
            # Get modifier from string
            modifier = getattr(xproto.ModMask, self.config['modifier'])

            try:
                # Get the keysym for the key defined in the config
                keysym = KeyUtil.string_to_keysym(action['key'])
                if keysym is None:
                    continue

                # Get the keycode from the keysym
                keycode = self.key_util.get_keycode(keysym)

                # Log the key and modifier to debug
                logging.debug(f"Keysym {keysym} for key {action['key']} converted to keycode {keycode}")

                # Use core.GrabKeyChecked to capture key events on the root window
                self.conn.core.GrabKeyChecked(
                    False,  # Send all key events to the root window
                    self.root_window,
                    modifier,
                    keycode,
                    xproto.GrabMode.Async,  # Non-blocking for key press events
                    xproto.GrabMode.Async   # Non-blocking for key release events
                ).check()

            except xproto.AccessError as e:
                logging.error(f"Failed to grab key {action['key']} # with modifier {self.config['modifier']}: {e}")
                logging.debug(traceback.format_exc())

            except Exception as e:
                logging.error(f"Unexpected error when grabbing key {action['key']}: {e}")
                logging.debug(traceback.format_exc())

    """nichtwm's event loop"""
    def _start_event_loop(self) -> None:
        while True:
            try:
                event = self.conn.wait_for_event()

                if isinstance(event, xproto.KeyPressEvent):
                    self._handle_key_press_event(event)
                if isinstance(event, xproto.MapRequestEvent):
                    self._handle_map_request_event(event)
                if isinstance(event, xproto.ConfigureRequestEvent):
                    self._handle_configure_request_event(event)
                if isinstance(event, xproto.EnterNotifyEvent):
                    self._handle_enter_notify_event(event)
                logging.debug(f"Received event: {event}")

                self.conn.flush()

            except xcffib.ConnectionException as e: # Usually when user kills or exits the WM
                logging.info("Connection to X server successfully terminated.")

            except Exception as e:
                logging.error(f"Unexpected error in event loop: {e}")
                logging.debug(traceback.format_exc())

    """Handle actions such as switching between windows"""
    def _handle_action(self, action) -> None:
        if not self.windows:
            logging.debug("No windows available to switch.")
            return
        # Unmap current window before switching
        self.conn.core.UnmapWindow(self.windows[self.current_window])

        # Switch to the next or previous window
        if action == 'NEXT_WINDOW':
            self.current_window = (self.current_window + 1) % len(self.windows)

        if action == 'PREVIOUS_WINDOW':
            self.current_window = (self.current_window - 1) % len(self.windows)

        if action == 'KILL_WINDOW':
            self.kill_current_window()

        if action.startswith("SWITCH_WORKSPACE"): # startswith due to the many different workspaces
            workspace_index = int(action.split("_")[-1]) - 1  # Parse the workspace number from the action
            self._switch_workspace(workspace_index)
            return

        if not self.workspaces[self.current_workspace]['windows']:
            logging.debug("No windows available to switch.")
            return

        # Map the new current window
        self.conn.core.MapWindow(self.windows[self.current_window])
        self.conn.flush()

    """Handle a key press event and execute the corresponding action or command."""
    def _handle_key_press_event(self, event):
        keycode = event.detail  # The keycode from the KeyPressEvent
        modifier = event.state  # The modifier mask (e.g., Mod1, Mod4)
        logging.debug(f"Received KeyPressEvent with keycode {keycode} and modifier {modifier}")

        # Iterate over the defined actions in the config file
        for action in self.config['actions']:
            # Convert the action key (e.g., 'o', 'a', etc.) to keysym
            action_keysym = KeyUtil.string_to_keysym(action['key'])

            # Convert the keysym to keycode
            action_keycode = self.key_util.get_keycode(action_keysym)

            # Map the modifier string in the config to the actual modifier mask (e.g., Mod1 or Mod4)
            action_modifier = getattr(xproto.ModMask, self.config['modifier'], 0)

            logging.debug(f"Processing action: {action['key']}, keysym: {action_keysym}, keycode: {action_keycode}") #, modifier: {action_modifier}")

            # Check if the keycode and modifier from the event match those from the config
            if action_keycode == keycode and action_modifier == modifier:
                logging.info(f"Executing action for key: {action['key']}, command: {action.get('command', 'No command specified')}")

                # Execute the command specified in the config
                if 'command' in action:
                    subprocess.Popen(action['command'], shell=True)
                    logging.info(f"Successfully executed command: {action['command']}")
                elif 'action' in action:
                    self._handle_action(action['action'])
                break
            else:
                logging.debug(f"No match for keycode {keycode} and modifier {modifier}")

    """Handle a map request (when a window requests to become visible)."""
    def _handle_map_request_event(self, event) -> None:
        try:
            # Get window attributes and check if it's override-redirect (bypasses window manager)
            attributes = self.conn.core.GetWindowAttributes(event.window).reply()
            if attributes.override_redirect:
                return

            import time
            time.sleep(0.05)  # Adjust this delay if necessary

            # Map the window (make it visible)
            self.conn.core.MapWindow(event.window)

            # Configure window to be fullscreen
            # X and Y coordinates (0, 0) place the window at the top-left corner of the screen
            window_width = self.screen.width_in_pixels
            window_height = self.screen.height_in_pixels

            self.conn.core.ConfigureWindow(
                event.window,
                xproto.ConfigWindow.X |
                xproto.ConfigWindow.Y |
                xproto.ConfigWindow.Width |
                xproto.ConfigWindow.Height,
                [
                    0,  # X position: 0 (left edge of the screen)
                    0,  # Y position: 0 (top edge of the screen)
                    window_width,
                    window_height
                ]
            )

            # Set the event mask to listen for EnterNotify events for this window
            self.conn.core.ChangeWindowAttributesChecked(
                event.window,
                xproto.CW.EventMask,
                [xproto.EventMask.EnterWindow]  # Listen for cursor entering window
            ).check()

            # Add the window to the current workspace only
            current_workspace_data = self.workspaces[self.current_workspace]
            if event.window not in current_workspace_data['windows']:
                current_workspace_data['windows'].append(event.window)
                current_workspace_data['tiling_manager'].add_window(event.window)

            # If you still need a global list of windows (optional, depending on your design):
            if event.window not in self.windows:
                self.windows.insert(0, event.window)
                self.current_window = 0  # Focus on the newly mapped window

            self.conn.flush()

        except xcffib.ConnectionException as e:
            logging.error(f"Failed to get window attributes for window {event.window}: {e}")
            logging.debug(traceback.format_exc())
            self._graceful_exit()

        except Exception as e:
            logging.error(f"Unexpected error in handling map request for window {event.window}: {e}")
            logging.debug(traceback.format_exc())
            self._graceful_shutdown()

    """Handle a configure request (resize/move requests)."""
    def _handle_configure_request_event(self, event) -> None:
        try:
            # Extract parameters from the event. Ensure that they are available and default to 0 or None if not.
            x = getattr(event, 'x', 0)
            y = getattr(event, 'y', 0)
            width = getattr(event, 'width', self.screen.width_in_pixels)
            height = getattr(event, 'height', self.screen.height_in_pixels)
            border_width = getattr(event, 'border_width', 0)
            sibling = getattr(event, 'sibling', None)
            stack_mode = getattr(event, 'stack_mode', None)

            # Configure the window with the parameters provided in the event.
            self.conn.core.ConfigureWindow(
                event.window,
                xproto.ConfigWindow.X |
                xproto.ConfigWindow.Y |
                xproto.ConfigWindow.Width |
                xproto.ConfigWindow.Height |
                xproto.ConfigWindow.BorderWidth |
                xproto.ConfigWindow.Sibling |
                xproto.ConfigWindow.StackMode,
                [
                    x,
                    y,
                    width,
                    height,
                    border_width,
                    sibling,
                    stack_mode
                ]
            )

            self.conn.flush()

        except xcffib.ConnectionException as e:
            logging.error(f"Failed to configure window {event.window}: {e}")
            logging.debug(traceback.format_exc())
            self._graceful_shutdown()

        except Exception as e:
            logging.error(f"Unexpected error in handling configure request for window {event.window}: {e}")
            logging.debug(traceback.format_exc())
            self._graceful_shutdown()

    """Cursor hovering focus implementation"""
    def _handle_enter_notify_event(self, event):
        """Focus the window when the cursor enters it."""
        try:
            # Focus the window the cursor entered
            self.conn.core.SetInputFocus(
                xproto.InputFocus.PointerRoot,
                event.event,
                xproto.Time.CurrentTime
            )

            # Update the current window index to match the newly focused window
            if event.event in self.windows:
                self.current_window = self.windows.index(event.event)
            logging.info(f"Focused window: {event.event}")
            self.conn.flush()
        except Exception as e:
            logging.error(f"Failed to focus window {event.event}: {e}")
            logging.debug(traceback.format_exc())

        def string_to_keysym(string):
            try:
                keysym = xpybutil.keysymdef.keysyms[string]
                logging.debug(f"Converted string '{string}' to keysym: {keysym}")
                return keysym
            except KeyError:
                logging.error(f"Failed to convert string '{string}' to keysym.")
                return None

    """Destroy currently focused window"""
    def kill_current_window(self) -> None:
        if self.windows:
            window = self.windows[self.current_window]
            # Destroy the window using XCB's destroy_window
            self.conn.core.DestroyWindow(window)
            self.windows.pop(self.current_window)

            # Remove the window from the tiling manager
            self.tiling_manager.remove_window(window)

            # Rearrange the remaining windows
            self.tiling_manager.arrange_windows()

            # Adjust the current window index to prevent out-of-bounds issues
            self.current_window = max(0, self.current_window - 1)
            self.conn.flush()
            arrange


    """Shutdown executor and disconnect connection gracefully"""
    def _graceful_shutdown(self) -> None:
        logging.info("Shutting down gracefully.")
        self.conn.disconnect()

    def switch_workspace(self, workspace_index: int) -> None:
        """Switch to a different workspace."""
        if workspace_index == self.current_workspace:
            return  # Already on the desired workspace

        logging.info(f"Switching to workspace {workspace_index + 1}")

        # Unmap windows from the current workspace
        for window in self.workspaces[self.current_workspace]:
            self.conn.core.UnmapWindow(window)

        # Map windows in the new workspace
        for window in self.workspaces[workspace_index]:
            self.conn.core.MapWindow(window)

        # Flush the X connection
        self.conn.flush()

        # Update the current workspace index
        self.current_workspace = workspace_index

    def add_window_to_workspace(self, window) -> None:
        """Add a window to the current workspace."""
        self.workspaces[self.current_workspace].append(window)
        logging.info(f"Added window {window} to workspace {self.current_workspace + 1}")

    def remove_window_from_workspace(self, window) -> None:
        """Remove a window from the current workspace."""
        if window in self.workspaces[self.current_workspace]:
            self.workspaces[self.current_workspace].remove(window)

    def _switch_workspace(self, workspace_index: int) -> None:
            """Switch to the specified workspace."""
            if workspace_index == self.current_workspace:
                return  # Do nothing if already in the desired workspace

            # Unmap all windows in the current workspace
            for window in self.workspaces[self.current_workspace]['windows']:
                self.conn.core.UnmapWindow(window)

            # Set the new current workspace
            self.current_workspace = workspace_index

            # Map all windows in the new workspace and tile them
            for window in self.workspaces[self.current_workspace]['windows']:
                self.conn.core.MapWindow(window)

            self.workspaces[self.current_workspace]['tiling_manager'].arrange_windows()
            self.conn.flush()

# nichtwm
# made by akai_hana, AKA. Matias Moya
if __name__ == '__main__':
    WindowManager().run()
