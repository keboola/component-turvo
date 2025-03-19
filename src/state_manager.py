import json
import os
import logging


class StateManager:
    """Handles state persistence for incremental fetching in Keboola Connection."""

    def __init__(self, state_dir: str):
        """Initialize the state manager with the path to state.json"""
        self.state_file = os.path.join(state_dir, "in", "state.json")
        self.state_out_file = os.path.join(state_dir, "out", "state.json")

    def load_state(self) -> dict:
        """Loads the state file if it exists, otherwise returns an empty dictionary."""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logging.warning("State file is corrupted. Resetting state.")
                    return {}
        return {}

    def get_last_sync_date(self, sync_time_value: int, sync_time_unit: str, default_start_date: str) -> str | None:
        """
        Retrieves the last sync timestamp from state.
        If the unit or amount has changed, resets to the configured start_datetime.
        """
        state = self.load_state()
        state_key = f"last_sync_{sync_time_value}_{sync_time_unit}"
        last_sync = state.get(state_key)

        if last_sync:
            logging.info(f"Resuming sync from {last_sync} (based on {sync_time_value} {sync_time_unit})")
            return last_sync

        logging.info(f"No previous sync found for {sync_time_value} {sync_time_unit} interval, starting fresh.")
        return default_start_date

    def save_state(self, sync_time_value: int, sync_time_unit: str, last_sync_time: str):
        """Saves the last successful sync timestamp for the current time unit & value."""
        state_key = f"last_sync_{sync_time_value}_{sync_time_unit}"
        state = self.load_state()
        state[state_key] = last_sync_time

        with open(self.state_out_file, "w") as f:
            json.dump(state, f)

        logging.info(f"Updated last sync time: {last_sync_time} (for {sync_time_value} {sync_time_unit} interval)")
