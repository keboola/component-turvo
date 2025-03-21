"""
TurvoAPI Extractor Component
"""
import asyncio
import os
import logging

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

from configuration import Configuration, EndpointEnum
from api_client import TurvoApiClient
from file_manager import FileManager
from manifest_manager import ManifestManager
from state_manager import StateManager
from lookups import (
    shipment_lookup_data,
    location_lookup_data,
)


class Component(ComponentBase):

    def __init__(self):
        super().__init__()

    def run(self):
        """
        Main execution code
        """
        data_dir = self.configuration.data_dir
        state_manager = StateManager(os.path.join(data_dir, "."))
        config = Configuration(state_manager, **self.configuration.parameters)

        api_client = TurvoApiClient(config)
        output_dir = os.path.join(data_dir, "out", "tables")
        os.makedirs(output_dir, exist_ok=True)

        file_manager = FileManager(config, output_dir)
        manifest_manager = ManifestManager(self, config, file_manager)

        async def process():
            """
            Downloads data based on selected endpoint.
            """
            if EndpointEnum.shipments in config.sync_options.endpoints:
                logging.info("Downloading shipments data...")

                shipment_list_metadata = file_manager.get_file_metadata("shipment_filters")
                shipment_list_stream = api_client.fetch_filtered_list_data(
                    resource="shipments",
                    element_key="shipments",
                    unique_id_key="id"
                )
                await file_manager.save_shipment_list_to_csv(
                    shipment_list_stream, shipment_list_metadata
                )

                if api_client.list_unique_ids:
                    shipment_details_metadata = file_manager.get_file_metadata("shipment_details")
                    shipment_details_stream = api_client.fetch_object_detail_data("shipments")
                    await file_manager.save_shipment_details_to_csv(
                        shipment_details_stream, shipment_details_metadata
                    )

                shipment_lookup_metadata = file_manager.get_file_metadata("shipment_lookups")
                await file_manager.save_lookup_data_to_csv(
                    shipment_lookup_data,
                    shipment_lookup_metadata
                )

            if EndpointEnum.locations in config.sync_options.endpoints:
                logging.info("Downloading locations data...")

                location_list_metadata = file_manager.get_file_metadata("location_filters")
                location_list_stream = api_client.fetch_filtered_list_data(
                    resource="locations",
                    element_key="locations",
                    unique_id_key="id"
                )
                await file_manager.save_location_list_to_csv(
                    location_list_stream, location_list_metadata
                )

                if api_client.list_unique_ids:
                    location_details_metadata = file_manager.get_file_metadata("location_details")
                    location_details_stream = api_client.fetch_object_detail_data("locations")
                    await file_manager.save_location_details_to_csv(
                        location_details_stream, location_details_metadata
                    )

                location_lookup_metadata = file_manager.get_file_metadata("location_lookups")
                await file_manager.save_lookup_data_to_csv(
                    location_lookup_data,
                    location_lookup_metadata
                )

        asyncio.run(process())

        logging.info("Data download completed. Proceeding to manifest creation...")
        manifest_manager.create_manifests()
        logging.info("Saving component state...")
        state_manager.save_state(
            config.sync_options.sync_time_value,
            config.sync_options.sync_time_unit.value,
            config.sync_options.end_datetime
        )

        logging.info("Data processing completed!")


"""
Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
