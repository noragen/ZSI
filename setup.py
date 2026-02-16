#! /usr/bin/env python
# $Header$
import sys

from setuptools import setup

_url = "http://pywebsvcs.sf.net/"

import configparser
cf = configparser.ConfigParser()
cf.read('setup.cfg')
major = cf.getint('version', 'major')
minor = cf.getint('version', 'minor')
patchlevel = cf.getint('version', 'patchlevel')
candidate = cf.getint('version', 'candidate')
alpha = cf.getint('version', 'alpha')
beta = cf.getint('version', 'beta')

_version = "%d.%d" % ( major, minor )
if patchlevel:
    _version += '.%d' % patchlevel
if candidate:
    _version += 'rc%d' % candidate
elif alpha:
    _version += 'a%d' % alpha
elif beta:
    _version += 'b%d' % beta

try:
    open('ZSI/version.py', 'r').close()
except:
    print('ZSI/version.py not found; run "make"')
    sys.exit(1)

_packages = [ "ZSI", "ZSI.generate", "ZSI.wstools"]
if sys.version_info[0:2] >= (2, 4):
    _packages.append("ZSI.twisted")

setup(
    name="ZSI",
    version=_version,
    license="Python",
    packages=_packages,
    description="Zolera SOAP Infrastructure",
    author="Rich Salz, et al",
    author_email="rsalz@datapower.com",
    maintainer="Rich Salz, et al",
    maintainer_email="pywebsvcs-talk@lists.sf.net",
    url=_url,
    long_description="For additional information, please see " + _url,
    entry_points={
        "console_scripts": [
            "wsdl2py = ZSI.generate.commands:wsdl2py",
        ],
    },
)
