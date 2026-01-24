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
    # This bat file matches your working 'LDraw2Print - Copy (2).bat'
    bat_content = """@echo off
setlocal

set "TARGET=%~1"
if "%TARGET%"=="" (
    echo.
    echo ========================================
    echo    LDraw2Print - LEGO to 3D Printer
    echo ========================================
    echo.
    echo ERROR: No file provided!
    echo.
    echo Usage: Drag and drop an .ldr or .mpd file onto this script
    echo.
    pause
    exit /b
)

echo.
echo ========================================
echo    LDraw2Print - LEGO to 3D Printer
echo ========================================
echo.
echo File: %~nx1
echo.
REM Ask if user wants building instructions
echo Do you want to generate building instructions?
echo (This will create step-by-step images showing how to build the model)
echo.
set /p INSTRUCTIONS="Your choice (y/n): "

set "GENERATE_INST=false"
if /i "%INSTRUCTIONS%"=="y" set "GENERATE_INST=true"
if /i "%INSTRUCTIONS%"=="yes" set "GENERATE_INST=true"

echo.
echo ========================================
echo Starting conversion...
if "%GENERATE_INST%"=="true" (
    echo Instructions: YES
) else (
    echo Instructions: NO
)
echo ========================================
echo.
REM Run the converter
"%~dp0blender\\blender.exe" --background --python "%~dp0converter.py" -- "%TARGET%" "%~dp0export_output" "%GENERATE_INST%"

echo.
echo ========================================
echo    CONVERSION COMPLETE!
echo ========================================
echo.
echo Your files are in: %~dp0export_output
echo.
if "%GENERATE_INST%"=="true" (
    echo Building instructions: export_output\\instructions\\
    echo.
)
echo You can now close this window or press any key to exit.
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