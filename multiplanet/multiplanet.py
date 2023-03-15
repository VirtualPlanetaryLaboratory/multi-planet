import argparse
import multiprocessing as mp
import os
import subprocess as sub
import sys

import h5py
import numpy as np
from bigplanet.bp_get import GetVplanetHelp
from bigplanet.bp_process import DictToBP, GatherData

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


## parallel implementation of running vplanet over a directory ##
def parallel_run_planet(input_file, cores, quiet, verbose, bigplanet, force):
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
    # with h5py.File(master_hdf5_file, "w") as Master:
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
                ),
            )
        )
    for w in workers:
        print("Starting worker")
        w.start()
    
    for w in workers:
        w.join()

    if bigplanet == False:
        if os.path.isfile(master_hdf5_file) == True:
            sub.run(["rm", master_hdf5_file])


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
            if l[1] == "0":
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

    if all(l[1] == "1" for l in datalist[2:-2]) == True:
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


## parallel worker to run vplanet ##
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
):

    while True:

        lock.acquire()
        datalist = []
        if bigplanet == True:
            data = {}
            vplanet_help = GetVplanetHelp()

        with open(checkpoint_file, "r") as f:
            for newline in f:
                datalist.append(newline.strip().split())

        folder = ""

        for l in datalist:
            if l[1] == "-1":
                folder = l[0]
                l[1] = "0"
                break
        if not folder:
            lock.release()
            return

        with open(checkpoint_file, "w") as f:
            for newline in datalist:
                f.writelines(" ".join(newline) + "\n")

        lock.release()

        if verbose:
            print(folder)
        os.chdir(folder)

        # runs vplanet on folder and writes the output to the log file
        with open("vplanet_log", "a+") as vplf:
            vplanet = sub.Popen(
                "vplanet vpl.in",
                shell=True,
                stdout=sub.PIPE,
                stderr=sub.PIPE,
                universal_newlines=True,
            )
            return_code = vplanet.poll()
            for line in vplanet.stderr:
                vplf.write(line)

            for line in vplanet.stdout:
                vplf.write(line)

        lock.acquire()
        datalist = []

        with open(checkpoint_file, "r") as f:
            for newline in f:
                datalist.append(newline.strip().split())

        if return_code is None:
            for l in datalist:
                if l[0] == folder:
                    l[1] = "1"
                    break
            if verbose:
                print(folder, "completed")
            if bigplanet == True:
                with h5py.File(h5_file, "a") as Master:
                    group_name = folder.split("/")[-1]
                    if group_name not in Master:
                        data = GatherData(
                            data,
                            system_name,
                            body_list,
                            log_file,
                            in_files,
                            vplanet_help,
                            folder,
                            verbose,
                        )
                        DictToBP(
                            data,
                            vplanet_help,
                            Master,
                            verbose,
                            group_name,
                            archive=True,
                        )
        else:
            for l in datalist:
                if l[0] == folder:
                    l[1] = "-1"
                    break
            if verbose:
                print(folder, "failed")

        with open(checkpoint_file, "w") as f:
            for newline in datalist:
                f.writelines(" ".join(newline) + "\n")

        lock.release()

        os.chdir("../../")


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
