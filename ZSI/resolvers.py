#! /usr/bin/env python
# $Header$
"""SOAP messaging parsing helpers."""

import io
from email import policy
from email.parser import Parser
import hashlib
import urllib.request

from ZSI import _copyright, _child_elements, EvaluateException, TC
from ZSI.telemetry import span
from ZSI.wstools.logging import getLogger as _GetLogger


_log = _GetLogger("ZSI.resolvers")
_CACHE_URL_TO_KEY = {}
_CACHE_CONTENT = {}


def _transfer_encoding(headers):
    return (headers.get("content-transfer-encoding") or "7bit").lower()


def _to_text(data, charset=None):
    if isinstance(data, str):
        return data
    if charset:
        try:
            return data.decode(charset)
        except Exception:
            pass
    return data.decode("latin-1")


def Opaque(uri, tc, ps, **keywords):
    """Resolve a URI and return its content as a string or bytes."""
    _log.debug("resolve opaque", event="resolver.fetch", uri=uri)
    with span("zsi.resolve.opaque", uri=uri):
        cache_key = _CACHE_URL_TO_KEY.get(uri)
        if cache_key and cache_key in _CACHE_CONTENT:
            _log.debug("cache hit", event="resolver.cache.hit", uri=uri, cache_key=cache_key)
            return _CACHE_CONTENT[cache_key]

        source = urllib.request.urlopen(uri, **keywords)
        enc = _transfer_encoding(source.info())
        body = source.read()
        if enc in ("7bit", "8bit", "binary"):
            value = body
        else:
            value = _to_text(body, source.info().get_content_charset())

        digest_source = value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
        digest = hashlib.sha256(digest_source).hexdigest()
        cache_key = f"{uri}#{digest}"
        _CACHE_URL_TO_KEY[uri] = cache_key
        _CACHE_CONTENT[cache_key] = value
        _log.debug("cache store", event="resolver.cache.store", uri=uri, cache_key=cache_key)
        return value


def XML(uri, tc, ps, **keywords):
    """Resolve a URI and return its content as an XML DOM element."""
    _log.debug("resolve xml", event="resolver.fetch", uri=uri)
    with span("zsi.resolve.xml", uri=uri):
        source = urllib.request.urlopen(uri, **keywords)
        body = source.read()
        stream = io.StringIO(_to_text(body, source.info().get_content_charset()))
        dom = ps.readerclass().fromStream(stream)
        return _child_elements(dom)[0]


class NetworkResolver:
    """A resolver that supports string and XML references."""

    def __init__(self, prefix=None):
        self.allowed = prefix or []

    def _check_allowed(self, uri):
        for a in self.allowed:
            if uri.startswith(a):
                return
        _log.warning("resolver rejected uri", event="resolver.reject", uri=uri)
        raise EvaluateException("Disallowed URI prefix")

    def Opaque(self, uri, tc, ps, **keywords):
        self._check_allowed(uri)
        return Opaque(uri, tc, ps, **keywords)

    def XML(self, uri, tc, ps, **keywords):
        self._check_allowed(uri)
        return XML(uri, tc, ps, **keywords)

    def Resolve(self, uri, tc, ps, **keywords):
        if isinstance(tc, TC.XML):
            return XML(uri, tc, ps, **keywords)
        return Opaque(uri, tc, ps, **keywords)


def ClearNetworkResolverCache():
    """Clear process-local resolver cache."""
    _CACHE_URL_TO_KEY.clear()
    _CACHE_CONTENT.clear()


class MIMEResolver:
    """Multi-part MIME resolver (SOAP With Attachments)."""

    def __init__(self, ct, f, next=None, uribase="thismessage:/", seekable=0, **kw):
        self.id_dict, self.loc_dict, self.parts = {}, {}, []
        self.next = next
        self.base = uribase

        raw = f.read()
        payload_text = raw if isinstance(raw, str) else raw.decode("latin-1")
        msg_text = "Content-Type: %s\nMIME-Version: 1.0\n\n%s" % (ct, payload_text)
        msg = Parser(policy=policy.compat32).parsestr(msg_text)

        for part in msg.walk():
            if part.is_multipart():
                continue

            content = part.get_payload(decode=True)
            if content is None:
                content = part.get_payload()
            content_text = _to_text(content or "", part.get_content_charset())

            item = (part, io.StringIO(content_text))
            self.parts.append(item)

            key = part.get("content-id")
            if key:
                key = key.strip()
                if key.startswith("<") and key.endswith(">"):
                    key = key[1:-1]
                self.id_dict[key] = item

            key = part.get("content-location")
            if key:
                self.loc_dict[key] = item

    def GetSOAPPart(self):
        """Get the SOAP body part."""
        if not self.parts:
            raise EvaluateException("No MIME body parts available")
        head, part = self.parts[0]
        return io.StringIO(part.getvalue())

    def get(self, uri):
        """Get content for the body part identified by the URI."""
        if uri.startswith("cid:"):
            item = self.id_dict.get(uri[4:])
            if item:
                head, part = item
                return io.StringIO(part.getvalue())
            return None
        if uri in self.loc_dict:
            head, part = self.loc_dict[uri]
            return io.StringIO(part.getvalue())
        return None

    def Opaque(self, uri, tc, ps, **keywords):
        content = self.get(uri)
        if content:
            return content.getvalue()
        if self.next is None:
            raise EvaluateException("Unresolvable URI " + uri)
        return self.next.Opaque(uri, tc, ps, **keywords)

    def XML(self, uri, tc, ps, **keywords):
        content = self.get(uri)
        if content:
            dom = ps.readerclass().fromStream(content)
            return _child_elements(dom)[0]
        if self.next is None:
            raise EvaluateException("Unresolvable URI " + uri)
        return self.next.XML(uri, tc, ps, **keywords)

    def Resolve(self, uri, tc, ps, **keywords):
        if isinstance(tc, TC.XML):
            return self.XML(uri, tc, ps, **keywords)
        return self.Opaque(uri, tc, ps, **keywords)

    def __getitem__(self, cid):
        head, body = self.id_dict[cid]
        return io.StringIO(body.getvalue())


if __name__ == "__main__":
    print(_copyright)
