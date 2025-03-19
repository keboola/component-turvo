import asyncio
import logging
import time
from typing import Dict, AsyncGenerator, Set

import httpx

from configuration import Configuration
from utils import generate_auth_request, flatten_shipment_list


class TurvoApiClient:
    """
    Asynchronous client for Turvo API Client
    """

    def __init__(self, config: Configuration):
        self.config = config
        self.shipment_ids: Set[int] = set()
        self.api_base_url = self.config.authentication.api_base_url
        self.max_retries = self.config.sync_options.max_retries
        self.auth_lock = asyncio.Lock()
        self.auth_key = None
        self.expires_at = 0
        self.retry_delay = 120
        self.request_delay = 2

    async def authenticate(self) -> str:
        """Calls the auth endpoint and retrieves the key for the further requests."""
        async with self.auth_lock:
            if self.auth_key and time.time() < self.expires_at:
                return self.auth_key

        logging.info("Authenticating with the Turvo API credentials...")
        headers, body, query_params = generate_auth_request(self.config.authentication)
        auth_url = f"{self.api_base_url}/oauth/token?{query_params}"

        # if self.config.debug:
        # logging.debug(f"Auth URL: %s", auth_url)
        # logging.debug(f"Request Body: %s", body)
        # logging.debug(f"Request Headers: %s", headers)
        # logging.debug(f"Query_params: %s", query_params)

        async with httpx.AsyncClient(verify=True) as client:
            retries = 0
            while retries < self.max_retries:
                try:
                    response = await client.post(auth_url, json=body, headers=headers)
                    response.raise_for_status()

                    data = response.json()
                    self.auth_key = data["access_token"]
                    self.expires_at = time.time() + data["expires_in"] - 60

                    return self.auth_key
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logging.error(f"Authentication attempt {retries + 1} failed: {e}")

                retries += 1
                await asyncio.sleep(min(self.retry_delay * (2 ** retries), 60))

            raise Exception("Maximum number of retries reached. Unable to authenticate.")

    async def fetch_shipments(self) -> AsyncGenerator[Dict, None]:
        """
        Generator that fetches shipments using `updated[gte]` while collecting unique shipment IDs.
        """
        start = 0
        page_size = 24
        start_datetime = self.config.sync_options.start_datetime
        self.shipment_ids.clear()

        headers = {
            "Authorization": f"Bearer {await self.authenticate()}",
            "Content-Type": "application/json",
            "x-api-key": self.config.authentication.xApiKey,
        }

        logging.info(f"Fetching shipments updated since {start_datetime}...")

        async with httpx.AsyncClient(verify=True) as client:
            while True:
                url = f"{self.api_base_url}/shipments/list?updated[gte]={start_datetime}&start={start}"
                logging.info(f"Fetching shipments (start={start}): {url}")

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    data = response.json()

                    if data.get("Status") != "SUCCESS":
                        logging.error(f"Unexpected API response: {data}")
                        break

                    pagination = data["details"].get("pagination", {})
                    if not pagination.get("moreAvailable", False):
                        logging.info("No more shipments available, stopping pagination.")
                        break

                    shipments = data["details"].get("shipments", [])
                    for shipment in shipments:
                        shipment_id = shipment.get("id")
                        if shipment_id:
                            self.shipment_ids.add(shipment_id)

                        for flattened_shipment in flatten_shipment_list(shipment):
                            yield flattened_shipment

                    start += page_size

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 400:
                        error_data = e.response.json()
                        if error_data.get("details", {}).get("errorCode") == "400":
                            logging.error(f"Date range is beyond the allowed limit: {start_datetime}")
                            break
                    logging.error(f"Request failed: {e}")
                    break

                await asyncio.sleep(self.request_delay)

        logging.info(f"Collected {len(self.shipment_ids)} unique shipment IDs.")

    async def fetch_shipment_details(self) -> AsyncGenerator[Dict, None]:
        """
        Generator that fetches detailed shipment data for each shipment ID.
        """
        headers = {
            "Authorization": f"Bearer {await self.authenticate()}",
            "Content-Type": "application/json",
            "x-api-key": self.config.authentication.xApiKey,
        }

        async with httpx.AsyncClient(verify=True) as client:
            for shipment_id in self.shipment_ids:
                url = f"{self.api_base_url}/shipments/{shipment_id}"
                logging.info(f"Fetching shipment details for {shipment_id}")

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    yield data

                except httpx.HTTPStatusError as e:
                    logging.error(f"Failed to fetch shipment {shipment_id}: {e}")

                await asyncio.sleep(self.request_delay)
