#!/usr/bin/env python

import unittest

from ZSI import schema, ParsedSoap, TC

"""Bug [ 1520092 ] URI Bug: urllib.quote escaping reserved chars
   Bug [ 2748314 ] Malformed type attribute (bad NS) with 2.1a1 but not with 2.
"""

class MyInt_Def(TC.Integer, schema.TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = "urn:vim25"
        type = (schema, "myInt")
        def __init__(self, pname, **kw):
            self.attribute_typecode_dict = {}
            TC.Integer.__init__(self, pname, **kw)
            #class Holder(int):
            #    __metaclass__ = pyclass_type
            #    typecode = self
            #self.pyclass = Holder
            self.pyclass = int

class TestCase(unittest.TestCase):

    def check_type_attribute_qname_in_default_ns(self):
        msg = """
<ns1:test xsi:type="ns1:myInt" xmlns:ns1="urn:vim25" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xmlns="http://www.w3.org/2001/XMLSchema">
100
</ns1:test>"""
        ps = ParsedSoap(msg, envelope=False)
        pyobj = ps.Parse(TC.AnyType(pname=("urn:vim25","test")))
        self.assertTrue(pyobj == 100, 'failed to parse type in default ns')

    def check_element_in_default_ns(self):
        msg = """
<test xsi:type="myInt" xmlns="urn:vim25" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema">
100
</test>"""
        ps = ParsedSoap(msg, envelope=False)
        pyobj = ps.Parse(TC.AnyType(pname=("urn:vim25","test")))
        self.assertTrue(pyobj == 100, 'failed to parse element in default ns')


#
# Creates permutation of test options: "check", "check_any", etc
#
_SEP = '_'
for t in [i[0].split(_SEP) for i in [i for i in list(TestCase.__dict__.items()) if callable(i[1])]]:
    test = ''
    for f in t:
        test += f
        if test in globals(): test += _SEP; continue
        def _closure():
            name = test
            def _makeTestSuite():
                suite = unittest.TestSuite()
                suite.addTest(unittest.makeSuite(TestCase, name))
                return suite
            return _makeTestSuite

        globals()[test] = _closure()
        test += _SEP


makeTestSuite = check
def main():
    unittest.main(defaultTest="makeTestSuite")
if __name__ == "__main__" : main()

