############################################################################
# Joshua Boverhof<JRBoverhof@lbl.gov>, LBNL
# Monte Goode <MMGoode@lbl.gov>, LBNL
# See Copyright for copyright notice!
############################################################################

import importlib
import importlib.util
import sys, optparse, os, warnings, traceback
from os.path import isfile, join, split

#from operator import xor
import ZSI
from configparser import ConfigParser
from ZSI.generate.wsdl2python import WriteServiceModule, ServiceDescription as wsdl2pyServiceDescription
from ZSI.wstools import WSDLTools, XMLSchema
from ZSI.wstools.logging import getLogger as _GetLogger, setBasicLoggerDEBUG,setBasicLoggerWARN
from ZSI.generate import containers, utility
from ZSI.generate.utility import NCName_to_ClassName as NC_to_CN, TextProtect
from ZSI.generate.wsdl2dispatch import ServiceModuleWriter as ServiceDescription
from ZSI.generate.wsdl2dispatch import WSAServiceModuleWriter as ServiceDescriptionWSA
from ZSI.diagnostics import append_context_to_exception
from ZSI.telemetry import span


warnings.filterwarnings('ignore', '', UserWarning)
_log = _GetLogger("ZSI.generate.commands")


def _describe_wsdl(wsdl):
    details = []
    location = getattr(wsdl, 'location', None)
    if location:
        details.append('location=%s' % location)
    target_ns = getattr(wsdl, 'targetNamespace', None)
    if not target_ns and hasattr(wsdl, 'types'):
        try:
            if len(wsdl.types):
                target_ns = list(wsdl.types.keys())[0]
        except Exception:
            target_ns = None
    if target_ns:
        details.append('targetNamespace=%s' % target_ns)
    name = getattr(wsdl, 'name', None)
    if name:
        details.append('name=%s' % name)
    return ', '.join(details)


def _load_plugin_module(spec):
    """Load a plugin from module path or from a local .py file."""
    if os.path.isfile(spec):
        module_name = "zsi_plugin_" + str(abs(hash(os.path.abspath(spec))))
        module_spec = importlib.util.spec_from_file_location(module_name, spec)
        if module_spec is None or module_spec.loader is None:
            raise ImportError("cannot load plugin from file: %s" % spec)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
    return importlib.import_module(spec)


def _load_plugins(specs):
    plugins = []
    for spec in specs or []:
        plugins.append(_load_plugin_module(spec))
    return plugins


def _invoke_plugin_hook(plugins, hook_name, **kwargs):
    for plugin in plugins:
        hook = getattr(plugin, hook_name, None)
        if callable(hook):
            hook(**kwargs)


def SetDebugCallback(option, opt, value, parser, *args, **kwargs):
    setBasicLoggerDEBUG()
    warnings.resetwarnings()

def SetPyclassMetaclass(option, opt, value, parser, *args, **kwargs):
    """set up pyclass metaclass for complexTypes"""
    from ZSI.generate.containers import ServiceHeaderContainer,\
        TypecodeContainerBase, TypesHeaderContainer

    TypecodeContainerBase.metaclass = kwargs['metaclass']
    import_stmt = 'from %(module)s import %(metaclass)s' % kwargs
    if import_stmt not in TypesHeaderContainer.imports:
        TypesHeaderContainer.imports.append(import_stmt)
    if import_stmt not in ServiceHeaderContainer.imports:
        ServiceHeaderContainer.imports.append(import_stmt)

def SetUpLazyEvaluation(option, opt, value, parser, *args, **kwargs):
    from ZSI.generate.containers import TypecodeContainerBase
    TypecodeContainerBase.lazy = True

def SetUpFastGeneration(option, opt, value, parser, *args, **kwargs):
    """Prototype: use faster generation defaults with reduced output."""
    parser.values.fast = True
    SetUpLazyEvaluation(option, opt, value, parser, *args, **kwargs)


def _validate_wsdl_strict(wsdl, schema_mode=False):
    """Apply stricter structural checks to fail early on weak definitions."""
    if schema_mode:
        tns = wsdl.getTargetNamespace()
        if not tns:
            raise ValueError('strict-schema requires schema targetNamespace')
        return

    types_count = 0
    try:
        types_count = len(getattr(wsdl, 'types', {}) or {})
    except Exception:
        types_count = 0
    if types_count == 0:
        raise ValueError('strict-schema requires at least one WSDL types/schema entry')

    services_count = 0
    try:
        services_count = len(getattr(wsdl, 'services', {}) or {})
    except Exception:
        services_count = 0
    if services_count == 0:
        raise ValueError('strict-schema requires at least one WSDL service')


