import numpy as np


class ArrayConvertable:

    def to_numpy(self):
        raise NotImplementedError

    def __array__(self):
        return self.to_numpy()
