"""
Component TurvoAPI Extractor
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
            file_created = False

            if config.sync_options.endpoint == EndpointEnum.shipments:
                logging.info("Downloading shipments data...")
                shipment_list_metadata = file_manager.get_file_metadata("shipments")
                shipment_list_stream = api_client.fetch_shipments()
                file_created = await file_manager.save_shipment_list_to_csv(
                    shipment_list_stream, shipment_list_metadata
                )

                if api_client.shipment_ids:
                    shipment_details_metadata = file_manager.get_file_metadata("shipment_details")
                    shipment_details_stream = api_client.fetch_shipment_details()
                    await file_manager.save_shipment_details_to_csv(
                        shipment_details_stream, shipment_details_metadata
                    )

            else:
                logging.info("No supported endpoint selected. Skipping download...")

            return file_created

        file_created = asyncio.run(process())

        if file_created:
            logging.info("All files written successfully. Proceeding to manifest creation.")
            manifest_manager.create_manifests()
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
