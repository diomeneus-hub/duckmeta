import subprocess
import unittest
from unittest.mock import patch
from duckmeta.clipboard import copy_png


class ClipboardTests(unittest.TestCase):
    def test_wayland_and_x11_png_targets(self):
        for environment,tool in [({'WAYLAND_DISPLAY':'wayland-0','DISPLAY':':97'},'wl-copy'),({'DISPLAY':':97'},'xclip')]:
            with patch.dict('os.environ',environment,clear=True),patch('shutil.which',return_value='/bin/helper'),patch('subprocess.run') as run:
                copy_png(b'png bytes')
                self.assertEqual(run.call_args.args[0][0],tool)
                self.assertIn('image/png',run.call_args.args[0])
                self.assertEqual(run.call_args.kwargs['input'],b'png bytes')

    def test_missing_helper_and_failed_clipboard(self):
        with patch('shutil.which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'pacman'):copy_png(b'png')
        with patch.dict('os.environ',{'DISPLAY':':97'},clear=True),patch('shutil.which',return_value='/bin/xclip'),patch('subprocess.run',side_effect=subprocess.CalledProcessError(1,'xclip')):
            with self.assertRaisesRegex(RuntimeError,'Could not copy'):copy_png(b'png')
