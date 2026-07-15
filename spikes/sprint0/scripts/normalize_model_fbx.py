"""Normalize a Hunyuan model to a target height in metres and verify FBX re-import.

Run with Blender in background mode. Arguments after ``--`` are handled here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--target-height-m", required=True, type=float)
    import sys

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def mesh_objects() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def dimensions(objects: list[bpy.types.Object]) -> Vector:
    low, high = bounds(objects)
    return high - low


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    args = parse_args()
    if args.target_height_m <= 0:
        raise ValueError("target height must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    bpy.ops.import_scene.gltf(filepath=str(args.input))
    imported = mesh_objects()
    if not imported:
        raise RuntimeError("GLB contains no mesh objects")

    before = dimensions(imported)
    if before.z <= 0:
        raise RuntimeError("Imported model has zero Z height")
    scale_factor = args.target_height_m / before.z

    for obj in imported:
        obj.scale *= scale_factor
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    normalized = mesh_objects()
    low, _ = bounds(normalized)
    for obj in normalized:
        obj.location.z -= low.z
    after = dimensions(normalized)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=str(args.output),
        use_selection=True,
        apply_unit_scale=True,
        global_scale=1.0,
    )

    clear_scene()
    bpy.ops.import_scene.fbx(filepath=str(args.output))
    reimported = mesh_objects()
    if not reimported:
        raise RuntimeError("Exported FBX contains no mesh objects after re-import")
    verified = dimensions(reimported)
    tolerance_m = max(0.01, args.target_height_m * 0.001)
    passed = abs(verified.z - args.target_height_m) <= tolerance_m

    report = {
        "input": str(args.input),
        "output": str(args.output),
        "target_height_m": args.target_height_m,
        "source_dimensions": dict(zip(("x", "y", "z"), before)),
        "scale_factor": scale_factor,
        "normalized_dimensions_m": dict(zip(("x", "y", "z"), after)),
        "reimported_dimensions_m": dict(zip(("x", "y", "z"), verified)),
        "mesh_objects": len(reimported),
        "vertices": sum(len(obj.data.vertices) for obj in reimported),
        "polygons": sum(len(obj.data.polygons) for obj in reimported),
        "tolerance_m": tolerance_m,
        "verification_passed": passed,
    }
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not passed:
        raise RuntimeError(f"FBX re-import height verification failed: {verified.z}")


if __name__ == "__main__":
    main()
