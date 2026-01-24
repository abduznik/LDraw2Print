# LDraw2Print

A streamlined tool to convert LDraw (`.ldr`, `.mpd`) Lego models into 3D printable `.obj` files. It automatically separates parts by color, strengthens studs for printing, and generates step-by-step building instructions.

## Features
- **One-Drag Conversion:** Drag and drop your `.ldr` file onto the executable/script to convert.
- **Diet Blender:** Bundles a stripped-down, lightweight version of Blender 4.5 (~700MB).
- **Auto-Strengthening:** Welds studs to brick bodies to prevent snapping during printing.
- **Smart Organization:** Exports parts into folders named by their color code.
- **Building Instructions:** Optionally generates high-quality PNG images of each building step (and soon PDF manuals!).

## Credits & Licenses
This project relies on:
- **Blender** (GPLv3): https://www.blender.org
- **ImportLDraw** (GPLv2) by TobyLobster: https://github.com/TobyLobster/ImportLDraw

This project is licensed under GPLv3.

## Usage
1. Download the latest release.
2. Drag and drop your `.ldr` file onto `LDraw2Print.bat`.
3. Follow the prompt to generate building instructions (y/n).
4. Find your exported 3D files in `export_output`.
5. **Building Manual:** Open `export_output/instructions/manual.html` in your browser. To save as PDF, press `Ctrl + P` and select "Save as PDF".
