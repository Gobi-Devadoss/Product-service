"""Controller: HTTP in, HTTP out. All decisions are made in the service."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductStatus
from app.repository import ProductRepository
from app.schemas import ProductPage, ProductPatch, ProductRequest, ProductResponse
from app.service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


def get_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductRequest,
    request: Request,
    response: Response,
    service: ProductService = Depends(get_service),
):
    product = service.create(body)
    response.headers["Location"] = f"{request.url.path}/{product.id}"
    return product


@router.get("", response_model=ProductPage)
def list_products(
    page: int = Query(1, ge=1, description="Page number, starts at 1"),
    size: int = Query(10, ge=1, le=100),
    category: str | None = None,
    status: ProductStatus | None = None,
    min_price: Decimal | None = Query(None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(None, alias="maxPrice", ge=0),
    sort: str = Query("id,asc", description="e.g. price,asc or name,desc"),
    service: ProductService = Depends(get_service),
):
    return service.list(
        page=page,
        size=size,
        category=category,
        status=status,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, service: ProductService = Depends(get_service)):
    return service.get(product_id)


@router.put("/{product_id}", response_model=ProductResponse)
def replace_product(
    product_id: int, body: ProductRequest, service: ProductService = Depends(get_service)
):
    return service.replace(product_id, body)


@router.patch("/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int, body: ProductPatch, service: ProductService = Depends(get_service)
):
    return service.patch(product_id, body)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, service: ProductService = Depends(get_service)):
    service.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
