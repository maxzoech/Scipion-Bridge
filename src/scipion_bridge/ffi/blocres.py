import os
from pathlib import Path
from functools import partial

from external_call import foreign_function, Domain
from proxy import proxify, OutputInfo


def find_blocres():
    try:
        software_root = Path(os.environ["SCIPION_SOFTWARE"])
    except KeyError:
        raise RuntimeError(
            "Could not find variable 'SCIPION_SOFTWARE' in environment! Please make sure to run your script as scipion python -m path.to.module"
        )

    blocres = software_root / "em" / "bsoft" / "bin" / "blocres"

    if not blocres.is_file():
        raise RuntimeError(
            "Blocres could not be found! Please make sure your install is correct"
        )

    return blocres


blocres_func = partial(
    foreign_function, domain=Domain("BlocRes", [str(find_blocres())])
)


def _postprocess_blocres(args):
    def _update_kwarg(arg):
        arg[0] = arg[0][1:]
        return arg

    # Remove arg names from the positional arguments (first 3)
    pos_args = [[v] for (_, v) in args[:3]]

    # Change the prefix for the keyword args (from '--' to '-')
    keyword_args = [_update_kwarg(arg) for arg in args[3:]]

    return keyword_args + pos_args


@proxify
@partial(
    blocres_func,
    func_name="",
    args_map={"no_fill": "nofill", "max_resolution": "maxresolution", "mask": "Mask"},
    args_validation={
        # "map_1": "(.+)\.map",
        # "map_2": "(.+)\.map",
        "sampling": "[0-9]+\.[0-9]+,[0-9]+\.[0-9]+,[0-9]+\.[0-9]+",
    },
    postprocess_fn=_postprocess_blocres,
)
def blocres(
    map_1: str,
    map_2: str,
    output=OutputInfo("map"),
    *,
    mask: str = None,
    sampling: str = None,
    box: float = None,
    cutoff: str = None,
    no_fill: bool = True,
    smooth: bool = True,
    pad: int = 1,
    step: int = 5,
    max_resolution: float = 0.5,
    verbose=0,
):
    pass
