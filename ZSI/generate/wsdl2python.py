############################################################################
# Monte M. Goode, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################

# main generator engine for new generation generator

# $Id: wsdl2python.py 1402 2007-07-06 22:51:32Z boverhof $

import sys

from ZSI import _get_idstr
from ZSI.generate.utility import GetModuleBaseNameFromWSDL, NormalizeNamespace
from ZSI.wstools.XMLSchema import SchemaReader
from ZSI.wstools.logging import getLogger as _GetLogger
from .containers import *

"""
classes:
    WriteServiceModule
    -- composes/writes out client stubs and types module.

    ServiceDescription
    -- represents a single WSDL service.

    MessageWriter
    -- represents a single WSDL Message and associated bindings
    of the port/binding.

    SchemaDescription
    -- generates classes for defs and decs in the schema instance.

    TypeWriter
    -- represents a type definition.

    ElementWriter
    -- represents a element declaration.

"""


class WriteServiceModule:
    """top level driver class invoked by wsd2py
    class variables:
        client_module_suffix -- suffix of client module.
        types_module_suffix -- suffix of types module.
    """
    client_module_suffix = '_client'
    messages_module_suffix = '_messages'
    types_module_suffix = '_types'
    logger = _GetLogger("WriteServiceModule")

    def __init__(self, wsdl, addressing=False, notification=False,
                 do_extended=False, extPyClasses=None, configParser=None):
        self._wsdl = wsdl
        self._addressing = addressing
        self._notification = notification
        self._configParser = configParser
        self.usedNamespaces = None
        self.services = []
        self.client_module_path = None
        self.types_module_name = None
        self.types_module_path = None
        self.messages_module_path = None  # used in extended generation
        self.do_extended = do_extended
        self.extPyClasses = extPyClasses

    def getClientModuleName(self):
        """client module name.
        """
        if name := GetModuleBaseNameFromWSDL(self._wsdl):
            return (
                name
                if self.client_module_suffix is None
                else f'{name}{self.client_module_suffix}'
            )
        else:
            raise WsdlGeneratorError('could not determine a service name')

    #    def getMessagesModuleName(self):
    #        name = GetModuleBaseNameFromWSDL(self._wsdl)
    #        if not name:
    #            raise WsdlGeneratorError, 'could not determine a service name'
    #
    #        if self.messages_module_suffix is None:
    #            return name
    #
    #        if len(self.messages_module_suffix) == 0:
    #            return self.getClientModuleName()
    #
    #        return '%s%s' %(name, self.messages_module_suffix)

    def setTypesModuleName(self, name):
        self.types_module_name = name

    def getTypesModuleName(self):
        """types module name.
        """
        if self.types_module_name is not None:
            return self.types_module_name

        if name := GetModuleBaseNameFromWSDL(self._wsdl):
            return (
                name
                if self.types_module_suffix is None
                else f'{name}{self.types_module_suffix}'
            )
        else:
            raise WsdlGeneratorError('could not determine a service name')

    def setClientModulePath(self, path):
        """setup module path to where client module before calling fromWsdl.
        module path to types module eg. MyApp.client
        """
        self.client_module_path = path

    def getTypesModulePath(self):
        """module path to types module eg. MyApp.types
        """
        return self.types_module_path

    #    def getMessagesModulePath(self):
    #        '''module path to messages module
    #           same as types path
    #        '''
    #        return self.messages_module_path

    def setTypesModulePath(self, path):
        """setup module path to where service module before calling fromWsdl.
        module path to types module eg. MyApp.types
        """
        self.types_module_path = path

    #    def setMessagesModulePath(self, path):
    #        """setup module path to where message module before calling fromWsdl.
    #        module path to types module eg. MyApp.types
    #        """
    #        self.messages_module_path = path

    def gatherNamespaces(self):
        """This method must execute once..  Grab all schemas
        representing each targetNamespace.
        """
        if self.usedNamespaces is not None:
            return

        self.logger.debug('gatherNamespaces')
        self.usedNamespaces = {}

        def recommended_ns(schema):
            if schema is None:
                return None
            tns = NormalizeNamespace(schema.getTargetNamespace())
            recommended = None
            attributes = getattr(schema, 'attributes', None) or {}
            for k, v in list(attributes.get('xmlns', {}).items()):
                if k == '':
                    continue
                if v == tns:
                    recommended = k
                    break

            return recommended

        # Add all schemas defined in wsdl
        # to used namespace and to the Alias dict
        for schema in list(self._wsdl.types.values()):
            if schema is None:
                continue
            tns = NormalizeNamespace(schema.getTargetNamespace())
            self.logger.debug(f'Register schema({_get_idstr(schema)}) -- TNS({tns})')
            if tns not in self.usedNamespaces:
                self.usedNamespaces[tns] = []
            self.usedNamespaces[tns].append(schema)
            NAD.add(tns, recommended_ns(schema))

        # Add all xsd:import schema instances
        # to used namespace and to the Alias dict
        for k, v in list(SchemaReader.namespaceToSchema.items()):
            if v is None:
                continue
            k = NormalizeNamespace(k)
            schema_ns = NormalizeNamespace(v.getTargetNamespace())
            tns = schema_ns or k
            self.logger.debug(f'Register schema({_get_idstr(v)}) -- TNS({tns})')
            if tns not in self.usedNamespaces:
                self.usedNamespaces[tns] = []
            self.usedNamespaces[tns].append(v)
            NAD.add(tns, recommended_ns(v))

    def writeClient(self, fd, sdClass=None, **kw):
        """write out client module to file descriptor.
        Parameters and Keywords arguments:
            fd -- file descriptor
            sdClass -- service description class name
            imports -- list of imports
            readerclass -- class name of ParsedSoap reader
            writerclass -- class name of SoapWriter writer
        """
        sdClass = sdClass or ServiceDescription
        assert issubclass(sdClass, ServiceDescription), \
                        'parameter sdClass must subclass ServiceDescription'

        #        header = '%s \n# %s.py \n# generated by %s\n%s\n'\
        #                  %('#'*50, self.getClientModuleName(), self.__module__, '#'*50)
        print('#' * 50, file=fd)
        print(f'# file: {self.getClientModuleName()}.py', file=fd)
        print('# ', file=fd)
        print(f'# client stubs generated by "{self.__class__}"', file=fd)
        print(f"#     {' '.join(sys.argv)}", file=fd)
        print('# ', file=fd)
        print('#' * 50, file=fd)

        self.services = []
        for service in self._wsdl.services.values():
            sd = sdClass(self._addressing, do_extended=self.do_extended,
                         wsdl=self._wsdl)
            if len(self._wsdl.types) > 0:
                sd.setTypesModuleName(self.getTypesModuleName(),
                                      self.getTypesModulePath())
            #                sd.setMessagesModuleName(self.getMessagesModuleName(),
            #                                         self.getMessagesModulePath())

            self.gatherNamespaces()
            sd.fromWsdl(service, **kw)
            sd.write(fd)
            self.services.append(sd)

    def writeTypes(self, fd):
        """write out types module to file descriptor.
        """
        print('#' * 50, file=fd)
        print(f'# file: {self.getTypesModuleName()}.py', file=fd)
        print('#', file=fd)
        print(f'# schema types generated by "{self.__class__}"', file=fd)
        print(f"#    {' '.join(sys.argv)}", file=fd)
        print('#', file=fd)
        print('#' * 50, file=fd)

        print(TypesHeaderContainer(), file=fd)
        self.gatherNamespaces()
        for l in list(self.usedNamespaces.values()):
            sd = SchemaDescription(do_extended=self.do_extended,
                                   extPyClasses=self.extPyClasses)
            for schema in l:
                sd.fromSchema(schema)
            sd.write(fd)


