import json
import bpy
import os
import sys
import re
import addon_utils
from pathlib import Path
from xhtml2pdf import pisa

# --- CONFIGURATION ---
DEFAULT_EXPORT_DIR = os.path.join(os.getcwd(), "export_output")
TOLERANCE_STRENGTH = -0.075
RENDER_SAMPLES = 8


def _load_config() -> dict:
    cfg_path = Path.cwd() / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"WARN Could not read config.json: ({e}). Using defaults.")
        return {}
    
def _apply_config(cfg: dict) -> None:
    global TOLERANCE_STRENGTH,RENDER_SAMPLES, DEFAULT_EXPORT_DIR

    if isinstance(cfg.get("TOLERANCE_STRENGTH"), (int, float)):
        TOLERANCE_STRENGTH = cfg["TOLERANCE_STRENGTH"]

    if isinstance(cfg.get("RENDER_SAMPLES"), int):
        RENDER_SAMPLES = cfg["RENDER_SAMPLES"]

    val = cfg.get("DEFAULT_EXPORT_DIR")
    if isinstance(cfg.get("DEFAULT_EXPORT_DIR"), str):
        DEFAULT_EXPORT_DIR = cfg["DEFAULT_EXPORT_DIR"]
    
    

_cfg = _load_config()
_apply_config(_cfg)

    


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
        generate_instructions = args[2].lower() == "true"

input_path = Path(input_file)

if not input_path.exists():
    print(f"ERROR: Input file does not exist: {input_path}")
    sys.exit(1)

if not input_path.is_file():
    print(f"ERROR: Input path is not a file: {input_path}")
    sys.exit(1)

try:
    with input_path.open("rb"):
        pass
except OSError as e:
    print(f"ERROR: Unable to open input file: {e}")
    sys.exit(1)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("--- LDraw2Print CLI ---")
print(f"Processing: {input_file}")

# --- 2. GENERATE LEGO-STYLE INSTRUCTIONS ---
def parse_ldraw_steps(filepath):
    steps = []
    current_step = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("0 STEP") or line.startswith("0 ROTSTEP"):
                    if current_step:
                        steps.append(current_step[:])
                        current_step = []
                elif line and line[0] == "1":
                    current_step.append(line)
            if current_step:
                steps.append(current_step)
    except Exception as e:
        print(f"Error parsing LDraw steps: {e}")
        return []
    return steps

def setup_instruction_scene():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.taa_render_samples = RENDER_SAMPLES
    except:
        scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = RENDER_SAMPLES

    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.film_transparent = True

    bpy.ops.object.camera_add(location=(25, -25, 20))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 40
    scene.camera = camera

    bpy.ops.object.light_add(type="SUN", location=(15, -15, 20))
    sun = bpy.context.active_object
    sun.data.energy = 2.5
    sun.rotation_euler = (0.9, 0, 0.6)

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (1, 1, 1, 1)

def render_step(step_num, visible_objects, new_objects, output_dir):
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = True
            obj.hide_viewport = True

    for obj in visible_objects:
        obj.hide_render = False
        obj.hide_viewport = False
        if obj in new_objects and obj.active_material:
            mat = obj.active_material
            if mat.use_nodes:
                nodes = mat.node_tree.nodes
                emission = nodes.new("ShaderNodeEmission")
                emission.inputs[0].default_value = (1, 0.2, 0.2, 1)
                emission.inputs[1].default_value = 0.3

    if visible_objects:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in visible_objects:
            obj.select_set(True)
        bpy.ops.view3d.camera_to_view_selected()

    output_path = os.path.join(output_dir, f"step_{step_num:03d}.png")
    bpy.context.scene.render.filepath = output_path

    try:
        bpy.ops.render.render(write_still=True)
        for obj in new_objects:
            if obj.active_material and obj.active_material.use_nodes:
                nodes = obj.active_material.node_tree.nodes
                for node in list(nodes):
                    if node.type == "EMISSION":
                        nodes.remove(node)
        return output_path if os.path.exists(output_path) else None
    except Exception as e:
        print(f"Error rendering step {step_num}: {e}")
        return None

