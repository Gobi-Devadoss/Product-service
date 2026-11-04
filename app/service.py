import logging
import math
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Product, ProductStatus
from app.repository import ProductRepository
from app.schemas import ProductPage, ProductPatch, ProductRequest, ProductResponse

logger = logging.getLogger("product_service.service")

SORTABLE_FIELDS = {
    "id": Product.id,
    "name": Product.name,
    "price": Product.price,
    "quantity": Product.quantity,
    "createdAt": Product.created_at,
}


class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repo = repository

    def create(self, data: ProductRequest) -> ProductResponse:
        self._ensure_name_is_free(data.name)
        product = self._save(Product(**data.model_dump()))
        logger.info("Created product id=%s", product.id)
        return ProductResponse.model_validate(product)

    def get(self, product_id: int) -> ProductResponse:
        return ProductResponse.model_validate(self._find(product_id))

    def replace(self, product_id: int, data: ProductRequest) -> ProductResponse:
        product = self._find(product_id)
        self._ensure_name_is_free(data.name, exclude_id=product_id)
        for field, value in data.model_dump().items():
            setattr(product, field, value)
        return ProductResponse.model_validate(self._save(product))

    def patch(self, product_id: int, data: ProductPatch) -> ProductResponse:
        product = self._find(product_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes:
            self._ensure_name_is_free(changes["name"], exclude_id=product_id)
        for field, value in changes.items():
            setattr(product, field, value)
        return ProductResponse.model_validate(self._save(product))

    def delete(self, product_id: int) -> None:
        self.repo.delete(self._find(product_id))
        logger.info("Deleted product id=%s", product_id)

    def list(
        self,
        *,
        page: int = 1,
        size: int = 10,
        category: str | None = None,
        status: ProductStatus | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort: str = "id,asc",
    ) -> ProductPage:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise BadRequestError(
                "Validation failed",
                [{"field": "minPrice", "issue": "must not be greater than maxPrice"}],
            )

        items, total = self.repo.search(
            category=category,
            status=status,
            min_price=min_price,
            max_price=max_price,
            order_by=self._parse_sort(sort),
            offset=(page - 1) * size,
            limit=size,
        )
        return ProductPage(
            items=[ProductResponse.model_validate(p) for p in items],
            page=page,
            size=size,
            total_items=total,
            total_pages=math.ceil(total / size),
        )

    # ---- helpers ----

    def _find(self, product_id: int) -> Product:
        product = self.repo.get(product_id)
        if product is None:
            raise NotFoundError(f"Product with id {product_id} not found")
        return product

    def _ensure_name_is_free(self, name: str, exclude_id: int | None = None) -> None:
        existing = self.repo.get_by_name(name)
        if existing and existing.id != exclude_id:
            raise ConflictError(f"A product named '{name}' already exists")

    def _save(self, product: Product) -> Product:
        try:
            return self.repo.save(product)
        except IntegrityError:
            # Safety net if two requests create the same name at the same time
            self.repo.rollback()
            raise ConflictError(f"A product named '{product.name}' already exists")

    @staticmethod
    def _parse_sort(sort: str):
        field, _, direction = sort.partition(",")
        direction = direction.lower() or "asc"
        if field not in SORTABLE_FIELDS or direction not in ("asc", "desc"):
            allowed = ", ".join(SORTABLE_FIELDS)
            raise BadRequestError(
                "Validation failed",
                [{"field": "sort", "issue": f"use <field>,<asc|desc> where field is one of: {allowed}"}],
            )
        column = SORTABLE_FIELDS[field]
        return column.asc() if direction == "asc" else column.desc()
