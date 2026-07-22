from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Literal

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

DitherName = Literal["none", "floyd-steinberg"]
ResizeName = Literal["balanced", "sharp", "smooth"]


@dataclass(frozen=True, slots=True)
class RenderSettings:
    width: int = 128
    height: int = 128
    colors: int = 32
    dither: DitherName = "floyd-steinberg"
    resize_mode: ResizeName = "balanced"
    detail: float = 1.15
    contrast: float = 1.08
    saturation: float = 1.05
    cleanup_passes: int = 1
    edge_strength: float = 0.0

    def validated(self) -> "RenderSettings":
        return replace(
            self,
            width=max(1, min(1024, int(self.width))),
            height=max(1, min(1024, int(self.height))),
            colors=max(2, min(256, int(self.colors))),
            detail=max(0.0, min(3.0, float(self.detail))),
            contrast=max(0.1, min(3.0, float(self.contrast))),
            saturation=max(0.0, min(3.0, float(self.saturation))),
            cleanup_passes=max(0, min(4, int(self.cleanup_passes))),
            edge_strength=max(0.0, min(1.0, float(self.edge_strength))),
        )


class PixelArtRenderer:
    """Small, deterministic image-to-pixel-art rendering pipeline."""

    _RESAMPLE = {
        "balanced": Image.Resampling.LANCZOS,
        "sharp": Image.Resampling.BOX,
        "smooth": Image.Resampling.BILINEAR,
    }

    def render(self, source: Image.Image, settings: RenderSettings) -> Image.Image:
        settings = settings.validated()
        image = ImageOps.exif_transpose(source).convert("RGBA")

        # Avoid wasting memory on huge camera images before the actual pixel reduction.
        image.thumbnail((4096, 4096), Image.Resampling.LANCZOS)

        alpha = image.getchannel("A")
        rgb = image.convert("RGB")
        resample = self._RESAMPLE[settings.resize_mode]

        rgb = rgb.resize((settings.width, settings.height), resample)
        alpha = alpha.resize((settings.width, settings.height), Image.Resampling.LANCZOS)

        if settings.contrast != 1.0:
            rgb = ImageEnhance.Contrast(rgb).enhance(settings.contrast)
        if settings.saturation != 1.0:
            rgb = ImageEnhance.Color(rgb).enhance(settings.saturation)
        if settings.detail != 1.0:
            rgb = ImageEnhance.Sharpness(rgb).enhance(settings.detail)

        dither = (
            Image.Dither.FLOYDSTEINBERG
            if settings.dither == "floyd-steinberg"
            else Image.Dither.NONE
        )

        # MEDIANCUT builds a palette from the source instead of forcing a fixed retro palette.
        rgb = rgb.quantize(
            colors=settings.colors,
            method=Image.Quantize.MEDIANCUT,
            dither=dither,
        ).convert("RGB")

        result = rgb.convert("RGBA")
        result.putalpha(alpha)

        if settings.cleanup_passes:
            result = self._cleanup_isolated_pixels(result, settings.cleanup_passes)

        if settings.edge_strength > 0:
            result = self._apply_edge_ink(result, settings.edge_strength)

        return result

    @staticmethod
    def upscale(image: Image.Image, scale: int) -> Image.Image:
        scale = max(1, min(64, int(scale)))
        if scale == 1:
            return image.copy()
        return image.resize(
            (image.width * scale, image.height * scale),
            Image.Resampling.NEAREST,
        )

    @staticmethod
    def _cleanup_isolated_pixels(image: Image.Image, passes: int) -> Image.Image:
        current = image.copy()
        width, height = current.size
        if width < 3 or height < 3:
            return current

        for _ in range(passes):
            source = current.load()
            cleaned = current.copy()
            destination = cleaned.load()

            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    center = source[x, y]
                    if center[3] == 0:
                        continue

                    neighbors = [
                        source[x - 1, y - 1], source[x, y - 1], source[x + 1, y - 1],
                        source[x - 1, y],                         source[x + 1, y],
                        source[x - 1, y + 1], source[x, y + 1], source[x + 1, y + 1],
                    ]
                    opaque_neighbors = [pixel for pixel in neighbors if pixel[3] > 0]
                    if not opaque_neighbors:
                        continue

                    same_count = sum(pixel[:3] == center[:3] for pixel in opaque_neighbors)
                    most_common, common_count = Counter(
                        pixel[:3] for pixel in opaque_neighbors
                    ).most_common(1)[0]

                    # Replace only obvious speckles. Real thin lines remain intact.
                    if same_count == 0 and common_count >= 4:
                        destination[x, y] = (*most_common, center[3])

            current = cleaned

        return current

    @staticmethod
    def _apply_edge_ink(image: Image.Image, strength: float) -> Image.Image:
        rgb = image.convert("RGB")
        alpha = image.getchannel("A")

        edges = ImageOps.autocontrast(rgb.convert("L").filter(ImageFilter.FIND_EDGES))
        threshold = int(235 - (strength * 120))
        mask = edges.point(lambda value: 255 if value >= threshold else 0)
        mask = mask.filter(ImageFilter.MaxFilter(3))

        # Use a darkened version of the local color, avoiding a universal black outline.
        dark = ImageEnhance.Brightness(rgb).enhance(max(0.15, 1.0 - strength * 0.8))
        inked = Image.composite(dark, rgb, mask).convert("RGBA")
        inked.putalpha(alpha)
        return inked
