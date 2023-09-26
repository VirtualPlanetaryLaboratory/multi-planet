import multiprocessing as mp
import os
import pathlib
import subprocess
import sys
import warnings
import shutil
import numpy as np


def test_bigplanet():
    # Get current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    dir = (path / "MP_Bigplanet")
    checkpoint = (path / ".MP_Bigplanet")

    # Get the number of cores on the machine
    cores = mp.cpu_count()
    if cores == 1:
        warnings.warn("There is only 1 core on the machine", stacklevel=3)
    else:
        # Remove anything from previous tests
        if (dir).exists():
            shutil.rmtree(dir)
        if (checkpoint).exists():
            os.remove(checkpoint)

        # Run vspace
        subprocess.check_output(["vspace", "vspace.in"], cwd=path)

        # Run multi-planet
        subprocess.check_output(["multiplanet", "vspace.in", "-bp"], cwd=path)

        file = path / "MP_Bigplanet.bpa"

        assert os.path.isfile(file) == True


if __name__ == "__main__":
    test_bigplanet()
