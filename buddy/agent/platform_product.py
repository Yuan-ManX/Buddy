"""
Buddy Platform Products System.

Manages AI-native products, services, and capabilities that can be
composed, deployed, and monitored across the Buddy platform.
Provides a product catalog with lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProductStatus(Enum):
    """Status of a platform product."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    MAINTENANCE = "maintenance"


class ProductCategory(Enum):
    """Categories of platform products."""
    AGENT = "agent"
    TOOL = "tool"
    SKILL = "skill"
    WORKFLOW = "workflow"
    TEMPLATE = "template"
    INTEGRATION = "integration"
    PLUGIN = "plugin"
    SERVICE = "service"


@dataclass
class ProductVersion:
    """A version of a product."""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    version: str = "1.0.0"
    changelog: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    active: bool = True


@dataclass
class Product:
    """A platform product definition."""
    product_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: ProductCategory = ProductCategory.AGENT
    status: ProductStatus = ProductStatus.DRAFT
    versions: list[ProductVersion] = field(default_factory=list)
    current_version: str = "1.0.0"
    icon: str = ""
    tags: list[str] = field(default_factory=list)
    author: str = ""
    license: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0
    rating: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ProductCatalog:
    """
    Product catalog for the Buddy platform.

    Manages the full lifecycle of platform products including
    creation, versioning, deployment, and monitoring.
    """

    def __init__(self):
        self._products: dict[str, Product] = {}
        self._usage_stats: dict[str, dict[str, int]] = {}

    # ── Product CRUD ───────────────────────────────────────────────

    def create_product(
        self,
        name: str,
        category: ProductCategory,
        display_name: str = "",
        description: str = "",
        tags: Optional[list[str]] = None,
        **metadata,
    ) -> Product:
        """Create a new product."""
        product = Product(
            name=name,
            display_name=display_name or name,
            description=description,
            category=category,
            tags=tags or [],
            metadata=metadata,
        )
        # Add initial version
        product.versions.append(ProductVersion(version="1.0.0"))
        self._products[product.product_id] = product
        logger.info("Product created: %s (category=%s)", name, category.value)
        return product

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID."""
        return self._products.get(product_id)

    def get_product_by_name(self, name: str) -> Optional[Product]:
        """Get a product by name."""
        for product in self._products.values():
            if product.name == name:
                return product
        return None

    def list_products(
        self,
        category: Optional[ProductCategory] = None,
        status: Optional[ProductStatus] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Product]:
        """List products with optional filtering."""
        products = list(self._products.values())
        if category:
            products = [p for p in products if p.category == category]
        if status:
            products = [p for p in products if p.status == status]
        if tags:
            products = [p for p in products if any(t in p.tags for t in tags)]
        return products

    def update_product(self, product_id: str, **kwargs) -> Optional[Product]:
        """Update a product."""
        product = self._products.get(product_id)
        if not product:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.updated_at = time.time()
        return product

    def delete_product(self, product_id: str) -> bool:
        """Delete a product."""
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

    def activate_product(self, product_id: str) -> bool:
        """Activate a product."""
        product = self._products.get(product_id)
        if product:
            product.status = ProductStatus.ACTIVE
            return True
        return False

    def deprecate_product(self, product_id: str) -> bool:
        """Deprecate a product."""
        product = self._products.get(product_id)
        if product:
            product.status = ProductStatus.DEPRECATED
            return True
        return False

    def archive_product(self, product_id: str) -> bool:
        """Archive a product."""
        product = self._products.get(product_id)
        if product:
            product.status = ProductStatus.ARCHIVED
            return True
        return False

    # ── Version Management ─────────────────────────────────────────

    def add_version(
        self,
        product_id: str,
        version: str,
        changelog: str = "",
        config: Optional[dict[str, Any]] = None,
        dependencies: Optional[dict[str, str]] = None,
    ) -> Optional[ProductVersion]:
        """Add a new version to a product."""
        product = self._products.get(product_id)
        if not product:
            return None

        product_version = ProductVersion(
            version=version,
            changelog=changelog,
            config=config or {},
            dependencies=dependencies or {},
        )
        product.versions.append(product_version)
        product.current_version = version
        product.updated_at = time.time()
        return product_version

    def get_version(self, product_id: str, version: str) -> Optional[ProductVersion]:
        """Get a specific version of a product."""
        product = self._products.get(product_id)
        if not product:
            return None
        for v in product.versions:
            if v.version == version:
                return v
        return None

    def list_versions(self, product_id: str) -> list[ProductVersion]:
        """List all versions of a product."""
        product = self._products.get(product_id)
        return product.versions if product else []

    # ── Usage Tracking ─────────────────────────────────────────────

    def record_usage(self, product_id: str, user_id: str = "anonymous") -> None:
        """Record product usage."""
        product = self._products.get(product_id)
        if product:
            product.usage_count += 1

        if product_id not in self._usage_stats:
            self._usage_stats[product_id] = {}
        self._usage_stats[product_id][user_id] = (
            self._usage_stats[product_id].get(user_id, 0) + 1
        )

    def get_usage_stats(self, product_id: str) -> dict[str, Any]:
        """Get usage statistics for a product."""
        product = self._products.get(product_id)
        if not product:
            return {"error": "Product not found"}

        return {
            "product_id": product_id,
            "total_usage": product.usage_count,
            "unique_users": len(self._usage_stats.get(product_id, {})),
            "usage_by_user": self._usage_stats.get(product_id, {}),
        }

    # ── Product Templates ──────────────────────────────────────────

    @staticmethod
    def create_agent_product_template() -> dict[str, Any]:
        """Create a template for an agent product."""
        return {
            "category": ProductCategory.AGENT,
            "template": {
                "agent_type": "custom",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048,
                "system_prompt": "",
                "tools": [],
                "memory_enabled": True,
                "streaming_enabled": True,
            },
        }

    @staticmethod
    def create_skill_product_template() -> dict[str, Any]:
        """Create a template for a skill product."""
        return {
            "category": ProductCategory.SKILL,
            "template": {
                "skill_type": "custom",
                "trigger_patterns": [],
                "handler": "",
                "parameters": {},
                "requires_approval": False,
                "timeout": 30.0,
            },
        }

    @staticmethod
    def create_workflow_product_template() -> dict[str, Any]:
        """Create a template for a workflow product."""
        return {
            "category": ProductCategory.WORKFLOW,
            "template": {
                "workflow_type": "sequential",
                "steps": [],
                "error_handling": "stop",
                "notifications": False,
                "schedule": None,
            },
        }

    # ── Search & Discovery ─────────────────────────────────────────

    def search_products(
        self,
        query: str,
        category: Optional[ProductCategory] = None,
        limit: int = 20,
    ) -> list[Product]:
        """Search products by name, description, or tags."""
        query_lower = query.lower()
        results = []

        for product in self._products.values():
            if product.status == ProductStatus.ARCHIVED:
                continue
            if category and product.category != category:
                continue

            score = 0
            if query_lower in product.name.lower():
                score += 10
            if query_lower in product.display_name.lower():
                score += 8
            if query_lower in product.description.lower():
                score += 5
            if any(query_lower in tag.lower() for tag in product.tags):
                score += 3

            if score > 0:
                results.append((score, product))

        results.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in results[:limit]]

    def get_featured_products(self, limit: int = 10) -> list[Product]:
        """Get featured products (by usage and rating)."""
        active = self.list_products(status=ProductStatus.ACTIVE)
        featured = sorted(
            active,
            key=lambda p: (p.usage_count * 0.7 + p.rating * 0.3),
            reverse=True,
        )
        return featured[:limit]

    def get_related_products(self, product_id: str, limit: int = 5) -> list[Product]:
        """Get products related to a given product by tags."""
        product = self._products.get(product_id)
        if not product:
            return []

        related = []
        for other in self._products.values():
            if other.product_id == product_id:
                continue
            shared_tags = set(product.tags) & set(other.tags)
            if shared_tags:
                related.append((len(shared_tags), other))

        related.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in related[:limit]]

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get product catalog statistics."""
        return {
            "total_products": len(self._products),
            "active_products": len(self.list_products(status=ProductStatus.ACTIVE)),
            "products_by_category": {
                cat.value: len(self.list_products(category=cat))
                for cat in ProductCategory
            },
            "products_by_status": {
                status.value: len(self.list_products(status=status))
                for status in ProductStatus
            },
            "total_usage": sum(p.usage_count for p in self._products.values()),
            "top_products": [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "category": p.category.value,
                    "usage_count": p.usage_count,
                    "rating": p.rating,
                }
                for p in sorted(
                    self._products.values(),
                    key=lambda x: x.usage_count,
                    reverse=True,
                )[:10]
            ],
        }


# Global product catalog instance
product_catalog = ProductCatalog()