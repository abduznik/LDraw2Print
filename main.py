import bpy
import os
import re

# --- SETTINGS ---
# CHANGE THIS to your export folder
export_root = "F:/3D_Prints/Lego_Export_Fixed/"

# Create root folder if needed
if not os.path.exists(export_root):
    os.makedirs(export_root)

print("Starting Fixed Export...")

# Deselect everything
if bpy.context.active_object:
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')

count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text)

# Loop through all objects
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        
        # 1. Get Color Name for Folder Sorting
        if obj.active_material:
            mat_name = clean_string(obj.active_material.name)
        else:
            mat_name = "No_Color"
            
        # Create the specific color folder
        color_folder = os.path.join(export_root, mat_name)
        if not os.path.exists(color_folder):
            os.makedirs(color_folder)
            
        # 2. Select Object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # 3. Create Filename
        clean_obj_name = clean_string(obj.name)
        target_file = os.path.join(color_folder, f"{clean_obj_name}.obj")
        
        try:
            # 4. EXPORT with SCALE 1000 (Fixes "Object too small" popup)
            if hasattr(bpy.ops.wm, "obj_export"):
                # Blender 4.0+
                bpy.ops.wm.obj_export(
                    filepath=target_file,
                    export_selected_objects=True,
                    export_materials=True,
                    global_scale=1000.0  # <--- THIS FIXES THE SIZE POPUP
                )
            else:
                # Older Blender
                bpy.ops.export_scene.obj(
                    filepath=target_file,
                    use_selection=True,
                    use_materials=True,
                    global_scale=1000.0, # <--- THIS FIXES THE SIZE POPUP
                    axis_forward='Y',
                    axis_up='Z'
                )

            count += 1
            print(f"Exported: {clean_obj_name}")
            
        except Exception as e:
            print(f"Error on {clean_obj_name}: {e}")
            
        # Deselect
        obj.select_set(False)

print("-" * 30)
print(f"DONE! Exported {count} parts.")
print(f"FILES ARE IN: {export_root}")