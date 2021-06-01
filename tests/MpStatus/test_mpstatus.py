import subprocess
import numpy as np
import os
import sys
import multiprocessing as mp
import warnings
import pathlib

def test_mpstatus():
    #gets current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    #gets the number of cores on the machine
    cores = mp.cpu_count()
    if cores == 1:
        warnings.warn("There is only 1 core on the machine",stacklevel=3)
    else:
        # Run vspace
        if not (path / "MP_Status").exists():
            subprocess.check_output(["vspace", "vspace.in"], cwd=path)

        # Run multi-planet
        if not (path / ".MP_Status").exists():
            subprocess.check_output(["multi-planet", "vspace.in"], cwd=path)
            subprocess.check_output(["mpstatus", "vspace.in"], cwd=path)

        #gets list of folders
        folders = sorted([f.path for f in os.scandir(path / "MP_Status") if f.is_dir()])

        for i in range(len(folders)):
            os.chdir(folders[i])
            assert os.path.isfile('earth.earth.forward') == True
            os.chdir('../')

if __name__ == "__main__":
    test_mpstatus()
