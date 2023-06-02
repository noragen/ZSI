#!/usr/bin/python
# -*- coding: utf-8 -*-

############################################################################
# Monte M. Goode, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################

# contains text container classes for new generation generator

# $Id: containers.py 1499 2011-11-18 00:37:13Z boverhof $

import contextlib
import warnings

import ZSI
from ZSI.TC import _is_xsd_or_soap_ns
from ZSI.generate import WSISpec, WSInteropError, Wsdl2PythonError, \
    WsdlGeneratorError, WSDLFormatError
from ZSI.typeinterpreter import BaseTypeInterpreter
from ZSI.wstools import XMLSchema, WSDLTools
from ZSI.wstools.Namespaces import SCHEMA, SOAP, WSDL, APACHE
from ZSI.wstools.logging import getLogger as _GetLogger
from .utility import NamespaceAliasDict as NAD, \
    NCName_to_ClassName as NC_to_CN
from .utility import StringWriter, TextProtect, \
    TextProtectAttributeName, GetPartsSubNames

ID1 = '    '
ID2 = 2 * ID1
ID3 = 3 * ID1
ID4 = 4 * ID1
ID5 = 5 * ID1
ID6 = 6 * ID1

KW = {
    'ID1': ID1,
    'ID2': ID2,
    'ID3': ID3,
    'ID4': ID4,
    'ID5': ID5,
    'ID6': ID6,
}

DEC = '_Dec'
DEF = '_Def'

type_class_name = lambda n: f'{NC_to_CN(n)}{DEF}'
element_class_name = lambda n: f'{NC_to_CN(n)}{DEC}'


def IsRPC(item):
    """item -- OperationBinding instance.
    """

    if not isinstance(item, WSDLTools.OperationBinding):
        raise TypeError('IsRPC takes 1 argument of type WSDLTools.OperationBinding'
                        )
    soapbinding = item.getBinding().findBinding(WSDLTools.SoapBinding)
    sob = item.findBinding(WSDLTools.SoapOperationBinding)
    style = soapbinding.style
    if sob is not None:
        style = sob.style or soapbinding.style
    return style == 'rpc'


def IsLiteral(item):
    """item -- MessageRoleBinding instance.
    """

    if not isinstance(item, WSDLTools.MessageRoleBinding):
        raise TypeError('IsLiteral takes 1 argument of type WSDLTools.MessageRoleBinding'
                        )
    sbb = None
    if item.type in ['input', 'output']:
        sbb = item.findBinding(WSDLTools.SoapBodyBinding)
    if sbb is None:
        raise ValueError('Missing soap:body binding.')
    return sbb.use == 'literal'


def SetTypeNameFunc(func):
    global type_class_name
    type_class_name = func


def SetElementNameFunc(func):
    global element_class_name
    element_class_name = func


def GetClassNameFromSchemaItem(item, do_extended=False):

    assert isinstance(item, XMLSchema.XMLSchemaComponent), \
        'must be a schema item.'
    alias = NAD.getAlias(item.getTargetNamespace())
    return (
        f"{alias}.{NC_to_CN(f'{type_class_name(item.getAttributeName())}')}"
        if item.isDefinition() is True
        else None
    )


def FromMessageGetSimpleElementDeclaration(message):
    '''If message consists of one part with an element attribute,
    and this element is a simpleType return a string representing
    the python type, else return None.

    '''

    assert isinstance(message, WSDLTools.Message), \
        'expecting WSDLTools.Message'

    if len(message.parts) == 1 and message.parts[0].element is not None:
        part = message.parts[0]
        (nsuri, name) = part.element
        wsdl = message.getWSDL()
        ns_types = wsdl.types
        if nsuri in ns_types and name in ns_types[nsuri].elements:
            e = ns_types[nsuri].elements[name]
            if isinstance(e, XMLSchema.ElementDeclaration) and e.getAttribute(
                'type'
            ):
                typ = e.getAttribute('type')
                bt = BaseTypeInterpreter()
                return bt.get_pythontype(typ[1], typ[0])
    return None


class AttributeMixIn:
    '''for containers that can declare attributes.
    Class Attributes:
        attribute_typecode -- typecode attribute name typecode dict
        built_in_refs -- attribute references that point to built-in
            types.  Skip resolving them into attribute declarations.
    '''

    attribute_typecode = 'self.attribute_typecode_dict'
    built_in_refs = [
        (SOAP.ENC, 'arrayType'),
        (SOAP.ENC12, 'arrayType'),
    ]

    def _setAttributes(self, attributes):
        """parameters
        attributes -- a flat list of all attributes,
        from this list all items in attribute_typecode_dict will
        be generated into attrComponents.

        returns a list of strings representing the attribute_typecode_dict.
        """

        atd_list = formatted_attribute_list = []
        if not attributes:
            return formatted_attribute_list

        atd_list.append('# attribute handling code')
        idx = 0
        atd = self.attribute_typecode
        while idx < len(attributes):
            a = attributes[idx]
            idx += 1
            if a.isWildCard() and a.isDeclaration():
                atd_list.append(
                    f'{atd}[("{SCHEMA.XSD3}","anyAttribute")] = ZSI.TC.AnyElement()'
                )
            elif a.isDeclaration():
                tdef = a.getTypeDefinition('type')
                if tdef is not None:
                    tc = f'{NAD.getAlias(tdef.getTargetNamespace())}.{self.mangle(type_class_name(tdef.getAttributeName()))}(None)'
                else:

                    # built-in

                    t = a.getAttribute('type')
                    try:
                        tc = BTI.get_typeclass(t[1], t[0])
                    except Exception:
                        # hand back a string by default.

                        tc = ZSI.TC.String

                    if tc is not None:
                        tc = f'{tc}()'

                key = None
                if a.getAttribute('form') == 'qualified':
                    key = f"""("{a.getTargetNamespace()}","{a.getAttribute('name')}")"""
                elif a.getAttribute('form') == 'unqualified':
                    key = f""""{a.getAttribute('name')}\""""
                else:
                    raise ContainerError(
                        f"attribute form must be un/qualified {a.getAttribute('form')}"
                    )

                atd_list.append(f'{atd}[{key}] = {tc}')
            elif a.isReference() and a.isAttributeGroup():

                # flatten 'em out....

                for ga in a.getAttributeGroup().getAttributeContent():
                    attributes += (ga,)
            elif a.isReference():

                try:
                    ga = a.getAttributeDeclaration()
                except XMLSchema.SchemaError:
                    key = a.getAttribute('ref')
                    self.logger.debug('No schema item for attribute ref (%s, %s)'
                                      % key)
                    if key in self.built_in_refs:
                        continue
                    raise

                tp = None
                if ga is not None:
                    tp = ga.getTypeDefinition('type')
                    key = f"""("{ga.getTargetNamespace()}","{ga.getAttribute('name')}")"""

                if ga is None:

                    # TODO: probably SOAPENC:arrayType

                    key = f"""("{a.getAttribute('ref').getTargetNamespace()}","{a.getAttribute('ref').getName()}")"""
                    atd_list.append(f'{atd}[{key}] = ZSI.TC.String()')
                elif tp is None:

                    # built in simple type

                    try:
                        (namespace, typeName) = ga.getAttribute('type')
                    except TypeError:

                        # TODO: attribute declaration could be anonymous type
                        # hack in something to work

                        atd_list.append(f'{atd}[{key}] = ZSI.TC.String()')
                    else:
                        atd_list.append(f'{atd}[{key}] = {BTI.get_typeclass(typeName, namespace)}()')
                else:
                    typeName = tp.getAttribute('name')
                    namespace = tp.getTargetNamespace()
                    alias = NAD.getAlias(namespace)
                    key = f"""("{ga.getTargetNamespace()}","{ga.getAttribute('name')}")"""
                    atd_list.append(f'{atd}[{key}] = {alias}.{type_class_name(typeName)}(None)')
            else:
                raise TypeError(f'expecting an attribute: {a.getItemTrace()}')

        return formatted_attribute_list


class ContainerError(Exception):
    pass


class ContainerBase:
    '''Base class for all Containers.
        func_aname -- function that takes name, and returns aname.
    '''

    func_aname = staticmethod(TextProtectAttributeName)
    logger = _GetLogger('ContainerBase')

    def __init__(self):
        self.content = StringWriter('\n')
        self.__setup = False
        self.ns = None

    def __str__(self):
        return self.getvalue()

    # - string content methods

    def mangle(self, s):
        '''class/variable name illegalities
        '''

        return TextProtect(s)

    def write(self, s):
        self.content.write(s)

    def writeArray(self, a):
        self.content.write('\n'.join(a))

    def _setContent(self):
        '''override in subclasses.  formats the content in the desired way.
        '''

        raise NotImplementedError('abstract method not implemented')

    def getvalue(self):
        if not self.__setup:
            self._setContent()
            self.__setup = True

        return self.content.getvalue()

    # - namespace utility methods

    def getNSAlias(self):
        if self.ns is not None:
            return NAD.getAlias(self.ns)
        raise ContainerError(f'no self.ns attr defined in {self.__class__}')

    def getNSModuleName(self):
        if self.ns:
            return NAD.getModuleName(self.ns)
        raise ContainerError(f'no self.ns attr defined in {self.__class__}')

    def getAttributeName(self, name):
        """represents the aname
        """

        if self.func_aname is None:
            return name
        assert callable(
            self.func_aname
        ), f'expecting callable method for attribute func_aname, not {type(self.func_aname)}'
        f = self.func_aname
        return f(name)


# -- containers for services file components

class ServiceContainerBase(ContainerBase):
    clientClassSuffix = 'SOAP'
    logger = _GetLogger('ServiceContainerBase')


class ServiceHeaderContainer(ServiceContainerBase):
    imports = ['\nimport urlparse, types',
               'from ZSI.TCcompound import ComplexType, Struct',
               'from ZSI import client',
               'from ZSI.schema import GED, GTD', 'import ZSI']
    logger = _GetLogger('ServiceHeaderContainer')

    def __init__(self, do_extended=False):
        ServiceContainerBase.__init__(self)

        self.basic = self.imports[:]
        self.types = None
        self.messages = None
        self.extras = []
        self.do_extended = do_extended

    def setTypesModuleName(self, module):
        self.types = module

    def setMessagesModuleName(self, module):
        self.messages = module

    def appendImport(self, statement):
        '''append additional import statement(s).
        import_stament -- tuple or list or str
        '''

        if type(statement) in (list, tuple):
            self.extras += statement
        else:
            self.extras.append(statement)

    def _setContent(self):
        if self.messages:
            self.write(f'from {self.messages} import *')
        if self.types:
            self.write(f'from {self.types} import *')

        imports = self.basic[:]
        imports += self.extras
        self.writeArray(imports)


class ServiceLocatorContainer(ServiceContainerBase):
    logger = _GetLogger('ServiceLocatorContainer')

    def __init__(self):
        ServiceContainerBase.__init__(self)
        self.serviceName = None
        self.portInfo = []
        self.locatorName = None
        self.portMethods = []

    def setUp(self, service):
        assert isinstance(service, WSDLTools.Service), \
                    'expecting WDSLTools.Service instance.'

        self.serviceName = service.name
        for p in service.ports.values():
            try:
                ab = p.getAddressBinding()
            except WSDLTools.WSDLError:
                self.logger.warning(f'Skip port({p.name}), missing address binding')
                continue
            if not isinstance(ab, WSDLTools.SoapAddressBinding):
                self.logger.warning(f'Skip port({p.name}), not a SOAP-1.1 address binding')
                continue

            # info = (p.getBinding().getPortType().name, p.getBinding().name, ab.location)

            self.portInfo.append((NC_to_CN(p.name),
                                  NC_to_CN(p.getBinding().name),
                                  ab.location))

    def getLocatorName(self):
        '''return class name of generated locator.
        '''

        return self.locatorName

    def getPortMethods(self):
        '''list of get port accessor methods of generated locator class.
        '''

        return self.portMethods

    def _setContent(self):
        if not self.serviceName:
            raise ContainerError('no service name defined!')

        self.serviceName = self.mangle(self.serviceName)
        self.locatorName = f'{self.serviceName}Locator'
        locator = ['# Locator', f'class {self.locatorName}:']
        self.portMethods = []
        kwargs = KW.copy()
        for (port, bind, addr) in self.portInfo:
            # access method each port

            method = f'get{port}'
            kwargs.update(dict(
                port=port,
                bind=bind,
                addr=addr,
                service=self.serviceName,
                suffix=self.clientClassSuffix,
                method=method,
            ))

            locator += ['%(ID1)s%(port)s_address = "%(addr)s"'
                        % kwargs, '%(ID1)sdef get%(port)sAddress(self):'
                        % kwargs,
                        '%(ID2)sreturn %(service)sLocator.%(port)s_address'
                        % kwargs,
                        '%(ID1)sdef %(method)s(self, url=None, **kw):'
                        % kwargs,
                        '%(ID2)sreturn %(bind)s%(suffix)s(url or %(service)sLocator.%(port)s_address, **kw)'
                        % kwargs]

            self.portMethods.append(method)

        self.writeArray(locator)