class ServiceDescription:
    """client interface - locator, port, etc classes"""
    separate_messages = False
    logger = _GetLogger("ServiceDescription")

    def __init__(self, addressing=False, do_extended=False, wsdl=None):
        self.typesModuleName = None
        self.messagesModuleName = None
        self.wsAddressing = addressing
        self.imports = ServiceHeaderContainer()
        self.messagesImports = ServiceHeaderContainer()
        self.locator = ServiceLocatorContainer()
        self.bindings = []
        self.messages = []
        self.do_extended = do_extended
        self._wsdl = wsdl  # None unless do_extended == True

    def setTypesModuleName(self, name, modulePath=None):
        """The types module to be imported.
        Parameters
        name -- name of types module
        modulePath -- optional path where module is located.
        """
        self.typesModuleName = f'{name}'
        if modulePath is not None:
            self.typesModuleName = f'{modulePath}.{name}'

    #    def setMessagesModuleName(self, name, modulePath=None):
    #        '''The types module to be imported.
    #        Parameters
    #        name -- name of types module
    #        modulePath -- optional path where module is located.
    #        '''
    #        self.messagesModuleName = '%s' %name
    #        if modulePath is not None:
    #            self.messagesModuleName = '%s.%s' %(modulePath,name)

    def fromWsdl(self, service, **kw):
        self.imports.setTypesModuleName(self.typesModuleName)
        #        if self.separate_messages:
        #            self.messagesImports.setMessagesModuleName(self.messagesModuleName)
        self.imports.appendImport(kw.get('imports', []))

        self.locator.setUp(service)

        seen_bindings = set()
        for port in service.ports.values():
            binding_name = getattr(port, 'binding', None)
            if not binding_name:
                warnings.warn('not all ports have binding declared,')
                continue
            if binding_name in seen_bindings:
                continue
            seen_bindings.add(binding_name)

            desc = BindingDescription(useWSA=self.wsAddressing,
                                      do_extended=self.do_extended,
                                      wsdl=self._wsdl)
            try:
                desc.setUp(port.getBinding())
            except Wsdl2PythonError as ex:
                self.logger.warning(f'Skipping port({port.name})')
                if len(ex.args):
                    self.logger.warning(ex.args[0])
                continue

            desc.setReaderClass(kw.get('readerclass'))
            desc.setWriterClass(kw.get('writerclass'))
            for soc in desc.operations:
                if soc.hasInput() is True:
                    mw = MessageWriter(do_extended=self.do_extended)
                    mw.setUp(soc, port, input=True)
                    self.messages.append(mw)

                    if soc.hasOutput() is True:
                        mw = MessageWriter(do_extended=self.do_extended)
                        mw.setUp(soc, port, input=False)
                        self.messages.append(mw)

            self.bindings.append(desc)

    def write(self, fd, msg_fd=None):
        """write out module to file descriptor.
        fd -- file descriptor to write out service description.
        msg_fd -- optional file descriptor for messages module.
        """
        #        if msg_fd != None:
        #            print >>fd, self.messagesImports
        #            print >>msg_fd, self.imports
        #        else:
        print(self.imports, file=fd)

        print(self.locator, file=fd)
        for m in self.bindings:
            print(m, file=fd)

        #        if msg_fd != None:
        #            for m in self.messages:
        #                print >>msg_fd, m
        #        else:
        for m in self.messages:
            print(m, file=fd)


