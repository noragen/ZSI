"""Small Python 3 compatibility shim for legacy mimetools usage."""

import base64
from email import policy
from email.parser import Parser
import quopri


class Message:
    def __init__(self, fp):
        header_lines = []
        while True:
            line = fp.readline()
            if line in ("", b""):
                break
            if isinstance(line, bytes):
                line = line.decode("latin-1")
            header_lines.append(line)
            if line in ("\n", "\r\n"):
                break
        self._message = Parser(policy=policy.compat32).parsestr("".join(header_lines))

    def __getitem__(self, key):
        return self._message.get(key)

    def get(self, key, default=None):
        return self._message.get(key, default)

    def gettype(self):
        return self._message.get_content_type().lower()

    def getencoding(self):
        return (self._message.get("content-transfer-encoding") or "7bit").lower()


def decode(source, output, encoding):
    data = source.read()
    if isinstance(data, str):
        raw = data.encode("latin-1")
    else:
        raw = data

    enc = (encoding or "").lower()
    if enc == "base64":
        decoded = base64.decodebytes(raw)
    elif enc in ("quoted-printable", "quopri"):
        decoded = quopri.decodestring(raw)
    else:
        decoded = raw

    try:
        output.write(decoded)
    except TypeError:
        output.write(decoded.decode("latin-1"))
