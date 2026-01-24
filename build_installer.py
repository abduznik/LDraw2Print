import os
import shutil
import subprocess
import sys

# CONFIG
BUILD_DIR = "dist/LDraw2Print"
BLENDER_SRC = "blender-diet"
ADDON_SRC = "blender-diet/4.5/scripts/addons_core/io_scene_importldraw"
SCRIPT_SRC = "export_cli.py"

def clean_build_dir():
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    os.makedirs(BUILD_DIR)

def copy_blender():
    print("Copying Blender Diet...")
    shutil.copytree(BLENDER_SRC, os.path.join(BUILD_DIR, "blender"), dirs_exist_ok=True)

def copy_script():
    print("Copying Export Script...")
    shutil.copy(SCRIPT_SRC, os.path.join(BUILD_DIR, "converter.py"))

def create_launcher():
    print("Creating Launcher...")
    # A bat file that accepts a file drop
    bat_content = """@echo off
setlocal
set "TARGET=%~1"
if "%TARGET%"=="" (
    echo Drag and drop an .ldr file onto this script!
    pause
    exit /b
)

echo Processing: %TARGET%
"%~dp0blender\\blender.exe" --background --python "%~dp0converter.py" -- "%TARGET%" "%~dp0export_output"

echo Done! Output is in the export_output folder.
pause
"""
    with open(os.path.join(BUILD_DIR, "LDraw2Print.bat"), "w") as f:
        f.write(bat_content)

def main():
    if not os.path.exists(BLENDER_SRC):
        print(f"Error: {BLENDER_SRC} not found. Please run the setup first.")
        return

    clean_build_dir()
    copy_blender()
    copy_script()
    create_launcher()
    
    print(f"Build Complete! Check the '{BUILD_DIR}' folder.")

if __name__ == "__main__":
    main()
