.. _proxies:
Proxies
========

Proxies are the second component of the ``scipion_bridge`` framework. Proxies
can help turn the C-style functions generated using the ``@foreign_function`` in
more ergonomic object orientated code.

Proxies wrap temporary files that are used as the input and  output files of
XMIPP programs. Functions marked with the ``@proxify`` can be passed a ``Proxy``
object for inputs and a ``OutputInfo`` object for output values. Proxies are
optional syntactic sugar meant to complement foreign functions. With proxies
you can call an XMIPP program like this::

    # Plain C-style call
    xmipp_image_resize("/path/to/input.vol", "/path/to/output.vol", dim=size)

    # Proxified
    input_volume = ... # Can be a path or another proxy object
    output = xmipp_image_resize(input_volume, dim=size)

When a ``Proxy`` object is passed to a ``@proxify``'ed function, only the path
of the underlying file is passed to the function. To map outputs, pass an
``OutputInfo`` object; ``@proxify`` will created a new proxy and pass its path
to the function. The newly created proxy objects are returned by the function.
XMIPP programs declared in ``ffi.scipion`` use a ``OutputInfo`` as their default
value for output parameters.

Proxies are File Abstractions
-----------------------------

Proxies provide an abstraction over temporary files that makes working with
XMIPP programs more economic. There are subclasses of ``Proxy``:

* ``TempFileProxy`` that provides temporary "scratchpad" files for XMIPP programs
* ``ReferenceProxy`` that wraps an existing file

Proxies can either be `owned` or `unowned`. Owned proxies delete the file after
they have been deallocated. Temporary file proxies are always owned, as they
create the file they wrap. Owned reference proxies are used in
``reassign(new_ext: str)`` to update the file extension of an existing
temporary file proxy (See :ref:`limitations_modified_path` for more details).

.. warning::
    Be careful creating owned a ``ReferenceProxy``. When the Python object is
    deallocated, the referenced file is deleted as well! By default, all
    ``ReferenceProxy`` objects are initialized as unowned. If you set
    ``owned=True``, make sure that only one proxy object refers to the file,
    as ``Proxy`` objects are always assumed to have a one-to-one mapping
    with an underlying file.

.. note::
    You do not need to create reference proxies for input files. ``@proxify``'ed
    functions retain the ability to accept paths.

To use proxies with a function, write a function that accepts paths as its
inputs and outputs and attach the ``@proxify`` decorator::

    @proxify
    def some_function(inputs: str) -> int:
        # Receives file paths here for inputs and outputs
        contents = ... # Read from disk

        return 0

    inputs = ... # Some other proxy or path
    some_function(inputs)

``@proxify`` is designed to work with command line programs executed through
``@foreign_function``. Therefore, the function should always return an integer
status code. Outputs should be written to a separate file passed to the
function::
    @proxify
    def some_function(inputs: str, outputs: str = OutputInfo(file_ext="txt")) -> int:
        # Receives file paths here for inputs and outputs
        contents = ... # Read from disk

        save(modified_contents, outputs) # Write back to the file

        return 0

    outputs = some_function(inputs)
    some_function(inputs, OutputInfo("txt"))


When passing ``OutputInfo`` to a parameter, the wrapper automatically creates
a new temporary file proxy. The proxy objects are returned in the order
parameters passed to the function. A good trick is to pass ``OutputInfo`` as
the default parameter to automatically create a scratchpad file with the
correct file extension.

.. note::
    Using ``OutputInfo`` erases the output value of functions. For example, in
    the following function, the original return value will be dropped::

        @proxify
        def benchmark_filter_and_resize(inputs, output=OutputInfo(vol)) -> float:
            start_time = time.time()
            
            output = xmipp_transform_filter(inputs, fourier="low_pass %f" % fourier_v)
            output = xmipp_image_resize(output, dim=size)

            return time.time() - start_time

    If you need to compute and return values in a function marked with
    ``@proxify``, either write the results to disk or use ``OutputInfo``.


All forward-declared XMIPP programs in ``ffi.scipion`` adopt ``@proxify`` and
in almost all pass the ``OutputInfo`` by default. You can therefore work with
them like with any other Python function::

    output_volume = ... # Path or other proxy
    output = xmipp_transform_filter(output_volume, fourier="low_pass %f" % fourier_v)
    output = xmipp_image_resize(output, dim=size)


Limitations
-----------

.. _limitations_modified_path:
Functions modifying the Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Proxies assume that the wrapped function writes it's data exactly to the path
provided. However, in some cases, this is not the case. For example the XMIPP
program ``xmipp_volume_from_pdb`` appends its own path extension to the output
path.

Thus, when passing a ``Proxy`` that wraps to path ``/path/to/file.vol`` the data
would be written to ``/path/to/file.vol.vol``, which breaks the proxy mechanism.
You can use ``reassign(new_ext: str)`` to add an extension to a file without
one::

    @proxify
    def path_modifying_func(outputs: str):
        pass

    path_modifying_func(
        OutputInfo(None) # Pass a proxy without extension
    ).reassign("vol") # Create a new proxy


In the above snippet, first a proxy referring to a file like ``/path/to/file``
is created. The program writes its data to ``/path/to/file.vol``. The
``reassign`` utility can be used to create a new owned reference proxy for the
file ``/path/to/file.vol``.


No ``__copy__`` Support
~~~~~~~~~~~~~~~~~~~~~~~

Owned proxies delete their managed file as soon as their ``__del__`` function is
called and currently do not implement any form of reference counting or 
copy-on-write mechanism. Therefore if two ``Proxy`` objects hold a reference to
the same file, the file will be deleted when the first proxy is deallocated.
This at the moment is undefined behavior.
