import argparse
import multiprocessing as mp
import os
import subprocess as sub
import sys

import h5py
import numpy as np
from bigplanet.read import GetVplanetHelp
from bigplanet.process import DictToBP, GatherData

# --------------------------------------------------------------------
# HELPER FUNCTIONS (extracted from BigPlanet architecture)
# --------------------------------------------------------------------


def fnGetNextSimulation(sCheckpointFile, lockFile):
    """
    Find and mark the next simulation to process from checkpoint file.

    Thread-safe with file locking. Reads checkpoint, finds first simulation
    with status -1, marks it as 0 (in-progress), and returns the folder path.

    Parameters
    ----------
    sCheckpointFile : str
        Path to checkpoint file
    lockFile : multiprocessing.Lock
        Lock for thread-safe file access

    Returns
    -------
    str or None
        Absolute path to simulation folder, or None if all done
    """
    lockFile.acquire()
    listData = []

    with open(sCheckpointFile, "r") as f:
        for sLine in f:
            listData.append(sLine.strip().split())

    sFolder = ""
    for listLine in listData:
        if len(listLine) > 1 and listLine[1] == "-1":
            sFolder = listLine[0]
            listLine[1] = "0"
            break

    if not sFolder:
        lockFile.release()
        return None

    with open(sCheckpointFile, "w") as f:
        for listLine in listData:
            f.writelines(" ".join(listLine) + "\n")

    lockFile.release()
    return os.path.abspath(sFolder)


def fnMarkSimulationComplete(sCheckpointFile, sFolder, lockFile):
    """
    Mark simulation as complete in checkpoint file.

    Thread-safe with file locking. Updates status from 0 or -1 to 1.

    Parameters
    ----------
    sCheckpointFile : str
        Path to checkpoint file
    sFolder : str
        Folder path to mark as complete
    lockFile : multiprocessing.Lock
        Lock for thread-safe file access

    Returns
    -------
    None
    """
    lockFile.acquire()
    listData = []

    with open(sCheckpointFile, "r") as f:
        for sLine in f:
            listData.append(sLine.strip().split())

    for listLine in listData:
        if len(listLine) > 1 and listLine[0] == sFolder:
            listLine[1] = "1"
            break

    with open(sCheckpointFile, "w") as f:
        for listLine in listData:
            f.writelines(" ".join(listLine) + "\n")

    lockFile.release()


def fnMarkSimulationFailed(sCheckpointFile, sFolder, lockFile):
    """
    Mark simulation as failed in checkpoint file.

    Thread-safe with file locking. Updates status back to -1 for retry.

    Parameters
    ----------
    sCheckpointFile : str
        Path to checkpoint file
    sFolder : str
        Folder path to mark as failed
    lockFile : multiprocessing.Lock
        Lock for thread-safe file access

    Returns
    -------
    None
    """
    lockFile.acquire()
    listData = []

    with open(sCheckpointFile, "r") as f:
        for sLine in f:
            listData.append(sLine.strip().split())

    for listLine in listData:
        if len(listLine) > 1 and listLine[0] == sFolder:
            listLine[1] = "-1"
            break

    with open(sCheckpointFile, "w") as f:
        for listLine in listData:
            f.writelines(" ".join(listLine) + "\n")

    lockFile.release()


# --------------------------------------------------------------------
# ORIGINAL FUNCTIONS (unchanged)
# --------------------------------------------------------------------


def GetSNames(in_files, sims):
    # get system and the body names
    body_names = []

    for file in in_files:
        # gets path to infile
        full_path = os.path.join(sims[0], file)
        # if the infile is the vpl.in, then get the system name
        if "vpl.in" in file:
            with open(full_path, "r") as vpl:
                content = [line.strip().split() for line in vpl.readlines()]
                for line in content:
                    if line:
                        if line[0] == "sSystemName":
                            system_name = line[1]
        else:
            with open(full_path, "r") as infile:
                content = [line.strip().split() for line in infile.readlines()]
                for line in content:
                    if line:
                        if line[0] == "sName":
                            body_names.append(line[1])

    return system_name, body_names


def GetSims(folder_name):
    """Pass it folder name where simulations are and returns list of simulation folders."""
    # gets the list of sims
    sims = sorted(
        [
            f.path
            for f in os.scandir(os.path.abspath(folder_name))
            if f.is_dir()
        ]
    )
    return sims


def GetDir(vspace_file):
    """Give it input file and returns name of folder where simulations are located."""

    infiles = []
    folder_name = None
    # gets the folder name with all the sims
    with open(vspace_file, "r") as vpl:
        content = [line.strip().split() for line in vpl.readlines()]
        for line in content:
            if line:
                if line[0] == "sDestFolder" or line[0] == "destfolder":
                    folder_name = line[1]

                if (
                    line[0] == "sBodyFile"
                    or line[0] == "sPrimaryFile"
                    or line[0] == "file"
                ):
                    infiles.append(line[1])
    if folder_name is None:
        raise IOError(
            "Name of destination folder not provided in file '%s'."
            "Use syntax 'destfolder <foldername>'" % vspace_file
        )

    if os.path.isdir(folder_name) == False:
        print(
            "ERROR: Folder",
            folder_name,
            "does not exist in the current directory.",
        )
        exit()

    return folder_name, infiles


