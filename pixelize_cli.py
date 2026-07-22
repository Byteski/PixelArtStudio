from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from pixelstudio.core import PixelArtRenderer, RenderSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert an image into pixel art.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--height", type=int, default=0, help="0 preserves aspect ratio")
    parser.add_argument("--colors", type=int, default=32)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--no-dither", action="store_true")
    parser.add_argument("--cleanup", type=int, default=1)
    parser.add_argument("--edge-strength", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with Image.open(args.input) as source:
        source = source.convert("RGBA")

    height = args.height
    if height <= 0:
        height = max(1, round(args.width * source.height / source.width))

    settings = RenderSettings(
        width=args.width,
        height=height,
        colors=args.colors,
        dither="none" if args.no_dither else "floyd-steinberg",
        cleanup_passes=args.cleanup,
        edge_strength=args.edge_strength,
    )

    renderer = PixelArtRenderer()
    result = renderer.render(source, settings)
    result = renderer.upscale(result, args.scale)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output.with_suffix(".png"), "PNG")
    print(f"Saved: {args.output.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
