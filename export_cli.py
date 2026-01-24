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
        generate_instructions = str(args[2]).lower() == "true"

if not input_file:
    print("ERROR: No input file provided.")
    sys.exit(1)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"--- LDraw2Print CLI ---")
print(f"Processing: {input_file}")
print(f"Generate Instructions: {generate_instructions}")

# --- 2. HTML MANUAL GENERATION ---

def create_html_manual(steps, output_path, model_name):
    """Create a high-quality LEGO-style HTML manual"""
    html_start = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{model_name} Instructions</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #f0f0f0; }}
        .page {{
            width: 210mm; height: 297mm; 
            padding: 20mm; margin: 10mm auto; 
            background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1);
            page-break-after: always; display: flex; flex-direction: column;
        }}
        .header {{ border-left: 10px solid #e3000b; padding-left: 20px; margin-bottom: 30px; }}
        .step-num {{ font-size: 80px; font-weight: bold; color: #e3000b; line-height: 1; }}
        .img-container {{ flex: 1; display: flex; align-items: center; justify-content: center; }}
        img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
        .cover {{ background: #e3000b; color: white; justify-content: center; text-align: center; display: flex; flex-direction: column; }}
        .cover h1 {{ font-size: 50px; text-transform: uppercase; }}
        @media print {{
            body {{ background: none; }}
            .page {{ margin: 0; box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="page cover">
        <h1>Building Instructions</h1>
        <div style="font-size: 100px; margin: 40px 0;">🧱</div>
        <h2>{model_name}</h2>
        <p>{len(steps)} Steps</p>
    </div>
"""
    html_steps = ""
    for i, step in enumerate(steps, 1):
        rel_path = os.path.relpath(step, os.path.dirname(output_path))
        html_steps += f"""
    <div class="page">
        <div class="header">
            <div class="step-num">{i}</div>
        </div>
        <div class="img-container">
            <img src="{rel_path}">
        </div>
        <div class="footer">Page {i+1} of {len(steps)+1}</div>
    </div>"""
    
    html_end = "</body></html>"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_start + html_steps + html_end)

# --- 3. RENDERING LOGIC ---

def parse_ldraw_steps(filepath):
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
        print(f"Warning: Could not parse steps: {e}")
    return steps

def setup_instruction_scene():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'MATCAP'
    scene.display.shading.color_type = 'TEXTURE' 
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 1500
    scene.render.film_transparent = True
    
    bpy.ops.object.camera_add(location=(25, -25, 20))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 40
    scene.camera = camera

def render_step(step_num, visible_objects, new_objects, output_dir):
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = True
            obj.hide_viewport = True
    
    for obj in visible_objects:
        obj.hide_render = False
        obj.hide_viewport = False
        obj.select_set(obj in new_objects)
    
    if visible_objects:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in visible_objects:
            obj.select_set(True)
        bpy.ops.view3d.camera_to_view_selected()

    output_path = os.path.join(output_dir, f"step_{step_num:03d}.png")
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    return output_path

def generate_instructions_manual(input_file, output_dir):
    try:
        print("\n=== GENERATING INSTRUCTIONS ===")
        ldraw_steps = parse_ldraw_steps(input_file)
        if not ldraw_steps: ldraw_steps = [["all"]]
        
        instructions_dir = os.path.join(output_dir, "instructions")
        renders_dir = os.path.join(instructions_dir, "renders")
        os.makedirs(renders_dir, exist_ok=True)
        
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon_utils.enable("io_scene_importldraw", default_set=True)
        bpy.ops.import_scene.importldraw(filepath=input_file, resPrims='Standard', addGaps=True, look='instructions')
        
        all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        setup_instruction_scene()
        
        step_images = []
        cumulative_objects = []
        obj_idx = 0
        
        for i, step_parts in enumerate(ldraw_steps, 1):
            num_parts_in_step = len(step_parts) if step_parts != ["all"] else len(all_objects)
            new_objects = all_objects[obj_idx : obj_idx + num_parts_in_step]
            obj_idx += num_parts_in_step
            cumulative_objects.extend(new_objects)
            
            print(f"  Rendering step {i}/{len(ldraw_steps)}...")
            img = render_step(i, cumulative_objects, new_objects, renders_dir)
            step_images.append(img)
            
        html_path = os.path.join(instructions_dir, "manual.html")
        create_html_manual(step_images, html_path, Path(input_file).stem)
        print(f"✓ Instructions generated: {html_path}")
        
    except Exception as e:
        print(f"Error: {e}")

# --- 4. MAIN EXECUTION ---

if generate_instructions:
    generate_instructions_manual(input_file, output_dir)

print("\n=== STARTING 3D EXPORT ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(input_file)[1].lower()
objects_to_process = []

try:
    if ext in [".ldr", ".mpd", ".dat"]:
        addon_utils.enable("io_scene_importldraw", default_set=True)
        bpy.ops.import_scene.importldraw(filepath=input_file, resPrims='High', addGaps=True, gapWidthMM=0.1, look='instructions')
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.duplicates_make_real()
        objects_to_process = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"): bpy.ops.wm.obj_import(filepath=input_file)
        else: bpy.ops.import_scene.obj(filepath=input_file)
        objects_to_process = [obj for obj in bpy.data.objects if obj.type == 'MESH']
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

count = 0
def clean_string(text): return re.sub(r'[\\/*?:"<>|]', "_", text)
def normalize_material_name(name):
    if name.endswith("_s"): name = name[:-2]
    return clean_string(re.sub(r'\.\d+$', '', name))

for obj in objects_to_process:
    if len(obj.data.vertices) < 3: continue
    try:
        mat_name = normalize_material_name(obj.active_material.name) if obj.active_material else "Uncolored"
        color_folder = os.path.join(output_dir, mat_name)
        if not os.path.exists(color_folder): os.makedirs(color_folder)
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_viewport = False; obj.hide_set(False); obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001) 
        bpy.ops.object.mode_set(mode='OBJECT')
        mod_tri = obj.modifiers.new(name="Tri", type='TRIANGULATE')
        mod_tol = obj.modifiers.new(name="Tol", type='DISPLACE')
        mod_tol.mid_level = 1.0; mod_tol.strength = TOLERANCE_STRENGTH
        bpy.context.view_layer.update()
        clean_name = clean_string(obj.name)
        final_path = os.path.join(color_folder, f"{clean_name}.obj")
        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(filepath=final_path, export_selected_objects=True, export_eval_mode='DAG_EVAL_VIEWPORT', export_materials=True, global_scale=1000.0)
        else:
            bpy.ops.export_scene.obj(filepath=final_path, use_selection=True, use_mesh_modifiers=True, use_materials=True, global_scale=1000.0)
        count += 1
        print(f"  [{count}] Exported: {clean_name}")
    except Exception as e:
        print(f"  FAILED {obj.name}: {e}")

print(f"\n=== JOB COMPLETE! ===")
sys.exit(0)
