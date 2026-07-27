"""Safely switch the visible Blender session to the private Nakaniwa R6 LOD0."""

from datetime import datetime
from pathlib import Path

import bpy


R6_ROOT = Path(
    "/private/tmp/hibana-blender/a21-nakaniwa-production-art-r6"
)
R6_BLEND = R6_ROOT / "assets/nakaniwa-a21-lod0.blend"
R6_RENDER = R6_ROOT / "views/00_eye165_dualhero.png"
BACKUP_ROOT = Path(
    "/private/tmp/hibana-blender/visible-session-backups"
)
CAMERA_NAME = "CAM_Nakaniwa_A21_Eye165_DualHero"

if not R6_BLEND.is_file():
    raise FileNotFoundError(f"R6 LOD0 blend is missing: {R6_BLEND}")

current_scene = bpy.context.scene
previous = {
    "filepath": bpy.data.filepath,
    "scene": current_scene.name,
    "objects": len(current_scene.objects),
    "collections": sorted(
        collection.name for collection in bpy.data.collections
    ),
}

BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
backup_path = BACKUP_ROOT / (
    "visible-session-before-nakaniwa-r6-"
    + datetime.now().strftime("%Y%m%d-%H%M%S")
    + ".blend"
)
bpy.ops.wm.save_as_mainfile(
    filepath=str(backup_path),
    copy=True,
    check_existing=False,
)

bpy.ops.wm.open_mainfile(filepath=str(R6_BLEND))
scene = bpy.context.scene
camera = bpy.data.objects.get(CAMERA_NAME)
if camera is None or camera.type != "CAMERA":
    raise RuntimeError(f"R6 camera is missing: {CAMERA_NAME}")
scene.camera = camera

render_image = None
if R6_RENDER.is_file():
    render_image = bpy.data.images.get(R6_RENDER.name)
    if render_image is None:
        render_image = bpy.data.images.load(
            str(R6_RENDER),
            check_existing=True,
        )

view_areas = 0
image_areas = 0
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == "VIEW_3D":
            view_areas += 1
            space = area.spaces.active
            space.region_3d.view_perspective = "CAMERA"
            space.shading.type = "RENDERED"
            space.shading.use_scene_lights = True
            space.shading.use_scene_world = True
        elif area.type == "IMAGE_EDITOR" and render_image is not None:
            image_areas += 1
            area.spaces.active.image = render_image

bpy.context.view_layer.objects.active = camera
camera.select_set(True)

__result__ = {
    "previous": previous,
    "backup": str(backup_path),
    "opened": bpy.data.filepath,
    "scene": scene.name,
    "objects": len(scene.objects),
    "camera": scene.camera.name,
    "view3dAreas": view_areas,
    "imageEditorAreas": image_areas,
    "renderImage": str(R6_RENDER) if render_image is not None else None,
}
