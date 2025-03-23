import pytz
import logging
from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from keboola.component.exceptions import UserException
from dateparser import parse as parse_natural_date

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


class Endpoints(BaseModel):
    shipment_filters: bool = Field(
        default=False,
        description="Shipments filters"
    ),
    shipment_details_for_filters: bool = Field(
        default=False,
        description="Shipment details for downloaded filters"
    ),
    shipment_details_custom: bool = Field(
        default=False,
        description="Shipment details for custom IDs"
    ),
    shipment_lookups: bool = Field(
        default=False,
        description="Shipment lookups"
    ),
    location_filters: bool = Field(
        default=False,
        description="Location filters"
    ),
    location_details_for_filters: bool = Field(
        default=False,
        description="Location details for downloaded filters"
    ),
    location_details_custom: bool = Field(
        default=False,
        description="Location details for custom IDs"
    ),
    location_lookups: bool = Field(
        default=False,
        description="Location lookups"
    ),

    @model_validator(mode="before")
    @classmethod
    def correct_invalid_combinations(cls, values: Dict) -> Dict:
        if not values.get("shipment_filters"):
            values["shipment_details_for_filters"] = False
        if not values.get("location_filters"):
            values["location_details_for_filters"] = False
        return values

    @property
    def as_dict(self) -> Dict[str, bool]:
        return self.model_dump()


class LoadOptions(BaseModel):
    date_from: str = Field(default="1 hour")

    def resolved_date_from(self, state: Dict[str, str], default: str = "1 hour") -> str:
        date_str = (self.date_from or default).strip().lower()

        if date_str in {"last", "lastrun", "last run", "last_run"}:
            last_run = state.get("last_successful_run")
            if not last_run:
                raise UserException("No previous run timestamp found in state, but 'last run' was selected.")
            return last_run

        date_obj = parse_natural_date(date_str, settings={"TIMEZONE": "UTC"})
        if date_obj is None:
            raise UserException(f"Invalid date string: '{date_str}'")

        date_obj = date_obj.replace(tzinfo=pytz.UTC)
        return date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")


class Configuration(BaseModel):
    authentication: Authentication
    endpoints: Endpoints
    load_options: LoadOptions
    custom_shipment_details_ids: str = Field(default="")
    custom_location_details_ids: str = Field(default="")
    debug: bool = False

    resolved_date_from: Optional[str] = None

    @property
    def parsed_custom_shipment_ids(self) -> List[int]:
        if not self.custom_shipment_details_ids.strip():
            return []
        parts = self.custom_shipment_details_ids.split(",")
        if not all(part.strip().isdigit() for part in parts):
            raise UserException("Custom Shipment IDs must be a comma-separated list of integers.")
        return [int(p.strip()) for p in parts if p.strip()]

    @property
    def parsed_custom_location_ids(self) -> List[int]:
        if not self.custom_location_details_ids.strip():
            return []
        parts = self.custom_location_details_ids.split(",")
        if not all(part.strip().isdigit() for part in parts):
            raise UserException("Custom Location IDs must be a comma-separated list of integers.")
        return [int(p.strip()) for p in parts if p.strip()]

    def __init__(self, state_manager: StateManager, **data):
        try:
            super().__init__(**data)
            self.resolved_date_from = self.load_options.resolved_date_from(
                state=state_manager.load_state()
            )
            logging.info(f"Resolved date_from: {self.resolved_date_from}")
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise UserException(f"Validation Error: {', '.join(error_messages)}")

        if self.debug:
            logging.debug("Component will run in Debug mode")
