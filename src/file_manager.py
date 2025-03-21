import asyncio
import json
import os
import csv
import logging

from dataclasses import dataclass
from typing import AsyncIterable, List, Dict

from utils import (
    shipment_filters_mapping,
    shipment_details_mapping,
    customer_filters_mapping,
    location_filters_mapping,
    carrier_filters_mapping,
    order_filters_mapping,
    location_details_mapping
)


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
    async def async_iterable(data: List[Dict[str, str]]):
        """Converts a list into an async generator to be used as AsyncIterable."""
        for row in data:
            await asyncio.sleep(0)
            yield row

    @staticmethod
    async def save_data_to_csv(
        data: AsyncIterable[dict],
        file_metadata: FileMetadata,
        fieldnames: List[str]
    ):
        """
        Generic method to save streamed data to a CSV file.
        Keeps inner JSON structures untouched.
        """
        file_created = False

        with open(file_metadata.file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            async for row in data:
                writer.writerow(FileManager.flatten_json_fields(row, fieldnames))
                file_created = True

        logging.info(f"Data successfully saved to {file_metadata.file_path}")
        return file_created

    @staticmethod
    def flatten_json_fields(data: Dict, fieldnames: List[str]) -> Dict:
        """
        Ensures that JSON fields are properly serialized as JSON strings while keeping known fields structured.
        """
        formatted_data = {}
        for field in fieldnames:
            value = data.get(field, None)
            if isinstance(value, (dict, list)):
                formatted_data[field] = json.dumps(value)
            else:
                formatted_data[field] = value
        return formatted_data

    async def save_shipment_list_to_csv(
        self,
        data: AsyncIterable[dict],
        file_metadata: FileMetadata
    ):
        """
        Saves shipment list data to a CSV file while keeping inner JSON fields.
        """
        fieldnames = [
            "id", "customId", "lastUpdatedOn", "updated",
            "createdDate", "created", "status", "customerOrder"
        ]

        async def transformed_data():
            async for shipment in data:
                yield shipment_filters_mapping(shipment)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_customer_list_to_csv(
        self,
        data: AsyncIterable[dict],
        file_metadata: FileMetadata
    ):
        """
        Saves customer list data to a CSV file while keeping inner JSON fields.
        """
        fieldnames = [
            "id", "name", "created", "updated",
            "addresses", "parentAccount", "status"
        ]

        async def transformed_data():
            async for customer in data:
                yield customer_filters_mapping(customer)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_location_list_to_csv(
        self,
        data: AsyncIterable[dict],
        file_metadata: FileMetadata
    ):
        """
        Saves location list data to a CSV file while keeping inner JSON fields.
        """
        fieldnames = [
            "id", "name", "created",
            "updated", "addresses", "phones"
        ]

        async def transformed_data():
            async for location in data:
                yield location_filters_mapping(location)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_carrier_list_to_csv(
        self,
        data: AsyncIterable[dict],
        file_metadata: FileMetadata
    ):
        """
        Saves carrier list data to a CSV file while keeping inner JSON fields.
        """
        fieldnames = [
            "id", "name", "mcNumber",
            "dotNumber", "created", "updated",
            "scac", "parentAccount", "contact",
            "externalIds", "accountDistribution",
            "addresses", "status"
        ]

        async def transformed_data():
            async for carrier in data:
                yield carrier_filters_mapping(carrier)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_order_list_to_csv(
        self,
        data: AsyncIterable[dict],
        file_metadata: FileMetadata
    ):
        """
        Saves order list data to a CSV file while keeping inner JSON fields.
        """
        fieldnames = [
            "id", "customId", "created", "lastUpdatedOn",
            "origin", "destination", "customer", "start_date",
            "end_date", "status", "external_ids"
        ]

        async def transformed_data():
            async for order in data:
                yield order_filters_mapping(order)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_shipment_details_to_csv(
            self,
            data: AsyncIterable[dict],
            file_metadata: FileMetadata
    ):
        """
        Saves structured shipment details with JSON columns.
        """
        fieldnames = [
            "id", "customId", "ltlShipment",
            "phase", "startDate", "endDate", "transportation",
            "status", "tracking", "margin", "equipment",
            "contributors", "lane", "globalRoute", "modeInfo",
            "customerOrder", "carrierOrder", "groups",
            "statusHistory", "details"
        ]

        async def transformed_data():
            async for shipment in data:
                yield shipment_details_mapping(shipment)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_location_details_to_csv(
            self,
            data: AsyncIterable[dict],
            file_metadata: FileMetadata
    ):
        """
        Saves structured location details with JSON columns.
        """
        fieldnames = [
            "id", "timezone", "name", "address", "group"
        ]

        async def transformed_data():
            async for location in data:
                yield location_details_mapping(location)

        await self.save_data_to_csv(transformed_data(), file_metadata, fieldnames)

    async def save_lookup_data_to_csv(
            self,
            lookup_data: List[Dict[str, str]],
            file_metadata: FileMetadata
    ):
        """
        Saves lookup data (e.g., shipment status codes) to a CSV file.
        The order of columns will be dynamically adjusted: `code`, `type`, `value`
        """
        fieldnames = ["code", "type", "value"]

        async def transformed_lookup_data():
            for row in lookup_data:
                yield {key: row[key] for key in fieldnames}

        await self.save_data_to_csv(transformed_lookup_data(), file_metadata, fieldnames)
