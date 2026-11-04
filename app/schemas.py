from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.alias_generators import to_camel

from app.models import ProductStatus

Name = Annotated[str, Field(min_length=2, max_length=100)]
Description = Annotated[str, Field(max_length=500)]
Price = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Quantity = Annotated[int, Field(ge=0, strict=True)]
Category = Annotated[str, Field(min_length=2, max_length=50)]

# Text is trimmed before length checks; unknown fields (id, createdAt, ...) are ignored.
REQUEST_CONFIG = ConfigDict(str_strip_whitespace=True, extra="ignore")


class ProductRequest(BaseModel):

    # The example gives Swagger "Try it out" a valid body (its generated default has price 0)
    model_config = REQUEST_CONFIG | ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Wireless Mouse",
                    "description": "2.4 GHz ergonomic mouse",
                    "price": 799.50,
                    "quantity": 25,
                    "category": "Electronics",
                    "status": "ACTIVE",
                }
            ]
        }
    )

    name: Name
    description: Description | None = None
    price: Price
    quantity: Quantity
    category: Category
    status: ProductStatus = ProductStatus.ACTIVE


class ProductPatch(BaseModel):

    model_config = REQUEST_CONFIG | ConfigDict(json_schema_extra={"examples": [{"quantity": 5}]})

    name: Name | None = None
    description: Description | None = None
    price: Price | None = None
    quantity: Quantity | None = None
    category: Category | None = None
    status: ProductStatus | None = None

    @field_validator("name", "price", "quantity", "category", "status")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("must not be null")
        return value


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ProductResponse(CamelModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    quantity: int
    category: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("price")
    def serialize_price(self, price: Decimal) -> float:
        return float(price)

    @field_serializer("created_at", "updated_at")
    def serialize_time(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc, microsecond=0).isoformat().replace("+00:00", "Z")


class ProductPage(CamelModel):
    items: list[ProductResponse]
    page: int
    size: int
    total_items: int
    total_pages: int
