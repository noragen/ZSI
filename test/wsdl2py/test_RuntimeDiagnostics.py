#!/usr/bin/env python

import unittest
from unittest import mock

from ZSI import EvaluateException
from ZSI.generate import commands
from ZSI.parse import ParsedSoap
from ZSI.schema import TypeDefinition


class _BrokenReader:
    def loadFromFile(self, location):
        raise ValueError('boom')

    def loadFromURL(self, location):
        raise ValueError('boom')


class _MissingSubstituteType(TypeDefinition):
    type = ('urn:declared', 'DeclaredType')


class RuntimeDiagnosticsTestCase(unittest.TestCase):
    def test_wsdl2py_load_error_contains_wsdl_context(self):
        with mock.patch.object(commands.WSDLTools, 'WSDLReader',
                               return_value=_BrokenReader()):
            with self.assertRaises(ValueError) as ctx:
                commands.wsdl2py(['missing.wsdl'])
        msg = str(ctx.exception)
        self.assertIn('phase=load', msg)
        self.assertIn('wsdl=missing.wsdl', msg)

    def test_find_local_href_error_contains_element_context(self):
        xml = (
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:m="urn:msg">'
            '<soap:Body><m:Request href="#missing"/></soap:Body>'
            '</soap:Envelope>'
        )
        ps = ParsedSoap(xml)
        with self.assertRaises(EvaluateException) as ctx:
            ps.FindLocalHREF('#missing', ps.body_root)
        msg = str(ctx.exception)
        self.assertIn('element=', msg)
        self.assertIn('urn:msg', msg)
        self.assertIn('Request', msg)

    def test_substitute_type_error_contains_element_context(self):
        xml = (
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:m="urn:msg" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<soap:Body><m:Request xsi:type="m:MissingType"/></soap:Body>'
            '</soap:Envelope>'
        )
        ps = ParsedSoap(xml)
        tc = _MissingSubstituteType()
        with self.assertRaises(EvaluateException) as ctx:
            tc.getSubstituteType(ps.body_root, ps)
        msg = str(ctx.exception)
        self.assertIn('element=', msg)
        self.assertIn('urn:msg', msg)
        self.assertIn('MissingType', msg)


if __name__ == '__main__':
    unittest.main()
