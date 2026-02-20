"""Example plugin for `scripts/wsdl2py --plugin ...`.

Hooks are optional. Implement any subset:
- on_options(options)
- on_wsdl_loaded(options, wsdl)
- before_generate(options, wsdl)
- after_generate(options, wsdl, files)
"""


def on_options(options):
    # Example: normalize custom defaults.
    if not hasattr(options, "compat"):
        return


def on_wsdl_loaded(options, wsdl):
    # Example: inspect loaded metadata for project-specific checks.
    _ = (options, wsdl)


def before_generate(options, wsdl):
    # Example: mutate naming flags before code generation.
    _ = (options, wsdl)


def after_generate(options, wsdl, files):
    # Example: post-process generated file list.
    _ = (options, wsdl, files)
