from typing import Dict, Optional
from pydantic import BaseModel, field_validator, ValidationError

# Luxury sneaker catalog for KicksVault India
# Prices in INR (Retail = max, Floor = brand margin minimum)
CATALOG: Dict[str, Dict] = {
    "PROD_001": {
        "id": "PROD_001",
        "name": "Air Jordan 1 High OG 'Chicago Lost & Found'",
        "description": "Iconic high-top sneakers with cracked leather detailing and the legendary Chicago colorway. Deadstock release.",
        "retail_price": 24999.0,
        "floor_price": 21500.0,
        "stock": 2,
        "badge": "Limited Drop",
        "image": "https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_002": {
        "id": "PROD_002",
        "name": "Yeezy Boost 350 V2 'Onyx'",
        "description": "Sleek all-black monochrome silhouette with full-length re-engineered Boost cushioning for unrivaled comfort.",
        "retail_price": 19499.0,
        "floor_price": 17000.0,
        "stock": 4,
        "badge": "Verified Authentic",
        "image": "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_003": {
        "id": "PROD_003",
        "name": "Nike Dunk Low Retro 'Panda'",
        "description": "The timeless two-tone monochrome dunk — a certified collector's daily staple that never loses demand.",
        "retail_price": 11999.0,
        "floor_price": 9999.0,
        "stock": 7,
        "badge": "In Stock",
        "image": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_004": {
        "id": "PROD_004",
        "name": "CreaseGuard Pro Care & Sneaker Shield Kit",
        "description": "Premium sneaker care armor including hydro-repellent shield inserts, horsehair brush, and enzymatic cleaning foam.",
        "retail_price": 1499.0,
        "floor_price": 999.0,
        "stock": 25,
        "badge": "Best Seller",
        "image": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_005": {
        "id": "PROD_005",
        "name": "Travis Scott x AJ1 Low 'Reverse Mocha'",
        "description": "The ultimate grail — Sail and Ridgerock nubuck upper with Cactus Jack oversized backward Swoosh and bespoke embroidery.",
        "retail_price": 89999.0,
        "floor_price": 82000.0,
        "stock": 1,
        "badge": "Grail Tier",
        "image": "https://images.unsplash.com/photo-1512374382149-233c42b6a83b?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_006": {
        "id": "PROD_006",
        "name": "New Balance 9060 'Rain Cloud'",
        "description": "Futuristic retro-runner silhouette fusing 990-series heritage with sculpted ABZORB dual-density pods.",
        "retail_price": 16499.0,
        "floor_price": 14200.0,
        "stock": 5,
        "badge": "Essential",
        "image": "https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_007": {
        "id": "PROD_007",
        "name": "Air Jordan 4 Retro 'Military Black'",
        "description": "Clean smooth white leather with neutral grey suede toe-wrap and contrasting black TPU eyelets and heel tab.",
        "retail_price": 34999.0,
        "floor_price": 30500.0,
        "stock": 3,
        "badge": "Vault Heat",
        "image": "https://images.unsplash.com/photo-1575537302964-96cd47c06b1b?auto=format&fit=crop&w=800&q=80",
    },
    "PROD_008": {
        "id": "PROD_008",
        "name": "KicksVault Premium Acrylic Sneaker Crate",
        "description": "Handcrafted display vault with UV-filtering magnetic door and integrated LED spotlighting.",
        "retail_price": 3999.0,
        "floor_price": 2800.0,
        "stock": 15,
        "badge": "Vault Accessory",
        "image": "https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?auto=format&fit=crop&w=800&q=80",
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
    """Round 1: 3% token courtesy discount off retail price."""
    retail = CATALOG[product_id]["retail_price"]
    return round(retail * 0.97, 2)


def get_stage2_price(product_id: str) -> float:
    """Round 2 (Persistent Buyer): Counter-offer halfway down to the floor price."""
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


def add_product_to_catalog(
    product_id: str,
    name: str,
    description: str,
    retail_price: float,
    floor_price: float,
    stock: int = 1,
    badge: str = "Verified Authentic",
    image: Optional[str] = None
) -> Dict:
    """Dynamically add or update a product in the live catalog."""
    CATALOG[product_id] = {
        "id": product_id,
        "name": name,
        "description": description,
        "retail_price": float(retail_price),
        "floor_price": float(floor_price),
        "stock": max(0, int(stock)),
        "badge": badge,
        "image": image or "https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80"
    }
    return CATALOG[product_id]


def update_product_stock(product_id: str, new_stock: int) -> Dict:
    """Update stock quantity for an existing product."""
    if product_id not in CATALOG:
        raise KeyError(f"Product {product_id} not found in catalog")
    CATALOG[product_id]["stock"] = max(0, int(new_stock))
    return CATALOG[product_id]
