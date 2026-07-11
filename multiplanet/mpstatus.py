import argparse
import os
import sys


def mpstatus(input_file):

    with open(input_file, "r") as vsf:
        vspace_all = vsf.readlines()
        dest_line = vspace_all[1]
        folder_name = dest_line.strip().split(None, 1)[1]
        if folder_name is None:
            raise IOError(
                "Name of destination folder not provided in file '%s'. Use syntax 'destfolder <foldername>'"
                % inputf
            )

    count_done = 0
    count_todo = 0
    count_ip = 0
    checkpoint_file = os.getcwd() + "/" + "." + folder_name
    if os.path.isfile(checkpoint_file) == False:
        raise Exception("Multi-Planet must be running prior to using mpstatus")
    else:
        with open(checkpoint_file, "r") as cp:
            content = [line.strip().split() for line in cp.readlines()]
            for number, line in enumerate(content):
                status = line[1]

                if status == "1":
                    count_done += 1
                elif status == "-1":
                    count_todo += 1
                elif status == "0":
                    count_ip += 1

        print("--Multi-Planet Status--")
        print("Number of Simulations completed: " + str(count_done))
        print("Number of Simulations in progress: " + str(count_ip))
        print("Number of Simulations remaining: " + str(count_todo))

    return fiWarnIfIncomplete(count_done, count_ip, count_todo)


def fiWarnIfIncomplete(count_done, count_ip, count_todo):
    """Warn and return non-zero if any simulation has not finished."""
    count_incomplete = count_ip + count_todo
    if count_incomplete > 0:
        count_total = count_done + count_incomplete
        print(
            "WARNING: %d of %d simulations have not completed; if the run has "
            "finished this indicates sims were killed (e.g. under core "
            "oversubscription) and results may be biased -- re-run with fewer "
            "cores." % (count_incomplete, count_total)
        )
        return 1
    return 0


def Arguments():
    parser = argparse.ArgumentParser(
        description="Checking the staus a multiplanet run"
    )
    parser.add_argument("InputFile", help="name of the vspace file")
    args = parser.parse_args()

    iExitCode = mpstatus(args.InputFile)
    if iExitCode:
        sys.exit(iExitCode)
