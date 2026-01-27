import os
import shutil
import subprocess
import sys
from pathlib import Path

# CONFIG
BUILD_DIR = Path("dist") / "LDraw2Print"
BLENDER_SRC = Path("blender-diet")
ADDON_SRC = Path("blender-diet") / "4.5" / "scripts" / "addons_core" / "io_scene_importldraw"
SCRIPT_SRC = Path("export_cli.py")


def clean_build_dir():
    """Remove existing dist folder and create fresh build directory"""
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def copy_blender():
    """Copy Blender Diet folder to build directory"""
    print("Copying Blender Diet...")
    shutil.copytree(
        BLENDER_SRC,
        BUILD_DIR / "blender",
        dirs_exist_ok=True
    )


def copy_script():
    """Copy export_cli.py script to build directory as converter.py"""
    print("Copying Export Script...")
    shutil.copy(
        SCRIPT_SRC,
        BUILD_DIR / "converter.py"
    )


def create_launcher():
    """Create a Windows launcher BAT file for the application"""
    print("Creating Launcher...")
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
    with (BUILD_DIR / "LDraw2Print.bat").open("w", encoding="utf-8") as f:
        f.write(bat_content)


def main():
    """Main build function"""
    if not BLENDER_SRC.exists():
        print(f"Error: {BLENDER_SRC} not found. Please run the setup first.")
        return

    clean_build_dir()
    copy_blender()
    copy_script()
    create_launcher()

    print(f"Build Complete! Check the '{BUILD_DIR}' folder.")


if __name__ == "__main__":
    main()