def wsdl2py(args=None):
    """Utility for automatically generating client/service interface code from
    a wsdl definition, and a set of classes representing element declarations
    and type definitions.  By default invoking this script produces three files,
    each named after the wsdl definition name, in the current working directory.

    Generated Modules Suffix (default mode):
        _client.py -- client locator, rpc proxy port, messages
        _types.py  -- typecodes representing
        _server.py -- server-side bindings
    In --fast mode, _server.py generation is skipped.

    Parameters:
        args -- optional can provide arguments, rather than parsing
            command-line.

    return:
        Default behavior is to return None, if args are provided then
        return names of the generated files.

    """
    op = optparse.OptionParser(usage="USAGE: %wsdl2py [options] WSDL",
             description=wsdl2py.__doc__)

    # Basic options
    op.add_option("-x", "--schema",
                  action="store_true", dest="schema", default=False,
                  help="process just the schema from an xsd file [no services]")

    op.add_option("-d", "--debug",
                  action="callback", callback=SetDebugCallback,
                  help="debug output")

    # WS Options
    op.add_option("-a", "--address",
                  action="store_true", dest="address", default=False,
                  help="ws-addressing support, must include WS-Addressing schema.")

    # pyclass Metaclass
    op.add_option("-b", "--complexType",
                  action="callback", callback=SetPyclassMetaclass,
                  callback_kwargs={'module':'ZSI.generate.pyclass',
                      'metaclass':'pyclass_type'},
                  help="add convenience functions for complexTypes, including Getters, Setters, factory methods, and properties (via metaclass). *** DONT USE WITH --simple-naming ***")

    # Lazy Evaluation of Typecodes (done at serialization/parsing when needed).
    op.add_option("-l", "--lazy",
                  action="callback", callback=SetUpLazyEvaluation,
                  callback_kwargs={},
                  help="EXPERIMENTAL: recursion error solution, lazy evalution of typecodes")

    op.add_option("-f", "--fast",
                  action="callback", callback=SetUpFastGeneration,
                  callback_kwargs={},
                  help="EXPERIMENTAL: faster generation prototype (enables lazy typecodes and skips _server.py generation)")

    op.add_option("--strict-schema",
                  action="store_true", dest="strict_schema", default=False,
                  help="EXPERIMENTAL: fail early on structurally weak schema/WSDL definitions")

    op.add_option("--compat",
                  action="store_true", dest="compat", default=False,
                  help="EXPERIMENTAL: compatibility mode (tolerate wsdl2dispatch generation failures)")

    op.add_option(
        "--plugin",
        action="append",
        dest="plugins",
        default=[],
        help=(
            "Optional plugin module path or .py file. "
            "Supported hooks: on_options, on_wsdl_loaded, before_generate, after_generate."
        ),
    )

    # Use Twisted
    op.add_option("-w", "--twisted",
                  action="store_true", dest='twisted', default=False,
                  help="generate a twisted.web client/server, dependencies python>=2.4, Twisted>=2.0.0, TwistedWeb>=0.5.0")

    op.add_option("-o", "--output-dir",
                  action="store", dest="output_dir", default=".", type="string",
                  help="save files in directory")

    op.add_option("-s", "--simple-naming",
                  action="store_true", dest="simple_naming", default=False,
                  help="map element names directly to python attributes")

    op.add_option("-p", "--pydoc",
                  action="store_true", dest="pydoc", default=False,
                  help="top-level directory for pydoc documentation.")

    with span("zsi.generator.wsdl2py"):
        setBasicLoggerWARN()
        is_cmdline = args is None
        if is_cmdline:
            (options, args) = op.parse_args()
        else:
            (options, args) = op.parse_args(args)

        if len(args) != 1:
            print('Expecting a file/url as argument (WSDL).', file=sys.stderr)
            sys.exit(70)
        if options.strict_schema and options.compat:
            raise ValueError('--strict-schema and --compat are mutually exclusive')

        try:
            plugins = _load_plugins(getattr(options, "plugins", []))
            _invoke_plugin_hook(plugins, "on_options", options=options)
        except Exception as ex:
            append_context_to_exception(ex, "phase=plugins-load")
            raise

        location = args[0]
        if options.schema is True:
            reader = XMLSchema.SchemaReader(base_url=location)
        else:
            reader = WSDLTools.WSDLReader()

        load = reader.loadFromFile
        if not isfile(location):
            load = reader.loadFromURL

        try:
            _log.debug(
                "loading wsdl/schema",
                event="generator.load.start",
                location=location,
                schema_mode=bool(options.schema),
            )
            with span("zsi.generator.load", location=location):
                wsdl = load(location)
            _log.debug(
                "loaded wsdl/schema",
                event="generator.load.end",
                location=location,
                schema_mode=bool(options.schema),
            )
        except Exception as ex:
            _log.error("load failed", event="generator.load.error", location=location)
            append_context_to_exception(ex, 'phase=load, wsdl=%s, loader=%s' % (
                location, load.__name__))
            raise

        try:
            _invoke_plugin_hook(plugins, "on_wsdl_loaded", options=options, wsdl=wsdl)
        except Exception as ex:
            append_context_to_exception(ex, "phase=plugins-on_wsdl_loaded, wsdl=%s" % location)
            raise

        if getattr(options, 'strict_schema', False):
            try:
                _validate_wsdl_strict(wsdl, schema_mode=bool(options.schema))
                _log.debug(
                    "strict validation passed",
                    event="generator.strict_schema.ok",
                    location=location,
                )
            except Exception as ex:
                _log.error(
                    "strict validation failed",
                    event="generator.strict_schema.error",
                    location=location,
                )
                append_context_to_exception(ex, 'phase=strict-validate, wsdl=%s' % location)
                raise

        if isinstance(wsdl, XMLSchema.XMLSchema):
            wsdl.location = location
            try:
                _invoke_plugin_hook(plugins, "before_generate", options=options, wsdl=wsdl)
                _log.debug("generate types from xsd", event="generator.types.start")
                with span("zsi.generator.types"):
                    files = _wsdl2py(options, wsdl)
                _log.debug("generate types from xsd finished", event="generator.types.end")
            except Exception as ex:
                append_context_to_exception(ex, 'phase=generate-types, %s'
                                          % _describe_wsdl(wsdl))
                raise
        else:
            try:
                _invoke_plugin_hook(plugins, "before_generate", options=options, wsdl=wsdl)
                _log.debug("generate client/types start", event="generator.client_types.start")
                with span("zsi.generator.client_types"):
                    files = _wsdl2py(options, wsdl)
                _log.debug("generate client/types end", event="generator.client_types.end")
            except Exception as ex:
                append_context_to_exception(ex, 'phase=generate-client-types, %s'
                                          % _describe_wsdl(wsdl))
                raise
            if not getattr(options, 'fast', False):
                try:
                    _log.debug("generate server start", event="generator.server.start")
                    with span("zsi.generator.server"):
                        files.append(_wsdl2dispatch(options, wsdl))
                    _log.debug("generate server end", event="generator.server.end")
                except Exception as ex:
                    if getattr(options, 'compat', False):
                        _log.warning(
                            "compat mode skipped server generation",
                            event="generator.server.skipped_compat",
                        )
                        warnings.warn('compat mode: skipping wsdl2dispatch failure: %s' % ex)
                    else:
                        append_context_to_exception(ex, 'phase=generate-server, %s'
                                                  % _describe_wsdl(wsdl))
                        raise

        try:
            _invoke_plugin_hook(
                plugins,
                "after_generate",
                options=options,
                wsdl=wsdl,
                files=files,
            )
        except Exception as ex:
            append_context_to_exception(ex, "phase=plugins-after_generate")
            raise

        if getattr(options, 'pydoc', False):
            try:
                _writepydoc(os.path.join('docs', 'API'), *files)
            except Exception as ex:
                append_context_to_exception(ex, 'phase=generate-pydoc, files=%s'
                                          % ','.join(files))
                raise

        if is_cmdline:
            return

        return files


