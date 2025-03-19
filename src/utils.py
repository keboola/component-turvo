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

def flatten_shipment(shipment: dict) -> list[dict]:
    """Flattens a shipment record into multiple rows if multiple carriers exist."""
    flattened_rows = []

    shipment_id = shipment.get("id")  # Keep shipment ID
    custom_id = shipment.get("customId")
    last_updated = shipment.get("lastUpdatedOn")
    created_date = shipment.get("createdDate")
    status = shipment.get("status", {}).get("code", {}).get("value", "")

    customer_id = None
    customer_name = None
    customer_order_id = None
    if shipment.get("customerOrder"):
        first_customer = shipment["customerOrder"][0]
        customer_order_id = first_customer.get("id")
        customer_id = first_customer["customer"]["id"]
        customer_name = first_customer["customer"]["name"]

    carrier_orders = shipment.get("carrierOrder", [])

    if carrier_orders:
        for carrier in carrier_orders:
            carrier_order_id = carrier.get("id")
            carrier_id = carrier["carrier"]["id"]
            carrier_name = carrier["carrier"]["name"]

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
