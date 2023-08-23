import subprocess
import numpy as np
import os
import pathlib
import multiprocessing as mp
import sys
import shutil

def test_serial():
    # Get current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    dir = (path / "MP_Serial")
    checkpoint = (path / ".MP_Serial")

    # Remove anything from previous tests
    if (dir).exists():
        shutil.rmtree(dir)
    if (checkpoint).exists():
        os.remove(checkpoint)
    # Run vspace
    subprocess.check_output(["vspace", "vspace.in"], cwd=path)

    # Run multi-planet
    subprocess.check_output(["multiplanet", "vspace.in", "-c", "1"], cwd=path)

    folders = sorted([f.path for f in os.scandir(dir) if f.is_dir()])

    for i in range(len(folders)):
        os.chdir(folders[i])
        assert os.path.isfile('earth.earth.forward') == True
        os.chdir('../')

if __name__ == "__main__":
    test_serial()
