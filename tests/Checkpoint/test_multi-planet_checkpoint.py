import subprocess
import numpy as np
import os
import multiprocessing as mp
import warnings
import pathlib
import sys


def test_mp_checkpoint():
    #gets current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    #gets the number of cores on the machine
    cores = mp.cpu_count()
    if cores == 1:
        warnings.warn("There is only 1 core on the machine",stacklevel=3)
    else:
        # Run vspace
        if not (path / "MP_Checkpoint").exists():
            subprocess.check_output(["vspace", "vspace.in"], cwd=path)

        # Run multi-planet
        if not (path / ".MP_Checkpoint").exists():
            subprocess.check_output(["multi-planet", "vspace.in"], cwd=path)
        #gets list of folders
        folders = sorted([f.path for f in os.scandir(path / "MP_Checkpoint") if f.is_dir()])

        for i in range(len(folders)):
            os.chdir(folders[i])
            assert os.path.isfile('earth.earth.forward') == True
            os.chdir('../')

if __name__ == "__main__":
    test_mp_checkpoint()