class ServiceOperationContainer(ServiceContainerBase):
    logger = _GetLogger('ServiceOperationContainer')

    def __init__(self, useWSA=False, do_extended=False):
        '''Parameters:
              useWSA -- boolean, enable ws-addressing
              do_extended -- boolean
        '''

        ServiceContainerBase.__init__(self)
        self.useWSA = useWSA
        self.do_extended = do_extended

    def hasInput(self):
        return self.inputName is not None

    def hasOutput(self):
        return self.outputName is not None

    def isRPC(self):
        return IsRPC(self.binding_operation)

    def isLiteral(self, input=True):
        msgrole = self.binding_operation.input
        if input is False:
            msgrole = self.binding_operation.output
        return IsLiteral(msgrole)

    def isSimpleType(self, input=True):
        return self.outputSimpleType if input is False else self.inputSimpleType

    def getOperation(self):
        return self.port.operations.get(self.name)

    def getBOperation(self):
        return self.port.get(self.name)

    def getOperationName(self):
        return self.name

    def setUp(self, item):
        '''
        Parameters:
            item -- WSDLTools BindingOperation instance.
        '''

        if not isinstance(item, WSDLTools.OperationBinding):
            raise TypeError('Expecting WSDLTools Operation instance')

        if not item.input:
            raise WSDLFormatError(
                f'No <input/> in <binding name="{item.getBinding().name}"><operation name="{item.name}">'
            )

        self.name = None
        self.port = None
        self.soapaction = None
        self.inputName = None
        self.outputName = None
        self.inputSimpleType = None
        self.outputSimpleType = None
        self.inputAction = None
        self.outputAction = None
        self.port = port = item.getBinding().getPortType()
        self._wsdl = item.getWSDL()
        self.name = name = item.name
        self.binding_operation = bop = item

        self.soap_input_headers = None
        self.soap_output_headers = None

        op = port.operations.get(name)
        if op is None:
            raise WSDLFormatError(
                f'<portType name="{port.name}"/> no match for <binding name="{item.getBinding().name}"><operation name="{item.name}">'
            )

        soap_bop = bop.findBinding(WSDLTools.SoapOperationBinding)
        if soap_bop is None:
            raise Exception('SOAPBindingError',
                            'expecting SOAP Bindings')

        self.soapaction = soap_bop.soapAction
        sbody = bop.input.findBinding(WSDLTools.SoapBodyBinding)
        if not sbody:
            raise Exception(
                'SOAPBindingError',
                f'Missing <binding name="{port.binding.name}"><operation name="{bop.name}"><input><soap:body>',
            )

        self.encodingStyle = None
        if sbody.use == 'encoded':
            assert sbody.encodingStyle in (
                SOAP.ENC,
                SOAP.ENC12,
            ), f'Supporting encodingStyle={SOAP.ENC}, not {sbody.encodingStyle}'
            self.encodingStyle = sbody.encodingStyle

        self.inputName = op.getInputMessage().name
        self.inputSimpleType = \
                FromMessageGetSimpleElementDeclaration(op.getInputMessage())
        self.inputAction = op.getInputAction()
        self.soap_input_headers = \
                bop.input.findBindings(WSDLTools.SoapHeaderBinding)

        if bop.output is not None:
            self._extracted_from_setUp_65(bop, item, name, op)

    # TODO Rename this here and in `setUp`
    def _extracted_from_setUp_65(self, bop, item, name, op):
        sbody = bop.output.findBinding(WSDLTools.SoapBodyBinding)
        if not item.output:
            raise WSDLFormatError(f'Operation {name}, no match for output binding')

        self.outputName = op.getOutputMessage().name
        self.outputSimpleType = \
                FromMessageGetSimpleElementDeclaration(op.getOutputMessage())
        self.outputAction = op.getOutputAction()
        self.soap_output_headers = \
                bop.output.findBindings(WSDLTools.SoapHeaderBinding)

    def _setContent(self):
        """create string representation of operation.
        """

        tCheck = f'if isinstance(request, {self.inputName}) is False:'
        bindArgs = ''
        if self.encodingStyle is not None:
            bindArgs = f'encodingStyle="{self.encodingStyle}", '

        if self.useWSA:
            wsactionIn = f'wsaction = "{self.inputAction}"'
            wsactionOut = f'wsaction = "{self.outputAction}"'
            bindArgs += \
                    'wsaction=wsaction, endPointReference=self.endPointReference, '
            responseArgs = ', wsaction=wsaction'
        else:
            wsactionIn = '# no input wsaction'
            wsactionOut = '# no output wsaction'
            responseArgs = ''

        bindArgs += '**kw)'

        if self.do_extended:
            method = self._extracted_from__setContent_25(wsactionIn, bindArgs)
        elif self.soap_input_headers:
            method = [
                f'{ID1}# op: {self.name}',
                f'{ID1}def {self.name}(self, request, soapheaders=(), **kw):',
                f'{ID2}{tCheck}',
                '%sraise TypeError, "%%s incorrect request type" %% (%s)'
                % (ID3, 'request.__class__'),
                f'{ID2}{wsactionIn}',
                f'{ID2}# TODO: Check soapheaders',
                f'{ID2}self.binding.Send(None, None, request, soapaction="{self.soapaction}", soapheaders=soapheaders, {bindArgs}',
            ]
        else:
            method = [
                f'{ID1}# op: {self.name}',
                f'{ID1}def {self.name}(self, request, **kw):',
                f'{ID2}{tCheck}',
                '%sraise TypeError, "%%s incorrect request type" %% (%s)'
                % (ID3, 'request.__class__'),
                f'{ID2}{wsactionIn}',
                f'{ID2}self.binding.Send(None, None, request, soapaction="{self.soapaction}", {bindArgs}',
            ]

        #
        # BP 1.0: rpc/literal
        # WSDL 1.1 Section 3.5 could be interpreted to mean the RPC response
        # wrapper element must be named identical to the name of the
        # wsdl:operation.
        # R2729

        #
        # SOAP-1.1 Note: rpc/encoded
        # Each parameter accessor has a name corresponding to the name of the
        # parameter and type corresponding to the type of the parameter. The name of
        # the return value accessor is not significant. Likewise, the name of the struct is
        # not significant. However, a convention is to name it after the method name
        # with the string "Response" appended.
        #

        if not self.outputName:
            method.append(f'{ID2}#check for soap, assume soap:fault')
            method.append(
                f'{ID2}if self.binding.IsSOAP(): self.binding.Receive(None, **kw)'
            )
            self.writeArray(method)
            return

        response = [f'{ID2}{wsactionOut}']
        if self.isRPC() and not self.isLiteral():

            # rpc/encoded Replace wrapper name with None

            response.append(
                f'{ID2}typecode = Struct(pname=None, ofwhat={self.outputName}.typecode.ofwhat, pyclass={self.outputName}.typecode.pyclass)'
            )
            response.append(
                f'{ID2}response = self.binding.Receive(typecode{responseArgs})'
            )
        else:
            response.append(
                f'{ID2}response = self.binding.Receive({self.outputName}.typecode{responseArgs})'
            )

        # only support lit

        if self.soap_output_headers:
            sh = '['
            for shb in self.soap_output_headers:

                # shb.encodingStyle, shb.use, shb.namespace

                shb.message
                shb.part
                try:
                    msg = self._wsdl.messages[shb.message]
                    part = msg.parts[shb.part]
                    if part.element is not None:
                        sh += f'GED{str(part.element)},'
                    else:
                        warnings.warn(f'skipping soap output header in Message "{str(msg)}"')
                except:
                    raise WSDLFormatError(
                        f'failure processing output header typecodes, could not find message "{shb.message}" or its part "{shb.part}"'
                    )

            sh += ']'
            if len(sh) > 2:
                response.append(
                    f'{ID2}self.soapheaders = self.binding.ps.ParseHeaderElements({sh})'
                )

        if self.outputSimpleType:
            response.append(f'{ID2}return {self.outputName}(response)')
        elif self.do_extended:
            self._extracted_from__setContent_165(response)
        else:
            response.append(f'{ID2}return response')
        method += response

        self.writeArray(method)

    # TODO Rename this here and in `_setContent`
    def _extracted_from__setContent_165(self, response):
        partsList = \
                list(self.getOperation().getOutputMessage().parts.values())
        subNames = GetPartsSubNames(partsList, self._wsdl)
        args = []
        for pa in subNames:
            args += pa

        for arg in args:
            response.append(
                f'{ID2}{self.mangle(arg)} = response.{self.getAttributeName(arg)}'
            )
        margs = ','.join(args)
        response.append(f'{ID2}return {margs}')

    # TODO Rename this here and in `_setContent`
    def _extracted_from__setContent_25(self, wsactionIn, bindArgs):
        #self.getOperation().getInputMessage().name
        partsList = \
                    list(self.getOperation().getInputMessage().parts.values())
        try:
            subNames = GetPartsSubNames(partsList, self._wsdl)
        except TypeError as e:
            raise Wsdl2PythonError(
                'Extended generation failure: only supports doc/lit, '
                + 'and all element attributes (<message><part element='
                + '"my:GED"></message>) must refer to single global '
                + 'element declaration with complexType content.  '
                + '''

**** TRY WITHOUT EXTENDED ****
'''
            ) from e

        args = []
        for pa in subNames:
            args += pa

        wrap_str = ''.join(
            '%srequest.%s = %s\n'
            % (ID2, self.getAttributeName(arg), self.mangle(arg))
            for arg in args
        )
        # args = [pa.name for pa in self.getOperation().getInputMessage().parts.values()]

        argsStr = ','.join(args)
        if len(argsStr) > 1:  # add inital comma if args exist
            argsStr = f', {argsStr}'

        kwstring = 'kw = {}'
        return [
            f'{ID1}# op: {self.getOperation().getInputMessage()}',
            f'{ID1}def {self.name}(self{argsStr}):',
            '\n%srequest = %s()' % (ID2, self.inputName),
            f'{wrap_str}',
            f'{ID2}{kwstring}',
            f'{ID2}{wsactionIn}',
            f'{ID2}self.binding.Send(None, None, request, soapaction="{self.soapaction}", {bindArgs}',
        ]


