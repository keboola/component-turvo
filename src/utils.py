import json

from configuration import Authentication


def generate_auth_request(auth_config: Authentication) -> (dict[str, str], dict[str, str], str):
    headers = {
        "Content-Type": "application/json",
        "x-api-key": auth_config.xApiKey
    }

    body = {
        "username": auth_config.username,
        "password": auth_config.password,
        "grant_type": "password",
        "scope": "read+trust+write",
        "type": "business"
    }

    query_params = f"client_id={auth_config.clientId}&client_secret={auth_config.clientSecret}"

    return headers, body, query_params


def shipment_filters_mapping(shipment: dict) -> dict:
    """Transforms a shipment record for CSV storage."""
    return {
        "id": shipment.get("id"),
        "customId": shipment.get("customId"),
        "lastUpdatedOn": shipment.get("lastUpdatedOn"),
        "updated": shipment.get("updated"),
        "createdDate": shipment.get("createdDate"),
        "created": shipment.get("created"),
        "status": json.dumps(shipment.get("status", {})),
        "customerOrder": json.dumps(shipment.get("customerOrder", []))
    }


def location_filters_mapping(location: dict) -> dict:
    """Transforms a location record for CSV storage."""
    return {
        "id": location.get("id"),
        "name": location.get("name"),
        "created": location.get("created"),
        "updated": location.get("updated"),
        "addresses": json.dumps(location.get("addresses", [])),
        "phones": json.dumps(location.get("phones", {})),
    }


def customer_filters_mapping(customer: dict) -> dict:
    """Transforms a customer record for CSV storage."""
    return {
        "id": customer.get("id"),
        "name": customer.get("name"),
        "created": customer.get("created"),
        "updated": customer.get("updated"),
        "addresses": json.dumps(customer.get("addresses", [])),
        "parentAccount": json.dumps(customer.get("parentAccount", {})),
        "status": json.dumps(customer.get("status", {})),
    }


def carrier_filters_mapping(carrier: dict) -> dict:
    """Transforms a carrier record for CSV storage."""
    return {
        "id": carrier.get("id"),
        "name": carrier.get("name"),
        "mcNumber": carrier.get("mcNumber"),
        "dotNumber": carrier.get("dotNumber"),
        "created": carrier.get("created"),
        "updated": carrier.get("updated"),
        "scac": json.dumps(carrier.get("scac", [])),
        "parentAccount": json.dumps(carrier.get("parentAccount", {})),
        "contact": json.dumps(carrier.get("contact", {})),
        "externalIds": json.dumps(carrier.get("externalIds", [])),
        "accountDistribution": json.dumps(carrier.get("accountDistribution", [])),
        "addresses": json.dumps(carrier.get("addresses", [])),
        "status": json.dumps(carrier.get("status", {})),
    }


def order_filters_mapping(order: dict) -> dict:
    """Transforms an order record for CSV storage."""
    return {
        "id": order.get("id"),
        "customId": order.get("customId"),
        "created": order.get("created"),
        "lastUpdatedOn": order.get("lastUpdatedOn"),
        "origin": json.dumps(order.get("origin", {})),
        "destination": json.dumps(order.get("destination", {})),
        "customer": json.dumps(order.get("customer", {})),
        "start_date": json.dumps(order.get("start_date", {})),
        "end_date": json.dumps(order.get("end_date", {})),
        "status": json.dumps(order.get("status", {})),
        "external_ids": json.dumps(order.get("external_ids", [])),
    }


def shipment_details_mapping(shipment: dict) -> dict:
    """
    Extracts high-level shipment fields while storing additional fields in 'details'.
    """
    details = shipment.get("details", {})

    known_fields = {
        "id": details.get("id"),
        "customId": details.get("customId"),
        "ltlShipment": details.get("ltlShipment"),
        "phase": json.dumps(details.get("phase", {})),
        "startDate": json.dumps(details.get("startDate", {})),
        "endDate": json.dumps(details.get("endDate", {})),
        "transportation": json.dumps(details.get("transportation", {})),
        "status": json.dumps(details.get("status", {})),
        "tracking": json.dumps(details.get("tracking", {})),
        "margin": json.dumps(details.get("margin", {})),
        "equipment": json.dumps(details.get("equipment", [])),
        "contributors": json.dumps(details.get("contributors", [])),
        "lane": json.dumps(details.get("lane", {})),
        "globalRoute": json.dumps(details.get("globalRoute", [])),
        "modeInfo": json.dumps(details.get("modeInfo", [])),
        "customerOrder": json.dumps(details.get("customerOrder", [])),
        "carrierOrder": json.dumps(details.get("carrierOrder", [])),
        "groups": json.dumps(details.get("groups", [])),
        "statusHistory": json.dumps(details.get("statusHistory", [])),
    }

    known_keys = set(known_fields.keys()) | {"details"}
    remaining_data = {k: v for k, v in details.items() if k not in known_keys}
    known_fields["details"] = json.dumps(remaining_data)

    return known_fields


def location_details_mapping(location: dict) -> dict:
    """
    Extracts high-level shipment fields while storing additional fields in 'details'.
    """
    details = location.get("details", {})

    known_fields = {
        "id": details.get("id"),
        "timezone": details.get("timezone"),
        "name": details.get("name"),
        "address": json.dumps(details.get("address", [])),
        "group": json.dumps(details.get("group", [])),
    }

    known_keys = set(known_fields.keys())
    remaining_data = {k: v for k, v in details.items() if k not in known_keys}
    known_fields["details"] = json.dumps(remaining_data)

    return known_fields
