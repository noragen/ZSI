#!/usr/bin/env python
import unittest

from ZSI.ServiceProxy import BoundServiceProxy


class _FakeMethod:
    def __init__(self, name, port):
        self.__name__ = name
        self.port_name = port
        self.soapheaders = []
        self.callinfo = object()


class _FakeParent:
    def __init__(self):
        self._methods = {
            "Echo": [_FakeMethod("Echo", "PortA"), _FakeMethod("Echo", "PortB")]
        }

    def _call(self, name, soapheaders, method=None):
        def fn(**kwargs):
            return {"name": name, "port": getattr(method, "port_name", None), "kwargs": kwargs}

        return fn


class ServiceProxyBindTests(unittest.TestCase):
    def test_bound_proxy_routes_to_selected_port(self):
        parent = _FakeParent()
        bound = BoundServiceProxy(parent, port="PortB")
        result = bound.Echo(msg="hello")
        self.assertEqual("Echo", result["name"])
        self.assertEqual("PortB", result["port"])
        self.assertEqual("hello", result["kwargs"]["msg"])


def makeTestSuite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(ServiceProxyBindTests)


if __name__ == "__main__":
    unittest.main(defaultTest="makeTestSuite")
