#!/usr/bin/env python

import time
import unittest
from io import StringIO

import ZSI
from ZSI.writer import SoapWriter
from ZSI import _get_element_nsuri_name
from ZSI.schema import GED, TypeDefinition, ElementDeclaration
from ZSI.parse import ParsedSoap

class TestList1_Def(ZSI.TC.List, TypeDefinition):
    itemType = ('http://www.w3.org/2001/XMLSchema', 'dateTime')
    schema = "urn:test"
    type = (schema, "tUsage")
    def __init__(self, pname, **kw):
        ZSI.TC.List.__init__(self, pname, **kw)

class TestList2_Def(ZSI.TC.List, TypeDefinition):
    itemType = ZSI.TC.gDateTime()
    schema = "urn:test"
    type = (schema, "tUsage")
    def __init__(self, pname, **kw):
        ZSI.TC.List.__init__(self, pname, **kw)

class ListTestCase(unittest.TestCase):
    "test List TypeCode"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def check_list_defs(self):
        gl = globals()
        for klass in [gl[h] for h in [g for g in gl if (g.startswith('TestList') and
            issubclass(gl[g],ZSI.TC.List))]]:

            typecode = klass('whatever', nillable=True)
            data = None
            for i in range(10):
                sw = SoapWriter()
                sw.serialize(data, typecode)
                s = str(sw)
                #print s
                ps = ParsedSoap(s); pyobj = ps.Parse(typecode)
                assert pyobj == data, 'Data corruption expected "%s", got "%s"' %(str(data),str(pyobj))
                if data is None:
                    data = []; continue;

                #
                # cut last 3 fields off: weekday (0-6, Monday is 0), Julian day (day in the year, 1-366),
                # DST (Daylight Savings Time) flag (-1, 0 or 1)
                #
                utc = list(time.gmtime(i)[:-3]) + [999,0,0]
                data.append(tuple(utc))

def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ListTestCase, "check"))
    return suite

def main():
    unittest.main(defaultTest="makeTestSuite")

if __name__ == '__main__':
    main()