def create_lego_style_instructions(steps, output_path, model_name):
    last_step_img = os.path.abspath(steps[-1]["image"]) if steps else ""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: A4;
    margin: 0;

    @frame header_frame {{
        -pdf-frame-content: header_content;
        left: 0pt;
        width: 595pt;
        top: 0pt;
        height: 180pt;
    }}

    @frame preview_frame {{
        -pdf-frame-content: preview_content;
        left: 0pt;
        width: 595pt;
        top: 160pt;
        height: 500pt;
    }}

    @frame footer_frame {{
        -pdf-frame-content: footer_content;
        left: 0pt;
        width: 595pt;
        bottom: 0pt;
        height: 110pt;
    }}
}}

@page inner_template {{
    size: A4;
    margin: 1cm;
}}

body {{
    font-family: Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 0;
}}

#header_content {{
    background-color: #D40000;
    color: white;
    text-align: center;
    padding-top: 30pt;
}}

#preview_content {{
    text-align: center;
    padding: 0pt;
    vertical-align: middle;
}}

#footer_content {{
    background-color: #D40000;
    color: white;
    text-align: center;
}}

.red-bar-thick {{
    background-color: #D40000;
    color: white;
    height: 35pt;
    margin-top: 4pt;
    padding: 10pt;
    font-weight: bold;
}}

.step-page {{
    page-break-before: always;
    padding: 10pt;
    font-size: 20pt;
    text-align: center;
}}

.step-header {{
    background: #f8f8f8;
    border-left: 10px solid #D40000;
    padding: 15px;
    text-align: left;
    margin-bottom: 20px;
}}

.step-number {{
    font-size: 50pt;
    font-weight: bold;
    color: #D40000;
    line-height: 1;
}}

.step-image {{
    width: 520px;
    margin: 0 auto;
}}
</style>
</head>

<body>

<div id="header_content">
    <h1 style="font-size: 38pt; margin: 0;">BUILDING<br>INSTRUCTIONS</h1>
    <div style="padding: 10pt; font-size: 22pt; font-weight: bold;">
        {model_name}
    </div>
</div>

<div id="preview_content">
    <img src="{last_step_img}" style="max-width:520pt; max-height:360pt;" />
</div>

<div id="footer_content">
    <div class="red-bar-thick" style="font-size: 18pt;">
        {len(steps)} STEPS
    </div>
    <div class="red-bar-thick" style="font-size: 11pt; height: 25pt;">
        ■ LDraw2Print Automation
    </div>
</div>

<pdf:nexttemplate name="inner_template"/>


"""

    for step_data in steps:
        abs_img_path = os.path.abspath(step_data["image"])
        html_content += f"""
<div class="step-page">
    <div class="step-header">
        <div class="step-number">{step_data["step_num"]}</div>
        <p style="font-size: 20pt; font-weight: bold; margin:0;">Step {step_data["step_num"]}</p>
        <p style="font-size: 20pt; color: #666; margin:0;">+ {step_data["new_parts"]} pieces added</p>
    </div>
    <img src="{abs_img_path}" class="step-image">
    <div style="color: #aaa; margin-top: 20pt;">
        Step {step_data["step_num"]} of {len(steps)}
    </div>
