"""Agent Cognitive Mapping — spatial/structural mental maps for self-localization.

Implements a Cognitive Mapping system that lets the agent build spatial and
structural mental maps of the environments it operates in. Environments may be
file systems, workspaces, UI trees, semantic graphs, networks, or knowledge
bases. Each map is a graph of places connected by spatial relations, decorated
with landmarks and anchors that the agent uses to localize itself and navigate.

Core capabilities:
  - Map Construction: create, update, archive, and delete cognitive maps.
  - Place Modeling: register named places with coordinates and properties.
  - Spatial Anchors: landmark, region, boundary, portal, and node anchors
    attached to places to support localization.
  - Spatial Relations: typed edges (contains, adjacent, nested_in,
    reachable_from, overlaps, part_of) with weights.
  - Pathfinding: breadth-first search between places along edges.
  - Self-Localization: find the current place by coordinates or anchor label.
  - Map Deltas: append-only log of ADD/UPDATE/REMOVE/MERGE changes per map.
  - Statistics: aggregate counts across all maps.

Architecture:
    AgentCognitiveMapping (singleton)
    ├── CognitiveMap (per-environment map)
    │   ├── MapPlace (named location with coordinates/properties)
    │   │   └── SpatialAnchor (landmark/region/boundary/portal/node)
    │   ├── MapEdge (typed spatial relation between places)
    │   └── MapDelta (append-only change record)
    └── MappingStats (aggregate engine statistics)
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class EnvironmentType(str, Enum):
    """Categories of environments the agent can map."""
    FILESYSTEM = "filesystem"          # directory and file trees
    WORKSPACE = "workspace"            # project/workspace layouts
    UI_TREE = "ui_tree"                # user interface element trees
    SEMANTIC_GRAPH = "semantic_graph"  # semantic concept graphs
    NETWORK = "network"                # host/service networks
    KNOWLEDGE_BASE = "knowledge_base"  # curated knowledge stores


class SpatialRelation(str, Enum):
    """Typed spatial/structural relations between two places.

    Relations are directed from the source place to the target place. For
    example, an edge with relation CONTAINS from A to B means "A contains B".
    """
    CONTAINS = "contains"              # source contains target
    ADJACENT = "adjacent"              # source is next to target
    NESTED_IN = "nested_in"            # source is nested within target
    REACHABLE_FROM = "reachable_from"  # source reachable from target
    OVERLAPS = "overlaps"              # source overlaps target
    PART_OF = "part_of"                # source is part of target


class MapStatus(str, Enum):
    """Lifecycle states of a cognitive map."""
    DRAFT = "draft"        # being authored, not yet usable
    ACTIVE = "active"      # in active use
    ARCHIVED = "archived"  # retired but retained for reference
    STALE = "stale"        # suspected out of date, needs refresh


class AnchorType(str, Enum):
    """Roles a spatial anchor can play within a map.

    Anchors decorate places with salient reference markers. Landmarks are
    highly recognizable reference points, regions mark area groupings,
    boundaries mark limits, portals mark transition points, and nodes are
    generic graph nodes.
    """
    LANDMARK = "landmark"  # highly salient reference point
    REGION = "region"      # area grouping
    BOUNDARY = "boundary"  # edge/limit of a region
    PORTAL = "portal"      # entry/exit transition point
    NODE = "node"          # generic graph node


class DeltaType(str, Enum):
    """Types of changes applied to a cognitive map.

    Deltas form an append-only log describing how a map evolved. ADD creates a
    new place, UPDATE overwrites place fields, REMOVE deletes a place and its
    incident edges, and MERGE merges data into an existing place.
    """
    ADD = "add"        # add a new place
    UPDATE = "update"  # update an existing place
    REMOVE = "remove"  # remove a place
    MERGE = "merge"    # merge data into an existing place


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    """Generate a short unique identifier for a map/place/edge/anchor/delta."""
    return str(uuid.uuid4())[:8]


# ═══════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SpatialAnchor:
    """A spatial anchor attached to a place.

    Anchors are salient reference markers the agent uses to orient itself.
    A landmark anchor marks a highly recognizable location, a region anchor
    marks an area grouping, a boundary anchor marks a limit, a portal anchor
    marks a transition point, and a node anchor is a generic graph node. The
    salience value is a float in [0, 1] indicating how strongly the anchor
    draws attention during localization.
    """
    anchor_id: str = field(default_factory=_new_id)
    place_id: str = ""
    anchor_type: AnchorType = AnchorType.NODE
    label: str = ""
    salience: float = 0.5
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this anchor to a plain dict, expanding the enum."""
        return {
            "anchor_id": self.anchor_id,
            "place_id": self.place_id,
            "anchor_type": self.anchor_type.value
            if isinstance(self.anchor_type, AnchorType)
            else str(self.anchor_type),
            "label": self.label,
            "salience": self.salience,
            "created_at": self.created_at,
        }


