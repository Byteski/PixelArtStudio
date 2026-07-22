# Pixel Art Studio

A compact offline desktop utility that converts ordinary images into crisp pixel art.

## Current features

- Drag-and-drop image loading
- True low-resolution pixel canvas
- Automatic color-palette reduction
- Floyd–Steinberg dithering or clean no-dither mode
- Adjustable detail, contrast, saturation, and edge ink
- Isolated-pixel cleanup
- Five starting presets
- Sharp nearest-neighbor PNG export at 1× to 16×
- Command-line converter included

## Windows setup

1. Install Python 3.10 or newer.
2. Double-click `setup_windows.bat` once.
3. Double-click `run_windows.bat`.
4. Drop an image into the window and press **Generate Pixel Art**.

Or use PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Build a Windows executable

Run:

```text
build_exe.bat
```

The program will be created at:

```text
dist\PixelArtStudio\PixelArtStudio.exe
```

The first build is a folder-based executable because it starts faster than a single-file PyInstaller build.

## Command line

```powershell
python pixelize_cli.py input.jpg output.png --width 96 --colors 24 --scale 8
```

Useful options:

```text
--height 0          Preserve source aspect ratio
--no-dither         Disable Floyd–Steinberg dithering
--cleanup 2         Run two isolated-pixel cleanup passes
--edge-strength .3  Add local dark edge ink
```

## Rendering pipeline

1. Correct EXIF orientation and preserve transparency.
2. Reduce the image to a real pixel canvas.
3. Adjust contrast, saturation, and detail.
4. Generate an adaptive palette with median-cut quantization.
5. Optionally dither the limited palette.
6. Remove obvious isolated color speckles.
7. Optionally darken prominent local edges.
8. Export with nearest-neighbor scaling.

## Planned next upgrades

- Bayer ordered dithering
- Editable custom palettes
- Before/after slider
- Pixel-grid zoom and hand editing
- Smarter cluster and line cleanup
- Batch processing
- Minecraft block-palette export

## License

MIT
