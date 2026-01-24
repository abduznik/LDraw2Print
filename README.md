# LDraw2Print

A Blender script to automate the process of separating and exporting LEGO models from BrickLink Studio 2 into individual part files, organized by color.

## Workflow

This script is part of a workflow to convert LEGO designs into individual 3D assets:

1.  **Export from Studio 2:** Create your model in [BrickLink Studio 2](https://www.bricklink.com/v3/studio/download.page) and export it as an **LDraw (.ldr/.mpd)** file.
2.  **Import to Blender:** Use the [ImportLDraw](https://github.com/TobyLobster/ImportLDraw) add-on for Blender to import the LDraw file.
    *   **Important:** When importing, ensure you change the **Resolution** to **High Resolution** and set the **Gap (Space)** to around **0.1** to **0.2**. This ensures the parts are high quality and have realistic spacing.
3.  **Separate and Export:** Run the script in `main.py` within Blender's Scripting tab.

## Features

-   Iterates through all mesh objects in the Blender scene.
-   Organizes exported files into subfolders based on their material (color) names.
-   Automatically cleans filenames to remove invalid characters.
-   Applies a global scale (default: 1000) during export to ensure parts are appropriately sized for other 3D applications (e.g., avoiding "object too small" errors in slicers).
-   Supports both Blender 4.0+ (`wm.obj_export`) and older versions (`export_scene.obj`).

## Usage

1.  Open your imported LEGO model in Blender.
2.  Switch to the **Scripting** workspace and open `main.py`.
3.  **Important:** Update the `export_root` variable in the script to your desired output directory:
    ```python
    # CHANGE THIS to your export folder
    export_root = "C:/Path/To/Your/Export/Folder/"
    ```
4.  Run the script.

Each piece will be exported as a `.obj` file in a folder named after its color.
