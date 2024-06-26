#! /usr/bin/env python
# $Header$
'''SOAP messaging parsing.
'''

try:
    import io as StringIO
except ImportError:
    import io
#import multifile
from email.mime.application import MIMEApplication
from email.parser import BytesParser
#import mimetools
import urllib.request, urllib.parse, urllib.error

from ZSI import _copyright, _child_elements, EvaluateException, TC

class Mimetools:
    def decode(a, b, c):
        c = a

mimetools = Mimetools()

def Opaque(uri, tc, ps, **keywords):
    '''Resolve a URI and return its content as a string.
    '''
    source = urllib.request.urlopen(uri, **keywords)
    enc = source.info().getencoding()
    if enc in ['7bit', '8bit', 'binary']: return source.read()

    data = io.StringIO()
    mimetools.decode(source, data, enc)
    return data.getvalue()


def XML(uri, tc, ps, **keywords):
    '''Resolve a URI and return its content as an XML DOM.
    '''
    source = urllib.request.urlopen(uri, **keywords)
    enc = source.info().getencoding()
    if enc in ['7bit', '8bit', 'binary']:
        data = source
    else:
        data = io.StringIO()
        mimetools.decode(source, data, enc)
        data.seek(0)
    dom = ps.readerclass().fromStream(data)
    return _child_elements(dom)[0]


class NetworkResolver:
    '''A resolver that support string and XML.
    '''

    def __init__(self, prefix=None):
        self.allowed = prefix or []

    def _check_allowed(self, uri):
        for a in self.allowed:
            if uri.startswith(a): return
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

class MIMEResolver:
    '''Multi-part MIME resolver -- SOAP With Attachments, mostly.
    '''

    def __init__(self, ct, f, next=None, uribase='thismessage:/',
    seekable=0, **kw):
        # Get the boundary.  It's too bad I have to write this myself,
        # but no way am I going to import cgi for 10 lines of code!
        for param in ct.split(';'):
            a = param.strip()
            if a.startswith('boundary='):
                if a[9] in [ '"', "'" ]:
                    boundary = a[10:-1]
                else:
                    boundary = a[9:]
                break
        else:
            raise ValueError('boundary parameter not found')

        self.id_dict, self.loc_dict, self.parts = {}, {}, []
        self.next = next
        self.base = uribase
        
        msg = BytesParser(policy=policy.default).parse(f)
        
        
        ma = MIMEApplication(f)
        #mf = multifile.MultiFile(f, seekable)
        body = msg.get_body()
        mf.push(boundary)
        
        part = (head, body)
        while next(mf):
            head = mimetools.Message(mf)
            body = io.StringIO()
            mimetools.decode(mf, body, head.getencoding())
            body.seek(0)
            part = (head, body)
            self.parts.append(part)
            key = head.get('content-id')
            if key:
                if key[0] == '<' and key[-1] == '>': key = key[1:-1]
                self.id_dict[key] = part
            key = head.get('content-location')
            if key: self.loc_dict[key] = part
        mf.pop()

    def GetSOAPPart(self):
        '''Get the SOAP body part.
        '''
        head, part = self.parts[0]
        return io.StringIO(part.getvalue())

    def get(self, uri):
        '''Get the content for the bodypart identified by the uri.
        '''
        if uri.startswith('cid:'):
            # Content-ID, so raise exception if not found.
            head, part = self.id_dict[uri[4:]]
            return io.StringIO(part.getvalue())
        if uri in self.loc_dict:
            head, part = self.loc_dict[uri]
            return io.StringIO(part.getvalue())
        return None

    def Opaque(self, uri, tc, ps, **keywords):
        content = self.get(uri)
        if content: return content.getvalue()
        if not self.__next__: raise EvaluateException("Unresolvable URI " + uri)
        return self.next.Opaque(uri, tc, ps, **keywords)

    def XML(self, uri, tc, ps, **keywords):
        content = self.get(uri)
        if content:
            dom = ps.readerclass().fromStream(content)
            return _child_elements(dom)[0]
        if not self.__next__: raise EvaluateException("Unresolvable URI " + uri)
        return self.next.XML(uri, tc, ps, **keywords)

    def Resolve(self, uri, tc, ps, **keywords):
        if isinstance(tc, TC.XML):
            return self.XML(uri, tc, ps, **keywords)
        return self.Opaque(uri, tc, ps, **keywords)

    def __getitem__(self, cid):
        head, body = self.id_dict[cid]
        newio = io.StringIO(body.getvalue())
        return newio

if __name__ == '__main__': print(_copyright)
