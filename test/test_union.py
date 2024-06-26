#!/usr/bin/env python
import base64
import unittest
import sys
from io import StringIO

import ZSI
from ZSI import _get_element_nsuri_name
from ZSI.schema import GED, TypeDefinition, ElementDeclaration
from ZSI.parse import ParsedSoap
from ZSI.wstools.c14n import Canonicalize
from ZSI.wstools.Namespaces import WSA200403, SOAP

#
# Generated code
class ns3:
    class localPAssertionId_Dec(ElementDeclaration):
        literal = "localPAssertionId"
        schema = "http://www.pasoa.org/schemas/version024/PStruct.xsd"
        def __init__(self, **kw):
            kw["pname"] = ("http://www.pasoa.org/schemas/version024/PStruct.xsd","localPAssertionId")
            kw["aname"] = "_localPAssertionId"
            if ns3.LocalPAssertionId_Def not in ns3.localPAssertionId_Dec.__bases__:
                bases = list(ns3.localPAssertionId_Dec.__bases__)
                bases.insert(0, ns3.LocalPAssertionId_Def)
                ns3.localPAssertionId_Dec.__bases__ = tuple(bases)

            ns3.LocalPAssertionId_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "localPAssertionId_Dec_Holder"


    class LocalPAssertionId_Def(ZSI.TC.Union, TypeDefinition):
        memberTypes = [('http://www.w3.org/2001/XMLSchema', 'long'), ('http://www.w3.org/2001/XMLSchema', 'string'), ('http://www.w3.org/2001/XMLSchema', 'anyURI')]
        schema = "http://www.pasoa.org/schemas/version024/PStruct.xsd"
        type = (schema, "LocalPAssertionId")
        def __init__(self, pname, **kw):
            ZSI.TC.Union.__init__(self, pname, **kw)

class TestUnionTC(ZSI.TC.Union, TypeDefinition):
    memberTypes = [('http://www.w3.org/2001/XMLSchema', 'long'), ('http://www.w3.org/2001/XMLSchema', 'dateTime')]
    schema = "urn:test:union"
    type = (schema, "TestUnion")
    def __init__(self, pname, **kw):
        ZSI.TC.Union.__init__(self, pname, **kw)

class UnionTestCase(unittest.TestCase):
    "test Union TypeCode"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def check_union_long(self):
        import time
        typecode = GED("http://www.pasoa.org/schemas/version024/PStruct.xsd", "localPAssertionId")
        for value in (1234455, "whatever", "urn:whatever"):
            sw = ZSI.SoapWriter()
            sw.serialize(value, typecode)

            xml = str(sw)
            ps = ParsedSoap(xml)
            pyobj = ps.Parse(typecode)

            # Union Limitation:
            #     currently it tries to parse it sequentially via memberTypes,
            #     so string is going to parse the URI when we want anyURI
            self.assertTrue(value == pyobj, 'Expected equivalent')

    def check_union_text_to_data(self):
        from ZSI.TC import EvaluateException
        class _PS:
            def Backtrace(self, *a, **kw): return ""
        typecode = TestUnionTC("TestUnion")
        self.assertEqual(100, typecode.text_to_data('100', None, None), "Fail to parse long")
        date = typecode.text_to_data("2002-10-30T12:30:00Z", None, None)
        self.assertEqual((2002, 10, 30), date[:3], "Fail to parse dateTime")
        self.assertRaises(EvaluateException, typecode.text_to_data, "urn:string", None, _PS())


def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UnionTestCase, "check"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == '__main__':
    main()

