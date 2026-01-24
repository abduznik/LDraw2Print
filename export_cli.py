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
        generate_instructions = args[2].lower() == "true"

if not input_file:
    print("ERROR: No input file provided.")
    sys.exit(1)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"--- LDraw2Print CLI ---")
print(f"Processing: {input_file}")
print(f"Generate Instructions: {generate_instructions}")

# --- 2. GENERATE LEGO-STYLE INSTRUCTIONS (if requested) ---
def parse_ldraw_steps(filepath):
    """Parse LDraw file to extract build steps"""
    steps = []
    current_step = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                
                # Check for STEP command
                if line.startswith('0 STEP') or line.startswith('0 ROTSTEP'):
                    if current_step:
                        steps.append(current_step[:])
                        current_step = []
                # Part reference (type 1 line)
                elif line and line[0] == '1':
                    current_step.append(line)
            
            # Add final step if exists
            if current_step:
                steps.append(current_step)
    
    except Exception as e:
        print(f"Warning: Could not parse LDraw file for steps: {e}")
        return []
    
    return steps

def generate_instructions_pdf(input_file, output_dir):
    """Generate LEGO-style step-by-step building instructions"""
    try:
        ext = os.path.splitext(input_file)[1].lower()
        if not ext in [".ldr", ".mpd", ".dat"]:
            print("Instructions only supported for LDraw files.")
            return
            
        print("\n========================================")
        print("    GENERATING BUILD INSTRUCTIONS")
        print("========================================\n")
        
        # Parse steps from LDraw file
        ldraw_steps = parse_ldraw_steps(input_file)
        
        if not ldraw_steps:
            print("No STEP commands found in LDraw file. Creating single step...")
            ldraw_steps = [["all"]]  # Single step with everything
        
        print(f"Found {len(ldraw_steps)} build steps in LDraw file")
        
        # Create instructions folder
        instructions_dir = os.path.join(output_dir, "instructions")
        renders_dir = os.path.join(instructions_dir, "renders")
        os.makedirs(renders_dir, exist_ok=True)
        
        # Import model once and track all objects
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon_utils.enable("io_scene_importldraw", default_set=True)
        
        print("Importing complete model...")
        bpy.ops.import_scene.importldraw(
            filepath=input_file,
            resPrims='Standard',
            addGaps=True,
            gapWidthMM=0.1,
            look='instructions'
        )
        
        # Get all imported objects in order
        all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        # Setup scene
        setup_instruction_scene()
        
        # Render each step cumulatively
        rendered_steps = []
        cumulative_objects = []
        
        if len(ldraw_steps) == 1 and ldraw_steps[0] == ["all"]:
            # Single step - show everything
            print(f"  Rendering complete model...")
            img_path = render_step(1, all_objects, [], renders_dir)
            if img_path:
                rendered_steps.append({
                    'step_num': 1,
                    'image': img_path,
                    'new_parts': len(all_objects)
                })
        else:
            # Multiple steps - show cumulative build
            objects_per_step = len(all_objects) // len(ldraw_steps)
            
            for step_idx, step_parts in enumerate(ldraw_steps, 1):
                # Calculate which objects belong to this step
                start_idx = (step_idx - 1) * objects_per_step
                end_idx = start_idx + objects_per_step if step_idx < len(ldraw_steps) else len(all_objects)
                
                new_objects = all_objects[start_idx:end_idx]
                cumulative_objects.extend(new_objects)
                
                print(f"  Rendering step {step_idx}/{len(ldraw_steps)} ({len(new_objects)} new parts)...")
                
                img_path = render_step(step_idx, cumulative_objects, new_objects, renders_dir)
                if img_path:
                    rendered_steps.append({
                        'step_num': step_idx,
                        'image': img_path,
                        'new_parts': len(new_objects)
                    })
        
        # Generate PDF-style HTML
        if rendered_steps:
            html_path = os.path.join(instructions_dir, f"{Path(input_file).stem}_instructions.html")
            create_lego_style_instructions(rendered_steps, html_path, Path(input_file).stem)
            print(f"\n✓ Instructions created: {html_path}")
            print(f"  Total steps: {len(rendered_steps)}")
            print(f"  Open in browser and Print to PDF for best results!")
        
    except Exception as e:
        print(f"Error generating instructions: {e}")
        import traceback
        traceback.print_exc()

def setup_instruction_scene():
    """Setup camera and lighting for LEGO-style rendering"""
    scene = bpy.context.scene
    
    # Render settings
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except:
        try:
            scene.render.engine = 'BLENDER_EEVEE'
        except:
            scene.render.engine = 'BLENDER_WORKBENCH'
    
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.film_transparent = True  # Transparent background like LEGO instructions
    
    # Camera - isometric-like view
    bpy.ops.object.camera_add(location=(25, -25, 20))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)  # 45 degree angle
    camera.data.type = 'ORTHO'  # Orthographic for LEGO style
    camera.data.ortho_scale = 40
    scene.camera = camera
    
    # Lighting - bright and even like LEGO instructions
    bpy.ops.object.light_add(type='SUN', location=(15, -15, 20))
    sun = bpy.context.active_object
    sun.data.energy = 2.5
    sun.rotation_euler = (0.9, 0, 0.6)
    
    # Fill light from opposite side
    bpy.ops.object.light_add(type='SUN', location=(-10, 10, 15))
    fill = bpy.context.active_object
    fill.data.energy = 1.5
    fill.rotation_euler = (1.0, 0, -0.6)
    
    # Background
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value = (1, 1, 1, 1)  # Pure white

