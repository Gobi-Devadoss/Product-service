from decimal import Decimal

import pytest

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import ProductStatus
from app.schemas import ProductPatch, ProductRequest


def make(name="Keyboard", price="1500.00", category="Electronics", **extra):
    return ProductRequest(name=name, price=Decimal(price), quantity=10, category=category, **extra)


def test_create_returns_product_with_defaults(service):
    product = service.create(make())

    assert product.id is not None
    assert product.status == ProductStatus.ACTIVE
    assert product.created_at is not None


def test_create_rejects_duplicate_name_case_insensitive(service):
    service.create(make(name="Keyboard"))

    with pytest.raises(ConflictError):
        service.create(make(name="KEYBOARD"))


def test_get_unknown_id_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(999)


def test_replace_overwrites_all_fields(service):
    created = service.create(make(description="old"))

    updated = service.replace(created.id, make(name="Keyboard Pro", price="2000.00"))

    assert updated.name == "Keyboard Pro"
    assert updated.price == Decimal("2000.00")
    assert updated.description is None


def test_replace_unknown_id_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.replace(999, make())


def test_patch_changes_only_given_fields(service):
    created = service.create(make(description="keep me"))

    patched = service.patch(created.id, ProductPatch(quantity=3))

    assert patched.quantity == 3
    assert patched.description == "keep me"
    assert patched.name == created.name


def test_patch_to_existing_name_conflicts(service):
    service.create(make(name="Mouse"))
    other = service.create(make(name="Monitor"))

    with pytest.raises(ConflictError):
        service.patch(other.id, ProductPatch(name="mouse"))


def test_patch_with_same_name_is_allowed(service):
    created = service.create(make(name="Mouse"))

    assert service.patch(created.id, ProductPatch(name="Mouse")).name == "Mouse"


def test_delete_removes_product(service):
    created = service.create(make())

    service.delete(created.id)

    with pytest.raises(NotFoundError):
        service.get(created.id)


def test_delete_unknown_id_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.delete(999)


def test_list_filters_sorts_and_paginates(service):
    service.create(make(name="Cheap Pen", price="10.00", category="Stationery"))
    service.create(make(name="Laptop", price="55000.00"))
    service.create(make(name="Phone", price="20000.00"))
    service.create(make(name="Tablet", price="30000.00", status=ProductStatus.INACTIVE))

    page = service.list(
        category="electronics", status=ProductStatus.ACTIVE, min_price=Decimal("1000"),
        sort="price,desc", page=1, size=1,
    )

    assert [p.name for p in page.items] == ["Laptop"]
    assert page.total_items == 2
    assert page.total_pages == 2


def test_list_rejects_invalid_sort(service):
    with pytest.raises(BadRequestError):
        service.list(sort="color,asc")


def test_list_rejects_min_price_above_max_price(service):
    with pytest.raises(BadRequestError):
        service.list(min_price=Decimal("100"), max_price=Decimal("10"))
