import logging
from datetime import date
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, ValidationError, field_validator
from keboola.component.exceptions import UserException

from src.state_manager import StateManager


class EnvironmentEnum(str, Enum):
    dev = "dev"
    prod = "prod"

ENVIRONMENT_URLS = {
    EnvironmentEnum.dev: "https://my-sandbox-publicapi.turvo.com/v1",
    EnvironmentEnum.prod: "https://publicapi.turvo.com/v1",
}

class EndpointEnum(str, Enum):
    shipments = "shipments"

class Authentication(BaseModel):
    username: str
    clientId: str
    password: str = Field(alias="#password")
    clientSecret: str = Field(alias="#clientSecret")
    xApiKey: str = Field(alias='#xApiKey')
    environment: EnvironmentEnum = Field(
        default=EnvironmentEnum.prod,
        description="Choose 'dev' for testing or 'prod' for production."
    )

    @field_validator("username", "password", "clientId", "clientSecret", "xApiKey")
    def must_not_be_empty(cls, value: str, info) -> str:
        if not value.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty")
        return value

    @property
    def api_base_url(self) -> str:
        """Returns the full API base URL based on the selected environment."""
        return ENVIRONMENT_URLS[self.environment]


class SyncOptions(BaseModel):
    endpoints: list[EndpointEnum] = Field(
        default=[],
        description="Endpoints for the data extraction"
    )
    date_from: str = Field(
        default="2020-01-01",
        description="Date from which to fetch data, default '2020-01-01'"
    )
    date_to: Optional[str] = Field(
        default=None,
        description="Date to which to fetch data."
    )
    reload_full_data: bool = Field(
        default=False,
        description="When enabled, retrieves the complete dataset from 'date_from', bypassing incremental loading."
    )
    max_concurrent_requests: int = Field(
        default=1,
        ge=1,
        le=2,
        description="Maximum amount of concurrent requests to allow fetching data."
    )
    max_retries: int = Field(
        default=5,
        ge=3,
        le=5,
        description="Maximum amount of retries to allow fetching data."
    )

    @field_validator("endpoints")
    def must_not_be_empty(cls, values: List[EndpointEnum], info) -> List[EndpointEnum]:
        if len(values) == 0:
            raise ValueError(f"Field '{info.field_name}' cannot be empty")
        return values

    @property
    def resolved_date_to(self) -> str:
        """Ensures date_to is always a string."""
        return self.date_to if self.date_to else str(date.today())


class Configuration(BaseModel):
    authentication: Authentication
    sync_options: SyncOptions
    debug: bool = False

    def __init__(self, state_manager: StateManager, **data):
        try:
            super().__init__(**data)

            last_processed_date = state_manager.get_last_processed_date()
            if last_processed_date and not self.sync_options.reload_full_data:
                self.sync_options.date_from = last_processed_date

            if not self.sync_options.date_to:
                self.sync_options.date_to = self.sync_options.resolved_date_to

            logging.info(f"Using date_from: {self.sync_options.date_from}")
            logging.info(f"Using date_to: {self.sync_options.date_to}")
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.debug("Component will run in Debug mode")