#def wsdl2dispatch(args=None):
#    """Deprecated: wsdl2py now generates everything
#    A utility for automatically generating service skeleton code from a wsdl
#    definition.
#    """
#    op = optparse.OptionParser()
#    op.add_option("-a", "--address",
#                  action="store_true", dest="address", default=False,
#                  help="ws-addressing support, must include WS-Addressing schema.")
#    op.add_option("-d", "--debug",
#                  action="callback", callback=SetDebugCallback,
#                  help="debug output")
#    op.add_option("-t", "--types",
#                  action="store", dest="types", default=None, type="string",
#                  help="Write generated files to OUTPUT_DIR")
#    op.add_option("-o", "--output-dir",
#                  action="store", dest="output_dir", default=".", type="string",
#                  help="file to load types from")
#    op.add_option("-s", "--simple-naming",
#                  action="store_true", dest="simple_naming", default=False,
#                  help="Simplify generated naming.")
#
#    if args is None:
#        (options, args) = op.parse_args()
#    else:
#        (options, args) = op.parse_args(args)
#
#    if len(args) != 1:
#        print>>sys.stderr, 'Expecting a file/url as argument (WSDL).'
#        sys.exit(os.EX_USAGE)
#
#    reader = WSDLTools.WSDLReader()
#    if isfile(args[0]):
#        _wsdl2dispatch(options, reader.loadFromFile(args[0]))
#        return
#
#    _wsdl2dispatch(options, reader.loadFromURL(args[0]))


