import io
import json
import unittest
import zipfile
from PIL import Image
from duckmeta.artwork import Artwork, regions
from duckmeta.model import EMPTY


class ArtworkTests(unittest.TestCase):
    def test_stroke_fill_erase_history_and_layer_composite(self):
        doc=Artwork(Image.new('RGBA',(96,56)))
        doc.record();doc.stroke((0,0),(5,5),(10,20,30,255))
        self.assertEqual(doc.composite().getpixel((3,3)),(10,20,30,255))
        doc.undo();self.assertIsNone(doc.composite().getbbox());doc.redo()
        doc.add();doc.record();doc.fill((1,0),(200,0,0,128))
        self.assertEqual(doc.composite().getpixel((20,20)),(200,0,0,128))
        doc.layers[1].visible=False
        self.assertEqual(doc.composite().getpixel((3,3)),(10,20,30,255))
        doc.layers[1].visible=True;doc.layers[1].opacity=128
        self.assertEqual(doc.composite().getpixel((20,20))[3],64)
        doc.stroke((20,20),(20,20),(0,0,0,0),True)
        self.assertEqual(doc.layers[1].image.getpixel((20,20)),(0,0,0,0))

    def test_project_roundtrip_all_layers_and_metadata(self):
        image=Image.new('RGBA',(96,56),(1,2,3,0));doc=Artwork(image)
        self.assertEqual(doc.composite().tobytes(),image.tobytes())
        doc.add();doc.layers[1].name='Star';doc.layers[1].visible=False;doc.layers[1].opacity=77
        doc.stroke((4,5),(4,5),(255,200,0,128))
        slots=[EMPTY]*56;slots[0]=(222,12,13,19)
        loaded,metadata=Artwork.load(doc.project(slots))
        self.assertEqual(metadata,slots);self.assertEqual(loaded.active,doc.active)
        for a,b in zip(loaded.layers,doc.layers):
            self.assertEqual((a.name,a.visible,a.opacity,a.image.tobytes()),(b.name,b.visible,b.opacity,b.image.tobytes()))

    def test_project_rejects_wrong_dimensions_and_metadata(self):
        doc=Artwork(Image.new('RGBA',(32,32)))
        for key,value in [('size',[31,32]),('slots',[[1,2,300,255]]*32),('active',9)]:
            original=doc.project([EMPTY]*32);out=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(original)) as src,zipfile.ZipFile(out,'w') as dest:
                manifest=json.loads(src.read('project.json'));manifest[key]=value
                for name in src.namelist():dest.writestr(name,json.dumps(manifest) if name=='project.json' else src.read(name))
            with self.assertRaises(ValueError):Artwork.load(out.getvalue())

    def test_layout_regions_and_layer_order(self):
        rects={name:(x,y,r,b) for name,x,y,r,b in regions(96,56)}
        self.assertEqual(rects['Cape'],(64,0,96,32))
        self.assertEqual(rects['Rock'],(0,32,24,56))
        self.assertEqual(rects['FX 4'],(36,44,48,56))
        self.assertEqual(len(regions(32,32)),1)
        doc=Artwork(Image.new('RGBA',(32,32),'red'));doc.add();doc.fill((0,0),(0,0,255,255))
        self.assertEqual(doc.composite().getpixel((0,0)),(0,0,255,255))
        doc.move(-1);self.assertEqual(doc.composite().getpixel((0,0)),(255,0,0,255))
        doc.undo();self.assertEqual(doc.composite().getpixel((0,0)),(0,0,255,255))
        doc.remove();self.assertEqual(len(doc.layers),1)