class BindingDescription(ServiceContainerBase):
    '''writes out SOAP Binding class

    class variables:
        readerclass --
        writerclass --
        operationclass -- representation of each operation.
    '''

    readerclass = None
    writerclass = None
    operationclass = ServiceOperationContainer
    logger = _GetLogger('BindingDescription')

    def __init__(
            self,
            useWSA=False,
            do_extended=False,
            wsdl=None,
    ):
        '''Parameters:
        name -- binding name
        property -- resource properties
        useWSA   -- boolean, enable ws-addressing
        name -- binding name
        '''

        ServiceContainerBase.__init__(self)
        self.useWSA = useWSA
        self.rProp = None

        # self.bName = None

        self.operations = None
        self.do_extended = do_extended
        self._wsdl = wsdl  # None unless do_extended == True

    def setReaderClass(cls, className):
        """specify a reader class name, this must be imported
        in service module.
        """

        cls.readerclass = className

    setReaderClass = classmethod(setReaderClass)

    def setWriterClass(cls, className):
        '''specify a writer class name, this must be imported
        in service module.
        '''

        cls.writerclass = className

    setWriterClass = classmethod(setWriterClass)

    def setOperationClass(cls, className):
        """specify an operation container class name.
        """

        cls.operationclass = className

    setOperationClass = classmethod(setOperationClass)

    def setUp(self, item):
        '''This method finds all SOAP Binding Operations, it will skip
        all bindings that are not SOAP.
        item -- WSDL.Binding instance
        '''

        assert isinstance(item, WSDLTools.Binding), \
                            'expecting WSDLTools Binding instance'

        portType = item.getPortType()
        self._kwargs = KW.copy()
        self._kwargs['bind'] = NC_to_CN(item.name)
        self.operations = []
        self.rProp = portType.getResourceProperties()
        soap_binding = item.findBinding(WSDLTools.SoapBinding)
        if soap_binding is None:
            raise Wsdl2PythonError(f'Binding({item.name}) missing WSDLTools.SoapBinding')

        for bop in item.operations.values():
            soap_bop = bop.findBinding(WSDLTools.SoapOperationBinding)
            if soap_bop is None:
                self.logger.warning(
                    f'Skip Binding({item.name}) operation({bop.name}) no SOAP Binding Operation'
                )
                continue

            # soapAction = soap_bop.soapAction

            if bop.input is not None:
                soapBodyBind = bop.input.findBinding(WSDLTools.SoapBodyBinding)
                if soapBodyBind is None:
                    self.logger.warning(
                        f'Skip Binding({item.name}) operation({bop.name}) Bindings({bop.extensions}) not supported'
                    )
                    continue

            op = portType.operations.get(bop.name)
            if op is None:
                raise Wsdl2PythonError(f'no matching portType/Binding operation({bop.name})')

            c = self.operationclass(useWSA=self.useWSA,
                                    do_extended=self.do_extended)
            c.setUp(bop)
            self.operations.append(c)

    def _setContent(self):
        if self.useWSA is True:
            args = 'endPointReference=None, **kw'
            epr = 'self.endPointReference = endPointReference'
        else:
            args = '**kw'
            epr = '# no ws-addressing'

        rp = f'kw.setdefault("ResourceProperties", ("{self.rProp[0]}","{self.rProp[1]}"))' \
            if self.rProp \
            else '# no resource properties'

        kwargs = self._kwargs
        kwargs.update(dict(
            suffix=self.clientClassSuffix,
            args=args,
            epr=epr,
            rp=rp,
            readerclass=self.readerclass,
            writerclass=self.writerclass,
        ))

        methods = [
            '# Methods',
            'class %(bind)s%(suffix)s:' % kwargs,
            '%(ID1)sdef __init__(self, url, %(args)s):' % kwargs,
            '%(ID2)skw.setdefault("readerclass", %(readerclass)s)'
            % kwargs,
            '%(ID2)skw.setdefault("writerclass", %(writerclass)s)'
            % kwargs,
            '%(ID2)s%(rp)s' % kwargs,
            '%(ID2)sself.binding = client.Binding(url=url, **kw)'
            % kwargs,
            '%(ID2)s%(epr)s' % kwargs,
        ]

        for op in self.operations:
            methods += [op.getvalue()]

        self.writeArray(methods)


ServiceOperationsClassContainer = BindingDescription


class MessageContainerInterface:
    logger = _GetLogger('MessageContainerInterface')

    def setUp(
            self,
            port,
            soc,
            input,
    ):
        '''sets the attribute _simple which represents a
        primitive type message represents, or None if not primitive.

        soc -- WSDLTools.ServiceOperationContainer instance
        port -- WSDLTools.Port instance
        input-- boolean, input messasge or output message of operation.
        '''

        raise NotImplementedError('Message container must implemented setUp.'
                                  )


class ServiceDocumentLiteralMessageContainer(ServiceContainerBase,
                                             MessageContainerInterface):
    logger = _GetLogger('ServiceDocumentLiteralMessageContainer')

    def __init__(self, do_extended=False):

        ServiceContainerBase.__init__(self)
        self.do_extended = do_extended

    def setUp(
            self,
            port,
            soc,
            input,
    ):

        content = self.content

        # TODO: check soapbody for part name

        self._simple = soc.isSimpleType(soc.getOperationName())
        name = soc.getOperationName()

        # Document/literal

        operation = port.getBinding().getPortType().operations.get(name)
        bop = port.getBinding().operations.get(name)
        soapBodyBind = None
        if input is True:
            soapBodyBind = \
                bop.input.findBinding(WSDLTools.SoapBodyBinding)
            message = operation.getInputMessage()
        else:
            soapBodyBind = \
                bop.output.findBinding(WSDLTools.SoapBodyBinding)
            message = operation.getOutputMessage()

        # using underlying data structure to avoid phantom problem.
        # with message.parts.data.values()

        if len(message.parts) == 0:
            raise Wsdl2PythonError('must specify part for doc/lit msg')

        p = None
        if soapBodyBind.parts is not None:
            if len(soapBodyBind.parts) > 1:
                raise Wsdl2PythonError('not supporting multiple parts in soap body'
                                       )
            if len(soapBodyBind.parts) == 0:
                return

            p = message.parts.get(soapBodyBind.parts[0])

        # XXX: Allow for some slop

        p = p or message.parts[0]

        if p.type:
            raise Wsdl2PythonError('no doc/lit suport for <part type>')

        if not p.element:
            return

        self.ns = p.element[0]
        content.ns = p.element[0]
        content.pName = p.element[1]
        content.mName = message.name

    def _setContent(self):
        '''create string representation of doc/lit message container.  If
        message element is simple(primitive), use python type as base class.
        '''

        try:
            self._simple
        except AttributeError:
            raise RuntimeError('call setUp first')

        # TODO: Hidden contract.  Must set self.ns before getNSAlias...
        #  File "/usr/local/python/lib/python2.4/site-packages/ZSI/generate/containers.py", line 625, in _setContent
        #    kw['message'],kw['prefix'],kw['typecode'] = \
        #  File "/usr/local/python/lib/python2.4/site-packages/ZSI/generate/containers.py", line 128, in getNSAlias
        #    raise ContainerError, 'no self.ns attr defined in %s' % self.__class__
        # ZSI.generate.containers.ContainerError: no self.ns attr defined in ZSI.generate.containers.ServiceDocumentLiteralMessageContainer
        #
        #        self.ns = self.content.ns

        kw = KW.copy()
        kw.update(dict(message=self.content.mName,
                       nsuri=self.content.ns, name=self.content.pName))

        #        kw['message'],kw['prefix'],kw['typecode'] = \
        #            self.content.mName, self.getNSAlias(), element_class_name(self.content.pName)
        #
        # These messsages are just global element declarations
        #        self.writeArray(['%(message)s = %(prefix)s.%(typecode)s().pyclass' %kw])

        self.writeArray(['%(message)s = GED("%(nsuri)s", "%(name)s").pyclass'
                         % kw])


class ServiceRPCEncodedMessageContainer(ServiceContainerBase,
                                        MessageContainerInterface):
    logger = _GetLogger('ServiceRPCEncodedMessageContainer')

    def setUp(
            self,
            port,
            soc,
            input,
    ):
        '''
        Instance Data:
           op    -- WSDLTools Operation instance
           bop   -- WSDLTools BindingOperation instance
           input -- boolean input/output
        '''

        name = soc.getOperationName()
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)

        assert op is not None, f'port has no operation {name}'
        assert bop is not None, f'port has no binding operation {name}'

        self.input = input
        self.op = op
        self.bop = bop

    def _setContent(self):
        try:
            self.op
        except AttributeError as e:
            raise RuntimeError('call setUp first') from e

        pname = self.op.name
        msgRole = self.op.input
        msgRoleB = self.bop.input
        if self.input is False:
            pname = f'{self.op.name}Response'
            msgRole = self.op.output
            msgRoleB = self.bop.output

        sbody = msgRoleB.findBinding(WSDLTools.SoapBodyBinding)
        if not sbody or not sbody.namespace:
            raise WSInteropError(WSISpec.R2717)

        assert sbody.use == 'encoded', 'Expecting use=="encoded"'
        encodingStyle = sbody.encodingStyle

        assert encodingStyle in (
            SOAP.ENC,
            SOAP.ENC12,
        ), f'Supporting encodingStyle={SOAP.ENC}, not {encodingStyle}'

        namespace = sbody.namespace
        tcb = MessageTypecodeContainer(tuple(msgRole.getMessage().parts.list))
        ofwhat = f'[{tcb.getTypecodeList()}]'
        pyclass = msgRole.getMessage().name

        fdict = KW.copy()
        fdict['nspname'] = sbody.namespace
        fdict['pname'] = pname
        fdict['pyclass'] = None
        fdict['ofwhat'] = ofwhat
        fdict['encoded'] = namespace

        # if self.input is False:
        #    fdict['typecode'] = \
        #        'Struct(pname=None, ofwhat=%(ofwhat)s, pyclass=%(pyclass)s, encoded="%(encoded)s")'
        # else:

        fdict['typecode'] = \
                                        'Struct(pname=("%(nspname)s","%(pname)s"), ofwhat=%(ofwhat)s, pyclass=%(pyclass)s, encoded="%(encoded)s")'

        message = ['class %(pyclass)s:',
                   '%(ID1)sdef __init__(self, **kw):',
                   '%(ID2)s"""Keyword parameters:']

        idx = len(message)
        for (a, p) in zip(tcb.getAttributeNames(),
                          tcb.getParameterNames()):
            message.insert(idx, f'%(ID2)s{p} -- part {p}')
            message.append(f'%(ID2)sself.{a} =  kw.get("{p}")')
            idx += 1

        message.insert(idx, '%(ID2)s"""')

        # TODO: This isn't a TypecodeContainerBase instance but it
        #    certaintly generates a pyclass and typecode.
        # if self.metaclass is None:
        fdict['typecode'] %= fdict
        fdict['pyclass'] = pyclass
        if TypecodeContainerBase.metaclass is None:
            message.append('%(pyclass)s.typecode = %(typecode)s')
        else:

            # Need typecode to be available when class is constructed.
            fdict['metaclass'] = TypecodeContainerBase.metaclass
            message.insert(0, '_%(pyclass)sTypecode = %(typecode)s')
            message.insert(2, '%(ID1)stypecode = _%(pyclass)sTypecode')
            message.insert(3, '%(ID1)s__metaclass__ = %(metaclass)s')
            message.append('%(pyclass)s.typecode.pyclass = %(pyclass)s')

        self.writeArray([l % fdict for l in message])


class ServiceRPCLiteralMessageContainer(ServiceContainerBase,
                                        MessageContainerInterface):
    logger = _GetLogger('ServiceRPCLiteralMessageContainer')

    def setUp(
            self,
            port,
            soc,
            input,
    ):
        '''
        Instance Data:
           op    -- WSDLTools Operation instance
           bop   -- WSDLTools BindingOperation instance
           input -- boolean input/output
        '''

        name = soc.getOperationName()
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)

        assert op is not None, f'port has no operation {name}'
        assert bop is not None, f'port has no binding operation {name}'

        self.op = op
        self.bop = bop
        self.input = input

    def _setContent(self):
        try:
            self.op
        except AttributeError:
            raise RuntimeError('call setUp first')

        operation = self.op
        input = self.input
        pname = operation.name
        msgRole = operation.input
        msgRoleB = self.bop.input
        if input is False:
            pname = f'{operation.name}Response'
            msgRole = operation.output
            msgRoleB = self.bop.output

        sbody = msgRoleB.findBinding(WSDLTools.SoapBodyBinding)
        if not sbody or not sbody.namespace:
            raise WSInteropError(WSISpec.R2717)

        namespace = sbody.namespace
        tcb = \
                MessageTypecodeContainer(tuple(msgRole.getMessage().parts.list))
        ofwhat = '[%s]' % tcb.getTypecodeList()
        pyclass = msgRole.getMessage().name

        fdict = KW.copy()
        fdict['nspname'] = sbody.namespace
        fdict['pname'] = pname
        fdict['pyclass'] = None
        fdict['ofwhat'] = ofwhat
        fdict['encoded'] = namespace
        fdict['typecode'] = \
                'Struct(pname=("%(nspname)s","%(pname)s"), ofwhat=%(ofwhat)s, pyclass=%(pyclass)s, encoded="%(encoded)s")'

        message = ['class %(pyclass)s:',
                   '%(ID1)sdef __init__(self, **kw):',
                   '%(ID2)s"""Keyword parameters:']

        idx = len(message)
        for (a, p) in zip(tcb.getAttributeNames(),
                          tcb.getParameterNames()):
            message.insert(idx, '%(ID2)s' + p + ' -- part ' + p)
            message.append('%(ID2)sself.' + a + ' =  kw.get("%s")' % p)
            idx += 1

        message.insert(idx, '%(ID2)s"""')

        # TODO: This isn't a TypecodeContainerBase instance but it
        #    certaintly generates a pyclass and typecode.
        # if self.metaclass is None:

        if TypecodeContainerBase.metaclass is None:
            fdict['pyclass'] = pyclass
            fdict['typecode'] = fdict['typecode'] % fdict
            message.append('%(pyclass)s.typecode = %(typecode)s')
        else:

            # Need typecode to be available when class is constructed.

            fdict['typecode'] = fdict['typecode'] % fdict
            fdict['pyclass'] = pyclass
            fdict['metaclass'] = TypecodeContainerBase.metaclass
            message.insert(0, '_%(pyclass)sTypecode = %(typecode)s')
            message.insert(2, '%(ID1)stypecode = _%(pyclass)sTypecode')
            message.insert(3, '%(ID1)s__metaclass__ = %(metaclass)s')
            message.append('%(pyclass)s.typecode.pyclass = %(pyclass)s')

        self.writeArray([l % fdict for l in message])


