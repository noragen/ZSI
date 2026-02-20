#!/usr/bin/env python

import os
import tempfile
import unittest

from ZSI.generate import commands


def dispatch():
    return makeTestSuite()


def local():
    return makeTestSuite()


def net():
    return makeTestSuite()


def all():
    return makeTestSuite()


class GeneratorAdversarialSmokeTestCase(unittest.TestCase):
    def _write(self, directory, filename, content):
        path = os.path.join(directory, filename)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
        return path

    def _assert_load_context(self, error, wsdl_path):
        message = str(error)
        self.assertIn('phase=load', message)
        self.assertIn('loader=loadFromFile', message)
        self.assertIn('wsdl=%s' % wsdl_path, message)

    def test_local_unreachable_import_chain_has_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            top_xsd = self._write(
                tmp,
                'top.xsd',
                '''<?xml version="1.0"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:test:adversarial:chain">
  <xsd:include schemaLocation="level1.xsd"/>
  <xsd:element name="Top" type="xsd:string"/>
</xsd:schema>
''',
            )
            self._write(
                tmp,
                'level1.xsd',
                '''<?xml version="1.0"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:test:adversarial:chain">
  <xsd:include schemaLocation="missing_leaf.xsd"/>
  <xsd:element name="Leaf" type="xsd:string"/>
</xsd:schema>
''',
            )

            with self.assertRaises(Exception) as ctx:
                commands.wsdl2py(['--schema', '--output-dir', tmp, top_xsd])

            self._assert_load_context(ctx.exception, top_xsd)
            self.assertIn('missing_leaf.xsd', str(ctx.exception))

    def test_circular_include_chain_has_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            a_path = self._write(
                tmp,
                'a.xsd',
                '''<?xml version="1.0"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:test:adversarial:circular">
  <xsd:include schemaLocation="b.xsd"/>
  <xsd:element name="A" type="xsd:string"/>
</xsd:schema>
''',
            )
            self._write(
                tmp,
                'b.xsd',
                '''<?xml version="1.0"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:test:adversarial:circular">
  <xsd:include schemaLocation="a.xsd"/>
  <xsd:element name="B" type="xsd:string"/>
</xsd:schema>
''',
            )

            with self.assertRaises(Exception) as ctx:
                commands.wsdl2py(['--schema', '--output-dir', tmp, a_path])

            self._assert_load_context(ctx.exception, a_path)
            self.assertIn('recursion', str(ctx.exception).lower())

    def test_broken_structure_has_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            wsdl_path = self._write(
                tmp,
                'broken.wsdl',
                '''<?xml version="1.0"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:xsd="http://www.w3.org/2001/XMLSchema"
             targetNamespace="urn:test:adversarial:broken"
             name="BrokenService">
  <types>
    <xsd:schema>
      <xsd:element name="Broken" type="xsd:string">
    </xsd:schema>
  </types>
</definitions>
''',
            )

            with self.assertRaises(Exception) as ctx:
                commands.wsdl2py(['--output-dir', tmp, wsdl_path])

            self._assert_load_context(ctx.exception, wsdl_path)
            self.assertIn('mismatched tag', str(ctx.exception).lower())


def makeTestSuite():
    return unittest.TestSuite((
        unittest.makeSuite(GeneratorAdversarialSmokeTestCase, 'test_'),
    ))


if __name__ == '__main__':
    unittest.TestProgram(defaultTest='makeTestSuite')