def _wsdl2py(options, wsdl):

    if options.twisted:
        from ZSI.generate.containers import ServiceHeaderContainer
        try:
            ServiceHeaderContainer.imports.remove('from ZSI import client')
        except ValueError:
            pass
        ServiceHeaderContainer.imports.append('from ZSI.twisted import client')


    if options.simple_naming:
        # Use a different client suffix
        # WriteServiceModule.client_module_suffix = "_client"
        # Write messages definitions to a separate file.
        #wsdl2pyServiceDescription.separate_messages = True
        # Use more simple type and element class names
        containers.SetTypeNameFunc( lambda n: '%s_' %(NC_to_CN(n)) )
        containers.SetElementNameFunc( lambda n: '%s' %(NC_to_CN(n)) )
        # Don't add "_" to the attribute name (remove when --aname works well)
        containers.ContainerBase.func_aname = lambda instnc,n: TextProtect(str(n))
        # write out the modules with their names rather than their number.
        utility.namespace_name = lambda cls, ns: utility.Namespace2ModuleName(ns)

    files = []
    append =  files.append
    if isinstance(wsdl, XMLSchema.XMLSchema):
        wsm = WriteServiceModule(_XMLSchemaAdapter(wsdl.location, wsdl),
                                 addressing=options.address)
    else:
        wsm = WriteServiceModule(wsdl, addressing=options.address)
        client_mod = wsm.getClientModuleName()
        client_file = join(options.output_dir, f'{client_mod}.py')
        append(client_file)
        with open(client_file, 'w+', encoding = "UTF-8") as fd:
            wsm.writeClient(fd)
    types_mod = wsm.getTypesModuleName()
    types_file = join(options.output_dir, f'{types_mod}.py')
    append(types_file)
    with open(types_file, 'w+', encoding = "UTF-8" ) as fd:
        wsm.writeTypes(fd)

    return files


def _wsdl2dispatch(options, wsdl):
    """TOOD: Remove ServiceContainer stuff, and replace with WSGI.
    """
    kw = dict()
    if options.twisted:
        from ZSI.twisted.WSresource import WSResource
        kw['base'] = WSResource
        ss = ServiceDescription(**kw)
        if options.address is True:
            raise RuntimeError('WS-Address w/twisted currently unsupported, edit the "factory" attribute by hand')
    else:
        # TODO: make all this handler arch
        if options.address is True:
            ss = ServiceDescriptionWSA()
        else:
            ss = ServiceDescription(**kw)

    ss.fromWSDL(wsdl)
    file_name = ss.getServiceModuleName()+'.py'
    fd = open( join(options.output_dir, file_name), 'w+')
    ss.write(fd)
    fd.close()

    return file_name


class _XMLSchemaAdapter:
    """Adapts an obj XMLSchema.XMLSchema to look like a WSDLTools.WSDL,
    just setting a couple attributes code expects to see.
    """
    def __init__(self, location, schema):
        """Parameters:
        location -- base location, file path
        schema -- XMLSchema instance
        """
        self.name = '_'.join(split(location)[-1].split('.'))
        self.types = {schema.targetNamespace:schema}




