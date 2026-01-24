import bpy
import os
import sys
import re
import addon_utils
from pathlib import Path

# --- CONFIGURATION ---
DEFAULT_EXPORT_DIR = os.path.join(os.getcwd(), "export_output")
TOLERANCE_STRENGTH = -0.075

# --- 1. SETUP ---
input_file = None
output_dir = DEFAULT_EXPORT_DIR
generate_instructions = False

if "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) >= 1:
        input_file = args[0]
    if len(args) >= 2:
        output_dir = args[1]
    if len(args) >= 3:
        # Check for explicit "true" string, otherwise default to False
        generate_instructions = str(args[2]).lower() == "true"

if not input_file:
    print("ERROR: No input file provided.")
    sys.exit(1)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"--- LDraw2Print CLI ---")
print(f"Processing: {input_file}")
print(f"Generate Instructions: {generate_instructions}")

# --- HELPER FUNCTIONS ---

def parse_ldraw_steps(filepath):
    """Parse LDraw file to extract build steps"""
    steps = []
    current_step = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('0 STEP') or line.startswith('0 ROTSTEP'):
                    if current_step:
                        steps.append(current_step[:])
                        current_step = []
                elif line and line[0] == '1':
                    current_step.append(line)
            if current_step:
                steps.append(current_step)
    except Exception as e:
        print(f"Warning: Could not parse LDraw file for steps: {e}")
        return []
    return steps

def setup_instruction_scene():
    """Setup camera and lighting for LEGO-style rendering"""
    scene = bpy.context.scene
    
    # Render settings: Use Workbench for speed/reliability if others fail
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'MATCAP'
    scene.display.shading.color_type = 'TEXTURE' 
    
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.film_transparent = True
    
    # Camera
    bpy.ops.object.camera_add(location=(25, -25, 20))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 40
    scene.camera = camera

def render_step(step_num, visible_objects, new_objects, output_dir):
    """Render a build step with new parts highlighted"""
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = True
            obj.hide_viewport = True
    
    for obj in visible_objects:
        obj.hide_render = False
        obj.hide_viewport = False
        
        # Highlight logic (Simple selection highlight for Workbench)
        if obj in new_objects:
            obj.select_set(True)
        else:
            obj.select_set(False)
    
    # Frame selection
    if visible_objects:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in visible_objects:
            obj.select_set(True)
        bpy.ops.view3d.camera_to_view_selected()

    output_path = os.path.join(output_dir, f"step_{step_num:03d}.png")
    bpy.context.scene.render.filepath = output_path
    
    try:
        bpy.ops.render.render(write_still=True)
        return output_path
    except Exception as e:
        print(f"    Warning: Render failed for step {step_num}: {e}")
        return None

def generate_instructions_images(input_file, output_dir):
    """Generate step-by-step images"""
    try:
        ext = os.path.splitext(input_file)[1].lower()
        if not ext in [".ldr", ".mpd", ".dat"]:
            print("Instructions only supported for LDraw files.")
            return
            
        print("\n=== GENERATING INSTRUCTION IMAGES ===")
        
        ldraw_steps = parse_ldraw_steps(input_file)
        if not ldraw_steps:
            ldraw_steps = [["all"]]
        
        instructions_dir = os.path.join(output_dir, "instructions")
        os.makedirs(instructions_dir, exist_ok=True)
        
        # Import for rendering
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon_utils.enable("io_scene_importldraw", default_set=True)
        
        bpy.ops.import_scene.importldraw(
            filepath=input_file,
            resPrims='Standard', # Standard is faster for render
            addGaps=True,
            gapWidthMM=0.1,
            look='instructions'
        )
        
        all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        setup_instruction_scene()
        
        cumulative_objects = []
        objects_per_step = max(1, len(all_objects) // len(ldraw_steps))
        
        for step_idx, step_parts in enumerate(ldraw_steps, 1):
            start_idx = (step_idx - 1) * objects_per_step
            end_idx = start_idx + objects_per_step if step_idx < len(ldraw_steps) else len(all_objects)
            
            new_objects = all_objects[start_idx:end_idx]
            cumulative_objects.extend(new_objects)
            
            print(f"  Rendering step {step_idx}/{len(ldraw_steps)}...")
            render_step(step_idx, cumulative_objects, new_objects, instructions_dir)
            
        print(f"✓ Images saved to: {instructions_dir}")
        
    except Exception as e:
        print(f"Error generating instructions: {e}")

# --- 2. EXECUTE INSTRUCTIONS (OPTIONAL) ---
if generate_instructions:
    generate_instructions_images(input_file, output_dir)

# --- 3. IMPORT FOR 3D EXPORT ---
print("\n=== STARTING 3D EXPORT ===")
bpy.ops.wm.read_factory_settings(use_empty=True)

ext = os.path.splitext(input_file)[1].lower()
objects_to_process = []

try:
    if ext in [".ldr", ".mpd", ".dat"]:
        addon_name = "io_scene_importldraw"
        if not addon_utils.check(addon_name)[0]:
            try:
                addon_utils.enable(addon_name, default_set=True)
            except:
                pass

        print("Importing LDraw for 3D export...")
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
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=input_file)
        else:
            bpy.ops.import_scene.obj(filepath=input_file)
        objects_to_process = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# --- 4. EXPORT LOOP ---
print(f"Processing {len(objects_to_process)} objects...")
count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:"<>|]', "_", text)

def normalize_material_name(name):
    if name.endswith("_s"):
        name = name[:-2]
    name = re.sub(r'\.\d+$', '', name)
    return clean_string(name)

for obj in objects_to_process:
    if len(obj.data.vertices) < 3:
        continue

    try:
        # A. Setup Folder
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
        
        # C. STRENGTHEN STUDS
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001) 
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # D. MODIFIERS
        mod_tri = obj.modifiers.new(name="AutoTriangulate", type='TRIANGULATE')
        mod_tri.keep_custom_normals = True
        mod_tri.quad_method = 'BEAUTY'
        
        mod_tol = obj.modifiers.new(name="ToleranceShrink", type='DISPLACE')
        mod_tol.mid_level = 1.0
        mod_tol.strength = TOLERANCE_STRENGTH
        
        bpy.context.view_layer.update()
        
        # E. Export
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
        print(f"  [{count}/{len(objects_to_process)}] Exported: {clean_name}")

    except Exception as e:
        print(f"  FAILED {obj.name}: {e}")

print(f"\n=== JOB COMPLETE ===")
print(f"  3D Files Exported: {count}")
if generate_instructions:
    print(f"  Instructions: Generated in {os.path.join(output_dir, 'instructions')}")
print(f"=====================\n")
sys.exit(0)
