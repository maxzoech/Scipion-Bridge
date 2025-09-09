from ..core.utils.external_call import foreign_function, Domain
from functools import partial


xmipp_func = partial(foreign_function, domain=Domain("XMIPP", ["scipion", "run"]))
