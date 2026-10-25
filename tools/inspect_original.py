#!/usr/bin/env python3
"""Offline inventory and Delphi form extraction; never executes the supplied binaries."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]


class FormReader:
    def __init__(self, data, offset):
        self.data, self.pos = data, offset

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Truncated form')
        value = self.data[self.pos:self.pos + size]
        self.pos += size
        return value

    def number(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def text(self):
        return self.take(self.number('<B')).decode('utf-8', errors='replace')

    def value(self):
        kind = self.number('<B')
        if kind in (2, 3, 4, 19, 21):
            return self.number({2: '<b', 3: '<h', 4: '<i', 19: '<q', 21: '<Q'}[kind])
        if kind == 5:
            raw = self.take(10)
            mantissa, exponent = struct.unpack('<QH', raw)
            return (-1 if exponent & 0x8000 else 1) * (mantissa / 2**63) * 2.0**((exponent & 0x7fff) - 16383) if mantissa else 0
        if kind in (6, 7):
            return self.text()
        if kind in (8, 9):
            return kind == 9
        if kind == 11:
            result = []
            while value := self.text():
                result.append(value)
            return result
        if kind in (12, 20):
            return self.take(self.number('<I')).decode('utf-8', errors='replace')
        if kind == 18:
            return self.take(self.number('<I') * 2).decode('utf-16le')
        if kind in (15, 17):
            return self.number('<f' if kind == 15 else '<d')
        if kind == 10:
            payload = self.take(self.number('<I'))
            return {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
        if kind == 13:
            return None
        raise ValueError(f'Unsupported form value type {kind} at {self.pos - 1:#x}')

    def component(self):
        result = {'class': self.text(), 'name': self.text(), 'properties': {}, 'children': []}
        while name := self.text():
            result['properties'][name] = self.value()
        while self.data[self.pos]:
            result['children'].append(self.component())
        self.pos += 1
        return result


def inspect(path):
    data = path.read_bytes()
    forms = []
    for match in re.finditer(rb'TPF0[\x09-\x0b]T(?:MainForm|ConfigForm|DummyForm)', data):
        form = FormReader(data, match.start() + 4).component()
        forms.append({'file_offset': hex(match.start()), **form})
    strings = []
    for match in re.finditer(rb'\xff\xff\xff\xff(.{4})', data, re.S):
        count = int.from_bytes(match[1], 'little')
        if 0 < count <= 80:
            text = data[match.end():match.end() + count * 2].decode('utf-16le', errors='replace')
            if text.isprintable() and ('納期' in text or 'おしごと' in text or text in
                ('Deadline', 'Line1Text', 'Line2Text', 'SubText1', 'SubText2',
                 'Line1Font', 'Line2Font', 'IgnoreClick', 'StayOnTop', 'Scale')):
                strings.append({'file_offset': hex(match.end()), 'text': text})
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'forms': forms, 'strings': strings}


if __name__ == '__main__':
    paths = ['deadlinep5/Windows/DeadlineP5.exe',
             'deadlinep5/macOS/DeadlineP5.app/Contents/MacOS/DeadlineP5']
    results = [inspect(ROOT / path) for path in paths]
    assert all({form['class'] for form in result['forms']} ==
               {'TMainForm', 'TConfigForm', 'TDummyForm'} for result in results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
