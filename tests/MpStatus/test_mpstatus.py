import multiprocessing as mp
import os
import pathlib
import subprocess
import sys
import warnings
import pathlib
import shutil

def test_mpstatus():
    # Get current path
    path = pathlib.Path(__file__).parents[0].absolute()
    sys.path.insert(1, str(path.parents[0]))

    dir = (path / "MP_Status")
    checkpoint = (path / ".MP_Status")

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

        # Run multi-planet and mpstatus
        subprocess.check_output(["multiplanet", "vspace.in"], cwd=path)
        subprocess.check_output(["mpstatus", "vspace.in"], cwd=path)

        # Get list of folders
        folders = sorted([f.path for f in os.scandir(dir) if f.is_dir()])

        for i in range(len(folders)):
            os.chdir(folders[i])
            assert os.path.isfile("earth.earth.forward") == True
            os.chdir("../")


if __name__ == "__main__":
    test_mpstatus()