TypesContainerBase = ContainerBase


class TypesHeaderContainer(TypesContainerBase):
    '''imports for all generated types modules.
    '''

    imports = ['import ZSI', 'import ZSI.TCcompound',
               'from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED'
               ]
    logger = _GetLogger('TypesHeaderContainer')

    def _setContent(self):
        self.writeArray(TypesHeaderContainer.imports)


NamespaceClassContainerBase = TypesContainerBase


class NamespaceClassHeaderContainer(NamespaceClassContainerBase):
    logger = _GetLogger('NamespaceClassHeaderContainer')

    def _setContent(self):
        head = [
            '#' * 30,
            '# targetNamespace',
            '# %s' % self.ns,
            '#' * 30 + '\n',
            '_TARGET_NAMESPACE = %r' % self.ns,
            'class %s:' % self.getNSAlias(),
            '%stargetNamespace = _TARGET_NAMESPACE' % (ID1,)
        ]

        self.writeArray(head)


class NamespaceClassFooterContainer(NamespaceClassContainerBase):
    logger = _GetLogger('NamespaceClassFooterContainer')

    def _setContent(self):
        foot = ['# end class %s (tns: %s)' % (self.getNSAlias(),
                                              self.ns)]

        self.writeArray(foot)


BTI = BaseTypeInterpreter()


def strip_typeclass_string_to_module_class_string(klass):
    return str(klass).rpartition("'")[0].partition("'")[2]


def strip_parameters(e):
    return str(e).partition(">")[2]


class TypecodeContainerBase(TypesContainerBase):
    '''Base class for all classes representing anything
    with element content.

    class variables:
        mixed_content_aname -- text content will be placed in this attribute.
        attributes_aname -- attributes will be placed in this attribute.
        metaclass -- set this attribute to specify a pyclass __metaclass__
    '''

    mixed_content_aname = 'text'
    attributes_aname = 'attrs'
    metaclass = None
    lazy = False
    logger = _GetLogger('TypecodeContainerBase')

    def __init__(self, do_extended=False, extPyClasses=None):
        TypesContainerBase.__init__(self)
        self.name = None

        # attrs for model groups and others with elements, tclists, etc...

        self.allOptional = False
        self.mgContent = None
        self.contentFlattened = False
        self.elementAttrs = []
        self.tcListElements = []
        self.tcListSet = False

        self.localTypes = []

        # used when processing nested anonymous types

        self.parentClass = None

        # used when processing attribute content

        self.mixed = False
        self.extraFlags = ''
        self.attrComponents = None

        # --> EXTENDED
        # Used if an external pyclass was specified for this type.

        self.do_extended = do_extended
        if extPyClasses is None:
            self.extPyClasses = {}
        else:
            self.extPyClasses = extPyClasses

        # <--

    def getvalue(self):
        out = ContainerBase.getvalue(self)
        for item in self.localTypes:
            content = None
            assert True is item.isElement() is item.isLocal(), \
                'expecting local elements only'

            etp = item.content
            qName = item.getAttribute('type')
            if not qName:
                etp = item.content
                local = True
            else:
                etp = item.getTypeDefinition('type')

            if etp is None:
                if local is True:
                    content = \
                        ElementLocalComplexTypeContainer(do_extended=self.do_extended)
                else:
                    content = ElementSimpleTypeContainer()
            elif etp.isLocal() is False:
                content = ElementGlobalDefContainer()
            elif etp.isSimple() is True:
                content = ElementLocalSimpleTypeContainer()
            elif etp.isComplex():
                content = \
                    ElementLocalComplexTypeContainer(do_extended=self.do_extended)
            else:
                raise Wsdl2PythonError('Unknown element declaration: %s'
                                       % item.getItemTrace())

            content.setUp(item)

            out += '''

'''
            if self.parentClass:
                content.parentClass = '%s.%s' % (self.parentClass,
                                                 self.getClassName())
            else:
                content.parentClass = '%s.%s' % (self.getNSAlias(),
                                                 self.getClassName())

            for l in content.getvalue().split('\n'):
                if l:
                    out += '%s%s\n' % (ID1, l)
                else:
                    out += '\n'

            out += '''

'''

        return out

    def getAttributeName(self, name):
        '''represents the aname
        '''

        if self.func_aname is None:
            return name
        assert callable(self.func_aname), \
            'expecting callable method for attribute func_aname, not %s' \
            % type(self.func_aname)
        f = self.func_aname
        return f(name)

    def getMixedTextAName(self):
        '''returns an aname representing mixed text content.
        '''

        return self.getAttributeName(self.mixed_content_aname)

    def getClassName(self):

        if not self.name:
            raise ContainerError('self.name not defined!')
        if not hasattr(self.__class__, 'type'):
            raise ContainerError('container type not defined!')

        # suffix = self.__class__.type

        if self.__class__.type == DEF:
            classname = type_class_name(self.name)
        elif self.__class__.type == DEC:
            classname = element_class_name(self.name)
        #print(classname)
        return self.mangle(classname)

    # --> EXTENDED

    def hasExtPyClass(self):
        if self.name in self.extPyClasses:
            return True
        else:
            return False

    # <--

    def getPyClass(self):
        '''Name of generated inner class that will be specified as pyclass.
        '''

        # --> EXTENDED

        if self.hasExtPyClass():
            classInfo = self.extPyClasses[self.name]
            return '.'.join(classInfo)

        # <--

        return 'Holder'

    def getPyClassDefinition(self):
        '''Return a list containing pyclass definition.
        '''

        kw = KW.copy()

        # --> EXTENDED

        if self.hasExtPyClass():
            classInfo = self.extPyClasses[self.name]
            kw['classInfo'] = classInfo[0]
            return ['%(ID3)simport %(classInfo)s' % kw]

        # <--

        kw['pyclass'] = self.getPyClass()
        definition = []
        definition.append('%(ID3)sclass %(pyclass)s:' % kw)
        if self.metaclass is not None:
            kw['type'] = self.metaclass
            definition.append('%(ID4)s__metaclass__ = %(type)s' % kw)
        definition.append('%(ID4)stypecode = self' % kw)

        # TODO: Remove pyclass holder __init__ -->

        definition.append('%(ID4)sdef __init__(self):' % kw)
        definition.append('%(ID5)s# pyclass' % kw)

        # JRB HACK need to call _setElements via getElements

        self._setUpElements()

        # JRB HACK need to indent additional one level

        for el in self.elementAttrs:
            kw['element'] = el
            definition.append('%(ID2)s%(element)s' % kw)
        definition.append('%(ID5)sreturn' % kw)

        # <--

        # pyclass descriptive name

        if self.name is not None:
            kw['name'] = self.name
            definition.append('%(ID3)s%(pyclass)s.__name__ = "%(name)s_Holder"'
                              % kw)

        return definition

    def nsuriLogic(self):
        '''set a variable "ns" that represents the targetNamespace in
        which this item is defined.  Used for namespacing local elements.
        '''

        if self.parentClass:
            return 'ns = %s.%s.schema' % (self.parentClass,
                                          self.getClassName())
        return 'ns = %s.%s.schema' % (self.getNSAlias(),
                                      self.getClassName())

    def schemaTag(self):
        if self.ns is not None:
            return 'schema = _TARGET_NAMESPACE'
        raise ContainerError('failed to set schema targetNamespace(%s)'
                             % self.__class__)

    def typeTag(self):
        if self.name is not None:
            return 'type = (schema, "%s")' % self.name
        raise ContainerError('failed to set type name(%s)'
                             % self.__class__)

    def literalTag(self):
        if self.name is not None:
            return 'literal = "%s"' % self.name
        raise ContainerError('failed to set element name(%s)'
                             % self.__class__)

    def getExtraFlags(self):
        if self.mixed:
            self.extraFlags += 'mixed=True, mixed_aname="%s", ' \
                               % self.getMixedTextAName()

        return self.extraFlags

    def simpleConstructor(self, superclass=None):

        if superclass:
            return '%s.__init__(self, **kw)' % superclass
        else:
            return 'def __init__(self, **kw):'

    def pnameConstructor(self, superclass=None):

        if superclass:
            return '%s.__init__(self, pname, **kw)' % superclass
        else:
            return 'def __init__(self, pname, **kw):'

    def _setUpElements(self):
        """TODO: Remove this method

        This method ONLY sets up the instance attributes.
        Dependency instance attribute:
            mgContent -- expected to be either a complex definition
                with model group content, a model group, or model group
                content.  TODO: should only support the first two.
        """

        self.logger.debug('_setUpElements: %s'
                          % self._item.getItemTrace())
        if hasattr(self, '_done'):
            # return '\n'.join(self.elementAttrs)

            return

        self._done = True
        flat = []
        content = self.mgContent
        if type(self.mgContent) is not tuple:
            mg = self.mgContent
            if not mg.isModelGroup():
                mg = mg.content

            content = mg.content
            if mg.isAll():
                flat = content
                content = []
            elif mg.isModelGroup() and mg.isDefinition():
                mg = mg.content
                content = mg.content

        idx = 0
        content = list(content)
        while idx < len(content):
            c = orig = content[idx]
            if c.isElement():
                flat.append(c)
                idx += 1
                continue

            if c.isReference() and c.isModelGroup():
                c = c.getModelGroupReference()

            if c.isDefinition() and c.isModelGroup():
                c = c.content

            if c.isSequence() or c.isChoice():
                begIdx = idx
                endIdx = begIdx + len(c.content)
                for i in range(begIdx, endIdx):
                    content.insert(i, c.content[i - begIdx])

                content.remove(orig)
                continue

            raise ContainerError('unexpected schema item: %s'
                                 % c.getItemTrace())

        for c in flat:
            if c.isDeclaration() and c.isElement():
                defaultValue = 'None'
                parent = c
                defs = []

                # stop recursion via global ModelGroupDefinition

                while defs.count(parent) <= 1:
                    maxOccurs = parent.getAttribute('maxOccurs')
                    if maxOccurs == 'unbounded' or int(maxOccurs) > 1:
                        defaultValue = '[]'
                        break

                    parent = parent._parent()
                    if not parent.isModelGroup():
                        break

                    if parent.isReference():
                        parent = parent.getModelGroupReference()

                    if parent.isDefinition():
                        parent = parent.content
                        defs.append(parent)

                if None == c.getAttribute('name') and c.isWildCard():
                    e = '%sself.%s = %s' % (ID3,
                                            self.getAttributeName('any'), defaultValue)
                else:
                    e = '%sself.%s = %s' % (ID3,
                                            self.getAttributeName(c.getAttribute('name'
                                                                                 )), defaultValue)
                self.elementAttrs.append(e)
                continue

            # TODO: This seems wrong

            if c.isReference():
                e = '%sself._%s = None' % (ID3,
                                           self.mangle(c.getAttribute('ref')[1]))
                self.elementAttrs.append(e)
                continue

            raise ContainerError('unexpected item: %s'
                                 % c.getItemTrace())

        # return '\n'.join(self.elementAttrs)

        return

    def _setTypecodeList(self):
        """generates ofwhat content, minOccurs/maxOccurs facet generation.
        Dependency instance attribute:
            mgContent -- expected to be either a complex definition
                with model group content, a model group, or model group
                content.  TODO: should only support the first two.
            localTypes -- produce local class definitions later
            tcListElements -- elements, local/global
        """

        self.logger.debug('_setTypecodeList(%r): %s' % (self.mgContent,
                                                        self._item.getItemTrace()))

        flat = []
        content = self.mgContent

        # TODO: too much slop permitted here, impossible
        # to tell what is going on.

        if type(content) is not tuple:
            mg = content
            if not mg.isModelGroup():
                raise Wsdl2PythonError('Expecting ModelGroup: %s'
                                       % mg.getItemTrace())

            self.logger.debug('ModelGroup(%r) contents(%r): %s' % (mg,
                                                                   mg.content, mg.getItemTrace()))

            # <group ref>

            if mg.isReference():
                raise RuntimeError('Unexpected modelGroup reference: %s'
                                   % mg.getItemTrace())

            # <group name>

            if mg.isDefinition():
                mg = mg.content

            if mg.isAll():
                flat = mg.content
                content = []
            elif mg.isSequence():
                content = mg.content
            elif mg.isChoice():
                content = mg.content
            else:
                raise RuntimeError('Unknown schema item')

        idx = 0
        content = list(content)
        self.logger.debug('content: %r' % content)
        while idx < len(content):
            c = orig = content[idx]
            if c.isElement():
                flat.append(c)
                idx += 1
                continue

            if c.isReference() and c.isModelGroup():
                c = c.getModelGroupReference()

            if c.isDefinition() and c.isModelGroup():
                c = c.content

            if c.isSequence() or c.isChoice():
                begIdx = idx
                endIdx = begIdx + len(c.content)
                for i in range(begIdx, endIdx):
                    content.insert(i, c.content[i - begIdx])

                content.remove(orig)
                continue

            raise ContainerError('unexpected schema item: %s'
                                 % c.getItemTrace())

        # TODO: Need to store "parents" in a dict[id] = list(),
        #    because cannot follow references, but not currently
        #    a big concern.

        # self.logger.debug("flat: %r" %list(flat))

        for c in flat:
            self.logger.debug('flat: %r' % c)
            tc = TcListComponentContainer()

            # TODO: Remove _getOccurs

            (min, max, nil) = self._getOccurs(c)
            max = None
            maxOccurs = 1

            parent = c
            defs = []

            # stop recursion via global ModelGroupDefinition

            while defs.count(parent) <= 1:
                max = parent.getAttribute('maxOccurs')
                if max == 'unbounded':
                    maxOccurs = '"%s"' % max
                    break

                maxOccurs = int(max) * maxOccurs
                parent = parent._parent()
                if not parent.isModelGroup():
                    break

                if parent.isReference():
                    parent = parent.getModelGroupReference()

                if parent.isDefinition():
                    parent = parent.content
                    defs.append(parent)

            del defs
            parent = c
            while 1:
                minOccurs = int(parent.getAttribute('minOccurs'))
                if minOccurs == 0 or parent.isChoice():
                    minOccurs = 0
                    break

                parent = parent._parent()
                if not parent.isModelGroup():
                    minOccurs = int(c.getAttribute('minOccurs'))
                    break

                if parent.isReference():
                    parent = parent.getModelGroupReference()
                    continue

                if parent.isDefinition():
                    parent = parent.content
                    continue

                break

            tc.setOccurs(minOccurs, maxOccurs, nil)
            processContents = self._getProcessContents(c)
            tc.setProcessContents(processContents)
            if c.isDeclaration() and c.isElement():
                global_type = c.getAttribute('type')
                content = getattr(c, 'content', None)
                if c.isLocal() and c.isQualified() is False:
                    tc.unQualified()

                if c.isWildCard():
                    tc.setStyleAnyElement()
                elif global_type is not None:
                    tc.name = c.getAttribute('name')
                    ns = global_type[0]

                    # APACHE.AXIS_NS is for DataHandler type

                    if ns in SCHEMA.XSD_LIST + [APACHE.AXIS_NS]:
                        tpc = BTI.get_typeclass(global_type[1],
                                                global_type[0])
                        tc.klass = tpc
                    else:

                        #                    elif (self.ns,self.name) == global_type:
                        #                        # elif self._isRecursiveElement(c)
                        #                        # TODO: Remove this, it only works for 1 level.
                        #                        tc.setStyleRecursion()

                        tc.setGlobalType(*global_type)

                    #                        tc.klass = '%s.%s' % (NAD.getAlias(ns),
                    #                            type_class_name(global_type[1]))

                    del ns
                elif content is not None and content.isLocal() \
                        and content.isComplex():
                    tc.name = c.getAttribute('name')
                    tc.klass = 'self.__class__.%s' \
                               % element_class_name(tc.name)

                    # TODO: Not an element reference, confusing nomenclature

                    tc.setStyleElementReference()
                    self.localTypes.append(c)
                elif content is not None and content.isLocal() \
                        and content.isSimple():

                    # Local Simple Type

                    tc.name = c.getAttribute('name')
                    tc.klass = 'self.__class__.%s' \
                               % element_class_name(tc.name)

                    # TODO: Not an element reference, confusing nomenclature

                    tc.setStyleElementReference()
                    self.localTypes.append(c)
                else:
                    raise ContainerError('unexpected item: %s'
                                         % c.getItemTrace())
            elif c.isReference():

                # element references

                ref = c.getAttribute('ref')

                #                tc.klass = '%s.%s' % (NAD.getAlias(ref[0]),
                #                                          element_class_name(ref[1]) )

                tc.setStyleElementReference()
                tc.setGlobalType(*ref)
            else:
                raise ContainerError('unexpected item: %s'
                                     % c.getItemTrace())

            self.tcListElements.append(tc)

    def getTypecodeList(self, indent=ID4):
        if not self.tcListSet:
            #            self._flattenContent()

            self._setTypecodeList()
            self.tcListSet = True

        l = []
        for e in self.tcListElements:
            classTypeWithParams = strip_typeclass_string_to_module_class_string(e.klass) + strip_parameters(e)
            l.append(classTypeWithParams or str(e))

        return (', %s\n' % indent).join(l)

    # the following _methods() are utility methods used during
    # TCList generation, et al.

    def _getOccurs(self, e):

        nillable = e.getAttribute('nillable')
        if nillable == 'true':
            nillable = True
        else:
            nillable = False

        maxOccurs = e.getAttribute('maxOccurs')
        if maxOccurs == 'unbounded':
            maxOccurs = '"%s"' % maxOccurs

        minOccurs = e.getAttribute('minOccurs')

        if self.allOptional is True:
            # JRB Hack

            minOccurs = '0'
            maxOccurs = '"unbounded"'

        return (minOccurs, maxOccurs, nillable)

    def _getProcessContents(self, e):
        processContents = e.getAttribute('processContents')
        return processContents

    def getBasesLogic(self, indent):
        try:
            prefix = NAD.getAlias(self.sKlassNS)
        except WsdlGeneratorError:

            # XSD or SOAP

            raise

        bases = []
        bases.append('if %s.%s not in %s.%s.__bases__:' % (prefix,
                                                           type_class_name(self.sKlass), self.getNSAlias(),
                                                           self.getClassName()))
        bases.append('%sbases = list(%s.%s.__bases__)' % (ID1,
                                                          self.getNSAlias(), self.getClassName()))
        bases.append('%sbases.insert(0, %s.%s)' % (ID1, prefix,
                                                   type_class_name(self.sKlass)))
        bases.append('%s%s.%s.__bases__ = tuple(bases)' % (ID1,
                                                           self.getNSAlias(), self.getClassName()))

        s = ''
        for b in bases:
            s += '%s%s\n' % (indent, b)

        return s


