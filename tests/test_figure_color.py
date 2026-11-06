"""Foreground colors for room lighting, including grey figurines with clothes."""
import ast
from io import BytesIO
from pathlib import Path
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/teddycloud_homeassistant'
source = ast.parse((ROOT / 'figure_color.py').read_text())
ns = {'BytesIO': BytesIO}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef)], type_ignores=[]), 'figure_color.py', 'exec'), ns)
dominant_color = ns['dominant_color']


def encoded(image):
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


class FigureColorTests(unittest.TestCase):
    def test_white_studio_backdrop_is_not_the_figure(self):
        image = Image.new('RGBA', (96,96), 'white')
        ImageDraw.Draw(image).rectangle((28,16,68,86), fill='#CF3326')
        self.assertEqual(dominant_color(encoded(image)), '#CF3326')

    def test_grey_body_with_colored_clothing_prefers_color(self):
        image = Image.new('RGBA', (96,96), (0,0,0,0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10,5,85,90), fill='#929291')
        draw.rectangle((24,55,75,85), fill='#CF3326')
        self.assertEqual(dominant_color(encoded(image)), '#CF3326')

    def test_dark_background_is_not_the_figure(self):
        image = Image.new('RGBA', (96,96), '#242424')
        ImageDraw.Draw(image).rectangle((25,15,70,84), fill='#2266BB')
        self.assertEqual(dominant_color(encoded(image)), '#2266BB')

    def test_colored_background_is_removed_only_when_connected_to_border(self):
        image = Image.new('RGBA', (96,96), '#AA3399')
        draw = ImageDraw.Draw(image)
        draw.rectangle((20,10,75,85), fill='#2255AA')
        draw.rectangle((40,30,46,38), fill='#AA3399')
        self.assertEqual(dominant_color(encoded(image)), '#2255AA')

    def test_neutral_figure_without_colored_parts_remains_grey(self):
        image = Image.new('RGBA', (96,96), 'white')
        ImageDraw.Draw(image).rectangle((20,10,75,85), fill='#929291')
        self.assertEqual(dominant_color(encoded(image)), '#929291')

    def test_transparent_cutout_touching_bottom_is_not_removed(self):
        image = Image.new('RGBA', (96,96), (0,0,0,0))
        ImageDraw.Draw(image).rectangle((25,10,70,95), fill='#2288AA')
        self.assertEqual(dominant_color(encoded(image)), '#2288AA')

    def test_seven_distinct_figure_colors(self):
        for color in ['#CF3326','#2288AA','#44AA22','#8822CC','#AA8833','#2255AA','#BB2277']:
            with self.subTest(color=color):
                image = Image.new('RGBA', (96,96), 'white')
                ImageDraw.Draw(image).ellipse((24,12,72,90), fill=color)
                self.assertEqual(dominant_color(encoded(image)), color)

    def test_uniform_image_retains_color(self):
        self.assertEqual(dominant_color(encoded(Image.new('RGBA',(12,12),'#2288AA'))), '#2288AA')
        self.assertEqual(dominant_color(encoded(Image.new('RGBA',(12,12),'white'))), '#FFFFFF')

    def test_empty_or_transparent_image_has_no_color(self):
        self.assertIsNone(dominant_color(None))
        self.assertIsNone(dominant_color(encoded(Image.new('RGBA',(12,12),(0,0,0,0)))))

