import tempfile
import unittest
from pathlib import Path
from duckmeta.model import EMPTY
from duckmeta.templates import TemplateStore, selected_pixels, plan_apply


class TemplateTests(unittest.TestCase):
    def test_merge_replaces_target_randomizers_and_keeps_unrelated_bytes(self):
        slots=[(1,128,128,255),(100,0,255,255),(222,1,2,128),(7,8,9,0),EMPTY,EMPTY]
        result,conflicts=plan_apply(slots,[(1,130,128,255),(101,128,255,255)])
        self.assertEqual(conflicts,[1])
        self.assertEqual(result[:4],[(1,130,128,255),(101,128,255,255),(222,1,2,128),(7,8,9,0)])
        self.assertEqual(slots[0],(1,128,128,255))

    def test_selection_requires_randomizer_parent(self):
        slots=[(1,128,128,255),(100,0,255,255),(10,128,128,255),(101,0,255,255)]
        with self.assertRaises(ValueError):selected_pixels(slots,[0,3])
        self.assertEqual(selected_pixels(slots,[0,1]),slots[:2])
        with self.assertRaises(ValueError):selected_pixels(slots,[])

    def test_capacity_noop_and_duplicate_order(self):
        slots=[(1,130,128,255),(100,0,255,255)]
        result,conflicts=plan_apply(slots,slots)
        self.assertEqual(result,slots);self.assertEqual(conflicts,[])
        with self.assertRaises(ValueError):plan_apply(slots,[(2,0,0,255)])
        incoming=[(1,129,128,255),(100,1,2,255),(1,131,128,255)]
        result,conflicts=plan_apply(slots+[EMPTY]*3,incoming)
        self.assertEqual(result[:3],incoming);self.assertEqual(conflicts,[1])

    def test_store_restart_names_and_bad_files(self):
        with tempfile.TemporaryDirectory() as directory:
            store=TemplateStore(directory);pixels=[(222,1,2,128)]
            path=store.save('../star',pixels)
            self.assertEqual(path.parent,Path(directory))
            self.assertEqual(TemplateStore(directory).list()[0],[('../star',pixels)])
            with self.assertRaises(ValueError):store.save('../STAR',pixels)
            (Path(directory)/'bad.json').write_text('{}')
            entries,errors=store.list()
            self.assertEqual(len(entries),1);self.assertEqual(len(errors),1)
            with self.assertRaises(ValueError):store.save('broken',[(1,300,0,255)])