class MessageTypecodeContainer(TypecodeContainerBase):
    '''Used for RPC style messages, where we have
    serveral parts serialized within a rpc wrapper name.
    '''

    logger = _GetLogger('MessageTypecodeContainer')

    def __init__(self, parts=None):
        TypecodeContainerBase.__init__(self)
        self.mgContent = parts

    def _getOccurs(self, e):
        '''return a 3 item tuple
        '''

        minOccurs = maxOccurs = '1'
        nillable = True
        return (minOccurs, maxOccurs, nillable)

    def _setTypecodeList(self):
        self.logger.debug('_setTypecodeList: %s' % str(self.mgContent))

        assert type(self.mgContent) is tuple, \
            'expecting tuple for mgContent not: %s' \
            % type(self.mgContent)

        for p in self.mgContent:

            # JRB
            #   not sure what needs to be set for tc, this should be
            #   the job of the constructor or a setUp method.

            (min, max, nil) = self._getOccurs(p)
            if p.element:
                raise WSInteropError(WSISpec.R2203)
            elif p.type:
                (nsuri, name) = p.type
                tc = RPCMessageTcListComponentContainer(qualified=False)
                tc.setOccurs(min, max, nil)
                tc.name = p.name
                if nsuri in XMLSchema.BUILT_IN_NAMESPACES:
                    tpc = BTI.get_typeclass(name, nsuri)
                    tc.klass = tpc
                else:
                    tc.klass = '%s.%s' % (NAD.getAlias(nsuri),
                                          type_class_name(name))
            else:
                raise ContainerError('part must define an element or type attribute'
                                     )

            self.tcListElements.append(tc)

    def getTypecodeList(self, indent=ID4):
        if not self.tcListSet:
            self._setTypecodeList()
            self.tcListSet = True

        list = []
        for e in self.tcListElements:
            list.append(str(e))
        return (', %s\n' % indent).join(list)

    def getAttributeNames(self):
        '''returns a list of anames representing the parts
        of the message.
        '''

        return [self.getAttributeName(e.name) for e in self.tcListElements]

    def getParameterNames(self):
        '''returns a list of pnames representing the parts
        of the message.
        '''

        return [e.name for e in self.tcListElements]

    def setParts(self, parts):
        self.mgContent = parts


class TcListComponentContainer(ContainerBase):
    '''Encapsulates a single value in the TClist list.
    it inherits TypecodeContainerBase only to get the mangle() method,
    it does not call the baseclass ctor.

    TODO: Change this inheritance scheme.
    '''

    logger = _GetLogger('TcListComponentContainer')

    def __init__(self, qualified=True):
        '''
        qualified -- qualify element.  All GEDs should be qualified,
            but local element declarations qualified if form attribute
            is qualified, else they are unqualified. Only relevant for
            standard style.
        '''

        # TypecodeContainerBase.__init__(self)

        ContainerBase.__init__(self)

        self.qualified = qualified
        self.name = None
        self.klass = None
        self.global_type = None

        self.min = None
        self.max = None
        self.nil = None
        self.style = None
        self.setStyleElementDeclaration()

    def setOccurs(
            self,
            min,
            max,
            nil,
    ):

        self.min = min
        self.max = max
        self.nil = nil

    def setProcessContents(self, processContents):
        self.processContents = processContents

    def setGlobalType(self, namespace, name):
        self.global_type = (namespace, name)

    def setStyleElementDeclaration(self):
        '''set the element style.
            standard -- GED or local element
        '''

        self.style = 'standard'

    def setStyleElementReference(self):
        '''set the element style.
            ref -- element reference
        '''

        self.style = 'ref'

    def setStyleAnyElement(self):
        '''set the element style.
            anyElement -- <any> element wildcard
        '''

        self.name = 'any'
        self.style = 'anyElement'

    #    def setStyleRecursion(self):
    #        '''TODO: Remove.  good for 1 level
    #        '''
    #        self.style = 'recursion'

    def unQualified(self):
        '''Do not qualify element.
        '''

        self.qualified = False

    def _getOccurs(self):
        return 'minOccurs=%s, maxOccurs=%s, nillable=%s' % (self.min,
                                                            self.max, self.nil)

    def _getProcessContents(self):
        return 'processContents="%s"' % self.processContents

    def _getvalue(self):
        kw = {
            'occurs': self._getOccurs(),
            'aname': self.getAttributeName(self.name),
            'klass': self.klass,
            'lazy': TypecodeContainerBase.lazy,
            'typed': 'typed=False',
            'encoded': 'encoded=kw.get("encoded")',
        }

        gt = self.global_type
        if gt is not None:
            (kw['nsuri'], kw['type']) = gt

        if self.style == 'standard':
            kw['pname'] = '"%s"' % self.name
            if self.qualified is True:
                kw['pname'] = '(ns,"%s")' % self.name
            if gt is None:
                return '%(klass)s(pname=%(pname)s, aname="%(aname)s", %(occurs)s, %(typed)s, %(encoded)s)' \
                    % kw
            return 'GTD("%(nsuri)s","%(type)s",lazy=%(lazy)s)(pname=%(pname)s, aname="%(aname)s", %(occurs)s, %(typed)s, %(encoded)s)' \
                % kw

        if self.style == 'ref':
            if gt is None:
                return '%(klass)s(%(occurs)s, %(encoded)s)' % kw
            return 'GED("%(nsuri)s","%(type)s",lazy=%(lazy)s, isref=True)(%(occurs)s, %(encoded)s)' \
                % kw

        kw['process'] = self._getProcessContents()
        if self.style == 'anyElement':
            return 'ZSI.TC.AnyElement(aname="%(aname)s", %(occurs)s, %(process)s)' \
                % kw

        #        if self.style == 'recursion':
        #            return 'ZSI.TC.AnyElement(aname="%(aname)s", %(occurs)s, %(process)s)' %kw

        raise RuntimeError('Must set style for typecode list generation'
                           )

    def __str__(self):
        return self._getvalue()


