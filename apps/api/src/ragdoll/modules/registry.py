"""Central registry of versioned backend modules."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from fastapi import APIRouter


@dataclass(frozen=True)
class ModuleRegistration:
    """Static registration for one API module."""

    module_name: str
    public_prefix: str
    capability_owner: str
    routes_module: str
    schemas_module: str

    def load_router(self) -> APIRouter:
        module = import_module(self.routes_module)
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            raise TypeError(f"{self.routes_module} does not expose an APIRouter named 'router'.")
        return router

    def import_schemas_module(self) -> None:
        import_module(self.schemas_module)


V1_MODULE_REGISTRY: tuple[ModuleRegistration, ...] = (
    ModuleRegistration(
        module_name="auth",
        public_prefix="/auth",
        capability_owner="modules/auth",
        routes_module="ragdoll.modules.auth.api.routes",
        schemas_module="ragdoll.modules.auth.api.schemas",
    ),
    ModuleRegistration(
        module_name="users",
        public_prefix="/users",
        capability_owner="modules/users",
        routes_module="ragdoll.modules.users.api.routes",
        schemas_module="ragdoll.modules.users.api.schemas",
    ),
    ModuleRegistration(
        module_name="spaces",
        public_prefix="/spaces",
        capability_owner="modules/spaces",
        routes_module="ragdoll.modules.spaces.api.routes",
        schemas_module="ragdoll.modules.spaces.api.schemas",
    ),
    ModuleRegistration(
        module_name="documents",
        public_prefix="/documents",
        capability_owner="modules/documents",
        routes_module="ragdoll.modules.documents.api.routes",
        schemas_module="ragdoll.modules.documents.api.schemas",
    ),
    ModuleRegistration(
        module_name="ingestion",
        public_prefix="/ingestion",
        capability_owner="modules/ingestion",
        routes_module="ragdoll.modules.ingestion.api.routes",
        schemas_module="ragdoll.modules.ingestion.api.schemas",
    ),
    ModuleRegistration(
        module_name="search",
        public_prefix="/search",
        capability_owner="modules/search",
        routes_module="ragdoll.modules.search.api.routes",
        schemas_module="ragdoll.modules.search.api.schemas",
    ),
    ModuleRegistration(
        module_name="chat",
        public_prefix="/chat",
        capability_owner="modules/chat",
        routes_module="ragdoll.modules.chat.api.routes",
        schemas_module="ragdoll.modules.chat.api.schemas",
    ),
    ModuleRegistration(
        module_name="entities",
        public_prefix="/entities",
        capability_owner="modules/entities",
        routes_module="ragdoll.modules.entities.api.routes",
        schemas_module="ragdoll.modules.entities.api.schemas",
    ),
    ModuleRegistration(
        module_name="knowledge_graph",
        public_prefix="/knowledge-graph",
        capability_owner="modules/knowledge_graph",
        routes_module="ragdoll.modules.knowledge_graph.api.routes",
        schemas_module="ragdoll.modules.knowledge_graph.api.schemas",
    ),
    ModuleRegistration(
        module_name="pinned_facts",
        public_prefix="/pinned-facts",
        capability_owner="modules/pinned_facts",
        routes_module="ragdoll.modules.pinned_facts.api.routes",
        schemas_module="ragdoll.modules.pinned_facts.api.schemas",
    ),
    ModuleRegistration(
        module_name="changes",
        public_prefix="/changes",
        capability_owner="modules/changes",
        routes_module="ragdoll.modules.changes.api.routes",
        schemas_module="ragdoll.modules.changes.api.schemas",
    ),
    ModuleRegistration(
        module_name="corrections",
        public_prefix="/corrections",
        capability_owner="modules/corrections",
        routes_module="ragdoll.modules.corrections.api.routes",
        schemas_module="ragdoll.modules.corrections.api.schemas",
    ),
    ModuleRegistration(
        module_name="admin",
        public_prefix="/admin",
        capability_owner="modules/admin",
        routes_module="ragdoll.modules.admin.api.routes",
        schemas_module="ragdoll.modules.admin.api.schemas",
    ),
    ModuleRegistration(
        module_name="usage",
        public_prefix="/usage",
        capability_owner="modules/usage",
        routes_module="ragdoll.modules.usage.api.routes",
        schemas_module="ragdoll.modules.usage.api.schemas",
    ),
)
