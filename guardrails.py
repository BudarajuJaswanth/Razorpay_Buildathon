from typing import Dict
from pydantic import BaseModel, field_validator, ValidationError

# Luxury sneaker catalog for KicksVault India
# Prices in INR (Retail = max, Floor = brand margin minimum)
CATALOG: Dict[str, Dict] = {
    "PROD_001": {
        "id": "PROD_001",
        "name": "Air Jordan 1 Retro High OG 'Chicago Lost & Found'",
        "description": "Iconic high-top sneakers with premium leather and the legendary Chicago colorway. Extremely limited release.",
        "retail_price": 24999.0,
        "floor_price": 21500.0,
        "stock": 2,
        "badge": "Limited Drop",
    },
    "PROD_002": {
        "id": "PROD_002",
        "name": "Yeezy Boost 350 V2 'Onyx'",
        "description": "Sleek all-black monochrome silhouette with full-length Boost midsole for unrivaled comfort.",
        "retail_price": 19499.0,
        "floor_price": 17000.0,
        "stock": 4,
        "badge": "Verified Authentic",
    },
    "PROD_003": {
        "id": "PROD_003",
        "name": "Nike Dunk Low Retro 'Panda'",
        "description": "The timeless black-white contrast dunk — a certified collector's staple that never goes out of style.",
        "retail_price": 11999.0,
        "floor_price": 9999.0,
        "stock": 7,
        "badge": "In Stock",
    },
    "PROD_004": {
        "id": "PROD_004",
        "name": "CreaseGuard Pro Care & Sneaker Shield Kit",
        "description": "Premium care kit to protect your kicks from creases and scuffs. Comes with shoe trees and cleaning solution.",
        "retail_price": 1499.0,
        "floor_price": 999.0,
        "stock": 25,
        "badge": "Best Seller",
    },
}


class PaymentProposal(BaseModel):
    product_id: str
    proposed_price: float
    customer_name: str = "Valued Customer"
    customer_phone: str = "9876543210"

    @field_validator("product_id")
    @classmethod
    def product_must_exist(cls, v: str):
        if v not in CATALOG:
            raise ValueError(f"product_id '{v}' does not exist in catalog")
        return v

    def validate_and_compute_final_price(self) -> float:
        """Clamp the proposed price to catalog constraints.

        * If the proposed price is lower than the floor price, return the floor price.
        * If the proposed price is higher than the retail price, return the retail price.
        * Otherwise, return the proposed price unchanged.
        """
        product = CATALOG[self.product_id]
        floor = product["floor_price"]
        retail = product["retail_price"]
        if self.proposed_price < floor:
            return floor
        if self.proposed_price > retail:
            return retail
        return self.proposed_price

    def is_below_floor(self) -> bool:
        """Return True if the proposed price is strictly below the floor price."""
        return self.proposed_price < CATALOG[self.product_id]["floor_price"]


def get_stage1_price(product_id: str) -> float:
    """Stage 1: 4% goodwill discount off retail price."""
    retail = CATALOG[product_id]["retail_price"]
    return round(retail * 0.96, 2)


def get_stage2_price(product_id: str) -> float:
    """Stage 2: arithmetic midpoint between retail and floor price."""
    p = CATALOG[product_id]
    return round((p["retail_price"] + p["floor_price"]) / 2, 2)


def get_catalog_summary() -> str:
    """Return a concise, human-readable summary of the catalog for LLM context."""
    lines = []
    for prod in CATALOG.values():
        lines.append(
            f"{prod['id']}: {prod['name']} — {prod['description']} "
            f"(Retail: ₹{prod['retail_price']:.2f}, Floor: ₹{prod['floor_price']:.2f}, "
            f"Stage-1 Offer: ₹{get_stage1_price(prod['id']):.2f}, "
            f"Stage-2 Offer: ₹{get_stage2_price(prod['id']):.2f}, "
            f"Stock: {prod['stock']})"
        )
    return "\n".join(lines)


def get_product(product_id: str) -> Dict:
    """Retrieve the dictionary representing a single product.
    Raises KeyError if the product does not exist.
    """
    return CATALOG[product_id]