class RPCMessageTcListComponentContainer(TcListComponentContainer):
    '''Container for rpc/literal rpc/encoded message typecode.
    '''

    logger = _GetLogger('RPCMessageTcListComponentContainer')

    def __init__(self, qualified=True, encoded=None):
        '''
        encoded -- encoded namespaceURI, if None treat as rpc/literal.
        '''

        TcListComponentContainer.__init__(self, qualified=qualified)
        self._encoded = encoded

    def _getvalue(self):
        encoded = self._encoded
        if encoded is not None:
            encoded = '"%s"' % self._encoded

        if self.style == 'standard':
            pname = '"%s"' % self.name
            if self.qualified is True:
                pname = '(ns,"%s")' % self.name
            return '%s(pname=%s, aname="%s", typed=False, encoded=%s, %s)' \
                % (self.klass, pname, self.getAttributeName(self.name),
                   encoded, self._getOccurs())
        elif self.style == 'ref':
            return '%s(encoded=%s, %s)' % (self.klass, encoded,
                                           self._getOccurs())
        elif self.style == 'anyElement':
            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
                % (self.getAttributeName(self.name), self._getOccurs(),
                   self._getProcessContents())

        #        elif self.style == 'recursion':
        #            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
        #                % (self.getAttributeName(self.name), self._getOccurs(), self._getProcessContents())

        raise RuntimeError('Must set style(%s) for typecode list generation'
                           % self.style)


class ElementSimpleTypeContainer(TypecodeContainerBase):
    type = DEC
    logger = _GetLogger('ElementSimpleTypeContainer')

    def _substitutionGroupTag(self):
        value = self.substitutionGroup
        if not value:
            return 'substitutionGroup = None'

        (nsuri, ncname) = value
        return 'substitutionGroup = ("%s","%s")' % (nsuri, ncname)

    def _setContent(self):
        aname = self.getAttributeName(self.name)
        pyclass = self.pyclass

        # bool cannot be subclassed

        if pyclass == 'bool':
            pyclass = 'int'
        kw = KW.copy()
        kw.update(dict(
            aname=aname,
            ns=self.ns,
            name=self.name,
            pname=(self.ns, self.name),
            substitutionGroup=self._substitutionGroupTag(),
            subclass=strip_typeclass_string_to_module_class_string(self.sKlass),
            literal=self.literalTag(),
            schema=self.schemaTag(),
            init=self.simpleConstructor(),
            klass=self.getClassName(),
            element='ElementDeclaration',
        ))

        #
        # TODO: What does this local check do???? relevant for
        # [ 1853368 ] "elementFormDefault='unqualified'" mishandled
        #

        if self.local:
            kw['element'] = 'LocalElementDeclaration'
            kw['pname'] = '"%s"' % self.name

        element = [i % kw for i in [
            '%(ID1)sclass %(klass)s(%(subclass)s, %(element)s):',
            '%(ID2)s%(literal)s',
            '%(ID2)s%(schema)s',
            '%(ID2)s%(init)s',
            '%(ID3)skw["pname"] = %(pname)s',
            '%(ID3)skw["aname"] = "%(aname)s"',
        ]]

        # TODO: What about getPyClass and getPyClassDefinition?
        #     I want to add pyclass metaclass here but this needs to be
        #     corrected first.
        #
        # anyType (?others) has no pyclass.

        app = element.append
        if pyclass is not None:
            app('%sclass IHolder(%s): typecode=self' % (ID3, pyclass))
            app('%skw["pyclass"] = IHolder' % ID3)
            app('%sIHolder.__name__ = "%s_immutable_holder"' % (ID3,
                                                                aname))

        app('%s%s' % (ID3, self.simpleConstructor(strip_typeclass_string_to_module_class_string(self.sKlass))))

        self.writeArray(element)

    def setUp(self, tp):
        self._item = tp
        self.local = tp.isLocal()
        try:
            self.name = tp.getAttribute('name')
            self.substitutionGroup = tp.getAttribute('substitutionGroup'
                                                     )
            self.ns = tp.getTargetNamespace()
            qName = tp.getAttribute('type')
        except Exception as ex:
            raise Wsdl2PythonError('Error occured processing element: %s'
                                   % tp.getItemTrace(), *ex.args)

        if qName is None:
            raise Wsdl2PythonError('Missing QName for element type attribute: %s'
                                   % tp.getItemTrace())

        (tns, local) = (qName.getTargetNamespace(), qName.getName())
        self.sKlass = BTI.get_typeclass(local, tns)
        if self.sKlass is None:
            raise Wsdl2PythonError('No built-in typecode for type definition("%s","%s"): %s'
                                   % (tns, local, tp.getItemTrace()))

        try:
            self.pyclass = BTI.get_pythontype(None, None,
                                              typeclass=self.sKlass)
        except Exception as ex:
            raise Wsdl2PythonError('Error occured processing element: %s'
                                   % tp.getItemTrace(), *ex.args)


class ElementLocalSimpleTypeContainer(TypecodeContainerBase):
    '''local simpleType container
    '''

    type = DEC
    logger = _GetLogger('ElementLocalSimpleTypeContainer')

    def _setContent(self):
        kw = KW.copy()
        kw.update(dict(
            aname=self.getAttributeName(self.name),
            ns=self.ns,
            name=self.name,
            pname=(self.ns, self.name),
            subclass=self.sKlass,
            literal=self.literalTag(),
            schema=self.schemaTag(),
            init=self.simpleConstructor(),
            klass=self.getClassName(),
            element='ElementDeclaration',
            baseinit=self.simpleConstructor(self.sKlass),
        ))

        #
        # TODO: What does this local check do???? relevant for
        # [ 1853368 ] "elementFormDefault='unqualified'" mishandled
        #

        if self.local:
            kw['element'] = 'LocalElementDeclaration'
            kw['pname'] = '"%s"' % self.name

        element = [i % kw for i in [
            '%(ID1)sclass %(klass)s(%(subclass)s, %(element)s):',
            '%(ID2)s%(literal)s',
            '%(ID2)s%(schema)s',
            '%(ID2)s%(init)s',
            '%(ID3)skw["pname"] = %(pname)s',
            '%(ID3)skw["aname"] = "%(aname)s"',
            '%(ID3)s%(baseinit)s',
        ]]

        app = element.append
        pyclass = self.pyclass
        if pyclass is not None:

            # bool cannot be subclassed

            if pyclass == 'bool':
                pyclass = 'int'
            kw['pyclass'] = pyclass
            app('%(ID3)sclass IHolder(%(pyclass)s): typecode=self' % kw)
            app('%(ID3)sself.pyclass = IHolder' % kw)
            app('%(ID3)sIHolder.__name__ = "%(aname)s_immutable_holder"'
                % kw)

        self.writeArray(element)

    def _setup_pyclass(self):
        try:
            self.pyclass = BTI.get_pythontype(None, None,
                                              typeclass=self.sKlass)
        except Exception as ex:
            raise Wsdl2PythonError('Error occured processing element: %s'
                                   % self._item.getItemTrace(),
                                   *ex.args)

    def setUp(self, tp):
        self._item = tp
        assert tp.isElement() is True and tp.content is not None \
               and tp.content.isLocal() is True and tp.content.isSimple() \
               is True, 'expecting local simple type: %s' \
                        % tp.getItemTrace()

        self.local = tp.isLocal()
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        content = tp.content.content
        if content.isRestriction():
            try:
                base = content.getTypeDefinition()
            except XMLSchema.SchemaError:
                base = None

            qName = content.getAttributeBase()
            if base is None:
                self.sKlass = BTI.get_typeclass(qName[1], qName[0])
                self._setup_pyclass()
                return

            raise Wsdl2PythonError('unsupported local simpleType restriction: %s'
                                   % tp.content.getItemTrace())

        if content.isList():
            try:
                base = content.getTypeDefinition()
            except XMLSchema.SchemaError:
                base = None

            if base is None:
                qName = content.getItemType()
                self.sKlass = BTI.get_typeclass(qName[1], qName[0])
                self._setup_pyclass()
                return

            raise Wsdl2PythonError('unsupported local simpleType List: %s'
                                   % tp.content.getItemTrace())

        if content.isUnion():
            raise Wsdl2PythonError('unsupported local simpleType Union: %s'
                                   % tp.content.getItemTrace())

        raise Wsdl2PythonError('unexpected schema item: %s'
                               % tp.content.getItemTrace())


class ElementLocalComplexTypeContainer(TypecodeContainerBase,
                                       AttributeMixIn):
    type = DEC
    logger = _GetLogger('ElementLocalComplexTypeContainer')

    def _setContent(self):
        kw = KW.copy()
        try:
            kw.update(dict(
                klass=self.getClassName(),
                subclass='ZSI.TCcompound.ComplexType',
                element='ElementDeclaration',
                literal=self.literalTag(),
                schema=self.schemaTag(),
                init=self.simpleConstructor(),
                ns=self.ns,
                name=self.name,
                pname=(self.ns, self.name),
                aname=self.getAttributeName(self.name),
                nsurilogic=self.nsuriLogic(),
                ofwhat=self.getTypecodeList(),
                atypecode=self.attribute_typecode,
                pyclass=self.getPyClass(),
            ))
        except Exception as ex:
            args = \
                ['Failure processing an element w/local complexType: %s'
                 % self._item.getItemTrace()]
            args += ex.args
            ex.args = tuple(args)
            raise

        #
        # TODO: What does this local check do???? relevant for
        # [ 1853368 ] "elementFormDefault='unqualified'" mishandled
        #

        if self.local:
            kw['element'] = 'LocalElementDeclaration'
            kw['pname'] = f'"{self.name}"'

        element = [
            '%(ID1)sclass %(klass)s(%(subclass)s, %(element)s):',
            '%(ID2)s%(literal)s',
            '%(ID2)s%(schema)s',
            '%(ID2)s%(init)s',
            '%(ID3)s%(nsurilogic)s',
            '%(ID3)sTClist = [%(ofwhat)s]',
            '%(ID3)skw["pname"] = %(pname)s',
            '%(ID3)skw["aname"] = "%(aname)s"',
            '%(ID3)s%(atypecode)s = {}',
            '%(ID3)sZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)'
            ,
        ]

        for l in self.attrComponents:
            element.append('%(ID3)s' + str(l))
        element += self.getPyClassDefinition()
        element.append('%(ID3)sself.pyclass = %(pyclass)s' % kw)
        self.writeArray([l % kw for l in element])

    def setUp(self, tp):
        '''
        {'xsd':['annotation', 'simpleContent', 'complexContent',\
        'group', 'all', 'choice', 'sequence', 'attribute', 'attributeGroup',\
        'anyAttribute', 'any']}
        '''

        #
        # TODO: Need a Recursive solution, this is incomplete will ignore many
        #  extensions, restrictions, etc.
        #

        self._item = tp

        # JRB HACK SUPPORTING element/no content.

        assert tp.isElement() is True and (tp.content is None
                                           or tp.content.isComplex() is True
                                           and tp.content.isLocal() is True), \
            'expecting element w/local complexType not: %s' \
            % tp.content.getItemTrace()

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.local = tp.isLocal()

        complex = tp.content

        # JRB HACK SUPPORTING element/no content.

        if complex is None:
            self.mgContent = ()
            return

        # attributeContent = complex.getAttributeContent()
        # self.mgContent = None

        if complex.content is None:
            self.mgContent = ()
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        is_simple = complex.content.isSimple()
        if is_simple and complex.content.content.isExtension():
            # TODO: Not really supported just passing thru

            self.mgContent = ()
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        if is_simple and complex.content.content.isRestriction():
            # TODO: Not really supported just passing thru

            self.mgContent = ()
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        if is_simple:
            raise ContainerError('not implemented local complexType/simpleContent: %s'
                                 % tp.getItemTrace())

        is_complex = complex.content.isComplex()
        if is_complex and complex.content.content is None:
            # TODO: Recursion...

            self.mgContent = ()
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        if is_complex and complex.content.content.isExtension() \
                and complex.content.content.content is not None \
                and complex.content.content.content.isModelGroup():
            self.mgContent = complex.content.content.content.content
            self.attrComponents = \
                self._setAttributes(complex.content.content.getAttributeContent())
            return

        if is_complex and complex.content.content.isRestriction() \
                and complex.content.content.content is not None \
                and complex.content.content.content.isModelGroup():
            self.mgContent = complex.content.content.content.content
            self.attrComponents = \
                self._setAttributes(complex.content.content.getAttributeContent())
            return

        if is_complex:
            self.mgContent = ()
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        if complex.content.isModelGroup():
            self.mgContent = complex.content.content
            self.attrComponents = \
                self._setAttributes(complex.getAttributeContent())
            return

        # TODO: Scary Fallthru

        self.mgContent = ()
        self.attrComponents = \
            self._setAttributes(complex.getAttributeContent())