import os, pydoc, sys, warnings, inspect
import  os.path
import logging

try:
    from setuptools._distutils import log
except Exception:
    log = logging.getLogger(__name__)

#from setuptools import find_packages
#from setuptools import Command
from ZSI.schema import ElementDeclaration, TypeDefinition
#from pyGridWare.utility.generate.Modules import NR
#from pyGridWare.utility.generate.Modules import CLIENT, TYPES

#def find_packages_modules(where='.'):
#    #pack,mod,mod_file
#    """Return a list all Python packages found within directory 'where'
#    """
#    out = []
#    stack=[(convert_path(where), '')]
#    while stack:
#        where,prefix = stack.pop(0)
#        for name in os.listdir(where):
#            fn = os.path.join(where,name)
#            #if (os.path.isdir(fn) and
#            #    os.path.isfile(os.path.join(fn,'__init__.py'))
#            #):
#            #    out.append(prefix+name); stack.append((fn,prefix+name+'.'))
#            if (os.path.isdir(fn) and
#                os.path.isfile(os.path.join(fn,'__init__.py'))):
#                stack.append((fn,prefix+name+'.'))
#                continue
#
#            if name == '__init__.py' or not name.endswith('.py'):
#                continue
#
#            out.append((prefix, name.split('.py')[0]))
#
#    return out


def _writedoc(doc, thing, forceload=0):
    """Write HTML documentation to a file in the current directory.
    """
    try:
        object, name = pydoc.resolve(thing, forceload)
        page = pydoc.html.page(pydoc.describe(object), pydoc.html.document(object, name))
        fname = os.path.join(doc, name + '.html')
        file = open(fname, 'w')
        file.write(page)
        file.close()
    except (ImportError, pydoc.ErrorDuringImport) as value:
        traceback.print_exc(sys.stderr)
    else:
        return name + '.html'


def _writeclientdoc(doc, thing, forceload=0):
    """Write HTML documentation to a file in the current directory.
    """
    docmodule = pydoc.HTMLDoc.docmodule
    def strongarm(self, object, name=None, mod=None, *ignored):
        result = docmodule(self, object, name, mod, *ignored)

        # Grab all the aliases to pyclasses and create links.
        nonmembers = []
        push = nonmembers.append
        for k,v in inspect.getmembers(object, inspect.isclass):
            if inspect.getmodule(v) is not object and getattr(v,'typecode',None) is not None:
                push('<a href="%s.html">%s</a>: pyclass alias<br/>' %(v.__name__,k))

        result += self.bigsection('Aliases', '#ffffff', '#eeaa77', ''.join(nonmembers))
        return result

    pydoc.HTMLDoc.docmodule = strongarm
    try:
        object, name = pydoc.resolve(thing, forceload)
        page = pydoc.html.page(pydoc.describe(object), pydoc.html.document(object, name))
        name = os.path.join(doc, name + '.html')
        file = open(name, 'w')
        file.write(page)
        file.close()
    except (ImportError, pydoc.ErrorDuringImport) as value:
        log.debug(str(value))

    pydoc.HTMLDoc.docmodule = docmodule

