#!/usr/bin/env python3

class WorkspaceManager:
    def __init__(self, conn, num_workspaces=6) -> None:
        self.conn = conn
        self.num_workspaces = num_workspaces
        self.workspaces = [[] for _ in range(num_workspaces)]  # List of lists to hold windows per workspace
        self.current_workspace = 0

    """Switch to a specific workspace."""
    def switch_to_workspace(self, workspace_index: int) -> None:
        if workspace_index < 0 or workspace_index >= self.num_workspaces:
            return  # Invalid workspace index

        # Unmap all windows in the current workspace
        for window in self.workspaces[self.current_workspace]:
            self.conn.core.UnmapWindow(window)

        # Switch to the new workspace
        self.current_workspace = workspace_index

        # Map all windows in the new workspace
        for window in self.workspaces[self.current_workspace]:
            self.conn.core.MapWindow(window)

        self.conn.flush()

    """Add a window to the current workspace."""
    def add_window_to_workspace(self, window) -> None:
        if window not in self.workspaces[self.current_workspace]:
            self.workspaces[self.current_workspace].append(window)

    """Remove a window from the current workspace."""
    def remove_window_from_workspace(self, window) -> None:
        if window in self.workspaces[self.current_workspace]:
            self.workspaces[self.current_workspace].remove(window)

    """Move a window to a specific workspace."""
    def move_window_to_workspace(self, window, workspace_index: int) -> None:
        if workspace_index < 0 or workspace_index >= self.num_workspaces:
            return  # Invalid workspace index

        # Remove the window from the current workspace
        self.remove_window_from_workspace(window)

        # Add the window to the new workspace
        self.workspaces[workspace_index].append(window)

    """Cycle between workspaces (forward or backward)."""
    def cycle_workspace(self, forward=True) -> None:
        next_workspace = (self.current_workspace + 1) % self.num_workspaces if forward else (self.current_workspace - 1) % self.num_workspaces
        self.switch_to_workspace(next_workspace)
