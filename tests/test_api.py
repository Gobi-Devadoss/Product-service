import json


BASE = "/api/v1/products"


def create(client, payload, **changes):
    return client.post(BASE, json={**payload, **changes})


def assert_error(response, status, message=None):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"timestamp", "status", "error", "message", "path", "details"}
    assert body["status"] == status
    if message:
        assert body["message"] == message
    return body


# ---------- POST ----------

def test_create_returns_201_with_location(client, product_payload):
    response = create(client, product_payload)

    assert response.status_code == 201
    body = response.json()
    assert response.headers["Location"] == f"{BASE}/{body['id']}"
    assert body["status"] == "ACTIVE"
    assert body["price"] == 799.5
    assert "createdAt" in body and "updatedAt" in body


def test_create_trims_text_and_ignores_client_id_and_timestamps(client, product_payload):
    response = create(
        client, product_payload, name="  Mouse  ", id=999, createdAt="2000-01-01T00:00:00Z"
    )

    body = response.json()
    assert body["name"] == "Mouse"
    assert body["id"] != 999
    assert not body["createdAt"].startswith("2000")


def test_create_validation_errors_return_400_with_details(client):
    response = client.post(BASE, json={"name": "A", "price": 0, "quantity": -1})

    body = assert_error(response, 400, "Validation failed")
    fields = {d["field"] for d in body["details"]}
    assert {"name", "price", "quantity", "category"} <= fields


def test_create_rejects_more_than_two_decimals(client, product_payload):
    assert_error(create(client, product_payload, price=10.999), 400)


def test_create_rejects_wrong_type(client, product_payload):
    assert_error(create(client, product_payload, quantity="ten"), 400)


def test_create_rejects_blank_name_after_trim(client, product_payload):
    assert_error(create(client, product_payload, name="   "), 400)


def test_create_malformed_json_returns_400(client):
    response = client.post(BASE, content="{bad json", headers={"Content-Type": "application/json"})

    assert_error(response, 400, "Malformed JSON")


def test_create_without_json_content_type_returns_400(client, product_payload):
    response = client.post(
        BASE, content=json.dumps(product_payload), headers={"Content-Type": "text/plain"}
    )
    assert_error(response, 400, "Request body must be JSON; send header Content-Type: application/json")


def test_create_duplicate_name_returns_409(client, product_payload):
    create(client, product_payload)

    assert_error(create(client, product_payload, name="wireless mouse"), 409)


# ---------- GET one ----------

def test_get_by_id(client, product_payload):
    product_id = create(client, product_payload).json()["id"]

    response = client.get(f"{BASE}/{product_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Wireless Mouse"


def test_get_unknown_id_returns_404(client):
    assert_error(client.get(f"{BASE}/12345"), 404)


def test_get_malformed_id_returns_400(client):
    assert_error(client.get(f"{BASE}/abc"), 400)


# ---------- GET list ----------

def test_list_with_pagination_filter_and_sort(client, product_payload):
    for name, price in [("Pen", 10), ("Laptop", 55000), ("Phone", 20000), ("Tablet", 30000)]:
        create(client, product_payload, name=name, price=price)

    response = client.get(BASE, params={"minPrice": 15000, "sort": "price,asc", "page": 1, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert [p["name"] for p in body["items"]] == ["Phone", "Tablet"]
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["totalItems"] == 3
    assert body["totalPages"] == 2


def test_list_defaults(client):
    body = client.get(BASE).json()

    assert body == {"items": [], "page": 1, "size": 10, "totalItems": 0, "totalPages": 0}


def test_list_size_over_100_returns_400(client):
    assert_error(client.get(BASE, params={"size": 101}), 400)


def test_list_invalid_sort_returns_400(client):
    assert_error(client.get(BASE, params={"sort": "price,up"}), 400)


def test_list_invalid_status_returns_400(client):
    assert_error(client.get(BASE, params={"status": "DELETED"}), 400)


# ---------- PUT ----------

def test_put_replaces_product(client, product_payload):
    product_id = create(client, product_payload).json()["id"]
    replacement = {"name": "Gaming Mouse", "price": 1999, "quantity": 5, "category": "Gaming"}

    response = client.put(f"{BASE}/{product_id}", json=replacement)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gaming Mouse"
    assert body["description"] is None


def test_put_requires_all_fields(client, product_payload):
    product_id = create(client, product_payload).json()["id"]

    assert_error(client.put(f"{BASE}/{product_id}", json={"name": "Only name"}), 400)


def test_put_unknown_id_returns_404(client, product_payload):
    assert_error(client.put(f"{BASE}/999", json=product_payload), 404)


# ---------- PATCH ----------

def test_patch_updates_only_given_fields(client, product_payload):
    product_id = create(client, product_payload).json()["id"]

    response = client.patch(f"{BASE}/{product_id}", json={"status": "INACTIVE"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert body["quantity"] == 25


def test_patch_rejects_null_for_required_field(client, product_payload):
    product_id = create(client, product_payload).json()["id"]

    body = assert_error(client.patch(f"{BASE}/{product_id}", json={"price": None}), 400)
    assert body["details"][0] == {"field": "price", "issue": "must not be null"}


def test_patch_unknown_id_returns_404(client):
    assert_error(client.patch(f"{BASE}/999", json={"quantity": 1}), 404)


# ---------- DELETE ----------

def test_delete_returns_204(client, product_payload):
    product_id = create(client, product_payload).json()["id"]

    response = client.delete(f"{BASE}/{product_id}")

    assert response.status_code == 204
    assert client.get(f"{BASE}/{product_id}").status_code == 404


def test_delete_unknown_id_returns_404(client):
    assert_error(client.delete(f"{BASE}/999"), 404)


# ---------- other ----------

def test_unsupported_method_returns_405(client):
    assert_error(client.delete(BASE), 405)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"