def CreateCP(checkpoint_file, input_file, sims):
    with open(checkpoint_file, "w") as cp:
        cp.write("Vspace File: " + os.getcwd() + "/" + input_file + "\n")
        cp.write("Total Number of Simulations: " + str(len(sims)) + "\n")
        for f in range(len(sims)):
            cp.write(sims[f] + " " + "-1 \n")
        cp.write("THE END \n")


def ReCreateCP(checkpoint_file, input_file, verbose, sims, folder_name, force):
    if verbose:
        print("WARNING: multi-planet checkpoint file already exists!")

    datalist = []
    with open(checkpoint_file, "r") as re:
        for newline in re:
            datalist.append(newline.strip().split())

        for l in datalist:
            if len(l) > 1 and l[1] == "0":
                l[1] = "-1"
        if datalist[-1] != ["THE", "END"]:
            lest = datalist[-2][0]
            idx = sims.index(lest)
            for f in range(idx + 2, len(sims)):
                datalist.append([sims[f], "-1"])
            datalist.append(["THE", "END"])

    with open(checkpoint_file, "w") as wr:
        for newline in datalist:
            wr.writelines(" ".join(newline) + "\n")

    if all(len(l) > 1 and l[1] == "1" for l in datalist[2:-2]) == True:
        print("All simulations have been ran")

        if force:
            if verbose:
                print("Deleting folder...")
            os.remove(folder_name)
            if verbose:
                print("Deleting Checkpoint File...")
            os.remove(checkpoint_file)
            if verbose:
                print("Recreating Checkpoint File...")
            CreateCP(checkpoint_file, input_file, sims)
        else:
            exit()


# --------------------------------------------------------------------
# REFACTORED WORKER (adopting BigPlanet architecture)
# --------------------------------------------------------------------


def par_worker(
    checkpoint_file,
    system_name,
    body_list,
    log_file,
    in_files,
    verbose,
    lock,
    bigplanet,
    h5_file,
    vplanet_help,
):
    """
    Worker process for running vplanet simulations.

    REFACTORED to adopt BigPlanet's architecture:
    - Uses fnGetNextSimulation() for thread-safe checkpoint access
    - GetVplanetHelp() passed as parameter (called once in main)
    - Minimal critical sections (lock held only during file I/O)
    - Proper subprocess return code handling (wait() not poll())
    - No os.chdir() calls (uses cwd parameter instead)

    Parameters
    ----------
    checkpoint_file : str
        Path to checkpoint file
    system_name : str
        Name of system
    body_list : list
        List of body names
    log_file : str
        Name of log file
    in_files : list
        List of input files
    verbose : bool
        Verbose output flag
    lock : multiprocessing.Lock
        Lock for thread-safe operations
    bigplanet : bool
        Create BigPlanet archive
    h5_file : str
        Path to HDF5 archive file
    vplanet_help : dict or None
        Vplanet help data (pre-fetched in main process)

    Returns
    -------
    None
    """
    while True:
        # STEP 1: Get next simulation (with lock - minimal critical section)
        sFolder = fnGetNextSimulation(checkpoint_file, lock)
        if sFolder is None:
            return  # No more work

        if verbose:
            print(f"Processing: {sFolder}")

        # STEP 2: Run vplanet simulation (NO LOCK - independent work)
        vplanet_log_path = os.path.join(sFolder, "vplanet_log")

        with open(vplanet_log_path, "a+") as vplf:
            vplanet = sub.Popen(
                ["vplanet", "vpl.in"],
                cwd=sFolder,
                stdout=sub.PIPE,
                stderr=sub.PIPE,
                universal_newlines=True,
            )
            # FIXED: Use communicate() to wait for completion and get output
            stdout, stderr = vplanet.communicate()

            # Write output to log
            vplf.write(stderr)
            vplf.write(stdout)

        # FIXED: Check actual return code (not poll())
        return_code = vplanet.returncode

        # STEP 3: Process BigPlanet data if needed (NO LOCK - CPU-bound work)
        if return_code == 0 and bigplanet and vplanet_help is not None:
            try:
                # Gather simulation data
                data = {}
                data = GatherData(
                    data,
                    system_name,
                    body_list,
                    log_file,
                    in_files,
                    vplanet_help,
                    sFolder,
                    verbose,
                )

                # STEP 4: Write to HDF5 (WITH LOCK - minimal critical section)
                lock.acquire()
                try:
                    with h5py.File(h5_file, "a") as Master:
                        group_name = os.path.basename(sFolder)
                        if group_name not in Master:
                            DictToBP(
                                data,
                                vplanet_help,
                                Master,
                                verbose,
                                group_name,
                                archive=True,
                            )
                finally:
                    lock.release()
            except Exception as e:
                # Log BigPlanet errors but don't fail the simulation
                if verbose:
                    print(f"Warning: BigPlanet archive failed for {sFolder}: {e}")
                # Write error to vplanet_log for debugging
                with open(os.path.join(sFolder, "vplanet_log"), "a") as f:
                    f.write(f"\nBigPlanet Error: {e}\n")

        # STEP 5: Update checkpoint (with lock)
        if return_code == 0:
            fnMarkSimulationComplete(checkpoint_file, sFolder, lock)
            if verbose:
                print(f"{sFolder} completed")
        else:
            fnMarkSimulationFailed(checkpoint_file, sFolder, lock)
            if verbose:
                print(f"{sFolder} failed with return code {return_code}")


