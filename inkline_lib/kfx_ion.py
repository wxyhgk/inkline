"""最小 Ion binary 解码/编码器（KFX 用子集）。

对照 boko src/kfx/ion.rs。只支持 KFX 实际出现的类型：
null/bool/int/float/string/symbol/list/struct/blob。decimal/timestamp 不出现。
"""
import struct as _st


class IonSymbol(int):
    pass


def _read_varuint(d, pos):
    v = 0
    while True:
        b = d[pos]; pos += 1
        v = (v << 7) | (b & 0x7F)
        if b & 0x80:
            break
    return v, pos


def _read_varint_signed(d, pos):
    """Ion VarInt：首字节含符号位。"""
    b = d[pos]; pos += 1
    neg = bool(b & 0x40)
    v = b & 0x3F
    while not (b & 0x80):
        b = d[pos]; pos += 1
        v = (v << 7) | (b & 0x7F)
    return (-v if neg else v), pos


class Decoder:
    def __init__(self, data):
        self.d = data
        self.pos = 0

    def dec(self):
        d, p = self.d, self.pos
        if p >= len(d):
            return None
        tb = d[p]; p += 1
        tc, lc = tb >> 4, tb & 0x0F
        if lc == 15:
            self.pos = p
            return None
        ln = _read_varuint(d, p)[0] if lc == 14 else lc
        if lc == 14:
            _, p = _read_varuint(d, p)
        if tc == 0:  # NOP
            self.pos = p + ln
            return None
        if tc == 1:  # bool
            self.pos = p
            return lc != 0
        if tc in (2, 3):  # int
            v = int.from_bytes(d[p:p+ln], 'big') if ln else 0
            self.pos = p + ln
            return -v if tc == 3 else v
        if tc == 4:  # float
            if ln == 0:
                v = 0.0
            elif ln == 4:
                v = _st.unpack('>f', d[p:p+4])[0]
            else:
                v = _st.unpack('>d', d[p:p+8])[0]
            self.pos = p + ln
            return v
        if tc == 7:  # symbol
            v = int.from_bytes(d[p:p+ln], 'big') if ln else 0
            self.pos = p + ln
            return IonSymbol(v)
        if tc == 5:  # decimal: exponent varint + sign-magnitude coefficient
            end = p + ln
            self.pos = p
            exp, self.pos = _read_varint_signed(d, self.pos)
            if self.pos >= end:
                coef = 0
            else:
                raw = d[self.pos:end]
                neg = bool(raw[0] & 0x80)
                mag = int.from_bytes(bytes([raw[0] & 0x7F]) + raw[1:], 'big')
                coef = -mag if neg else mag
            self.pos = end
            return ('decimal', exp, coef)
        if tc == 8:  # string
            v = d[p:p+ln].decode('utf-8')
            self.pos = p + ln
            return v
        if tc in (9, 10):  # clob/blob
            v = bytes(d[p:p+ln])
            self.pos = p + ln
            return v
        if tc == 11:  # list
            end = p + ln
            out = []
            self.pos = p
            while self.pos < end:
                out.append(self.dec())
            return out
        if tc == 13:  # struct
            end = p + ln
            out = []
            self.pos = p
            while self.pos < end:
                fid, self.pos = _read_varuint(d, self.pos)
                out.append((fid, self.dec()))
            return out
        if tc == 14:  # annotation
            end = p + ln
            self.pos = p
            alen, self.pos = _read_varuint(d, self.pos)
            anns = []
            while len(anns) < alen:
                a, self.pos = _read_varuint(d, self.pos)
                anns.append(a)
            val = self.dec()
            return (anns, val)
        raise ValueError(f'unsupported ion type {tc}')


def decode(data):
    """解单个顶层 Ion 值。返回 (value, 消费字节数)。"""
    dec = Decoder(data)
    # 跳过 BVM
    if data[:4] == b'\xe0\x01\x00\xea':
        dec.pos = 4
    v = dec.dec()
    return v, dec.pos


