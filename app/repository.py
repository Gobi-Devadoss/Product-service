from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, ProductStatus


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def get_by_name(self, name: str) -> Product | None:
        stmt = select(Product).where(func.lower(Product.name) == name.lower())
        return self.db.scalars(stmt).first()

    def save(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        self.db.delete(product)
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def search(
        self,
        *,
        category: str | None,
        status: ProductStatus | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        order_by,
        offset: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        filters = []
        if category:
            filters.append(func.lower(Product.category) == category.lower())
        if status:
            filters.append(Product.status == status)
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)

        total = self.db.scalar(select(func.count()).select_from(Product).where(*filters))
        stmt = (
            select(Product)
            .where(*filters)
            .order_by(order_by, Product.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt)), total
