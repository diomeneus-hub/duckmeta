import io
import unittest
from PIL import Image
from duckmeta.model import ASSETS, BY_ID, EFFECTS, EMPTY, Hat, History, decode_value, evaluate


def png(image):
    stream=io.BytesIO();image.save(stream,format="PNG");return stream.getvalue()


class ModelTests(unittest.TestCase):
    def test_rgba_roundtrip_preserves_all_bytes(self):
        data=bytes((i*37+19)%256 for i in range(97*56*4))
        original=Image.frombytes("RGBA",(97,56),data)
        hat=Hat.read(png(original),"random.png")
        self.assertTrue(hat.had_meta)
        result=Image.open(io.BytesIO(hat.png())).convert("RGBA")
        self.assertEqual(result.tobytes(),data)
        self.assertEqual(result.size,(97,56))

    def test_add_column_without_changing_art(self):
        hat=Hat.read(ASSETS/"wizard.png");before=hat.artwork.tobytes()
        self.assertFalse(hat.had_meta)
        hat.add(1);hat.slots[0]=(1,140,128,255)
        imported=Hat.read(hat.png())
        self.assertEqual(imported.width,96);self.assertEqual(imported.artwork.tobytes(),before)
        self.assertEqual(imported.slots[0],(1,140,128,255))
        self.assertEqual(Hat.read(imported.png()).width,96)

    def test_palette_transparency(self):
        image=Image.new("P",(32,32));image.putpalette([10,20,30,200,100,20]+[0]*762)
        image.putpixel((1,1),1);image.info["transparency"]=bytes([0,128])
        hat=Hat.read(png(image))
        self.assertEqual(hat.artwork.getpixel((0,0)),(10,20,30,0))
        self.assertEqual(hat.artwork.getpixel((1,1)),(200,100,20,128))

    def test_rejects_invalid_dimensions_depth_and_crc(self):
        for data in [b"not png",png(Image.new("RGBA",(40,32))),png(Image.new("I;16",(32,32)))]:
            with self.assertRaises(ValueError):Hat.read(data)
        data=bytearray(png(Image.new("RGBA",(32,32),"red")));data[data.index(b"IDAT")+5]^=1
        with self.assertRaises((ValueError,SyntaxError,OSError)):Hat.read(data)

    def test_definition_count_and_decoding(self):
        self.assertEqual(len(EFFECTS),35);self.assertEqual(len(BY_ID),35)
        for ident,raw,expected in [(1,128,0),(1,255,16),(1,0,-16),(34,136,8),(35,255,2),(36,0,-2),(38,255,1)]:
            self.assertEqual(decode_value(BY_ID[ident],raw),expected)

    def test_randomizers_order_and_alpha(self):
        values=evaluate([(100,0,0,255),(36,255,255,255),(100,0,0,255),(101,255,255,255),(37,255,0,255),(2,0,0,0)],lambda:.5)
        self.assertEqual(values[36],[-2,2]);self.assertEqual(values[37],[2,-2]);self.assertNotIn(2,values)
        self.assertIn(2,evaluate([(2,0,0,1)]))

    def test_insertion_preserves_rows_and_rejects_full_stack(self):
        hat=Hat.read(ASSETS/"wizard.png");hat.slots[:2]=[(36,255,255,255),(222,10,20,128)]
        self.assertEqual(hat.add(100,0),1);self.assertEqual(hat.slots[2],(222,10,20,128))
        hat.slots=[(1,128,128,255)]*hat.height;before=list(hat.slots)
        with self.assertRaises(ValueError):hat.add(2,0)
        self.assertEqual(hat.slots,before)

    def test_history_undo_redo_and_branch(self):
        hat=Hat.example();history=History();before=list(hat.slots)
        history.record(hat.slots);hat.slots[0]=(1,140,128,255)
        self.assertTrue(history.undo(hat));self.assertEqual(hat.slots,before)
        self.assertTrue(history.redo(hat));self.assertEqual(hat.slots[0][1],140)
        history.undo(hat);history.record(hat.slots);hat.slots[0]=EMPTY
        self.assertFalse(history.redo(hat))
