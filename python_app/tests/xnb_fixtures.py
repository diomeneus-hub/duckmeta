"""Generated XNBs: no proprietary game assets required."""
import struct
from lz4.block import compress


def varint(value):
    result=bytearray()
    while value>=128:
        result.append((value&127)|128);value>>=7
    return bytes(result)+bytes([value])


def texture_payload(width=32,height=32,fmt=0,pixels=None,reader_name=None):
    name=(reader_name or 'Microsoft.Xna.Framework.Content.Texture2DReader, Microsoft.Xna.Framework.Graphics').encode()
    if pixels is None:pixels=bytes([255,255,255,255])*width*height
    return b'\x01'+varint(len(name))+name+struct.pack('<I',0)+b'\x00\x01'+struct.pack('<IIIII',fmt,width,height,1,len(pixels))+pixels


def _words(bits):
    bits+='0'*(-len(bits)%16)
    return b''.join(int(bits[i:i+16],2).to_bytes(2,'little') for i in range(0,len(bits),16))


def lzx_literal_frame(payload):
    # Complete canonical trees and real LZX verbatim-block literal codes.
    pretree='0100'*16+'0000'*4
    bits='0'+'001'+format(len(payload),'024b')
    bits+=pretree+'1000'*256
    bits+=pretree+'1000'*256
    bits+=pretree+'1010'*7+'1001'*242
    bits+=''.join(format(b,'09b') for b in payload)
    return _words(bits)


def xnb(payload,compression='none'):
    flag=0;body=payload
    if compression=='lz4':flag=0x40;body=struct.pack('<I',len(payload))+compress(payload,store_size=False)
    if compression=='lzx':
        flag=0x80;frame=lzx_literal_frame(payload)
        body=struct.pack('<I',len(payload))+b'\xff'+struct.pack('>HH',len(payload),len(frame))+frame
    if compression=='lzx-multi':
        flag=0x80
        prefix=_words('0'+'011'+format(len(payload),'024b'))+struct.pack('<III',1,1,1)
        frames=[]
        for i in range(0,len(payload),32768):
            part=payload[i:i+32768];frame=(prefix if i==0 else b'')+part
            if i+len(part)==len(payload) and len(payload)%2:frame+=b'\0'
            frames.append(b'\xff'+struct.pack('>HH',len(part),len(frame))+frame)
        body=struct.pack('<I',len(payload))+b''.join(frames)
    return b'XNBw\x05'+bytes([flag])+struct.pack('<I',10+len(body))+body