class ElementGlobalDefContainer(TypecodeContainerBase):
    type = DEC
    logger = _GetLogger('ElementGlobalDefContainer')

    def _substitutionGroupTag(self):
        value = self.substitutionGroup
        if not value:
            return 'substitutionGroup = None'

        (nsuri, ncname) = value
        return 'substitutionGroup = ("%s","%s")' % (nsuri, ncname)

    def _setContent(self):
        '''GED defines element name, so also define typecode aname
        '''

        kw = KW.copy()
        try:
            kw.update(dict(  # ofwhat=self.getTypecodeList(),
                # atypecode=self.attribute_typecode,
                # pyclass=self.getPyClass(),
                klass=self.getClassName(),
                element='ElementDeclaration',
                literal=self.literalTag(),
                substitutionGroup=self._substitutionGroupTag(),
                schema=self.schemaTag(),
                init=self.simpleConstructor(),
                ns=self.ns,
                name=self.name,
                pname=(self.ns, self.name),
                aname=self.getAttributeName(self.name),
                baseslogic=self.getBasesLogic(ID3),
                alias=NAD.getAlias(self.sKlassNS),
                subclass=type_class_name(self.sKlass),
            ))
        except Exception as ex:
            args = \
                ['Failure processing an element w/local complexType: %s'
                 % self._item.getItemTrace()]
            args += ex.args
            ex.args = tuple(args)
            raise

        #
        # TODO: What does this local check do???? relevant for
        # [ 1853368 ] "elementFormDefault='unqualified'" mishandled
        #

        if self.local:
            kw['element'] = 'LocalElementDeclaration'
            kw['pname'] = '"%s"' % self.name

        element = [
            '%(ID1)sclass %(klass)s(%(element)s):',
            '%(ID2)s%(literal)s',
            '%(ID2)s%(schema)s',
            '%(ID2)s%(substitutionGroup)s',
            '%(ID2)s%(init)s',
            '%(ID3)skw["pname"] = %(pname)s',
            '%(ID3)skw["aname"] = "%(aname)s"',
            '%(baseslogic)s',
            '%(ID3)s%(alias)s.%(subclass)s.__init__(self, **kw)',
            '%(ID3)sif self.pyclass is not None: self.pyclass.__name__ = "%(klass)s_Holder"'
            ,
        ]

        self.writeArray([l % kw for l in element])

    def setUp(self, element):

        # Save for debugging

        self._item = element
        self.local = element.isLocal()
        self.name = element.getAttribute('name')
        self.substitutionGroup = \
            element.getAttribute('substitutionGroup')
        self.ns = element.getTargetNamespace()
        tp = element.getTypeDefinition('type')
        self.sKlass = tp.getAttribute('name')
        self.sKlassNS = tp.getTargetNamespace()


class ComplexTypeComplexContentContainer(TypecodeContainerBase,
                                         AttributeMixIn):
    '''Represents ComplexType with ComplexContent.
    '''

    type = DEF
    logger = _GetLogger('ComplexTypeComplexContentContainer')

    def __init__(self, do_extended=False):
        TypecodeContainerBase.__init__(self, do_extended=do_extended)

    def setUp(self, tp):
        '''complexContent/[extension,restriction]
            restriction
            extension
            extType -- used in figuring attrs for extensions
        '''

        self._item = tp
        assert tp.content.isComplex() is True \
               and (tp.content.content.isRestriction()
                    or tp.content.content.isExtension() is True), \
            'expecting complexContent/[extension,restriction]'

        self.extType = None
        self.restriction = False
        self.extension = False
        self._kw_array = None
        self._is_array = False
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()

        # xxx: what is this for?
        # self.attribute_typecode = 'attributes'

        derivation = tp.content.content

        # Defined in Schema instance?

        try:
            base = derivation.getTypeDefinition('base')
        except XMLSchema.SchemaError:
            base = None

        # anyType, arrayType, etc...

        if base is None:
            base = derivation.getAttributeQName('base')
            if base is None:
                raise ContainerError('Unsupported derivation: %s'
                                     % derivation.getItemTrace())

            if base != (SOAP.ENC, 'Array') and base != (SOAP.ENC12, 'Array') and base != (SCHEMA.XSD3, 'anyType'):
                raise ContainerError('Unsupported base(%s): %s'
                                     % (base, derivation.getItemTrace()))

        if base == (SOAP.ENC, 'Array') or base == (SOAP.ENC12, 'Array'):

            # SOAP-ENC:Array expecting arrayType attribute reference

            self.logger.debug('Derivation of soapenc:Array')
            self._is_array = True
            self._kw_array = {'atype': None, 'id3': ID3, 'ofwhat': None}
            self.sKlass = BTI.get_typeclass(base[1], base[0])
            self.sKlassNS = base[0]

            for a in derivation.getAttributeContent():

                assert a.isAttribute() is True, \
                    'only attribute content expected: %s' \
                    % a.getItemTrace()

                if a.isReference() is False:
                    continue

                if a.getAttribute('ref') not in ((SOAP.ENC, 'arrayType'), (SOAP.ENC12, 'arrayType')):
                    continue

                attr = a.getAttributeQName((WSDL.BASE, 'arrayType'))
                if attr is None:
                    warnings.warn(
                        'soapenc:array derivation declares attribute reference ("%s","%s"), does not define attribute ("%s","%s")'
                        % (SOAP.ENC, 'arrayType', WSDL.BASE,
                           'arrayType'))
                    break

                self._kw_array['atype'] = attr
                qname = self._kw_array.get('atype')
                if a is not None:
                    ncname = qname[1].strip('[]')
                    namespace = qname[0]
                    try:
                        ofwhat = a.getSchemaItem(XMLSchema.TYPES,
                                                 namespace, ncname)
                    except XMLSchema.SchemaError:
                        ofwhat = None

                    if ofwhat is None:
                        self._kw_array['ofwhat'] = \
                            BTI.get_typeclass(ncname, namespace)
                    else:
                        self._kw_array['ofwhat'] = \
                            GetClassNameFromSchemaItem(ofwhat,
                                                       do_extended=self.do_extended)

                    if self._kw_array['ofwhat'] is None:
                        raise ContainerError('For Array could not resolve ofwhat typecode(%s,%s): %s'
                                             % (namespace, ncname,
                                                derivation.getItemTrace()))

                    self.logger.debug('Attribute soapenc:arrayType="%s"'
                                      % str(self._kw_array['ofwhat']))

                    break
        elif isinstance(base, XMLSchema.XMLSchemaComponent):

            # else:
            #    raise Wsdl2PythonError, \
            #        'derivation of soapenc:array must declare attribute reference ("%s","%s")' %(
            #        SOAP.ENC,'arrayType')

            self.sKlass = base.getAttribute('name')
            self.sKlassNS = base.getTargetNamespace()
        else:

            # TypeDescriptionComponent

            self.sKlass = base.getName()
            self.sKlassNS = base.getTargetNamespace()

        attrs = []
        if derivation.isRestriction():
            self.restriction = True
            self.extension = False

            # derivation.getAttributeContent subset of tp.getAttributeContent

            attrs += derivation.getAttributeContent() or ()
        else:
            self.restriction = False
            self.extension = True
            attrs += tp.getAttributeContent() or ()
            if isinstance(derivation, XMLSchema.XMLSchemaComponent):
                attrs += derivation.getAttributeContent() or ()

        # XXX: not sure what this is doing

        if attrs:
            self.extType = derivation

        if derivation.content is not None \
                and derivation.content.isModelGroup():
            group = derivation.content
            if group.isReference():
                group = group.getModelGroupReference()
            self.mgContent = group.content
        elif derivation.content:
            raise Wsdl2PythonError('expecting model group, not: %s'
                                   % derivation.content.getItemTrace())
        else:
            self.mgContent = ()

        self.attrComponents = self._setAttributes(tuple(attrs))

    def _setContent(self):
        """JRB What is the difference between instance data
        ns, name, -- type definition?
        sKlass, sKlassNS? -- element declaration?
        """

        kw = KW.copy()
        definition = []
        if self._is_array:

            # SOAP-ENC:Array

            if _is_xsd_or_soap_ns(self.sKlassNS) is False \
                        and self.sKlass == 'Array':
                raise ContainerError('unknown type: (%s,%s)'
                                     % (self.sKlass, self.sKlassNS))

            # No need to xsi:type array items since specify with
            # SOAP-ENC:arrayType attribute.

            definition += [
                f'{ID1}class {self.getClassName()}(ZSI.TC.Array, TypeDefinition):',
                f'{ID2}#complexType/complexContent base="SOAP-ENC:Array"',
                f'{ID2}{self.schemaTag()}',
                f'{ID2}{self.typeTag()}',
                f'{ID2}{self.pnameConstructor()}',
            ]

            append = definition.append
            if self._kw_array.get('ofwhat') is None:
                append('%s%s.__init__(self, None, None, pname=pname, childnames=\'item\', undeclared=True, **kw)'
                       % (ID3, self.sKlass))
            else:
                append('%(id3)sofwhat = %(ofwhat)s(None, typed=False)'
                       % self._kw_array)
                append('%(id3)satype = %(atype)s' % self._kw_array)
                append('%s%s.__init__(self, atype, ofwhat, pname=pname, childnames=\'item\', **kw)'
                       % (ID3, self.sKlass))

            self.writeArray(definition)
            return

        definition += [
            f'{ID1}class {self.getClassName()}(TypeDefinition):',
            f'{ID2}{self.schemaTag()}',
            f'{ID2}{self.typeTag()}',
            f'{ID2}{self.pnameConstructor()}',
            f'{ID3}{self.nsuriLogic()}',
            f"{ID3}TClist = [{self.getTypecodeList()}]",
        ]

        definition.append(f'{ID3}attributes = {self.attribute_typecode} = attributes or {{}}')

        #
        # Special case: anyType restriction

        isAnyType = (self.sKlassNS, self.sKlass) == (SCHEMA.XSD3,
                                                     'anyType')
        if isAnyType:
            del definition[0]
            definition.insert(0,
                              '%sclass %s(ZSI.TC.ComplexType, TypeDefinition):'
                              % (ID1, self.getClassName()))
            definition.insert(1,
                              '%s#complexType/complexContent restrict anyType'
                              % ID2)

        # derived type support

        definition.append('%sif extend: TClist += ofwhat' % ID3)
        definition.append('%sif restrict: TClist = ofwhat' % ID3)
        if len(self.attrComponents) > 0:
            definition.append('%selse:' % ID3)
            for l in self.attrComponents:
                definition.append('%s%s' % (ID4, l))

        if isAnyType:
            definition.append('%sZSI.TC.ComplexType.__init__(self, None, TClist, pname=pname, **kw)'
                              % ID3)

            # pyclass class definition

            definition += self.getPyClassDefinition()
            kw['pyclass'] = self.getPyClass()
            definition.append('%(ID3)sself.pyclass = %(pyclass)s' % kw)
            self.writeArray(definition)
            return

        definition.append('%s' % self.getBasesLogic(ID3))
        prefix = NAD.getAlias(self.sKlassNS)
        typeClassName = type_class_name(self.sKlass)
        if self.restriction:
            definition.append('%s%s.%s.__init__(self, pname, ofwhat=TClist, restrict=True, **kw)'
                              % (ID3, prefix, typeClassName))
            definition.insert(1,
                              '%s#complexType/complexContent restriction'
                              % ID2)
            self.writeArray(definition)
            return

        if self.extension:
            definition.append('%s%s.%s.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)'
                              % (ID3, prefix, typeClassName))
            definition.insert(1,
                              '%s#complexType/complexContent extension'
                              % ID2)
            self.writeArray(definition)
            return

        raise Wsdl2PythonError('ComplexContent must be a restriction or extension'
                               )

    def pnameConstructor(self, superclass=None):
        if superclass:
            return '%s.__init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw)' \
                % superclass

        return 'def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):'


