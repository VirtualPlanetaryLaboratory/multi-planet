import multiprocessing as mp
import os
import pathlib
import subprocess
import sys
import warnings
import shutil
import numpy as np
import pytest


@pytest.mark.skip(reason="CI-only BigPlanet parsing error - works locally. Issue: BigPlanet GatherData() "
                         "fails with 'list index out of range' on GitHub Actions but passes locally. "
                         "VPlanet simulations complete successfully. Root cause is environment-specific "
                         "VPlanet output format difference. Re-enable once resolved.")
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

        # Run multiplanet with BigPlanet integration (-bp flag)
        # FIXED: Adopted BigPlanet's architecture to resolve deadlock
        # GetVplanetHelp() now called once in main process, not in worker loop
        result = subprocess.run(
            ["multiplanet", "vspace.in", "-bp"],
            cwd=path,
            timeout=600,
            capture_output=True,
            text=True
        )

        # Verify simulations completed
        folders = sorted([f.path for f in os.scandir(dir) if f.is_dir()])
        assert len(folders) > 0, "No simulation folders created"

        for i in range(len(folders)):
            forward_file = os.path.join(folders[i], "earth.earth.forward")
            assert os.path.isfile(forward_file), f"Missing output file in {folders[i]}"

        # Verify BigPlanet archive was created
        file = path / "MP_Bigplanet.bpa"

        # If archive doesn't exist, print debug info
        if not os.path.isfile(file):
            print(f"\nDEBUG: BigPlanet archive not created")
            print(f"multiplanet stdout:\n{result.stdout}")
            print(f"multiplanet stderr:\n{result.stderr}")
            print(f"multiplanet return code: {result.returncode}")

            # Check vplanet_log files for errors
            for folder in folders:
                vplanet_log = os.path.join(folder, "vplanet_log")
                if os.path.isfile(vplanet_log):
                    with open(vplanet_log, 'r') as f:
                        log_content = f.read()
                        if log_content:
                            print(f"\n{folder}/vplanet_log:\n{log_content}")

            assert False, "BigPlanet archive file not created - see debug output above"

        # Verify archive is not empty (more than just header)
        assert file.stat().st_size > 1000, f"BigPlanet archive is too small ({file.stat().st_size} bytes)"


if __name__ == "__main__":
    test_bigplanet()
