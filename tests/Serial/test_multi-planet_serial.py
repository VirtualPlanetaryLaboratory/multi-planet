import subprocess
import numpy as np
import os
import pathlib
import multiprocessing as mp
import sys

def test_mp_serial():
    #gets current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    if not (path / "MP_Serial").exists():
        subprocess.check_output(["vspace", "vspace.in"], cwd=path)

    # Run multi-planet
    if not (path / ".MP_Serial").exists():
        subprocess.check_output(["multi-planet", "vspace.in", "-c", "1"], cwd=path)

    folders = sorted([f.path for f in os.scandir(path / "MP_Serial") if f.is_dir()])

    for i in range(len(folders)):
        os.chdir(folders[i])
        assert os.path.isfile('earth.earth.forward') == True
        os.chdir('../')

if __name__ == "__main__":
    test_mp_serial()
