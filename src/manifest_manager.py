import logging
import os

from keboola.component.base import ComponentBase
from file_manager import FileManager
from configuration import Configuration


class ManifestManager:
    """Handles the generation of Keboola manifest files."""
    PRIMARY_KEYS = {
        "shipment_filters.csv": ["id"],
        "shipment_details.csv": ["id"],
        "shipment_lookups.csv": ["code"],

        "customer_filters.csv": ["id"],
        "customer_details.csv": ["id"],
        "customer_lookups.csv": ["code"],

        "location_filters.csv": ["id"],
        "location_details.csv": ["id"],
        "location_lookups.csv": ["code"],

        "carrier_filters.csv": ["id"],
        "carrier_details.csv": ["id"],
        "carrier_lookups.csv": ["code"],

        "order_filters.csv": ["id"],
        "order_details.csv": ["id"],
        "order_lookups.csv": ["code"],
    }

    def __init__(self, component: ComponentBase, config: Configuration, file_manager: FileManager):
        self.config = config
        self.component = component
        self.file_manager = file_manager

    def get_primary_keys(self, file_name: str) -> list[str]:
        """Returns the primary keys based on the filename."""
        return self.PRIMARY_KEYS.get(file_name, [])

    def create_manifest(self, file_name: str):
        """
        Generates a Keboola manifest file for a dataset.
        Uses FileManager to ensure consistent file naming.
        """
        file_path = os.path.join(self.file_manager.output_dir, file_name)

        if not os.path.exists(file_path):
            logging.warning(f"Skipping manifest creation: {file_name} does not exist.")
            return

        file_metadata = self.file_manager.get_file_metadata(file_name)
        logging.info(f"Creating manifest for {file_name}...")

        table_name = file_name.replace(".csv", "")

        output_table = self.component.create_out_table_definition(
            file_name,
            incremental=True,
            primary_key=self.get_primary_keys(file_name),
            destination=f"out.c-turvo.{table_name}",
        )

        self.component.write_manifest(output_table)
        logging.info(f"Manifest successfully created for {file_metadata.file_name}")

    def create_manifests(self):
        """
        Iterates over all CSV files in the output directory and creates manifests
        only for those that exist, using the existing create_manifest() method.
        """
        for file_name in os.listdir(self.file_manager.output_dir):
            if file_name.endswith(".csv"):
                self.create_manifest(file_name)
