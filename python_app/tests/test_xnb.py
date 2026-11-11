import struct
import unittest
from duckmeta.xnb import read_texture, XnbError
from xnb_fixtures import texture_payload, xnb


class XnbTests(unittest.TestCase):
    def test_color_uncompressed_and_lz4(self):
        pixels=bytes([20,40,60,255])*32*32
        for codec in ['none','lz4']:
            texture=read_texture(xnb(texture_payload(pixels=pixels),codec))
            self.assertEqual(texture.image.tobytes(),pixels)
            self.assertEqual(texture.image.size,(32,32))

    def test_actual_lzx_huffman_literal_stream(self):
        pixels=bytes([17,23,41,255])*32*32
        texture=read_texture(xnb(texture_payload(pixels=pixels),'lzx'))
        self.assertEqual(texture.compression,'LZX');self.assertEqual(texture.image.tobytes(),pixels)

    def test_lzx_multiple_frames(self):
        pixels=bytes([20,30,40,255])*128*128
        texture=read_texture(xnb(texture_payload(128,128,pixels=pixels),'lzx-multi'))
        self.assertEqual(texture.image.tobytes(),pixels)

    def test_unpremultiplies_partial_alpha(self):
        data=xnb(texture_payload(pixels=bytes([50,25,0,128])*1024))
        self.assertEqual(read_texture(data).image.getpixel((0,0)),(100,50,0,128))
        self.assertEqual(read_texture(data,straight_alpha=False).image.getpixel((0,0)),(50,25,0,128))

    def test_dxt_surface_formats(self):
        block=struct.pack('<HHI',0xf800,0,0)
        for fmt,data in [(4,block),(5,b'\xff'*8+block),(6,b'\xff\x00'+b'\0'*6+block)]:
            self.assertEqual(read_texture(xnb(texture_payload(4,4,fmt,data))).image.getpixel((0,0)),(255,0,0,255))

    def test_packed_color_formats(self):
        for fmt,value in [(1,0xf800),(2,0xfc00),(3,0xff00)]:
            self.assertEqual(read_texture(xnb(texture_payload(1,1,fmt,struct.pack('<H',value)))).image.getpixel((0,0)),(255,0,0,255))

    def test_rejects_corruption_wrong_type_and_unknown_formats(self):
        good=xnb(texture_payload())
        for data in [good[:-1],b'not xnb',xnb(texture_payload(reader_name='Microsoft.Xna.Framework.Content.SoundEffectReader')),
                     xnb(texture_payload(1,1,99,b'1234')),xnb(texture_payload(5000,1,pixels=b''))]:
            with self.assertRaises(XnbError):read_texture(data)
