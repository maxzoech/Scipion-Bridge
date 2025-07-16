def configure_default_env():
    from .container import Container

    container = Container()
    container.wire(modules=[__name__, "emv_tools.ffi.scipion"], packages=["emv_tools"])
