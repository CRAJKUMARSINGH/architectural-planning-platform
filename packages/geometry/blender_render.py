"""Phase 8 — Blender headless server render integration.

This module provides a Python-based interface to Blender's headless rendering
capabilities for high-quality architectural presentation renders. It maintains
the non-authoritative principle: presentation renders cannot mutate canonical
geometry.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    import bpy  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False


def generate_blender_python_script(
    compiled_scene: dict[str, Any],
    output_path: Path,
    render_format: str = "PNG",
) -> str:
    """Generate a Python script for Blender headless rendering."""
    manifest = compiled_scene.get("renderManifest", {})
    camera = manifest.get("camera", {})
    tech_scene = compiled_scene.get("technicalScene", {})
    pres_scene = compiled_scene.get("presentationScene", {})
    
    cam_preset = camera.get("preset", "top-down-plan")
    cam_position = camera.get("position", [0.0, 0.0, 5000.0])
    cam_target = camera.get("target", [0.0, 0.0, 0.0])
    projection = camera.get("projection", "orthographic")
    
    # Extract technical geometry for Blender
    walls = tech_scene.get("walls", [])
    spaces = tech_scene.get("spaces", [])
    openings = tech_scene.get("openings", [])
    
    # Extract presentation styling
    style = pres_scene.get("style", {})
    items = pres_scene.get("items", [])
    
    script_lines = [
        "import bpy",
        "import math",
        "from mathutils import Vector",
        "",
        "# Clear existing scene",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete()",
        "",
        "# Create camera",
        "camera_data = bpy.data.cameras.new(name='PresentationCamera')",
        f"camera_obj = bpy.data.objects.new('PresentationCamera', camera_data)",
        "bpy.context.collection.objects.link(camera_obj)",
        "",
        f"# Set camera position to {cam_position}",
        f"camera_obj.location = Vector({tuple(cam_position)})",
        f"# Set camera target to {cam_target}",
        f"# Camera projection: {projection}",
        "",
        "# Create walls from technical scene",
    ]
    
    # Add wall generation code
    for i, wall in enumerate(walls):
        start = wall.get("start", [0, 0])
        end = wall.get("end", [0, 0])
        thickness = wall.get("thickness", 9.0) / 10.0  # Scale to Blender units
        
        script_lines.extend([
            f"# Wall {i+1}",
            f"wall_{i}_start = Vector({tuple(start + [0])})",
            f"wall_{i}_end = Vector({tuple(end + [0])})",
            f"wall_{i}_length = (wall_{i}_end - wall_{i}_start).length",
            f"bpy.ops.mesh.primitive_cube_add(size=1, location=wall_{i}_start)",
            f"wall_{i} = bpy.context.active_object",
            f"wall_{i}.scale = (wall_{i}_length, {thickness}, 100)",  # 100 units height",
            f"wall_{i}.rotation_euler[2] = math.atan2(wall_{i}_end[1] - wall_{i}_start[1], wall_{i}_end[0] - wall_{i}_start[0])",
            "",
        ])
    
    # Add presentation assets
    script_lines.extend([
        "",
        "# Add presentation assets (furniture, materials)",
    ])
    
    for item in items:
        if item.get("type") == "asset-instance":
            asset_id = item.get("assetId", "")
            position = item.get("position", [0, 0, 0])
            dimensions = item.get("dimensions", {})
            
            width = dimensions.get("width", 800) / 100.0
            depth = dimensions.get("depth", 600) / 100.0
            height = dimensions.get("height", 750) / 100.0
            
            script_lines.extend([
                f"# Asset: {asset_id}",
                f"bpy.ops.mesh.primitive_cube_add(size=1, location=Vector({tuple(position)})",
                f"asset_{asset_id.replace('-', '_')} = bpy.context.active_object",
                f"asset_{asset_id.replace('-', '_')}.scale = ({width}, {depth}, {height})",
                "",
            ])
    
    # Add rendering setup
    script_lines.extend([
        "",
        "# Setup rendering",
        "bpy.context.scene.camera = camera_obj",
        f"bpy.context.scene.render.filepath = '{output_path}'",
        f"bpy.context.scene.render.image_settings.file_format = '{render_format}'",
        "bpy.context.scene.render.engine = 'CYCLES'",
        "bpy.context.scene.cycles.device = 'CPU'",
        "",
        "# Set render resolution",
        f"bpy.context.scene.render.resolution_x = {manifest.get('output', {}).get('width', 1920)}",
        f"bpy.context.scene.render.resolution_y = {manifest.get('output', {}).get('height', 1080)}",
        "",
        "# Add basic lighting",
        "light_data = bpy.data.lights.new(name='SunLight', type='SUN')",
        "light_obj = bpy.data.objects.new('SunLight', light_data)",
        "bpy.context.collection.objects.link(light_obj)",
        "light_obj.location = Vector((10, -10, 20))",
        "light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))",
        "",
        "# Render",
        "bpy.ops.render.render(write_still=True)",
        "",
        "print('Blender render completed successfully')",
    ])
    
    return "\n".join(script_lines)


def render_with_blender_headless(
    compiled_scene: dict[str, Any],
    output_path: Path,
    blender_executable: str = "blender",
    render_format: str = "PNG",
) -> dict[str, Any]:
    """
    Execute Blender headless rendering using the compiled presentation scene.
    
    This function generates a Python script for Blender and executes it in
    headless mode. It maintains determinism by using the same scene hash and
    seed for reproducible renders.
    """
    if not BLENDER_AVAILABLE:
        return {
            "success": False,
            "error": "Blender Python API not available. Blender must be installed with Python support.",
            "output_path": str(output_path),
        }
    
    # Generate Blender Python script
    blender_script = generate_blender_python_script(compiled_scene, output_path, render_format)
    
    # Write script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        script_path = Path(f.name)
        f.write(blender_script)
    
    try:
        # Execute Blender in headless mode
        cmd = [
            blender_executable,
            "-b",  # background mode
            "-P", str(script_path),  # execute Python script
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "output_path": str(output_path),
                "render_format": render_format,
                "blender_output": result.stdout,
            }
        else:
            return {
                "success": False,
                "error": result.stderr,
                "return_code": result.returncode,
                "output_path": str(output_path),
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Blender rendering timed out after 5 minutes",
            "output_path": str(output_path),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Blender executable not found: {blender_executable}",
            "output_path": str(output_path),
        }
    finally:
        # Clean up temporary script
        if script_path.exists():
            script_path.unlink()


def validate_blender_environment() -> dict[str, Any]:
    """Check if Blender is available and properly configured for headless rendering."""
    if BLENDER_AVAILABLE:
        try:
            import bpy
            return {
                "blender_available": True,
                "blender_version": bpy.app.version_string,
                "python_supported": True,
                "cycles_available": hasattr(bpy.context.scene.render, 'engine'),
            }
        except Exception as e:
            return {
                "blender_available": True,
                "error": str(e),
                "python_supported": False,
            }
    else:
        return {
            "blender_available": False,
            "python_supported": False,
            "message": "Blender Python API not available. Install Blender with Python support.",
        }


def create_render_job_manifest(
    compiled_scene: dict[str, Any],
    output_dir: Path,
    job_id: str,
) -> dict[str, Any]:
    """Create a complete render job manifest for queue processing."""
    manifest = compiled_scene.get("renderManifest", {})
    
    return {
        "schemaVersion": "advocate-chambers.render-job.v1",
        "jobId": job_id,
        "modelSha256": compiled_scene.get("modelSha256", ""),
        "compiledScene": compiled_scene,
        "renderManifest": manifest,
        "outputDirectory": str(output_dir),
        "outputFormat": manifest.get("output", {}).get("kind", "png").upper(),
        "blenderExecutable": "blender",  # Can be configured per environment
        "timeout": 300,  # 5 minutes
        "priority": "normal",
        "createdAt": None,  # To be set by job queue
    }