# --------------------------------------------------------------------
# REFACTORED MAIN FUNCTION
# --------------------------------------------------------------------


def parallel_run_planet(input_file, cores, quiet, verbose, bigplanet, force):
    """
    Run vplanet simulations in parallel.

    REFACTORED to fix BigPlanet deadlock:
    - GetVplanetHelp() called ONCE in main process (not in workers)
    - Passed to workers as immutable parameter
    - No subprocess calls within multiprocessing context

    Parameters
    ----------
    input_file : str
        Vspace input file
    cores : int
        Number of CPU cores to use
    quiet : bool
        Suppress output
    verbose : bool
        Verbose output
    bigplanet : bool
        Create BigPlanet HDF5 archive
    force : bool
        Force rerun if already completed

    Returns
    -------
    None
    """
    # gets the folder name with all the sims
    folder_name, in_files = GetDir(input_file)
    # gets the list of sims
    sims = GetSims(folder_name)
    # Get the SNames (sName and sSystemName) for the simuations
    # Save the name of the log file
    system_name, body_list = GetSNames(in_files, sims)
    logfile = system_name + ".log"
    # initalizes the checkpoint file
    checkpoint_file = os.getcwd() + "/" + "." + folder_name
    # checks if the files doesn't exist and if so then it creates it
    if os.path.isfile(checkpoint_file) == False:
        CreateCP(checkpoint_file, input_file, sims)

    # if it does exist, it checks for any 0's (sims that didn't complete) and
    # changes them to -1 to be re-ran
    else:
        ReCreateCP(
            checkpoint_file, input_file, verbose, sims, folder_name, force
        )

    lock = mp.Lock()
    workers = []

    master_hdf5_file = os.getcwd() + "/" + folder_name + ".bpa"

    # CRITICAL FIX: Call GetVplanetHelp() ONCE in main process
    # This is passed to workers instead of being called inside worker loop
    if bigplanet:
        vplanet_help = GetVplanetHelp()
    else:
        vplanet_help = None

    # Spawn worker processes
    for i in range(cores):
        workers.append(
            mp.Process(
                target=par_worker,
                args=(
                    checkpoint_file,
                    system_name,
                    body_list,
                    logfile,
                    in_files,
                    verbose,
                    lock,
                    bigplanet,
                    master_hdf5_file,
                    vplanet_help,  # PASSED as parameter
                ),
            )
        )

    # Start all workers
    for w in workers:
        if verbose:
            print("Starting worker")
        w.start()

    # Wait for all workers to complete
    for w in workers:
        w.join()

    # Clean up HDF5 file if not using bigplanet
    if bigplanet == False:
        if os.path.isfile(master_hdf5_file) == True:
            sub.run(["rm", master_hdf5_file])


def Arguments():
    max_cores = mp.cpu_count()
    parser = argparse.ArgumentParser(
        description="Using multi-processing to run a large number of simulations"
    )
    parser.add_argument(
        "-c",
        "--cores",
        type=int,
        default=max_cores,
        help="The total number of processors used",
    )
    parser.add_argument(
        "-bp",
        "--bigplanet",
        action="store_true",
        help="Runs bigplanet and creates the Bigplanet Archive file alongside running multiplanet",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="forces rerun of multi-planet if completed",
    )

    parser.add_argument("InputFile", help="name of the vspace file")

    # adds the quiet and verbose as mutually exclusive groups
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q", "--quiet", action="store_true", help="no output for multiplanet"
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Prints out excess output for multiplanet",
    )

    args = parser.parse_args()

    try:
        if sys.version_info >= (3, 0):
            help = sub.getoutput("vplanet -h")
        else:
            help = sub.check_output(["vplanet", "-h"])
    except OSError:
        raise Exception("Unable to call VPLANET. Is it in your PATH?")

    parallel_run_planet(
        args.InputFile,
        args.cores,
        args.quiet,
        args.verbose,
        args.bigplanet,
        args.force,
    )


if __name__ == "__main__":
    Arguments()
