import bpy
import os
import re

# --- SETTINGS ---
export_root = "F:/3D_Prints/Lego_Export_Fixed/"  # <--- Verify this path

if not os.path.exists(export_root):
    os.makedirs(export_root)

print("--- Starting Auto-Triangulate Export ---")

# Ensure Object Mode
if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')

count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text)

for obj in bpy.data.objects:
    # 1. Filter: Must be Mesh and have Geometry
    if obj.type != 'MESH':
        continue
    
    # Check if object actually has vertices (Fixes "No Geometry" error)
    if len(obj.data.vertices) < 3:
        print(f"SKIPPING {obj.name}: Not enough vertices.")
        continue

    try:
        # 2. Setup Folders
        if obj.active_material:
            mat_name = clean_string(obj.active_material.name)
        else:
            mat_name = "No_Color"
            
        color_folder = os.path.join(export_root, mat_name)
        if not os.path.exists(color_folder):
            os.makedirs(color_folder)

        # 3. ISOLATE OBJECT
        bpy.ops.object.select_all(action='DESELECT')
        
        # Force visibility
        obj.hide_viewport = False
        obj.hide_set(False)
        
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # 4. FIX: ADD TRIANGULATE MODIFIER
        # This fixes "Polygons > 4 vertices" error in Bambu Studio
        mod = obj.modifiers.new(name="AutoTriangulate", type='TRIANGULATE')
        mod.keep_custom_normals = True
        mod.quad_method = 'BEAUTY'
        mod.ngon_method = 'BEAUTY'
        
        # Force update so Blender 'sees' the modifier
        bpy.context.view_layer.update()

        # 5. EXPORT
        clean_obj_name = clean_string(obj.name)
        target_file = os.path.join(color_folder, f"{clean_obj_name}.obj")
        
        if hasattr(bpy.ops.wm, "obj_export"):
            # Blender 4.0+
            bpy.ops.wm.obj_export(
                filepath=target_file,
                export_selected_objects=True,
                export_eval_mode='DAG_EVAL_VIEWPORT', # Applies modifiers (Triangulation)
                export_materials=True,
                global_scale=1000.0 
            )
        else:
            # Blender 3.x
            bpy.ops.export_scene.obj(
                filepath=target_file,
                use_selection=True,
                use_mesh_modifiers=True, # Applies modifiers (Triangulation)
                use_materials=True,
                global_scale=1000.0,
                axis_forward='Y',
                axis_up='Z'
            )

        # 6. CLEANUP
        # Remove the modifier so we don't mess up the original scene
        obj.modifiers.remove(mod)
        
        count += 1
        print(f"[{count}] Exported: {clean_obj_name}")

    except Exception as e:
        print(f"!!! FAILED on {obj.name}: {e}")

print(f"--- Complete. Exported {count} parts. ---")