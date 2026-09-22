"""Phase 9 — Safe import pipeline with provenance, confidence scoring, and uncertainty boundary.

Governing principle:
  - Every imported object retains sourcePath, sourceId, sourceFormat, sourceHash, confidence, provenance, and reviewRequired.
  - Unknown or low-confidence objects remain uncertain and cannot silently become authoritative geometry.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Mapping

from packages.geometry.serializers import canonical_json, sha256


class ImportProvenanceTracker:
    """Attaches immutable provenance metadata to every imported geometry element."""

    def __init__(
        self,
        *,
        source_format: str,
        source_path: str = "upload://source",
        source_content: bytes | str | None = None,
    ) -> None:
        self.source_format = source_format.lower()
        self.source_path = source_path
        if isinstance(source_content, str):
            self.source_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()
        elif isinstance(source_content, bytes):
            self.source_hash = hashlib.sha256(source_content).hexdigest()
        else:
            self.source_hash = "0" * 64

    def tag_object(
        self,
        obj: dict[str, Any],
        *,
        source_id: str,
        confidence: float = 1.0,
        review_required: bool = False,
    ) -> dict[str, Any]:
        """Tag drawable object with strict provenance and confidence metadata."""
        tagged = dict(obj)
        tagged["source"] = {
            "sourcePath": self.source_path,
            "sourceId": source_id,
            "sourceFormat": self.source_format,
            "sourceHash": self.source_hash,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "provenance": f"imported-from-{self.source_format}",
            "reviewRequired": review_required or (confidence < 0.90),
        }
        return tagged


class ProjectImporter:
    """Safe multi-format importer generating canonical models with provenance."""

    def import_native_json(self, raw_json: str | dict[str, Any], *, source_path: str = "upload://project.json") -> dict[str, Any]:
        """Import native advocate-chambers project JSON."""
        data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        content_bytes = canonical_json(data).encode("utf-8")
        tracker = ImportProvenanceTracker(source_format="native-json", source_path=source_path, source_content=content_bytes)

        walls = [
            tracker.tag_object(w, source_id=w.get("id", f"w-{i}"), confidence=1.0, review_required=False)
            for i, w in enumerate(data.get("walls", []))
        ]
        openings = [
            tracker.tag_object(o, source_id=o.get("id", f"op-{i}"), confidence=1.0, review_required=False)
            for i, o in enumerate(data.get("openings", []))
        ]
        spaces = [
            tracker.tag_object(s, source_id=s.get("id", f"sp-{i}"), confidence=1.0, review_required=False)
            for i, s in enumerate(data.get("spaces", data.get("rooms", [])))
        ]

        return {
            "schemaVersion": "advocate-chambers.project.v2",
            "projectId": data.get("projectId", f"proj-imported-{uuid.uuid4().hex[:8]}"),
            "units": data.get("units", "inch"),
            "levels": data.get("levels", [{"id": "L0", "name": "Ground Floor", "elevation": 0.0}]),
            "walls": walls,
            "openings": openings,
            "spaces": spaces,
            "sourceHash": tracker.source_hash,
            "importSummary": {
                "format": "native-json",
                "wallCount": len(walls),
                "openingCount": len(openings),
                "spaceCount": len(spaces),
                "uncertainObjectCount": 0,
            },
        }

    def import_dxf_entities(
        self,
        entities: list[dict[str, Any]],
        *,
        source_path: str = "upload://drawing.dxf",
        units: str = "inch",
    ) -> dict[str, Any]:
        """Import extracted DXF geometric entities with layer-aware confidence tagging."""
        content_str = json.dumps(entities, sort_keys=True)
        tracker = ImportProvenanceTracker(source_format="dxf", source_path=source_path, source_content=content_str)

        walls: list[dict[str, Any]] = []
        openings: list[dict[str, Any]] = []
        uncertain: list[dict[str, Any]] = []

        for i, ent in enumerate(entities):
            layer = str(ent.get("layer", "")).upper()
            ent_type = str(ent.get("type", "")).upper()
            ent_id = f"dxf-ent-{i+1}"

            if "WALL" in layer and ent_type == "LINE":
                w = {
                    "id": f"w-dxf-{i+1}",
                    "start": ent.get("start", [0.0, 0.0]),
                    "end": ent.get("end", [0.0, 0.0]),
                    "thickness": ent.get("thickness", 9.0),
                    "levelId": "L0",
                }
                walls.append(tracker.tag_object(w, source_id=ent_id, confidence=0.95, review_required=False))
            elif "DOOR" in layer or "OPENING" in layer or "WINDOW" in layer:
                op = {
                    "id": f"op-dxf-{i+1}",
                    "kind": "window" if "WINDOW" in layer else "door",
                    "offset": ent.get("offset", 0.0),
                    "width": ent.get("width", 36.0),
                    "levelId": "L0",
                }
                openings.append(tracker.tag_object(op, source_id=ent_id, confidence=0.90, review_required=False))
            else:
                # Low confidence / unclassified layer
                un = {
                    "id": f"unc-{i+1}",
                    "rawLayer": layer,
                    "rawType": ent_type,
                    "data": ent,
                }
                uncertain.append(tracker.tag_object(un, source_id=ent_id, confidence=0.50, review_required=True))

        return {
            "schemaVersion": "advocate-chambers.project.v2",
            "projectId": f"proj-dxf-{uuid.uuid4().hex[:8]}",
            "units": units,
            "levels": [{"id": "L0", "name": "Ground Floor", "elevation": 0.0}],
            "walls": walls,
            "openings": openings,
            "spaces": [],
            "uncertainEntities": uncertain,
            "sourceHash": tracker.source_hash,
            "importSummary": {
                "format": "dxf",
                "wallCount": len(walls),
                "openingCount": len(openings),
                "spaceCount": 0,
                "uncertainObjectCount": len(uncertain),
                "requiresReview": len(uncertain) > 0,
            },
        }

    def import_raster_assisted(
        self,
        detected_contours: list[dict[str, Any]],
        *,
        source_path: str = "upload://scan.png",
        scale_ratio: float = 1.0,
    ) -> dict[str, Any]:
        """Import raster image contours with assisted recognition confidence tags."""
        content_str = json.dumps(detected_contours, sort_keys=True)
        tracker = ImportProvenanceTracker(source_format="raster-image", source_path=source_path, source_content=content_str)

        walls: list[dict[str, Any]] = []
        for i, c in enumerate(detected_contours):
            conf = float(c.get("confidence", 0.70))
            w = {
                "id": f"w-img-{i+1}",
                "start": [c.get("x1", 0.0) * scale_ratio, c.get("y1", 0.0) * scale_ratio],
                "end": [c.get("x2", 0.0) * scale_ratio, c.get("y2", 0.0) * scale_ratio],
                "thickness": 9.0,
                "levelId": "L0",
            }
            # Raster recognition ALWAYS requires human review before promotion to issue-ready
            walls.append(tracker.tag_object(w, source_id=f"cnt-{i+1}", confidence=conf, review_required=True))

        return {
            "schemaVersion": "advocate-chambers.project.v2",
            "projectId": f"proj-scan-{uuid.uuid4().hex[:8]}",
            "units": "inch",
            "levels": [{"id": "L0", "name": "Ground Floor", "elevation": 0.0}],
            "walls": walls,
            "openings": [],
            "spaces": [],
            "sourceHash": tracker.source_hash,
            "importSummary": {
                "format": "raster-image",
                "wallCount": len(walls),
                "uncertainObjectCount": len(walls),
                "requiresReview": True,
            },
        }
