import asyncio
import logging
import time
from typing import List, Dict, AsyncGenerator

import httpx

from configuration import Configuration
from utils import generate_auth_request, flatten_shipment


class TurvoApiClient:
    """
    Asynchronous client for Turvo API Client
    """

    def __init__(self, config: Configuration):
        self.config = config
        self.api_base_url = self.config.authentication.api_base_url
        self.max_retries =self.config.sync_options.max_retries
        self.auth_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(self.config.sync_options.max_concurrent_requests)
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

        if self.config.debug:
            logging.debug(f"Auth URL: %s", auth_url)
            logging.debug(f"Request Body: %s", body)
            logging.debug(f"Request Headers: %s", headers)
            logging.debug(f"Query_params: %s", query_params)

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


    async def fetch_shipments(self, max_pages: int = 3) -> AsyncGenerator[Dict, None]:
        """
        Generator that yields shipments page by page.
        Stops when the API returns an error (5001) or if max_pages is reached.
        """
        start = 0
        page_size = 24
        pages_fetched = 0

        headers = {
            "Authorization": f"Bearer {await self.authenticate()}",
            "Content-Type": "application/json",
            "x-api-key": self.config.authentication.xApiKey,
        }

        async with httpx.AsyncClient(verify=False) as client:
            while True:
                url = f"{self.api_base_url}/shipments/list?start={start}"
                logging.info(f"Fetching shipments (Page {pages_fetched+1}): {url}")

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    data = response.json()

                    if data.get("Status") != "SUCCESS":
                        logging.error(f"Unexpected API response: {data}")
                        break

                    for shipment in data["details"].get("shipments", []):
                        for row in flatten_shipment(shipment):
                            yield row

                    pages_fetched += 1

                    if max_pages and pages_fetched >= max_pages:
                        logging.info(f"Reached max page limit: {max_pages}")
                        break

                    start += page_size

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 500:
                        error_data = e.response.json()
                        if error_data.get("details", {}).get("errorCode") == "5001":
                            logging.info("Reached the last available page (5001 error). Stopping pagination.")
                            break
                    logging.error(f"Request failed: {e}")
                    break

                await asyncio.sleep(self.request_delay)