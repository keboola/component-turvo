import json
import os
import logging


class StateManager:
    """Handles state persistence for incremental fetching."""

    def __init__(self, state_dir: str):
        """Initialize the state manager with the path to state.json."""
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

    def save_run_state(self, date_from: str, last_successful_run: str):
        state = self.load_state()
        state["date_from"] = date_from
        state["last_successful_run"] = last_successful_run
        with open(self.state_out_file, "w") as f:
            json.dump(state, f)
        logging.info(f"State saved: date_from='{date_from}', last_successful_run='{last_successful_run}'")
