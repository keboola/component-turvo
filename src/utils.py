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


def flatten_shipment_list(shipment: dict) -> list[dict]:
    """Flattens a shipment record into multiple rows if multiple carriers exist."""
    flattened_rows = []

    shipment_id = shipment.get("id")
    custom_id = shipment.get("customId")
    last_updated = shipment.get("lastUpdatedOn")
    created_date = shipment.get("createdDate")
    status = shipment.get("status", {}).get("code", {}).get("value", "")

    customer_order_id = None
    customer_id = None
    customer_name = None
    if shipment.get("customerOrder"):
        first_customer = shipment["customerOrder"][0]
        customer_order_id = first_customer.get("id")
        customer = first_customer.get("customer", {})
        customer_id = customer.get("id")
        customer_name = customer.get("name")

    carrier_orders = shipment.get("carrierOrder", [])

    if carrier_orders:
        for carrier in carrier_orders:
            carrier_order_id = carrier.get("id")
            carrier_data = carrier.get("carrier", {})
            carrier_id = carrier_data.get("id")
            carrier_name = carrier_data.get("name")

            flattened_rows.append({
                "shipment_id": shipment_id,
                "customId": custom_id,
                "lastUpdatedOn": last_updated,
                "createdDate": created_date,
                "status": status,
                "customer_order_id": customer_order_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "carrier_order_id": carrier_order_id,
                "carrier_id": carrier_id,
                "carrier_name": carrier_name
            })
    else:
        flattened_rows.append({
            "shipment_id": shipment_id,
            "customId": custom_id,
            "lastUpdatedOn": last_updated,
            "createdDate": created_date,
            "status": status,
            "customer_order_id": customer_order_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "carrier_order_id": None,
            "carrier_id": None,
            "carrier_name": None
        })

    return flattened_rows


def structure_shipment_details(shipment: dict) -> dict:
    """
    Extracts known fields while storing the remaining data in 'details'.
    Ensures structured fields are properly extracted.
    """
    known_fields = {
        "shipment_id": shipment.get("details", {}).get("id"),
        "customId": shipment.get("details", {}).get("customId"),
        "ltlShipment": shipment.get("details", {}).get("ltlShipment"),
        "phase": json.dumps(shipment.get("details", {}).get("phase", {})),
        "startDate": json.dumps(shipment.get("details", {}).get("startDate", {})),
        "endDate": json.dumps(shipment.get("details", {}).get("endDate", {})),
        "transportation": json.dumps(shipment.get("details", {}).get("transportation", {})),
        "status": json.dumps(shipment.get("details", {}).get("status", {})),
        "tracking": json.dumps(shipment.get("details", {}).get("tracking", {})),
        "margin": json.dumps(shipment.get("details", {}).get("margin", {})),
        "equipment": json.dumps(shipment.get("details", {}).get("equipment", [])),
        "contributors": json.dumps(shipment.get("details", {}).get("contributors", [])),
        "lane": json.dumps(shipment.get("details", {}).get("lane", {})),
        "globalRoute": json.dumps(shipment.get("details", {}).get("globalRoute", [])),
        "modeInfo": json.dumps(shipment.get("details", {}).get("modeInfo", [])),
        "customerOrder": json.dumps(shipment.get("details", {}).get("customerOrder", [])),
        "carrierOrder": json.dumps(shipment.get("details", {}).get("carrierOrder", [])),
        "groups": json.dumps(shipment.get("details", {}).get("groups", [])),
        "statusHistory": json.dumps(shipment.get("details", {}).get("statusHistory", [])),
    }

    known_keys = set(known_fields.keys()) | {"details"}

    remaining_data = {k: v for k, v in shipment.get("details", {}).items() if k not in known_keys}
    known_fields["details"] = json.dumps(remaining_data)

    return known_fields