def _writetypesdoc(doc, thing, forceload=0):
    """Write HTML documentation to a file in the current directory.
    """
    try:
        object, name = pydoc.resolve(thing, forceload)
        name = os.path.join(doc, name + '.html')
    except (ImportError, pydoc.ErrorDuringImport) as value:
        log.debug(str(value))
        return

    # inner classes
    cdict = {}
    fdict = {}
    elements_dict = {}
    types_dict = {}
    for kname,klass in inspect.getmembers(thing, inspect.isclass):
        if thing is not inspect.getmodule(klass):
            continue

        cdict[kname] = inspect.getmembers(klass, inspect.isclass)
        for iname,iklass in cdict[kname]:
            key = (kname,iname)
            fdict[key] = _writedoc(doc, iklass)
            if issubclass(iklass, ElementDeclaration):

                try:
                    typecode = iklass()
                except (AttributeError,RuntimeError) as ex:
                    elements_dict[iname] = _writebrokedoc(doc, ex, iname)
                    continue

                elements_dict[iname] = None
                if typecode.pyclass is not None:
                    elements_dict[iname] = _writedoc(doc, typecode.pyclass)

                continue

            if issubclass(iklass, TypeDefinition):
                try:
                    typecode = iklass(None)
                except (AttributeError,RuntimeError) as ex:
                    types_dict[iname] = _writebrokedoc(doc, ex, iname)
                    continue

                types_dict[iname] = None
                if typecode.pyclass is not None:
                    types_dict[iname] = _writedoc(doc, typecode.pyclass)

                continue


    def strongarm(self, object, name=None, mod=None, funcs={}, classes={}, *ignored):
        """Produce HTML documentation for a class object."""
        realname = object.__name__
        name = name or realname
        bases = object.__bases__
        object, name = pydoc.resolve(object, forceload)
        contents = []
        push = contents.append
        if name == realname:
            title = '<a name="%s">class <strong>%s</strong></a>' % (
                name, realname)
        else:
            title = '<strong>%s</strong> = <a name="%s">class %s</a>' % (
                name, name, realname)

        mdict = {}
        if bases:
            parents = []
            for base in bases:
                parents.append(self.classlink(base, object.__module__))
            title = title + '(%s)' % pydoc.join(parents, ', ')

        doc = self.markup(pydoc.getdoc(object), self.preformat, funcs, classes, mdict)
        doc = doc and '<tt>%s<br>&nbsp;</tt>' % doc
        for iname,iclass in cdict[name]:
            fname = fdict[(name,iname)]

            if iname in elements_dict:
                push('class <a href="%s">%s</a>: element declaration typecode<br/>'\
                    %(fname,iname))
                pyclass = elements_dict[iname]
                if pyclass is not None:
                    push('<ul>instance attributes:')
                    push('<li><a href="%s">pyclass</a>: instances serializable to XML<br/></li>'\
                        %elements_dict[iname])
                    push('</ul>')
            elif iname in types_dict:
                push('class <a href="%s">%s</a>: type definition typecode<br/>' %(fname,iname))
                pyclass = types_dict[iname]
                if pyclass is not None:
                    push('<ul>instance attributes:')
                    push('<li><a href="%s">pyclass</a>: instances serializable to XML<br/></li>'\
                          %types_dict[iname])
                    push('</ul>')
            else:
                push('class <a href="%s">%s</a>: TODO not sure what this is<br/>' %(fname,iname))

        contents = ''.join(contents)
        return self.section(title, '#000000', '#ffc8d8', contents, 3, doc)

    doclass = pydoc.HTMLDoc.docclass
    pydoc.HTMLDoc.docclass = strongarm

    try:
        page = pydoc.html.page(pydoc.describe(object), pydoc.html.document(object, name))
        file = open(name, 'w')
        file.write(page)
        file.close()
    except (ImportError, pydoc.ErrorDuringImport) as value:
        log.debug(str(value))

    pydoc.HTMLDoc.docclass = doclass



def _writebrokedoc(doc, ex, name, forceload=0):
    try:
        fname = os.path.join(doc, name + '.html')
        page = pydoc.html.page(pydoc.describe(ex), pydoc.html.document(str(ex), fname))
        file = open(fname, 'w')
        file.write(page)
        file.close()
    except (ImportError, pydoc.ErrorDuringImport) as value:
        log.debug(str(value))

    return name + '.html'

def _writepydoc(doc, *args):
    """create pydoc html pages
    doc -- destination directory for documents
    *args -- modules run thru pydoc
    """
    ok = True
    if not os.path.isdir(doc):
        os.makedirs(doc)

    if os.path.curdir not in sys.path:
        sys.path.append(os.path.curdir)

    for f in args:
        if f.startswith('./'): f = f[2:]
        name = os.path.sep.join(f.strip('.py').split(os.path.sep))
        try:
            e = __import__(name)
        except Exception as ex:
            raise
#            _writebrokedoc(doc, ex, name)
#            continue

        if name.endswith('_client'):
            _writeclientdoc(doc, e)
            continue

        if name.endswith('_types'):
            _writetypesdoc(doc, e)
            continue

        try:
            _writedoc(doc, e)
        except IndexError as ex:
            _writebrokedoc(doc, ex, name)
            continue