class ComplexTypeContainer(TypecodeContainerBase, AttributeMixIn):
    '''Represents a global complexType definition.
    '''

    type = DEF
    logger = _GetLogger('ComplexTypeContainer')

    def setUp(self, tp, empty=False):
        '''Problematic, loose all model group information.
        <all>, <choice>, <sequence> ..

           tp -- type definition
           empty -- no model group, just use as a dummy holder.
        '''

        self._item = tp

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.mixed = tp.isMixed()
        self.mgContent = ()
        self.attrComponents = \
            self._setAttributes(tp.getAttributeContent())

        # Save reference to type for debugging

        self._item = tp

        if empty:
            return

        model = tp.content
        if model.isReference():
            model = model.getModelGroupReference()

        if model is None:
            return

        if model.content is None:
            return

        # sequence, all or choice
        # self.mgContent = model.content

        self.mgContent = model

    def _setContent(self):
        try:
            definition = [  # '%s'   % self.getElements(),
                f'{ID1}class {self.getClassName()}(ZSI.TCcompound.ComplexType, TypeDefinition):',
                f'{ID2}{self.schemaTag()}',
                f'{ID2}{self.typeTag()}',
                f'{ID2}{self.pnameConstructor()}',
                f'{ID3}{self.nsuriLogic()}',
                f'{ID3}TClist = [{self.getTypecodeList()}]',
            ]
        except Exception as ex:
            args = ['Failure processing %s' % self._item.getItemTrace()]
            args += ex.args
            ex.args = tuple(args)
            raise

        definition.append('%s%s = attributes or {}' % (ID3,
                                                       self.attribute_typecode))

        # IF EXTEND

        definition.append('%sif extend: TClist += ofwhat' % ID3)

        # IF RESTRICT

        definition.append('%sif restrict: TClist = ofwhat' % ID3)

        # ELSE

        if len(self.attrComponents) > 0:
            definition.append('%selse:' % ID3)
            for l in self.attrComponents:
                definition.append('%s%s' % (ID4, l))

        definition.append('%sZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, %s**kw)'
                          % (ID3, self.getExtraFlags()))

        # pyclass class definition

        definition += self.getPyClassDefinition()

        # set pyclass

        kw = KW.copy()
        kw['pyclass'] = self.getPyClass()
        definition.append('%(ID3)sself.pyclass = %(pyclass)s' % kw)
        self.writeArray(definition)

    def pnameConstructor(self, superclass=None):
        ''' TODO: Logic is a little tricky.  If superclass is ComplexType this is not used.
        '''

        if superclass:
            return '%s.__init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw)' \
                % superclass

        return 'def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):'


class SimpleTypeContainer(TypecodeContainerBase):
    type = DEF
    logger = _GetLogger('SimpleTypeContainer')

    def __init__(self):
        """
        Instance Data From TypecodeContainerBase NOT USED...
           mgContent
        """

        TypecodeContainerBase.__init__(self)

    def setUp(self, tp):
        raise NotImplementedError('abstract method not implemented')

    def _setContent(self, tp):
        raise NotImplementedError('abstract method not implemented')

    def getPythonType(self):
        if issubclass(self.sKlass, ZSI.TC.String):
            return 'str'
        if issubclass(self.sKlass, ZSI.TC.Ilong) or issubclass(self.sKlass,
                                                               ZSI.TC.IunsignedLong):
            return 'long'
        if issubclass(self.sKlass, ZSI.TC.Boolean) or issubclass(self.sKlass,
                                                                 ZSI.TC.Integer):
            return 'int'
        if issubclass(self.sKlass, ZSI.TC.Decimal):
            return 'float'
        if issubclass(self.sKlass, ZSI.TC.Gregorian) or issubclass(self.sKlass,
                                                                   ZSI.TC.Duration):
            return 'tuple'
        return None

    def getPyClassDefinition(self):
        definition = []
        pt = self.getPythonType()
        if pt is not None:
            definition.append('%sclass %s(%s):' % (ID3,
                                                   self.getPyClass(), pt))
            definition.append('%stypecode = self' % ID4)
        return definition


class RestrictionContainer(SimpleTypeContainer):
    """
       simpleType/restriction
    """

    logger = _GetLogger('RestrictionContainer')

    def setUp(self, tp):
        self._item = tp

        assert (
                tp.isSimple() and tp.isDefinition() and tp.content.isRestriction()
        ), f'expecting simpleType restriction, not: {tp.getItemTrace()}'

        if tp.content is None:
            raise Wsdl2PythonError(f'empty simpleType defintion: {tp.getItemTrace()}')

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = None

        base = tp.content.getAttribute('base')
        if base is not None:
            try:
                item = tp.content.getTypeDefinition('base')
            except XMLSchema.SchemaError:
                item = None

            if item is None:
                self.sKlass = BTI.get_typeclass(base.getName(),
                                                base.getTargetNamespace())
                if self.sKlass is not None:
                    return

                raise Wsdl2PythonError('no built-in type nor schema instance type for base attribute("%s","%s"): %s'
                                       % (base.getTargetNamespace(), base.getName(),
                                          tp.getItemTrace()))
            else:
                base = item.content.getAttribute('base')
                self.sKlass = BTI.get_typeclass(base.getName(),
                                                base.getTargetNamespace())
                if self.sKlass is not None:
                    return

            warnings.warn(
                f'Using string for simpleType/Restriction w/User-Defined Base: {tp.getItemTrace()} {item.getItemTrace()}'
            )

            self.logger.warning(
                f'Unsupported: SimpleType  ({self.ns},{self.name}), setting restriction base to xsd:string'
            )

            # self.sKlass = "%s.%s" %(base.getName(), base.getTargetNamespace())

            self.sKlass = BTI.get_typeclass('string', SCHEMA.XSD3)

            return

        sc = tp.content.getSimpleTypeContent()
        if sc is not None and True is sc.isSimple() is sc.isLocal() \
                            is sc.isDefinition():
            base = None
            if sc.content.isRestriction() is True:
                with contextlib.suppress(XMLSchema.SchemaError):
                    item = tp.content.getTypeDefinition('base')
                if item is None:
                    base = sc.content.getAttribute('base')
                    if base is not None:
                        self.sKlass = BTI.get_typeclass(base.getTargetNamespace(),
                                                        base.getName())
                        return
                    raise Wsdl2PythonError(
                        f'Not Supporting simpleType/Restriction w/User-Defined Base: {item.getItemTrace()}')

                raise Wsdl2PythonError(
                    f'Not Supporting simpleType/Restriction w/User-Defined Base: {item.getItemTrace()}')

            if sc.content.isList() is True:
                raise Wsdl2PythonError(f'iction base in subtypes: {sc.getItemTrace()}')

            if sc.content.isUnion() is True:
                raise Wsdl2PythonError(
                    f'could not get restriction base in subtypes: {sc.getItemTrace()}'
                )

            return

        raise Wsdl2PythonError(f'No Restriction @base/simpleType: {tp.getItemTrace()}')

    def _setContent(self):

        definition = [
            f'{ID1}class {self.getClassName()}({strip_typeclass_string_to_module_class_string(self.sKlass)}, TypeDefinition):',
            f'{ID2}{self.schemaTag()}',
            f'{ID2}{self.typeTag()}',
            f'{ID2}{self.pnameConstructor()}',
        ]
        if not self.getPythonType():
            definition.append(f'{ID3}{strip_typeclass_string_to_module_class_string(self.sKlass)}.__init__(self, pname, **kw)')
        else:
            definition.append(
                f'{ID3}{strip_typeclass_string_to_module_class_string(self.sKlass)}.__init__(self, pname, pyclass=None, **kw)'
            )

            # pyclass class definition

            definition += self.getPyClassDefinition()

            # set pyclass

            kw = KW.copy()
            kw['pyclass'] = self.getPyClass()
            definition.append('%(ID3)sself.pyclass = %(pyclass)s' % kw)

        self.writeArray(definition)


class ComplexTypeSimpleContentContainer(SimpleTypeContainer,
                                        AttributeMixIn):
    """Represents a ComplexType with simpleContent.
    """

    type = DEF
    logger = _GetLogger('ComplexTypeSimpleContentContainer')

    def setUp(self, tp):
        """tp -- complexType/simpleContent/[Exention,Restriction]
        """

        self._item = tp

        assert (
            tp.isComplex() is True and tp.content.isSimple() is True
        ), f'expecting complexType/simpleContent not: {tp.content.getItemTrace()}'

        simple = tp.content
        dv = simple.content
        assert (
            dv.isExtension() is True or dv.isRestriction() is True
        ), f'expecting complexType/simpleContent/[Extension,Restriction] not: {tp.content.getItemTrace()}'

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()

        # TODO: Why is this being set?

        self.content.attributeContent = dv.getAttributeContent()

        base = dv.getAttribute('base')
        if base is not None:
            self.sKlass = BTI.get_typeclass(base[1], base[0])
            if not self.sKlass:
                (self.sKlass, self.sKlassNS) = (base[1], base[0])

            self.attrComponents = self._setAttributes(self.content.attributeContent)
            return

        raise Wsdl2PythonError('simple content derivation bad base attribute: '
                               % tp.getItemTrace())

    def _setContent(self):

        # TODO: Add derivation logic to constructors.

        if type(self.sKlass) in (type, type):
            definition = [
                f'{ID1}class {self.getClassName()}({self.sKlass}, TypeDefinition):',
                f'{ID2}# ComplexType/SimpleContent derivation of built-in type',
                f'{ID2}{self.schemaTag()}',
                f'{ID2}{self.typeTag()}',
                f'{ID2}{self.pnameConstructor()}',
                f'{ID3}if getattr(self, "attribute_typecode_dict", None) is None: {self.attribute_typecode} = {{}}',
            ]

            definition.extend(f'{ID3}{l}' for l in self.attrComponents)
            definition.append(f'{ID3}{self.sKlass}.__init__(self, pname, **kw)')
            if self.getPythonType() is not None:
                definition += self.getPyClassDefinition()
                kw = KW.copy()
                kw['pyclass'] = self.getPyClass()
                definition.append('%(ID3)sself.pyclass = %(pyclass)s'
                                  % kw)

            self.writeArray(definition)
            return

        definition = [
            f'{ID1}class {self.getClassName()}(TypeDefinition):',
            f'{ID2}# ComplexType/SimpleContent derivation of user-defined type',
            f'{ID2}{self.schemaTag()}',
            f'{ID2}{self.typeTag()}',
            f'{ID2}{self.pnameConstructor()}',
            f'{ID3}{self.nsuriLogic()}',
            f'{self.getBasesLogic(ID3)}',
            f'{ID3}if getattr(self, "attribute_typecode_dict", None) is None: {self.attribute_typecode} = {{}}',
        ]

        definition.extend(f'{ID3}{l}' for l in self.attrComponents)
        definition.append(
            f'{ID3}{NAD.getAlias(self.sKlassNS)}.{type_class_name(self.sKlass)}.__init__(self, pname, **kw)'
        )

        self.writeArray(definition)

    def getPyClassDefinition(self):
        definition = []
        pt = self.getPythonType()
        if pt is not None:
            definition.append(f'{ID3}class {self.getPyClass()}({pt}):')
            if self.metaclass is not None:
                definition.append(f'{ID4}__metaclass__ = {self.metaclass}')

            definition.append(f'{ID4}typecode = self')
        return definition


class UnionContainer(SimpleTypeContainer):
    """SimpleType Union
    """

    type = DEF
    logger = _GetLogger('UnionContainer')

    def __init__(self):
        SimpleTypeContainer.__init__(self)
        self.memberTypes = None

    def setUp(self, tp):
        self._item = tp

        if tp.content.isUnion() is False:
            raise ContainerError(f'content must be a Union: {tp.getItemTrace()}')
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = 'ZSI.TC.Union'
        self.memberTypes = tp.content.getAttribute('memberTypes')

    def _setContent(self):
        definition = [
            f'{ID1}class {self.getClassName()}({self.sKlass}, TypeDefinition):',
            f'{ID2}memberTypes = {self.memberTypes}',
            f'{ID2}{self.schemaTag()}',
            f'{ID2}{self.typeTag()}',
            f'{ID2}{self.pnameConstructor()}',
            f'{ID3}{self.pnameConstructor(self.sKlass)}',
        ]

        # TODO: Union pyclass is None

        self.writeArray(definition)


class ListContainer(SimpleTypeContainer):
    """SimpleType List
    """

    type = DEF
    logger = _GetLogger('ListContainer')

    def setUp(self, tp):
        self._item = tp

        if tp.content.isList() is False:
            raise ContainerError('content must be a List: %s'
                                 % tp.getItemTrace())
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = 'ZSI.TC.List'
        self.itemType = tp.content.getAttribute('itemType')

    def _setContent(self):
        definition = [
            '%sclass %s(%s, TypeDefinition):' % (ID1,
                                                 self.getClassName(), self.sKlass),
            '%sitemType = %s' % (ID2, self.itemType),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.typeTag()),
            '%s%s' % (ID2, self.pnameConstructor()),
            '%s%s' % (ID3, self.pnameConstructor(self.sKlass)),
        ]
        self.writeArray(definition)
