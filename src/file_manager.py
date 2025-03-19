import os
import csv
import logging
from dataclasses import dataclass
from typing import AsyncIterable

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

    def get_file_metadata(self) -> FileMetadata:
        """Generates file metadata containing name and full path."""
        table_name = f"shipments"
        file_name = f"{table_name}.csv"
        file_path = os.path.join(self.output_dir, file_name)
        return FileMetadata(table_name, file_name, file_path)

    @staticmethod
    async def save_to_csv(data: AsyncIterable[dict], file_metadata: FileMetadata):
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
