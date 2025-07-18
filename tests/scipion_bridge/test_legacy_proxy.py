# import os

# from scipion_bridge.proxy import (
#     proxify,
#     OutputInfo,
#     TempFileProxy,
#     ReferenceProxy,
# )
# from scipion_bridge.utils.environment.container import Container
# import pytest


# class TempFileMock:

#     def __init__(self):
#         self.count = 0

#     def new_temporary_file(self, suffix: str) -> os.PathLike:
#         file = f"/tmp/temp_file_{self.count}{suffix}"
#         self.count += 1

#         return file

#     def delete(path: os.PathLike):
#         pass


# def test_proxify():

#     @proxify
#     def foo(path: str):
#         assert path == "/tmp/temp_file_0.vol"

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()

#     with container.temp_file_provider.override(temp_file_mock):
#         foo(TempFileProxy("vol"))


# def test_output_proxy():
#     @proxify
#     def foo(output: str):
#         with open(output, mode="w+") as f:
#             f.write("Hello, output!")

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()
#     with container.temp_file_provider.override(temp_file_mock):
#         output = foo(OutputInfo("txt"))
#         assert output.path == "/tmp/temp_file_0.txt"

#         with open(output.path) as f:
#             assert f.read() == "Hello, output!"


# def test_multi_output_proxy():

#     @proxify
#     def foo(output_1, output_2):
#         pass

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()
#     with container.temp_file_provider.override(temp_file_mock):
#         output = foo(OutputInfo("vol"), OutputInfo("vol"))

#         assert output[0].path == "/tmp/temp_file_0.vol"
#         assert output[1].path == "/tmp/temp_file_1.vol"


# def test_proxy_attr():
#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()

#     with container.temp_file_provider.override(temp_file_mock):
#         assert (
#             str(TempFileProxy("vol"))
#             == "<TempFileProxy for /tmp/temp_file_0.vol (owned)>"
#         )


# def test_create_proxy_from_lines():
#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()

#     with container.temp_file_provider.override(temp_file_mock):
#         lines = ["Hello", "World"]
#         files_proxy = TempFileProxy.concatenated_strings(lines, file_ext="txt")

#         with open(files_proxy.path) as f:
#             contents = f.read()
#             assert contents == "HelloWorld"


# def test_nested_proxies():

#     @proxify
#     def func_1(output_path: str):
#         with open(output_path, "w+") as f:
#             f.write("Write from func 1")

#     @proxify
#     def func_2():
#         return func_1(OutputInfo("txt"))

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()
#     with container.temp_file_provider.override(temp_file_mock):
#         output = func_2()
#         assert output.path == "/tmp/temp_file_0.txt"

#         with open(output.path) as f:
#             assert f.read() == "Write from func 1"


# def test_return_value_warning():

#     @proxify
#     def foo(output: str):
#         del output
#         return 42

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()
#     with container.temp_file_provider.override(temp_file_mock):
#         with pytest.warns(UserWarning):
#             foo(OutputInfo("bar"))


# def test_create_reference_proxy():

#     ref_proxy = ReferenceProxy("/path/to/referenced/file.vol")
#     assert ref_proxy.path == "/path/to/referenced/file.vol"


# def test_reassign_proxy():

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()

#     with container.temp_file_provider.override(temp_file_mock):

#         untyped_proxy = TempFileProxy(file_ext=None)
#         with open("/tmp/temp_file_0.txt", mode="w+") as f:
#             f.write("Hello world")

#         typed_proxy = untyped_proxy.reassign("txt")

#         assert typed_proxy.path == "/tmp/temp_file_0.txt"


# def test_reassign_proxy_file_not_found_error():

#     container = Container()
#     container.wire(modules=[__name__])

#     temp_file_mock = TempFileMock()

#     with container.temp_file_provider.override(temp_file_mock):

#         untyped_proxy = TempFileProxy(file_ext=None)
#         # Don't write anything, this will therefore fail

#         with pytest.raises(FileNotFoundError):
#             untyped_proxy.reassign("vol")