@dataclass
class MapPlace:
    """A named place within a cognitive map.

    A place has a free-form type string (e.g. "directory", "panel", "host"),
    optional coordinates for geometric localization, arbitrary properties,
    and a list of anchors that decorate it. Coordinates are a dict so callers
    can use whatever coordinate scheme fits the environment (x/y, lat/lon,
    path depth, index, etc.).
    """
    place_id: str = field(default_factory=_new_id)
    map_id: str = ""
    name: str = ""
    place_type: str = "node"
    coordinates: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    anchors: List[SpatialAnchor] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this place to a plain dict, expanding nested anchors."""
        return {
            "place_id": self.place_id,
            "map_id": self.map_id,
            "name": self.name,
            "place_type": self.place_type,
            "coordinates": dict(self.coordinates),
            "properties": dict(self.properties),
            "anchors": [
                a.to_dict() if hasattr(a, "to_dict") else dict(a)
                for a in self.anchors
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MapEdge:
    """A directed, typed spatial relation between two places.

    The relation is directed from source_place_id to target_place_id. The
    weight is a positive float that may be used by pathfinding or ranking.
    """
    edge_id: str = field(default_factory=_new_id)
    map_id: str = ""
    source_place_id: str = ""
    target_place_id: str = ""
    relation: SpatialRelation = SpatialRelation.ADJACENT
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this edge to a plain dict, expanding the enum."""
        return {
            "edge_id": self.edge_id,
            "map_id": self.map_id,
            "source_place_id": self.source_place_id,
            "target_place_id": self.target_place_id,
            "relation": self.relation.value
            if isinstance(self.relation, SpatialRelation)
            else str(self.relation),
            "weight": self.weight,
            "properties": dict(self.properties),
            "created_at": self.created_at,
        }


@dataclass
class MapDelta:
    """An immutable record of a single change applied to a map.

    Deltas form an append-only log per map. The place_id field identifies the
    affected place (None for ADD, since the place is created by the delta).
    The place_data field carries the payload describing the change.
    """
    delta_id: str = field(default_factory=_new_id)
    map_id: str = ""
    delta_type: DeltaType = DeltaType.ADD
    place_id: Optional[str] = None
    place_data: Dict[str, Any] = field(default_factory=dict)
    applied_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this delta to a plain dict, expanding the enum."""
        return {
            "delta_id": self.delta_id,
            "map_id": self.map_id,
            "delta_type": self.delta_type.value
            if isinstance(self.delta_type, DeltaType)
            else str(self.delta_type),
            "place_id": self.place_id,
            "place_data": dict(self.place_data),
            "applied_at": self.applied_at,
        }


@dataclass
class CognitiveMap:
    """A cognitive map of a single environment.

    A map owns a set of places and a set of edges between those places, plus
    an append-only list of deltas describing how the map has changed over
    time. Each map belongs to one agent and describes one environment. The
    status field tracks the map lifecycle (draft, active, archived, stale).
    """
    map_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    name: str = ""
    environment_type: EnvironmentType = EnvironmentType.FILESYSTEM
    description: str = ""
    status: MapStatus = MapStatus.DRAFT
    places: Dict[str, MapPlace] = field(default_factory=dict)
    edges: Dict[str, MapEdge] = field(default_factory=dict)
    deltas: List[MapDelta] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this map to a plain dict, expanding nested dataclasses."""
        return {
            "map_id": self.map_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "environment_type