def render_step(step_num, visible_objects, new_objects, output_dir):
    """Render a build step with new parts highlighted"""
    # Hide everything
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = True
            obj.hide_viewport = True
    
    # Show cumulative objects
    for obj in visible_objects:
        obj.hide_render = False
        obj.hide_viewport = False
        
        # Highlight new objects with emission (red glow effect)
        if obj in new_objects and obj.active_material:
            # Store original emission
            mat = obj.active_material
            if mat.use_nodes:
                # Add emission to new parts temporarily
                nodes = mat.node_tree.nodes
                emission = nodes.new('ShaderNodeEmission')
                emission.inputs[0].default_value = (1, 0.2, 0.2, 1)  # Red
                emission.inputs[1].default_value = 0.3  # Subtle glow
    
    # Frame all visible objects
    if visible_objects:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in visible_objects:
            obj.select_set(True)
        bpy.ops.view3d.camera_to_view_selected()
    
    # Render
    output_path = os.path.join(output_dir, f"step_{step_num:03d}.png")
    bpy.context.scene.render.filepath = output_path
    
    try:
        bpy.ops.render.render(write_still=True)
        
        # Clean up emission nodes
        for obj in new_objects:
            if obj.active_material and obj.active_material.use_nodes:
                nodes = obj.active_material.node_tree.nodes
                for node in nodes:
                    if node.type == 'EMISSION':
                        nodes.remove(node)
        
        return output_path if os.path.exists(output_path) else None
    except Exception as e:
        print(f"    Warning: Render failed for step {step_num}: {e}")
        return None

def create_lego_style_instructions(steps, output_path, model_name):
    """Create LEGO-style instruction manual as HTML (print to PDF)"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{model_name} - Building Instructions</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            background: white;
        }}
        
        .cover-page {{
            page-break-after: always;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%);
            color: white;
            text-align: center;
            padding: 40px;
        }}
        
        .cover-page h1 {{
            font-size: 48px;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 3px;
        }}
        
        .cover-page .subtitle {{
            font-size: 24px;
            margin-bottom: 40px;
        }}
        
        .cover-page .info {{
            font-size: 18px;
            margin-top: 40px;
            opacity: 0.9;
        }}
        
        .step-page {{
            page-break-after: always;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        
        .step-header {{
            display: flex;
            align-items: center;
            margin-bottom: 30px;
            padding: 15px;
            background: #f0f0f0;
            border-left: 5px solid #FF0000;
        }}
        
        .step-number {{
            font-size: 72px;
            font-weight: bold;
            color: #FF0000;
            margin-right: 20px;
            line-height: 1;
        }}
        
        .step-info {{
            flex: 1;
        }}
        
        .step-info h2 {{
            font-size: 28px;
            margin-bottom: 5px;
        }}
        
        .step-info .parts-count {{
            font-size: 16px;
            color: #666;
        }}
        
        .step-content {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .step-image {{
            max-width: 100%;
            max-height: 700px;
            width: auto;
            height: auto;
            object-fit: contain;
        }}
        
        .parts-list {{
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
        }}
        
        .parts-list h3 {{
            font-size: 18px;
            margin-bottom: 10px;
            color: #FF0000;
        }}
        
        .footer {{
            margin-top: auto;
            padding-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .step-page {{
                page-break-after: always;
            }}
        }}
    </style>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover-page">
        <h1>Building Instructions</h1>
        <div class="subtitle">{model_name}</div>
        <div style="font-size: 64px; margin: 40px 0;">🧱</div>
        <div class="info">
            {len(steps)} Steps
        </div>
    </div>
"""
    
    # Add each step
    for step_data in steps:
        step_num = step_data['step_num']
        img_path = step_data['image']
        new_parts = step_data['new_parts']
        
        rel_path = os.path.relpath(img_path, os.path.dirname(output_path))
        
        html += f"""
    <!-- Step {step_num} -->
    <div class="step-page">
        <div class="step-header">
            <div class="step-number">{step_num}</div>
            <div class="step-info">
                <h2>Step {step_num}</h2>
                <div class="parts-count">{new_parts} piece{'s' if new_parts != 1 else ''} in this step</div>
            </div>
        </div>
        
        <div class="step-content">
            <img src="{rel_path}" alt="Step {step_num}" class="step-image">
        </div>
        
        <div class="footer">
            Step {step_num} of {len(steps)}
        </div>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\nTo create PDF:")
    print(f"  1. Open: {output_path}")
    print(f"  2. Press Ctrl+P (Print)")
    print(f"  3. Select 'Save as PDF'")
    print(f"  4. Done! 🎉")

# Execute instruction generation FIRST if requested
if generate_instructions:
    generate_instructions_pdf(input_file, output_dir)
    print("\nInstruction generation complete. Now starting 3D file export...\n")

# --- 3. IMPORT FOR 3D EXPORT ---
bpy.ops.wm.read_factory_settings(use_empty=True)

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
        print("Detected OBJ file.")
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=input_file)
        else:
            bpy.ops.import_scene.obj(filepath=input_file)
            
        objects_to_process = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# --- 4. EXPORT LOOP ---
print(f"\n========================================")
print("    EXPORTING 3D PRINTABLE FILES")
print("========================================\n")
print(f"Processing {len(objects_to_process)} objects...")

count = 0

def clean_string(text):
    return re.sub(r'[\\/*?:":<>|]', "_", text)

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

print(f"\n========================================")
print(f"    JOB COMPLETE!")
print(f"========================================")
print(f"  3D Files Exported: {count}")
if generate_instructions:
    print(f"  Instructions: Created")
print(f"  Output Location: {output_dir}")
print(f"========================================\n")

sys.exit(0)