class MessageWriter:
    logger = _GetLogger("MessageWriter")

    def __init__(self, do_extended=False):
        """Representation of a WSDL Message and associated WSDL Binding.
        operation --
        boperation --
        input --
        rpc --
        literal --
        simple --
        """
        self.content = None
        self.do_extended = do_extended

    def __str__(self):
        if not self.content:
            raise Wsdl2PythonError('Must call setUp.')
        return self.content.getvalue()

    def setUp(self, soc, port, input=False):
        assert isinstance(soc, ServiceOperationContainer), \
                'expecting a ServiceOperationContainer instance'
        assert isinstance(port, WSDLTools.Port), \
                'expecting a WSDL.Port instance'

        rpc, literal = soc.isRPC(), soc.isLiteral(input)
        kw, klass = {}, None

        if rpc and literal:
            klass = ServiceRPCLiteralMessageContainer
        elif not rpc and literal:
            kw['do_extended'] = self.do_extended
            klass = ServiceDocumentLiteralMessageContainer
        elif rpc:
            klass = ServiceRPCEncodedMessageContainer
        else:
            raise WsdlGeneratorError('doc/enc not supported.')

        self.content = klass(**kw)
        self.content.setUp(port, soc, input)


class SchemaDescription:
    """generates classes for defs and decs in the schema instance.
    """
    logger = _GetLogger("SchemaDescription")

    def __init__(self, do_extended=False, extPyClasses=None):
        self.classHead = NamespaceClassHeaderContainer()
        self.classFoot = NamespaceClassFooterContainer()
        self.items = []
        self.__types = []
        self.__elements = []
        self.targetNamespace = None
        self.do_extended = do_extended
        self.extPyClasses = extPyClasses

    def fromSchema(self, schema):
        """ Can be called multiple times, but will not redefine a
        previously defined type definition or element declaration.
        """
        ns = NormalizeNamespace(schema.getTargetNamespace())
        assert (
                self.targetNamespace is None or self.targetNamespace == ns
        ), f'SchemaDescription instance represents {self.targetNamespace}, not {ns}'

        if self.targetNamespace is None:
            self.targetNamespace = ns

        self.classHead.ns = self.classFoot.ns = ns
        for item in [t for t in schema.types.values() if t.getAttributeName() not in self.getTypes()]:
            self.__types.append(item.getAttributeName())
            self.items.append(TypeWriter(do_extended=self.do_extended, extPyClasses=self.extPyClasses))
            self.items[-1].fromSchemaItem(item)

        for item in [e for e in schema.elements.values() if e.getAttributeName() not in self.getElements()]:
            self.__elements.append(item.getAttributeName())
            self.items.append(ElementWriter(do_extended=self.do_extended))
            self.items[-1].fromSchemaItem(item)

    def getTypes(self):
        return self.__types

    def getElements(self):
        return self.__elements

    def write(self, fd):
        """write out to file descriptor.
        """
        print(self.classHead, file=fd)
        for t in self.items:
            print(t, file=fd)
        print(self.classFoot, file=fd)


