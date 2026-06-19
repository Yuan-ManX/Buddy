"""
Buddy Product Composer - Application Assembly Engine

Enables agents to compose complete applications from modular components,
including UI layouts, data models, API endpoints, and deployment configs.
Provides a visual product definition system for agent-driven development.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComponentType(str, Enum):
    """Types of application components."""
    UI_PAGE = "ui_page"              # Web page component
    UI_COMPONENT = "ui_component"    # Reusable UI component
    API_ENDPOINT = "api_endpoint"    # Backend API endpoint
    DATA_MODEL = "data_model"        # Data model/schema
    DATABASE = "database"            # Database configuration
    MIDDLEWARE = "middleware"         # Middleware component
    AUTH = "auth"                    # Authentication component
    STORAGE = "storage"              # Storage configuration
    DEPLOYMENT = "deployment"        # Deployment configuration
    WORKFLOW = "workflow"            # Business workflow
    TASK = "task"                    # Background task
    NOTIFICATION = "notification"    # Notification service
    ANALYTICS = "analytics"          # Analytics integration
    CUSTOM = "custom"                # Custom component


class ProductStatus(str, Enum):
    """Status of a product definition."""
    DRAFT = "draft"
    BUILDING = "building"
    REVIEW = "review"
    READY = "ready"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


@dataclass
class ProductComponent:
    """A single component in a product definition."""
    component_id: str
    name: str
    component_type: ComponentType
    description: str = ""
    code: str = ""
    config: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    required: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "type": self.component_type.value,
            "description": self.description,
            "dependencies": self.dependencies,
            "required": self.required,
            "config": self.config,
        }


@dataclass
class ProductDefinition:
    """Complete product definition with components and configuration."""
    product_id: str
    name: str
    description: str
    status: ProductStatus = ProductStatus.DRAFT
    components: list[ProductComponent] = field(default_factory=list)
    agent_id: str = ""
    version: str = "0.1.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def add_component(self, component: ProductComponent):
        """Add a component to the product."""
        self.components.append(component)
        self.updated_at = time.time()

    def remove_component(self, component_id: str):
        """Remove a component from the product."""
        self.components = [c for c in self.components if c.component_id != component_id]
        self.updated_at = time.time()

    def get_component(self, component_id: str) -> ProductComponent | None:
        """Get a component by ID."""
        for c in self.components:
            if c.component_id == component_id:
                return c
        return None

    def get_components_by_type(self, component_type: ComponentType) -> list[ProductComponent]:
        """Get all components of a specific type."""
        return [c for c in self.components if c.component_type == component_type]

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "version": self.version,
            "agent_id": self.agent_id,
            "components": [c.to_dict() for c in self.components],
            "component_count": len(self.components),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ProductComposer:
    """Application assembly engine for agent-driven development.

    Enables agents to compose complete applications from modular
    components, managing the full lifecycle from definition through
    assembly, validation, and deployment readiness.
    """

    def __init__(self):
        self._products: dict[str, ProductDefinition] = {}
        self._templates: dict[str, ProductDefinition] = {}
        self._total_products = 0
        self._register_templates()

    def _register_templates(self):
        """Register product templates."""
        # Web application template
        web_app = ProductDefinition(
            product_id="template-web-app",
            name="Web Application",
            description="Full-stack web application with React frontend and FastAPI backend",
            components=[
                ProductComponent("c1", "Frontend UI", ComponentType.UI_PAGE, "React + TypeScript frontend"),
                ProductComponent("c2", "Backend API", ComponentType.API_ENDPOINT, "FastAPI REST API"),
                ProductComponent("c3", "Database", ComponentType.DATABASE, "SQLite/PostgreSQL database"),
                ProductComponent("c4", "Auth System", ComponentType.AUTH, "JWT-based authentication"),
                ProductComponent("c5", "Deployment", ComponentType.DEPLOYMENT, "Docker deployment config"),
            ],
        )
        self._templates["web-app"] = web_app

        # API service template
        api_service = ProductDefinition(
            product_id="template-api-service",
            name="API Service",
            description="Standalone API service with database and caching",
            components=[
                ProductComponent("c1", "API Layer", ComponentType.API_ENDPOINT, "REST/GraphQL API"),
                ProductComponent("c2", "Database", ComponentType.DATABASE, "Data storage"),
                ProductComponent("c3", "Caching", ComponentType.STORAGE, "Redis cache layer"),
                ProductComponent("c4", "Monitoring", ComponentType.ANALYTICS, "Health checks and metrics"),
            ],
        )
        self._templates["api-service"] = api_service

        # Agent workflow template
        agent_workflow = ProductDefinition(
            product_id="template-agent-workflow",
            name="Agent Workflow",
            description="Multi-step agent workflow with tools and integrations",
            components=[
                ProductComponent("c1", "Agent Core", ComponentType.CUSTOM, "Agent logic and reasoning"),
                ProductComponent("c2", "Tool Set", ComponentType.CUSTOM, "Tool definitions and handlers"),
                ProductComponent("c3", "Workflow", ComponentType.WORKFLOW, "Step-by-step workflow"),
                ProductComponent("c4", "Notifications", ComponentType.NOTIFICATION, "Status updates and alerts"),
            ],
        )
        self._templates["agent-workflow"] = agent_workflow

    def create_product(
        self,
        name: str,
        description: str,
        agent_id: str,
        template_id: str | None = None,
    ) -> ProductDefinition:
        """Create a new product definition."""
        product_id = f"product-{uuid.uuid4().hex[:12]}"

        if template_id and template_id in self._templates:
            template = self._templates[template_id]
            product = ProductDefinition(
                product_id=product_id,
                name=name,
                description=description or template.description,
                agent_id=agent_id,
                components=[ProductComponent(
                    component_id=f"{c.component_id}-{uuid.uuid4().hex[:6]}",
                    name=c.name,
                    component_type=c.component_type,
                    description=c.description,
                    dependencies=c.dependencies.copy(),
                    config=c.config.copy(),
                ) for c in template.components],
            )
        else:
            product = ProductDefinition(
                product_id=product_id,
                name=name,
                description=description,
                agent_id=agent_id,
            )

        self._products[product_id] = product
        self._total_products += 1
        return product

    def get_product(self, product_id: str) -> ProductDefinition | None:
        """Get a product by ID."""
        return self._products.get(product_id)

    def list_products(self) -> list[ProductDefinition]:
        """List all products."""
        return list(self._products.values())

    def list_templates(self) -> list[dict]:
        """List available templates."""
        return [t.to_dict() for t in self._templates.values()]

    def delete_product(self, product_id: str) -> bool:
        """Delete a product definition."""
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

    def get_stats(self) -> dict:
        return {
            "total_products": self._total_products,
            "active_products": len(self._products),
            "templates": len(self._templates),
            "products": [p.to_dict() for p in self._products.values()],
            "template_list": [t.to_dict() for t in self._templates.values()],
        }


# Global product composer instance
_product_composer: ProductComposer | None = None


def get_product_composer() -> ProductComposer:
    """Get or create the global product composer."""
    global _product_composer
    if _product_composer is None:
        _product_composer = ProductComposer()
    return _product_composer