Exposing XMIPP Programs
=======================

The ``@foreign_function`` decorator can be used to expose XMIPP programs as
Python functions. XMIPP programs are called using the ``scipion run`` command
in the terminal, for example ``scipion run xmipp_xmipp_volume_from_pdb -i ... -o ...``.
The ``@foreign_function`` decorator constructs the scaffolding to validate
program inputs and execute the command.

When exposing an XMIPP program you can rename input arguments and add input
validation to make the function more pythonic. The default function executor
runs the program in a subprocess, so you can handle failed programs as Python
errors.

Mapping XMIPP to Python
-----------------------

To map a program to Python define a function that with the same name as the
XMIPP program you want to expose and mark it as ``@foreign_function``::

    @foreign_function
    def xmipp_transform_threshold(i: str, o: str, *, select: str, substitute: str):
        pass

This function must not have an implementation (during construction the function
gets called once as part of input validation). The idea is to "forward declare"
XMIPP programs that can then be executed.

The positional parameters of the function will be mapped to positional arguments
like ``-i``, while the keyword parameters to arguments like ``--select``. You 
can add the ``*`` operator to mark the end of the positional arguments; the
remaining arguments can then only passed as keyword arguments.

When you call this function the following command will be executed::

    scipion run xmipp_transform_threshold -i ... -o ... --select ... --substitute ...


When passing a boolean value, annotate your function definition with the ``bool``
type. The name of the parameter will be added if the boolean is ``True``. For
example a function defined as
::

    def xmipp_volume_align(o: str, *, i1: str, i2: str, local: bool, apply: bool):
        pass

will be mapped to the following shell command::

    // Call xmipp_volume_align(/output, i1=/emdb_map, i2=/volume, local=True, apply=False)
    scipion run xmipp_volume_align -o ... --i1 ... i2 ... --local ...


.. note::
    Should the underlying program not conform to the pattern the decorator expects,
    ``postprocess_fn`` provides an escape hatch to manually postprocess the
    arguments::

        def remove_output_label(args):
            return [[args[0][1]]] + args[1:]

        @partial(foreign_function, postprocess_fn=remove_output_label)
        def some_function(outputs, *, value: int):
            pass

            # Is executed as scipion run some_function /path/to/output --value 42

    In the above example, ``remove_output_label`` is passed a list of pairs of
    argument names and values. It is called with all transformations applied.
    The function removes the label ``-outputs`` from the first argument.


Remapping Parameter Names
--------------------------

Mapped XMIPP functions provide a direct interface for XMIPP programs. However,
sometimes the signature the original program be a bit cumbersome in Python. You
can provide a dictionary mapping Python names to XMIPP arguments names. For
example the call ``xmipp_volume_align`` takes two arguments ``i1`` and ``i2``
which can be remapped to ``embdb_map`` and ``volume`` respectively::

    @partial(
        foreign_function,
        args_map={
            "embdb_map": "i1",
            "volume": "i2",
        },
        postprocess_fn=remove_output_label
    )
    def xmipp_volume_align(outputs: str, *, embdb_map: str, volume: str, local: bool, apply: bool):
        pass

This will call the following command in the shell::

    scipion run xmipp_volume_align ... --i1 ... i2 ... --local ...


Input Validation
-----------------

Input to XMIPP programs is inherently untyped; the input is only validated
during execution. The ``foreign_function`` provides an optional parameter
``args_validation`` to validate input data using a regex pattern. This can be
used to for example validate file extensions or enum options. For example,
programs that expect Spider files are validated to only be executed with files
with the ``.vol`` file extension::

    @partial(
        foreign_function,
        args_map={"inputs": "i", "outputs": "o"},
        args_validation={
            "outputs": "(.+)\.vol",
            "inputs": "(.+)\.vol"
        }
    )
    def xmipp_image_resize(inputs: str, outputs: str, *, factor=None, dim=None) -> int:
        pass

If you pass a file with the wrong extension, the function will throw a ``ValueError``.