class SchemaItemWriter:
    """contains/generates a single declaration"""
    logger = _GetLogger("SchemaItemWriter")

    def __init__(self, do_extended=False, extPyClasses=None):
        self.content = None
        self.do_extended = do_extended
        self.extPyClasses = extPyClasses

    def __str__(self):
        """this appears to set up whatever is in self.content.localElements,
        local elements simpleType|complexType.
        """
        assert self.content is not None, 'Must call fromSchemaItem to setup.'
        return str(self.content)

    def fromSchemaItem(self, item):
        raise NotImplementedError('')


class ElementWriter(SchemaItemWriter):
    """contains/generates a single declaration"""
    logger = _GetLogger("ElementWriter")

    def fromSchemaItem(self, item):
        """set up global elements.
        """
        if item.isElement() is False or item.isLocal() is True:
            raise TypeError(f'expecting global element declaration: {item.getItemTrace()}')

        local = False
        if item.getAttribute('type'):
            etp = item.getTypeDefinition('type')

        else:
            etp = item.content
            local = True
        if etp is None:
            if local:
                self.content = ElementLocalComplexTypeContainer(do_extended=self.do_extended)
            else:
                self.content = ElementSimpleTypeContainer()
        elif etp.isLocal() is False:
            self.content = ElementGlobalDefContainer()
        elif etp.isSimple() is True:
            self.content = ElementLocalSimpleTypeContainer()
        elif etp.isComplex():
            self.content = ElementLocalComplexTypeContainer(do_extended=self.do_extended)
        else:
            raise Wsdl2PythonError(f"Unknown element declaration: {item.getItemTrace()}")

        self.logger.debug('ElementWriter setUp container "%r", Schema Item "%s"' % (
            self.content, item.getItemTrace()))

        self.content.setUp(item)


class TypeWriter(SchemaItemWriter):
    """contains/generates a single definition"""
    logger = _GetLogger("TypeWriter")

    def fromSchemaItem(self, item):
        if item.isDefinition() is False or item.isLocal() is True:
            raise TypeError(f'expecting global type definition not: {item.getItemTrace()}')

        self.content = None
        if item.isSimple():
            if item.content.isRestriction():
                self.content = RestrictionContainer()
            elif item.content.isUnion():
                self.content = UnionContainer()
            elif item.content.isList():
                self.content = ListContainer()
            else:
                raise Wsdl2PythonError(
                    f'unknown simple type definition: {item.getItemTrace()}'
                )

            self.content.setUp(item)
            return

        if item.isComplex():
            kw = {}
            if item.content is None or item.content.isModelGroup():
                self.content = \
                                        ComplexTypeContainer(
                            do_extended=self.do_extended,
                        extPyClasses=self.extPyClasses
                    )
                kw['empty'] = item.content is None
            elif item.content.isSimple():
                self.content = ComplexTypeSimpleContentContainer()
            elif item.content.isComplex():
                self.content = ComplexTypeComplexContentContainer(do_extended=self.do_extended)
            else:
                raise Wsdl2PythonError(
                    f'unknown complex type definition: {item.getItemTrace()}'
                )

            self.logger.debug('TypeWriter setUp container "%r", Schema Item "%s"' % (
                self.content, item.getItemTrace()))

            try:
                self.content.setUp(item, **kw)
            except Exception as ex:
                args = [f'Failure in setUp: {item.getItemTrace()}']
                args += ex.args
                ex.args = tuple(args)
                raise

            return

        raise TypeError(f'expecting SimpleType or ComplexType: {item.getItemTrace()}')
