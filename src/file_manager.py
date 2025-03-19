import os
import csv
import logging
from dataclasses import dataclass
from typing import AsyncIterable

from utils import structure_shipment_details


@dataclass
class FileMetadata:
    """Encapsulates output file information"""
    table_name: str
    file_name: str
    file_path: str


class FileManager:
    """Handles file path generation and saving data to CSV files."""
    def __init__(self, config, output_dir):
        self.config = config
        self.output_dir = output_dir

    def get_file_metadata(self, table_name: str) -> FileMetadata:
        """Generates file metadata containing name and full path."""
        table_name = f"{table_name}"
        file_name = f"{table_name}.csv"
        file_path = os.path.join(self.output_dir, file_name)
        return FileMetadata(table_name, file_name, file_path)

    @staticmethod
    async def save_shipment_list_to_csv(data: AsyncIterable[dict], file_metadata: FileMetadata):
        """
        Saves streamed data to a CSV file.
        """
        """Saves streaming shipment data to a CSV file."""
        fieldnames = [
            "shipment_id", "customId", "lastUpdatedOn", "createdDate",
            "status", "customer_order_id", "customer_id", "customer_name",
            "carrier_order_id", "carrier_id", "carrier_name"
        ]

        file_created = False

        with open(file_metadata.file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            async for row in data:
                writer.writerow(row)
                file_created = True

        logging.info(f"Data successfully saved to {file_metadata.file_path}")
        return file_created

    @staticmethod
    async def save_shipment_details_to_csv(data: AsyncIterable[dict], file_metadata: FileMetadata):
        """
        Saves structured shipment details with JSON columns.
        """
        fieldnames = [
            "shipment_id", "customId", "ltlShipment",
            "phase", "startDate", "endDate", "transportation",
            "status", "tracking", "margin", "equipment",
            "contributors", "lane", "globalRoute", "modeInfo",
            "customerOrder", "carrierOrder", "groups",
            "statusHistory", "details"
        ]

        with open(file_metadata.file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            async for shipment in data:
                mapped_row = structure_shipment_details(shipment)
                writer.writerow(mapped_row)

        logging.info(f"Structured shipment details saved to {file_metadata.file_path}")