# ---------- 编码 ----------
def _varuint(n):
    if n == 0:
        return b'\x80'
    out = bytearray()
    out.append(0x80 | (n & 0x7F))
    n >>= 7
    while n:
        out.append(n & 0x7F)
        n >>= 7
    return bytes(reversed(out))


def _uint_bytes(n):
    if n == 0:
        return b''
    ln = (n.bit_length() + 7) // 8
    return n.to_bytes(ln, 'big')


def _td(tc, ln):
    if ln < 14:
        return bytes([(tc << 4) | ln])
    return bytes([(tc << 4) | 14]) + _varuint(ln)


class Encoder:
    def __init__(self):
        self.b = bytearray()

    def enc(self, v):
        if v is None:
            self.b.append(0x0F)
        elif isinstance(v, bool):
            self.b.append(0x11 if v else 0x10)
        elif isinstance(v, IonSymbol):
            bb = _uint_bytes(int(v))
            self.b += _td(7, len(bb)) + bb
        elif isinstance(v, int):
            if v == 0:
                self.b.append(0x20)
            elif v > 0:
                bb = _uint_bytes(v)
                self.b += _td(2, len(bb)) + bb
            else:
                bb = _uint_bytes(-v)
                self.b += _td(3, len(bb)) + bb
        elif isinstance(v, float):
            self.b.append(0x48)
            import struct as _s
            self.b += _s.pack('>d', v)
        elif isinstance(v, str):
            bb = v.encode('utf-8')
            self.b += _td(8, len(bb)) + bb
        elif isinstance(v, bytes):
            self.b += _td(10, len(v)) + v
        elif isinstance(v, tuple) and len(v) == 3 and v[0] == 'decimal':
            _, exp, coef = v
            # exponent varint signed
            mag = abs(exp)
            eb = bytearray()
            first = (0x40 if exp < 0 else 0x00) | (mag & 0x3F)
            mag >>= 6
            rest = []
            while mag:
                rest.append(mag & 0x7F)
                mag >>= 7
            for x in reversed(rest):
                eb.append(x)
            eb.append(0x80 | first) if False else None
            # Ion VarInt: 最高位0的字节在前，终止字节最高位1
            out = bytearray()
            lead = (0x40 if exp < 0 else 0x00)
            # 简化：exp小，只需1-2字节
            if abs(exp) < 64 and not rest:
                out.append(0x80 | lead | (abs(exp) & 0x3F))
            else:
                out.append(lead | (abs(exp) & 0x3F))
                for x in reversed(rest):
                    out.append(x)
                out[-1] |= 0x80
                # 修正：首字节不应有终止位，已处理
            if coef == 0:
                cb = b''
            else:
                neg = coef < 0
                c = -coef if neg else coef
                ln = max(1, (c.bit_length() + 7) // 8)
                cb = c.to_bytes(ln, 'big')
                if cb[0] & 0x80:
                    cb = (b'\x80' if neg else b'\x00') + cb
                elif neg:
                    cb = bytes([cb[0] | 0x80]) + cb[1:]
            body = bytes(out) + cb
            self.b += _td(5, len(body)) + body
        elif isinstance(v, list) and v and all(isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], int) for x in v):
            sub = Encoder()  # struct
            for fid, val in v:
                sub.b += _varuint(fid)
                sub.enc(val)
            bb = bytes(sub.b)
            self.b += _td(13, len(bb)) + bb
        elif isinstance(v, list):
            sub = Encoder()  # list
            for i in v:
                sub.enc(i)
            bb = bytes(sub.b)
            self.b += _td(11, len(bb)) + bb
        elif isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], list):
            anns, inner = v
            sub = Encoder()
            sub.enc(inner)
            ib = bytes(sub.b)
            ab = _varuint(len(anns))
            for a in anns:
                ab += _varuint(a)
            self.b += _td(14, len(ab) + len(ib)) + ab + ib
        else:
            raise ValueError(f'cannot encode {type(v)} {str(v)[:50]}')

    def bytes(self):
        return bytes(self.b)


def encode(v, bvm=True):
    e = Encoder()
    if bvm:
        e.b += b'\xe0\x01\x00\xea'
    e.enc(v)
    return e.bytes()
