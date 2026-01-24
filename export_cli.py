import bpy
import os
import sys
import re
import addon_utils

# --- CONFIGURATION ---
DEFAULT_EXPORT_DIR = os.path.join(os.getcwd(), "export_output")
TOLERANCE_STRENGTH = -0.075

# --- 1. SETUP ---
input_file = None
output_dir = DEFAULT_EXPORT_DIR

if "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) >= 1:
        input_file = args[0]
    if len(args) >= 2:
        output_dir = args[1]

if not input_file:
    print("ERROR: No input file provided.")
    sys.exit(1)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"--- BrickForge CLI (LDraw Edition) ---")
print(f"Processing: {input_file}")

# Clear Scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# --- 2. IMPORT LOGIC ---
ext = os.path.splitext(input_file)[1].lower()
objects_to_process = []

try:
    if ext in [".ldr", ".mpd", ".dat"]:
        print("Detected LDraw file. Enabling addon...")
        addon_name = "io_scene_importldraw"
        if not addon_utils.check(addon_name)[0]:
            try:
                addon_utils.enable(addon_name, default_set=True)
            except Exception as e:
                print(f"CRITICAL: Could not enable {addon_name}: {e}")
                sys.exit(1)

        print("Importing LDraw...")
        bpy.ops.import_scene.importldraw(
            filepath=input_file,
            resPrims='High',
            addGaps=True,
            gapWidthMM=0.1,
            look='instructions'
        )
        
        print("Converting LDraw Instances to Real Meshes...")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.duplicates_make_real()
        
        objects_to_process = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        bpy.ops.object.select_all(action='DESELECT')

    elif ext == ".obj":
        print("Detected OBJ file.")
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=input_file)
        else:
            bpy.ops.import_scene.obj(filepath=input_file)
            
        objects_to_process = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# --- 3. EXPORT LOOP ---
print(f"Starting Export Loop for {len(objects_to_process)} objects...")

count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:":<>|]', "_", text)

def normalize_material_name(name):
    # Removes '_s' suffix (specular/smooth variant)
    if name.endswith("_s"):
        name = name[:-2]
    # Removes '.001' suffix (duplicates) using regex
    name = re.sub(r'\.\d+$', '', name)
    return clean_string(name)

for obj in objects_to_process:
    
    if len(obj.data.vertices) < 3:
        continue

    try:
        # A. Setup Folder (With Color Tolerance)
        if obj.active_material:
            mat_name = normalize_material_name(obj.active_material.name)
        else:
            mat_name = "Uncolored"
            
        color_folder = os.path.join(output_dir, mat_name)
        if not os.path.exists(color_folder):
            os.makedirs(color_folder)

        # B. Isolate
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # NEW: STRENGTHEN STUDS (Weld Geometry)
        # 0.0001 threshold (0.1mm if scale is meters) merges touching shells without destroying small parts.
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001) 
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # C. MODIFIERS
        mod_tri = obj.modifiers.new(name="AutoTriangulate", type='TRIANGULATE')
        mod_tri.keep_custom_normals = True
        mod_tri.quad_method = 'BEAUTY'
        
        mod_tol = obj.modifiers.new(name="ToleranceShrink", type='DISPLACE')
        mod_tol.mid_level = 1.0
        mod_tol.strength = TOLERANCE_STRENGTH
        
        # Force update
        bpy.context.view_layer.update()
        
        # D. Export
        clean_name = clean_string(obj.name)
        
        base_name = clean_name
        dup_c = 1
        final_path = os.path.join(color_folder, f"{clean_name}.obj")
        while os.path.exists(final_path):
            clean_name = f"{base_name}_{dup_c}"
            final_path = os.path.join(color_folder, f"{clean_name}.obj")
            dup_c += 1

        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(
                filepath=final_path,
                export_selected_objects=True,
                export_eval_mode='DAG_EVAL_VIEWPORT',
                export_materials=True,
                global_scale=1000.0 
            )
        else:
            bpy.ops.export_scene.obj(
                filepath=final_path,
                use_selection=True,
                use_mesh_modifiers=True,
                use_materials=True,
                global_scale=1000.0,
                axis_forward='Y',
                axis_up='Z'
            )

        obj.modifiers.remove(mod_tri)
        obj.modifiers.remove(mod_tol)
        
        count += 1
        print(f"[{count}] Exported: {clean_name}")

    except Exception as e:
        print(f"FAILED {obj.name}: {e}")

print(f"--- JOB FINISHED. Total Exported: {count} ---")
sys.exit(0)