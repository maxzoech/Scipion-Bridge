from functools import partial

import scipion_bridge
import scipion_bridge.typed
import scipion_bridge.typed.volume
from ..external_call import foreign_function, Domain
from ..typed.proxy import proxify, Proxy, Output, ResolveParam
from ..typed.array import ArrayConvertable
from ..typed.resolve import Resolve

# from ..typed.volume import SpiderFile

xmipp_func = partial(foreign_function, domain=Domain("XMIPP", ["scipion", "run"]))


# @proxify
# @partial(
#     xmipp_func,
#     args_map={"inputs": "i", "outputs": "o"},
#     args_validation={
#         "outputs": "(.+)\.vol",
#         # "inputs": "(.+)\.vol",
#         "fourier": "low_pass [0-9]+\.[0-9]+",
#     },
# )
# def xmipp_transform_filter(
#     inputs: str, outputs=OutputInfo("vol"), *, fourier: str
# ) -> int:
#     pass


# @proxify
# @partial(
#     xmipp_func,
#     args_map={"inputs": "i", "outputs": "o"},
#     args_validation={"outputs": "(.+)\.vol", "inputs": "(.+)\.vol"},
# )
# def xmipp_image_resize(
#     inputs: str, outputs=OutputInfo("vol"), *, factor=None, dim=None
# ) -> int:
#     pass


@proxify
@partial(
    xmipp_func,
    args_map={"inputs": "i", "outputs": "o", "center_pdb": "centerPDB"},
)
def xmipp_volume_from_pdb(
    inputs: str,
    outputs: Resolve[Proxy, Output] = Output(Proxy),
    *,
    center_pdb: str,
    sampling: float,
    size: int
):
    pass


# def postprocess_volume_align_args(raw_args):
#     _, out_path = raw_args[0]
#     return raw_args[1:] + [[out_path]]


@proxify
@partial(
    xmipp_func,
    args_map={
        "embdb_map": "i1",
        "volume": "i2",
    },
    # postprocess_fn=postprocess_volume_align_args,
)
def xmipp_volume_align(
    *,
    embdb_map: str,
    volume: str,
    local: bool,
    apply: Resolve[Proxy, Output] = Output(scipion_bridge.typed.volume.SpiderFile)
):
    pass


@proxify
@partial(
    xmipp_func,
    args_map={
        "inputs": "i",
        "outputs": "o",
    },
)
def xmipp_transform_threshold(
    inputs: ResolveParam[scipion_bridge.typed.volume.SpiderFile],
    outputs: ResolveParam[scipion_bridge.typed.volume.SpiderFile] = Output(
        scipion_bridge.typed.volume.SpiderFile
    ),
    *,
    select: str,
    substitute: str
):
    pass


# @proxify
# @partial(
#     xmipp_func,
#     args_map={"inputs": "i", "outputs": "o", "binary_operation": "binaryOperation"},
#     args_validation={
#         "inputs": "(.+)\.vol",
#         "outputs": "(.+)\.vol",
#     },
# )
# def xmipp_transform_morphology(
#     inputs: str, outputs=OutputInfo("vol"), *, binary_operation: str, size: int
# ):
#     pass


# @proxify
# @partial(
#     xmipp_func,
#     args_map={
#         "outputs": "o",
#         "volume": "vol",
#     },
# )
# def xmipp_pdb_label_from_volume(
#     outputs=OutputInfo("vol"),
#     *,
#     pdb: str,
#     volume: str,
#     mask: str,
#     sampling,
#     origin: str,
# ):
#     pass


# @proxify
# @partial(
#     xmipp_func,
#     args_map={
#         "inputs": "i",
#         "outputs": "o",
#     },
#     args_validation={
#         "inputs": "(.+)\.vol",
#         "outputs": "(.+)\.vol",
#     },
# )
# def xmipp_transform_threshold(
#     inputs: str, outputs=OutputInfo("vol"), *, select: str, substitute: str
# ):
#     pass


# @proxify
# @partial(
#     xmipp_func,
#     args_map={
#         "outputs": "o",
#         "volume": "vol",
#     },
#     args_validation={
#         "outputs": "(.+)\.atom.pdb",
#         # "pdb": "(.+)\.pdb",
#         # "volume": "(.+)\.vol",
#     },
# )
# def xmipp_pdb_label_from_volume(
#     outputs=OutputInfo("atom.pdb"),
#     *,
#     pdb: str,
#     volume: str,
#     mask: str,
#     sampling: str,
#     origin: str,
# ):
#     pass


# @proxify
# @partial(xmipp_func, args_map={"inputs": "i", "outputs": "o", "astype": "t"})
# def xmipp_image_convert(inputs: str, outputs=OutputInfo("mrc"), astype: str = "vol"):
#     pass


# @proxify
# @partial(xmipp_func, args_map={"inputs": "i", "sampling": "s"})
# def xmipp_image_header(inputs: str, sampling: float):
#     pass


# @proxify
# @partial(xmipp_func, args_map={"inputs": "i", "outputs": "o"})
# def xmipp_image_operate(inputs: str, outputs=OutputInfo("vol"), *, minus: str):
#     pass
