from PIL import Image

from pixelstudio.core import PixelArtRenderer, RenderSettings


def test_render_dimensions_and_palette_limit() -> None:
    source = Image.new("RGB", (320, 180))
    pixels = source.load()
    for y in range(source.height):
        for x in range(source.width):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)

    renderer = PixelArtRenderer()
    result = renderer.render(
        source,
        RenderSettings(width=64, height=36, colors=16, cleanup_passes=1),
    )

    assert result.size == (64, 36)
    assert len(set(result.getdata())) <= 16


def test_nearest_neighbor_upscale() -> None:
    source = Image.new("RGBA", (2, 1))
    source.putdata([(255, 0, 0, 255), (0, 0, 255, 255)])

    result = PixelArtRenderer.upscale(source, 3)

    assert result.size == (6, 3)
    assert result.getpixel((0, 0)) == (255, 0, 0, 255)
    assert result.getpixel((5, 2)) == (0, 0, 255, 255)
