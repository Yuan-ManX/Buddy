from __future__ import annotations

"""Agent Cognitive Mapping — spatial/structural mental maps for self-localization.


Lets the agent build spatial and structural mental maps of the environments it
operates in (file systems, workspaces, UI trees, semantic graphs, networks,
knowledge bases). Each map is a graph of places connected by spatial
relations, decorated with anchors the agent uses to localize itself and
navigate.

Capabilities: map lifecycle, place modeling, spatial anchors, typed relation
edges, BFS pathfinding, self-localization (by coordinates or anchor label),
an append-only delta log per map, and aggregate statistics.

Architecture:
    AgentCognitiveMapping (singleton)
    ├── CognitiveMap (per-environment map)
    │   ├── MapPlace (named location with coordinates/properties)
    │   │   └── SpatialAnchor (landmark/region/boundary/portal/node)
    │   ├── MapEdge (typed spatial relation between places)
    │   └── MapDelta (append-only change record)
    └── MappingStats (aggregate engine statistics)
"""

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List


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


def _resolve_enum(enum_cls: type, value: Any) -> Any:
    """Resolve a value to an enum member, accepting name or value strings.

    Enum members are returned unchanged. Strings are matched first against
    member values (e.g. ``"filesystem"``) and then against member names
    (e.g. ``"FILESYSTEM"``), so callers may pass either form. Raises
    ``ValueError`` if neither matches.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
        try:
            return enum_cls[value]
        except KeyError:
            pass
    raise ValueError(f"{value!r} is not a valid {enum_cls.__name__}")


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
            "environment_type": self.environment_type.value
            if isinstance(self.environment_type, EnvironmentType)
            else str(self.environment_type),
            "description": self.description,
            "status": self.status.value
            if isinstance(self.status, MapStatus)
            else str(self.status),
            "places": {
                pid: p.to_dict() if hasattr(p, "to_dict") else dict(p)
                for pid, p in self.places.items()
            },
            "edges": {
                eid: e.to_dict() if hasattr(e, "to_dict") else dict(e)
                for eid, e in self.edges.items()
            },
            "deltas": [
                d.to_dict() if hasattr(d, "to_dict") else dict(d)
                for d in self.deltas
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MappingStats:
    """Aggregate statistics across the entire cognitive mapping engine.

    Computed on demand by ``AgentCognitiveMapping.get_stats``. The
    maps_by_environment dict maps environment type values to the number of
    maps of that type currently registered.
    """
    total_maps: int = 0
    active_maps: int = 0
    total_places: int = 0
    total_edges: int = 0
    total_anchors: int = 0
    total_deltas: int = 0
    maps_by_environment: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a plain dict."""
        return {
            "total_maps": self.total_maps,
            "active_maps": self.active_maps,
            "total_places": self.total_places,
            "total_edges": self.total_edges,
            "total_anchors": self.total_anchors,
            "total_deltas": self.total_deltas,
            "maps_by_environment": dict(self.maps_by_environment),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AgentCognitiveMapping:
    """Cognitive mapping engine with map/place/anchor/edge management.

    Maintains a registry of cognitive maps keyed by map_id. Each map owns its
    own places, edges, anchors, and deltas. All state mutations are guarded
    by a single lock to ensure thread safety.

    The engine supports a full map lifecycle: maps are created in DRAFT
    status, transitioned to ACTIVE when ready for use, and eventually
    ARCHIVED or marked STALE when no longer current. Places within a map are
    connected by typed spatial relation edges and decorated with anchors that
    the agent uses for self-localization.

    Pathfinding uses breadth-first search over the directed edge graph, and
    localization supports both coordinate matching (exact then nearest) and
    anchor-label matching (with landmark/portal priority).
    """

    # Capacity limits to bound memory use per engine instance.
    MAX_MAPS: int = 500
    MAX_PLACES_PER_MAP: int = 2000
    MAX_EDGES_PER_MAP: int = 5000
    MAX_ANCHORS_PER_PLACE: int = 50
    MAX_DELTAS_PER_MAP: int = 5000

    # Localization tuning constants.
    _LOCALIZE_COORD_TOLERANCE: float = 1e-6  # exact match tolerance for coords

    def __init__(self) -> None:
        self._maps: Dict[str, CognitiveMap] = {}
        self._lock = threading.Lock()
        # Internal engine creation time, used for diagnostics. Stored as a
        # monotonic-ish float rather than an ISO string for easy comparison.
        self._created_at: float = time.time()

    # ── Map Management ──────────────────────────────────────────────

    def create_map(
        self,
        agent_id: str,
        name: str,
        environment_type: EnvironmentType,
        description: str = "",
    ) -> CognitiveMap:
        """Create a new cognitive map in DRAFT status and register it.

        ``environment_type`` may be passed as an ``EnvironmentType`` or its
        string name/value. Raises ``RuntimeError`` if the registry is full and
        no STALE/ARCHIVED map can be evicted.
        """
        environment_type = _resolve_enum(EnvironmentType, environment_type)
        with self._lock:
            if len(self._maps) >= self.MAX_MAPS:
                # Evict the oldest STALE or ARCHIVED map if possible.
                evicted = False
                for candidate_id, candidate in list(self._maps.items()):
                    if candidate.status in (MapStatus.STALE, MapStatus.ARCHIVED):
                        del self._maps[candidate_id]
                        evicted = True
                        break
                if not evicted:
                    raise RuntimeError("cognitive map registry is full")
            cmap = CognitiveMap(
                agent_id=agent_id,
                name=name,
                environment_type=environment_type,
                description=description,
                status=MapStatus.DRAFT,
            )
            self._maps[cmap.map_id] = cmap
            return cmap

    def get_map(self, map_id: str) -> Optional[CognitiveMap]:
        """Retrieve a cognitive map by its identifier, or ``None`` if absent."""
        with self._lock:
            return self._maps.get(map_id)

    def list_maps(
        self,
        agent_id: Optional[str] = None,
        environment_type: Optional[EnvironmentType] = None,
    ) -> List[CognitiveMap]:
        """List maps, optionally filtered by ``agent_id`` and/or ``environment_type``.

        Either filter may be passed as the corresponding enum or its string
        value (name or value). Returns an empty list if nothing matches.
        """
        environment_type = (
            _resolve_enum(EnvironmentType, environment_type)
            if environment_type is not None
            else None
        )
        with self._lock:
            results: List[CognitiveMap] = []
            for cmap in self._maps.values():
                if agent_id is not None and cmap.agent_id != agent_id:
                    continue
                if (
                    environment_type is not None
                    and cmap.environment_type != environment_type
                ):
                    continue
                results.append(cmap)
            return results

    def update_map(
        self,
        map_id: str,
        name: Optional[str] = None,
        status: Optional[MapStatus] = None,
    ) -> CognitiveMap:
        """Update the name and/or status of a map.

        ``None`` arguments leave the corresponding field unchanged;
        ``updated_at`` is always refreshed. ``status`` may be passed as a
        ``MapStatus`` or its string name/value. Raises ``KeyError`` if the
        map_id is not registered.
        """
        status = (
            _resolve_enum(MapStatus, status)
            if status is not None
            else None
        )
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                raise KeyError(f"map not found: {map_id}")
            if name is not None:
                cmap.name = name
            if status is not None:
                cmap.status = status
            cmap.updated_at = _now()
            return cmap

    def delete_map(self, map_id: str) -> bool:
        """Delete a map and all of its places/edges/anchors/deltas.

        Returns ``True`` if a map was deleted, ``False`` if no map matched.
        This operation cannot be undone.
        """
        with self._lock:
            if map_id in self._maps:
                del self._maps[map_id]
                return True
            return False

    # ── Place Management ────────────────────────────────────────────

    def add_place(
        self,
        map_id: str,
        name: str,
        place_type: str = "node",
        coordinates: Optional[Dict[str, Any]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> MapPlace:
        """Add a new place to a map.

        ``place_type`` is a free-form string (e.g. "directory", "panel").
        ``coordinates`` and ``properties`` are copied defensively. Raises
        ``KeyError`` if the map is absent or ``RuntimeError`` if the place
        capacity has been reached.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                raise KeyError(f"map not found: {map_id}")
            if len(cmap.places) >= self.MAX_PLACES_PER_MAP:
                raise RuntimeError("place limit reached for map")
            place = MapPlace(
                map_id=map_id,
                name=name,
                place_type=place_type,
                coordinates=dict(coordinates) if coordinates else {},
                properties=dict(properties) if properties else {},
            )
            cmap.places[place.place_id] = place
            cmap.updated_at = _now()
            return place

    def get_place(self, map_id: str, place_id: str) -> Optional[MapPlace]:
        """Retrieve a place within a map, or ``None`` if the map/place is absent."""
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return None
            return cmap.places.get(place_id)

    def list_places(
        self,
        map_id: str,
        place_type: Optional[str] = None,
    ) -> List[MapPlace]:
        """List places in a map, optionally filtered by ``place_type``.

        Returns an empty list if the map is absent or has no matches.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return []
            results: List[MapPlace] = []
            for place in cmap.places.values():
                if place_type is not None and place.place_type != place_type:
                    continue
                results.append(place)
            return results

    # ── Anchor Management ───────────────────────────────────────────

    def add_anchor(
        self,
        map_id: str,
        place_id: str,
        anchor_type: AnchorType,
        label: str,
        salience: float = 0.5,
    ) -> SpatialAnchor:
        """Attach a spatial anchor to a place.

        ``anchor_type`` may be passed as an ``AnchorType`` or its string
        name/value. ``salience`` is clamped to [0, 1]. Raises ``KeyError`` if
        the map or place is absent or ``RuntimeError`` if the anchor capacity
        for the place has been reached.
        """
        anchor_type = _resolve_enum(AnchorType, anchor_type)
        # Clamp salience into [0, 1] so callers cannot skew localization.
        if salience < 0.0:
            salience = 0.0
        elif salience > 1.0:
            salience = 1.0
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                raise KeyError(f"map not found: {map_id}")
            place = cmap.places.get(place_id)
            if place is None:
                raise KeyError(f"place not found: {place_id}")
            if len(place.anchors) >= self.MAX_ANCHORS_PER_PLACE:
                raise RuntimeError("anchor limit reached for place")
            anchor = SpatialAnchor(
                place_id=place_id,
                anchor_type=anchor_type,
                label=label,
                salience=salience,
            )
            place.anchors.append(anchor)
            place.updated_at = _now()
            cmap.updated_at = _now()
            return anchor

    def list_anchors(
        self,
        map_id: str,
        place_id: Optional[str] = None,
    ) -> List[SpatialAnchor]:
        """List anchors in a map.

        If ``place_id`` is given, only anchors attached to that place are
        returned; otherwise anchors across all places in the map are returned.
        Returns an empty list if the map (or place, when specified) is absent.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return []
            results: List[SpatialAnchor] = []
            if place_id is not None:
                place = cmap.places.get(place_id)
                if place is None:
                    return []
                results.extend(place.anchors)
            else:
                for place in cmap.places.values():
                    results.extend(place.anchors)
            return results

    # ── Edge Management ─────────────────────────────────────────────

    def add_edge(
        self,
        map_id: str,
        source_place_id: str,
        target_place_id: str,
        relation: SpatialRelation,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> MapEdge:
        """Add a directed, typed spatial relation edge between two places.

        The edge runs from ``source_place_id`` to ``target_place_id``; both
        must already exist. ``relation`` may be passed as a ``SpatialRelation``
        or its string name/value. ``properties`` is copied defensively. Raises
        ``KeyError`` if the map or either endpoint is absent or
        ``RuntimeError`` if the edge capacity has been reached.
        """
        relation = _resolve_enum(SpatialRelation, relation)
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                raise KeyError(f"map not found: {map_id}")
            if source_place_id not in cmap.places:
                raise KeyError(f"source place not found: {source_place_id}")
            if target_place_id not in cmap.places:
                raise KeyError(f"target place not found: {target_place_id}")
            if len(cmap.edges) >= self.MAX_EDGES_PER_MAP:
                raise RuntimeError("edge limit reached for map")
            edge = MapEdge(
                map_id=map_id,
                source_place_id=source_place_id,
                target_place_id=target_place_id,
                relation=relation,
                weight=weight,
                properties=dict(properties) if properties else {},
            )
            cmap.edges[edge.edge_id] = edge
            cmap.updated_at = _now()
            return edge

    def list_edges(
        self,
        map_id: str,
        source_place_id: Optional[str] = None,
    ) -> List[MapEdge]:
        """List edges in a map, optionally filtered by ``source_place_id``.

        Returns an empty list if the map is absent or has no matches.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return []
            results: List[MapEdge] = []
            for edge in cmap.edges.values():
                if (
                    source_place_id is not None
                    and edge.source_place_id != source_place_id
                ):
                    continue
                results.append(edge)
            return results

    # ── Pathfinding ─────────────────────────────────────────────────

    def find_path(
        self,
        map_id: str,
        source_place_id: str,
        target_place_id: str,
    ) -> List[str]:
        """Find a shortest path between two places using breadth-first search.

        Traverses directed edges from source to target; edge weights are not
        considered. Returns the list of place ids from source to target
        inclusive, ``[source_place_id]`` when source equals target, or an
        empty list if no path exists or the map/endpoints are absent.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return []
            if source_place_id not in cmap.places:
                return []
            if target_place_id not in cmap.places:
                return []
            if source_place_id == target_place_id:
                return [source_place_id]

            # Build adjacency from edges (directed: source -> target). A
            # place may have multiple outgoing edges to different targets.
            adjacency: Dict[str, List[str]] = {}
            for edge in cmap.edges.values():
                adjacency.setdefault(
                    edge.source_place_id, []
                ).append(edge.target_place_id)

            # Breadth-first search. Track visited places and parent pointers
            # so the path can be reconstructed once the target is reached.
            queue: deque = deque([source_place_id])
            visited = {source_place_id}
            parent: Dict[str, Optional[str]] = {source_place_id: None}
            found = False
            while queue:
                current = queue.popleft()
                if current == target_place_id:
                    found = True
                    break
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        parent[neighbor] = current
                        queue.append(neighbor)
            if not found and target_place_id not in visited:
                return []

            # Reconstruct the path by walking parents back to the source.
            path: List[str] = []
            node: Optional[str] = target_place_id
            while node is not None:
                path.append(node)
                node = parent.get(node)
            path.reverse()
            return path

    # ── Self-Localization ───────────────────────────────────────────

    def localize(
        self,
        map_id: str,
        coordinates: Optional[Dict[str, Any]] = None,
        anchor_label: Optional[str] = None,
    ) -> Optional[MapPlace]:
        """Localize the agent within a map.

        Strategies are applied in order:

          1. Coordinate match (if ``coordinates`` given): return the place
             whose coordinates match exactly (within tolerance), else the
             place with the smallest Euclidean distance over shared numeric
             coordinate keys.
          2. Anchor label match (if ``anchor_label`` given): return the place
             with an anchor whose label contains the query
             (case-insensitive). Landmarks take priority, then portals,
             regions, boundaries, nodes; ties break by salience.

        Returns ``None`` if no match is found or the map is absent.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return None

            # Strategy 1: coordinate matching.
            if coordinates:
                target_coords = dict(coordinates)
                exact_match: Optional[MapPlace] = None
                best_distance: Optional[float] = None
                best_place: Optional[MapPlace] = None
                for place in cmap.places.values():
                    if not place.coordinates:
                        continue
                    if self._coords_equal(place.coordinates, target_coords):
                        exact_match = place
                        break
                    dist = self._coord_distance(place.coordinates, target_coords)
                    if dist is None:
                        continue
                    if best_distance is None or dist < best_distance:
                        best_distance = dist
                        best_place = place
                if exact_match is not None:
                    return exact_match
                if best_place is not None:
                    return best_place

            # Strategy 2: anchor label matching.
            if anchor_label:
                needle = anchor_label.lower()
                # Priority order favors landmarks and portals, which are the
                # most useful reference points for self-localization.
                priority = {
                    AnchorType.LANDMARK: 0,
                    AnchorType.PORTAL: 1,
                    AnchorType.REGION: 2,
                    AnchorType.BOUNDARY: 3,
                    AnchorType.NODE: 4,
                }
                best: Optional[MapPlace] = None
                best_priority = 1_000
                best_salience = -1.0
                for place in cmap.places.values():
                    for anchor in place.anchors:
                        if not anchor.label:
                            continue
                        if needle not in anchor.label.lower():
                            continue
                        anchor_priority = priority.get(anchor.anchor_type, 5)
                        if (
                            best is None
                            or anchor_priority < best_priority
                            or (
                                anchor_priority == best_priority
                                and anchor.salience > best_salience
                            )
                        ):
                            best = place
                            best_priority = anchor_priority
                            best_salience = anchor.salience
                if best is not None:
                    return best

            return None

    @staticmethod
    def _coords_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Return ``True`` if two coordinate dicts are numerically equal.

        Two dicts are considered equal when they share the same keys and the
        values for each key match. Numeric values are compared with a small
        tolerance to absorb floating-point noise; non-numeric values must
        match exactly.
        """
        if set(a.keys()) != set(b.keys()):
            return False
        for key in a:
            av = a[key]
            bv = b[key]
            if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                if (
                    abs(float(av) - float(bv))
                    > AgentCognitiveMapping._LOCALIZE_COORD_TOLERANCE
                ):
                    return False
            else:
                if av != bv:
                    return False
        return True

    @staticmethod
    def _coord_distance(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[float]:
        """Return Euclidean distance over shared numeric coordinate keys.

        Only keys present in both dicts with numeric values in both
        contribute to the distance. Returns ``None`` if there are no shared
        numeric keys, in which case the caller should ignore this candidate.
        """
        shared = [
            key for key in a
            if key in b
            and isinstance(a[key], (int, float))
            and isinstance(b[key], (int, float))
        ]
        if not shared:
            return None
        total = 0.0
        for key in shared:
            diff = float(a[key]) - float(b[key])
            total += diff * diff
        return total ** 0.5

    # ── Deltas ──────────────────────────────────────────────────────

    def apply_delta(
        self,
        map_id: str,
        delta_type: DeltaType,
        place_id: Optional[str] = None,
        place_data: Optional[Dict[str, Any]] = None,
    ) -> MapDelta:
        """Apply a typed change to a map and append it to the delta log.

        Semantics:

          - ADD: create a new place from ``place_data`` (``place_id`` ignored;
            the new id is captured in the returned delta).
          - UPDATE: overwrite fields present in ``place_data`` on an existing
            place.
          - REMOVE: delete the place and any edges incident to it.
          - MERGE: merge ``place_data`` into an existing place; coordinates
            and properties are merged dict-wise.

        ``delta_type`` may be passed as a ``DeltaType`` or its string
        name/value; ``place_data`` is copied defensively. Raises ``KeyError``
        if the map (or referenced place, for UPDATE/REMOVE/MERGE) is absent,
        or ``ValueError`` for an unknown delta type.
        """
        delta_type = _resolve_enum(DeltaType, delta_type)
        place_data = dict(place_data) if place_data else {}
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                raise KeyError(f"map not found: {map_id}")
            if len(cmap.deltas) >= self.MAX_DELTAS_PER_MAP:
                # Drop the oldest delta to make room for the new one.
                cmap.deltas.pop(0)
            now = _now()

            if delta_type == DeltaType.ADD:
                # Create a new place from the provided payload.
                name = place_data.get("name", "untitled")
                place_type = place_data.get("place_type", "node")
                coords = place_data.get("coordinates") or {}
                props = place_data.get("properties") or {}
                if len(cmap.places) >= self.MAX_PLACES_PER_MAP:
                    raise RuntimeError("place limit reached for map")
                place = MapPlace(
                    map_id=map_id,
                    name=str(name),
                    place_type=str(place_type),
                    coordinates=dict(coords),
                    properties=dict(props),
                )
                cmap.places[place.place_id] = place
                place_id = place.place_id
            elif delta_type == DeltaType.UPDATE:
                # Overwrite specified fields on an existing place.
                if place_id is None or place_id not in cmap.places:
                    raise KeyError(f"place not found for update: {place_id}")
                place = cmap.places[place_id]
                if "name" in place_data:
                    place.name = str(place_data["name"])
                if "place_type" in place_data:
                    place.place_type = str(place_data["place_type"])
                if "coordinates" in place_data:
                    place.coordinates = dict(place_data["coordinates"] or {})
                if "properties" in place_data:
                    place.properties = dict(place_data["properties"] or {})
                place.updated_at = now
            elif delta_type == DeltaType.REMOVE:
                # Delete the place and any edges incident to it.
                if place_id is None or place_id not in cmap.places:
                    raise KeyError(f"place not found for remove: {place_id}")
                del cmap.places[place_id]
                to_remove = [
                    eid for eid, edge in cmap.edges.items()
                    if edge.source_place_id == place_id
                    or edge.target_place_id == place_id
                ]
                for eid in to_remove:
                    del cmap.edges[eid]
            elif delta_type == DeltaType.MERGE:
                # Merge data into an existing place without replacing whole
                # dicts for coordinates/properties.
                if place_id is None or place_id not in cmap.places:
                    raise KeyError(f"place not found for merge: {place_id}")
                place = cmap.places[place_id]
                if "name" in place_data:
                    place.name = str(place_data["name"])
                if "place_type" in place_data:
                    place.place_type = str(place_data["place_type"])
                if "coordinates" in place_data:
                    merged_coords = dict(place.coordinates)
                    merged_coords.update(place_data["coordinates"] or {})
                    place.coordinates = merged_coords
                if "properties" in place_data:
                    merged_props = dict(place.properties)
                    merged_props.update(place_data["properties"] or {})
                    place.properties = merged_props
                place.updated_at = now
            else:
                raise ValueError(f"unknown delta type: {delta_type}")

            delta = MapDelta(
                map_id=map_id,
                delta_type=delta_type,
                place_id=place_id,
                place_data=place_data,
                applied_at=now,
            )
            cmap.deltas.append(delta)
            cmap.updated_at = now
            return delta

    def list_deltas(self, map_id: str) -> List[MapDelta]:
        """List deltas recorded against a map in application order.

        Returns an empty list if the map is absent or has no deltas.
        """
        with self._lock:
            cmap = self._maps.get(map_id)
            if cmap is None:
                return []
            return list(cmap.deltas)

    # ── Statistics ──────────────────────────────────────────────────

    def get_stats(self) -> MappingStats:
        """Compute aggregate statistics across all registered maps.

        Counts maps (total and active), places, edges, anchors, and deltas,
        and groups maps by environment type. Returns a ``MappingStats``
        snapshot of the current engine state.
        """
        with self._lock:
            total_maps = len(self._maps)
            active_maps = 0
            total_places = 0
            total_edges = 0
            total_anchors = 0
            total_deltas = 0
            maps_by_environment: Dict[str, int] = {}
            for cmap in self._maps.values():
                if cmap.status == MapStatus.ACTIVE:
                    active_maps += 1
                total_places += len(cmap.places)
                total_edges += len(cmap.edges)
                total_deltas += len(cmap.deltas)
                for place in cmap.places.values():
                    total_anchors += len(place.anchors)
                env_key = (
                    cmap.environment_type.value
                    if isinstance(cmap.environment_type, EnvironmentType)
                    else str(cmap.environment_type)
                )
                maps_by_environment[env_key] = (
                    maps_by_environment.get(env_key, 0) + 1
                )
            return MappingStats(
                total_maps=total_maps,
                active_maps=active_maps,
                total_places=total_places,
                total_edges=total_edges,
                total_anchors=total_anchors,
                total_deltas=total_deltas,
                maps_by_environment=maps_by_environment,
            )

    def reset(self) -> None:
        """Clear all registered maps. Intended for testing."""
        with self._lock:
            self._maps.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Singleton Access
# ═══════════════════════════════════════════════════════════════════════════

_engine: Optional[AgentCognitiveMapping] = None
_engine_lock = threading.Lock()


def get_cognitive_mapping_engine() -> AgentCognitiveMapping:
    """Get or create the singleton ``AgentCognitiveMapping`` instance.

    The first call constructs the engine; subsequent calls return the same
    instance. Access is guarded by a module-level lock so the singleton is
    safe to initialize from multiple threads.
    """
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = AgentCognitiveMapping()
        return _engine


def reset_cognitive_mapping_engine() -> None:
    """Reset the singleton ``AgentCognitiveMapping`` instance to ``None``.

    Clears any state held by the current engine (if one exists) and drops
    the reference so the next ``get_cognitive_mapping_engine`` call creates
    a fresh instance. Useful for tests that need a clean engine state.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.reset()
        _engine = None
