import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, ValidationError, field_validator
from keboola.component.exceptions import UserException

from state_manager import StateManager


class EnvironmentEnum(str, Enum):
    dev = "dev"
    prod = "prod"


ENVIRONMENT_URLS = {
    EnvironmentEnum.dev: "https://my-sandbox-publicapi.turvo.com/v1",
    EnvironmentEnum.prod: "https://publicapi.turvo.com/v1",
}


class EndpointEnum(str, Enum):
    shipments = "shipments"
    customers = "customers"
    locations = "locations"
    carriers = "carriers"
    orders = "orders"


class TimeUnit(Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


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
    endpoints: List[EndpointEnum] = Field(
        default=[EndpointEnum.shipments],
        description="List of endpoints for data extraction"
    )

    sync_time_value: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Time value for downloading the data"
    )

    sync_time_unit: TimeUnit = Field(
        default=TimeUnit.HOUR,
        description="Time unit for downloading the data"
    )

    max_retries: int = Field(
        default=5,
        ge=3,
        le=5,
        description="Maximum amount of retries to allow fetching data."
    )

    start_datetime: Optional[str] = Field(default=None)
    end_datetime: Optional[str] = Field(default=None)

    @field_validator("endpoints")
    def must_not_be_empty(cls, values: List[EndpointEnum]) -> List[EndpointEnum]:
        """Ensures that at least one endpoint is selected."""
        if not values:
            raise ValueError("At least one endpoint must be specified.")
        return values

    @field_validator("endpoints")
    def validate_endpoints(cls, values: list[str]) -> list[str]:
        """
        Ensures that all provided endpoints exist in EndpointEnum.
        """
        valid_endpoints = {e.value for e in EndpointEnum}
        invalid_endpoints = [e for e in values if e not in valid_endpoints]

        if invalid_endpoints:
            raise ValueError(
                f"Invalid endpoints specified: {invalid_endpoints}. "
                f"Allowed values: {list(valid_endpoints)}"
            )
        return values

    def calculate_start_date(self, now: datetime) -> str:
        """Calculate the start date based on the time value and unit."""
        unit_map = {
            TimeUnit.HOUR: timedelta(hours=self.sync_time_value),
            TimeUnit.DAY: timedelta(days=self.sync_time_value),
            TimeUnit.WEEK: timedelta(weeks=self.sync_time_value),
            TimeUnit.MONTH: relativedelta(months=self.sync_time_value),
            TimeUnit.YEAR: relativedelta(years=self.sync_time_value),
        }
        start_date = now - unit_map[self.sync_time_unit]
        return start_date.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def initialize_sync_window(self, state_manager: StateManager):
        """
        Initializes the sync window by setting `start_datetime` and `end_datetime`.
        Uses `state_manager` to retrieve the last known sync or generate a new one.
        """
        now = datetime.now(timezone.utc)
        self.end_datetime = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

        self.start_datetime = state_manager.get_last_sync_date(
            sync_time_value=self.sync_time_value,
            sync_time_unit=self.sync_time_unit.value,
            default_start_date=self.calculate_start_date(now),
        )

        logging.info(f"Fetching data from {self.start_datetime} to {self.end_datetime}")


class Configuration(BaseModel):
    authentication: Authentication
    sync_options: SyncOptions
    debug: bool = False

    def __init__(self, state_manager: StateManager, **data):
        try:
            super().__init__(**data)
            self.sync_options.initialize_sync_window(state_manager)
            logging.info(f"Using download date: {self.sync_options.start_datetime}")
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.debug("Component will run in Debug mode")
