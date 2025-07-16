def configure_default_env():
    from .container import Container

    container = Container()
    container.wire(
        modules=[__name__, "scipion_bridge.ffi.scipion"], packages=["scipion_bridge"]
    )
