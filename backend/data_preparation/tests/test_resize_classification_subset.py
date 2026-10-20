import tempfile
import unittest
from pathlib import Path

from PIL import Image

from data_preparation.resize_classification_subset import create_variants


class ResizeClassificationSubsetTests(unittest.TestCase):
    def test_exif_orientation_and_resize_preserve_rgb_and_aspect_ratio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            image = Image.new('RGB', (80, 40), (150, 30, 20))
            exif = image.getexif()
            exif[274] = 6
            image.save(source / 'oriented.jpg', exif=exif)

            report = create_variants(source, root / 'derived', (32,), quality=90)

            row = report['files'][0]
            self.assertEqual((row['source_width'], row['source_height']), (40, 80))
            self.assertEqual((row['output_width'], row['output_height']), (16, 32))
            with Image.open(root / 'derived' / 'max_32' / 'oriented.jpg') as result:
                self.assertEqual(result.mode, 'RGB')
                self.assertEqual(result.getexif().get(274), None)
                result.load()

    def test_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            Image.new('RGB', (40, 20)).save(source / 'one.jpg')
            output = root / 'derived'
            output.mkdir()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                create_variants(source, output, (32,))


if __name__ == '__main__':
    unittest.main()
