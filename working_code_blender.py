import bpy
import os
import re

# --- SETTINGS ---
export_root = "F:/3D_Prints/Lego_Export_PrintReady/"  # Changed folder name to avoid mixing files
TOLERANCE_STRENGTH = -0.075  # Shrinks surface by 0.075mm (Total gap 0.15mm). Increase to -0.1 if still too tight.

if not os.path.exists(export_root):
    os.makedirs(export_root)

print(f"--- Starting Export with Tolerance {TOLERANCE_STRENGTH} ---")

if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    
    # Skip empty objects
    if len(obj.data.vertices) < 3:
        continue

    try:
        # 1. Setup Folders
        if obj.active_material:
            mat_name = clean_string(obj.active_material.name)
        else:
            mat_name = "No_Color"
            
        color_folder = os.path.join(export_root, mat_name)
        if not os.path.exists(color_folder):
            os.makedirs(color_folder)

        # 2. Isolate
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # 3. MODIFIER 1: TRIANGULATE (Fixes Bambu Errors)
        mod_tri = obj.modifiers.new(name="AutoTriangulate", type='TRIANGULATE')
        mod_tri.keep_custom_normals = True
        mod_tri.quad_method = 'BEAUTY'
        
        # 4. MODIFIER 2: DISPLACE (Fixes Snapping / Tolerance)
        mod_tol = obj.modifiers.new(name="ToleranceShrink", type='DISPLACE')
        mod_tol.mid_level = 1.0  # Shrink inwards
        mod_tol.strength = TOLERANCE_STRENGTH
        
        # Force update
        bpy.context.view_layer.update()

        # 5. Export
        clean_obj_name = clean_string(obj.name)
        target_file = os.path.join(color_folder, f"{clean_obj_name}.obj")
        
        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(
                filepath=target_file,
                export_selected_objects=True,
                export_eval_mode='DAG_EVAL_VIEWPORT', # Applies the modifiers!
                export_materials=True,
                global_scale=1000.0 
            )
        else:
            bpy.ops.export_scene.obj(
                filepath=target_file,
                use_selection=True,
                use_mesh_modifiers=True,
                use_materials=True,
                global_scale=1000.0,
                axis_forward='Y',
                axis_up='Z'
            )

        # 6. Cleanup Modifiers (So your Blender scene stays normal)
        obj.modifiers.remove(mod_tri)
        obj.modifiers.remove(mod_tol)
        
        count += 1
        print(f"[{count}] Exported: {clean_obj_name}")

    except Exception as e:
        print(f"!!! FAILED on {obj.name}: {e}")

print("--- Export Complete ---")