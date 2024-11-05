import xpybutil
import xpybutil.keybind

"""
This module provides functions to translate between keycodes and keysyms
in order to convert the keysyms of the config to keycodes
for the WM to be able to listen to and handle KeyPress events.

Keycode = "Physical" key ('A' and 'a' share the same keycode.)
Keysym  = "Symbolic" representation of a key ('A' = <Shift>+a)
"""

class KeyUtil:
    def __init__(self, conn):
        self.conn = conn # as "connection" to the X server.

        # The the min and max of keycodes associated with your keyboard.
        # A keycode will never be less than eight because 0-7 keycodes are reserved.
        # The keycode zero symbolizes AnyKey. The max keycode is 255.
        self.min_keycode = self.conn.get_setup().min_keycode
        self.max_keycode = self.conn.get_setup().max_keycode

        self.keyboard_mapping = self.conn.core.GetKeyboardMapping(
            # The array of keysyms returned by this function will start at min_keycodes
            # so that the modifiers are not included.
            self.min_keycode,
            # Total number of keycodes
            self.max_keycode - self.min_keycode + 1
        ).reply()

    def string_to_keysym(string):
        # Converts string to keysym
        return xpybutil.keysymdef.keysyms[string]

    def get_keysym(self, keycode, keysym_offset):
        keysyms_per_keycode = self.keyboard_mapping.keysyms_per_keycode
        index = (keycode - self.min_keycode) * keysyms_per_keycode + keysym_offset

        if 0 <= index < len(self.keyboard_mapping.keysyms):
            return self.keyboard_mapping.keysyms[index]
        else:
            raise ValueError(f"Invalid keycode or keysym offset: keycode={keycode}, offset={keysym_offset}")

    def get_keycode(self, keysym):
        """
        Get a keycode from a keysym

        :param keysym: keysym you wish to convert to keycode
        :returns: Keycode if found, else None
        """

        keysyms_per_keycode = self.keyboard_mapping.keysyms_per_keycode

        # Loop through each keycode. Think of this as a row in a 2d array.
        # Row: loop from the min_keycode through the max_keycode
        for keycode in range(self.min_keycode, self.max_keycode + 1):
            # Col: loop from 0 to keysyms_per_keycode. Think of this as a column in a 2d array.
            for keysym_offset in range(0, keysyms_per_keycode):
                if self.get_keysym(keycode, keysym_offset) == keysym:
                    return keycode

        return None
