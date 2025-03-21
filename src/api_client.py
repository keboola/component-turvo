import asyncio
import logging
import time
from typing import Dict, AsyncGenerator, Set

import httpx

from configuration import Configuration
from utils import generate_auth_request


class TurvoApiClient:
    """
    Asynchronous client for Turvo API Client
    """

    def __init__(self, config: Configuration):
        self.config = config
        self.list_unique_ids: Set[int] = set()
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

    async def fetch_filtered_list_data(
            self,
            resource: str,
            element_key: str,
            unique_id_key: str
    ) -> AsyncGenerator[Dict, None]:
        """
        Generic generator to fetch filtered list data from a Turvo endpoint.

        :param resource: The endpoint resource, e.g., "shipments"
        :param element_key: The key inside `details` that contains the list of items
        :param unique_id_key: The key inside each element used to collect unique IDs
        """
        start = 0
        page_size = 24
        start_datetime = self.config.sync_options.start_datetime
        self.list_unique_ids.clear()

        headers = {
            "Authorization": f"Bearer {await self.authenticate()}",
            "Content-Type": "application/json",
            "x-api-key": self.config.authentication.xApiKey,
        }

        logging.info(f"Fetching {resource} updated since {start_datetime}...")

        async with httpx.AsyncClient(verify=True) as client:
            while True:
                url = f"{self.api_base_url}/{resource}/list?updated[gte]={start_datetime}&start={start}"
                logging.info(f"Fetching {resource} (start={start}): {url}")

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    data = response.json()

                    if data.get("Status") != "SUCCESS":
                        logging.error(f"Unexpected API response: {data}")
                        break

                    pagination = data["details"].get("pagination", {})
                    if not pagination.get("moreAvailable", False):
                        logging.info("No more results available, stopping pagination.")
                        break

                    elements = data["details"].get(element_key, [])
                    for element in elements:
                        element_id = element.get(unique_id_key)
                        if element_id:
                            self.list_unique_ids.add(element_id)

                        yield element

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

        logging.info(f"Collected {len(self.list_unique_ids)} unique {resource} IDs.")

    async def fetch_object_detail_data(self, object_name: str) -> AsyncGenerator[Dict, None]:
        """
        Generator that fetches detailed data for each object ID in self.list_unique_ids.

        :param object_name: API path like "shipments" or "orders"
        """
        headers = {
            "Authorization": f"Bearer {await self.authenticate()}",
            "Content-Type": "application/json",
            "x-api-key": self.config.authentication.xApiKey,
        }

        async with httpx.AsyncClient(verify=True) as client:
            for object_id in self.list_unique_ids:
                url = f"{self.api_base_url}/{object_name}/{object_id}"
                logging.info(f"Fetching {object_name} details for {object_id}")

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    yield response.json()

                except httpx.HTTPStatusError as e:
                    logging.error(f"Failed to fetch {object_name} {object_id}: {e}")

                await asyncio.sleep(self.request_delay)