</div>
"""

    html_content += "</body></html>"

    with open(output_path.replace(".html", ".pdf"), "wb") as pdf_file:
        pisa.CreatePDF(html_content, dest=pdf_file)

def generate_instructions_pdf(input_file, output_dir):
    try:
        ext = os.path.splitext(input_file)[1].lower()
        if ext not in [".ldr", ".mpd", ".dat"]:
            return

        ldraw_steps = parse_ldraw_steps(input_file)
        steps_count = len(ldraw_steps) + 4 if ldraw_steps else 1

        instructions_dir = os.path.join(output_dir, "instructions")
        renders_dir = os.path.join(instructions_dir, "renders")
        os.makedirs(renders_dir, exist_ok=True)

        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon_utils.enable("io_scene_importldraw", default_set=True)

        bpy.ops.import_scene.importldraw(
            filepath=input_file,
            resPrims="Standard",
            addGaps=True,
            gapWidthMM=0.1,
            look="instructions",
        )

        all_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        setup_instruction_scene()

        rendered_steps = []
        cumulative_objects = []

        total_parts = len(all_objects)
        parts_per_step = max(1, total_parts // steps_count)

        for step_idx in range(1, steps_count + 1):
            start = (step_idx - 1) * parts_per_step
            end = start + parts_per_step if step_idx < steps_count else total_parts
            new_objects = all_objects[start:end]
            cumulative_objects.extend(new_objects)

            img = render_step(step_idx, cumulative_objects, new_objects, renders_dir)
            if img:
                rendered_steps.append(
                    {
                        "step_num": step_idx,
                        "image": img,
                        "new_parts": len(new_objects),
                    }
                )

        if rendered_steps:
            html_path = os.path.join(
                instructions_dir,
                f"{Path(input_file).stem}_instructions.html",
            )
            create_lego_style_instructions(
                rendered_steps, html_path, Path(input_file).stem
            )

    except Exception as e:
        print(f"Error generating instructions: {e}")

# --- 3. RUN PROCESS ---
if generate_instructions:
    generate_instructions_pdf(input_file, output_dir)

# --- 4. EXPORT 3D FILES ---
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(input_file)[1].lower()
objects_to_process = []

try:
    if ext in [".ldr", ".mpd", ".dat"]:
        addon_utils.enable("io_scene_importldraw", default_set=True)
        bpy.ops.import_scene.importldraw(
            filepath=input_file,
            resPrims="High",
            addGaps=True,
            gapWidthMM=0.1,
            look="instructions",
        )
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.duplicates_make_real()
        objects_to_process = [
            obj for obj in bpy.context.selected_objects if obj.type == "MESH"
        ]
        bpy.ops.object.select_all(action="DESELECT")

    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=input_file)
        else:
            bpy.ops.import_scene.obj(filepath=input_file)
        objects_to_process = [
            obj for obj in bpy.context.selected_objects if obj.type == "MESH"
        ]
except Exception as e:
    print(f"Error importing file: {e}")
    sys.exit(1)

print("\n========================================")
print("    EXPORTING 3D PRINTABLE FILES")
print("========================================\n")

count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:":<>|]', "_", text)

def normalize_material_name(name):
    name = name[:-2] if name.endswith("_s") else name
    return clean_string(re.sub(r"\.\d+$", "", name))

for obj in objects_to_process:
    if len(obj.data.vertices) < 3:
        continue
    try:
        mat_name = (
            normalize_material_name(obj.active_material.name)
            if obj.active_material
            else "Uncolored"
        )
        color_folder = os.path.join(output_dir, mat_name)
        os.makedirs(color_folder, exist_ok=True)

        bpy.ops.object.select_all(action="DESELECT")
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.object.mode_set(mode="OBJECT")

        mod_tri = obj.modifiers.new(name="AutoTriangulate", type="TRIANGULATE")
        mod_tri.keep_custom_normals = True

        mod_tol = obj.modifiers.new(name="ToleranceShrink", type="DISPLACE")
        mod_tol.mid_level = 1.0
        mod_tol.strength = TOLERANCE_STRENGTH

        bpy.context.view_layer.update()

        raw_name = clean_string(obj.name)
        final_path = os.path.join(color_folder, f"{raw_name}.obj")
        dup = 1
        while os.path.exists(final_path):
            final_path = os.path.join(color_folder, f"{raw_name}_{dup}.obj")
            dup += 1

        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(
                filepath=final_path,
                export_selected_objects=True,
                export_eval_mode="DAG_EVAL_VIEWPORT",
                export_materials=True,
                global_scale=1000.0,
            )
        else:
            bpy.ops.export_scene.obj(
                filepath=final_path,
                use_selection=True,
                use_mesh_modifiers=True,
                use_materials=True,
                global_scale=1000.0,
                axis_forward="Y",
                axis_up="Z",
            )

        obj.modifiers.remove(mod_tri)
        obj.modifiers.remove(mod_tol)

        count += 1
        print(f"  [{count}/{len(objects_to_process)}] Exported: {raw_name}")

    except Exception as e:
        print(f"Error processing object {obj.name if 'obj' in locals() else 'unknown'}: {e}")

print("\n========================================")
print("    JOB COMPLETE!")
print("========================================\n")
sys.exit(0)
