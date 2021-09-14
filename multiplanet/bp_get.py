#!/usr/bin/env python

import os
import subprocess as sub
import sys


def ReadFile(bplSplitFile,verbose = False):

    includelist = []
    excludelist = []
    bodylist = []
    bpl_file = None

    with open(bplSplitFile, 'r') as input:
        #first thing we check is if both include and exclude are in the file bc that is bad
        if 'saKeyInclude' and 'saKeyExclude' in input.read():
            print("ERROR: saKeyInclude and saKeyExclude are mutually exclusive")
            exit()

    with open(bplSplitFile, 'r') as input:
        #now we loop over the file and get the various inputs
        content = [line.strip().split() for line in input.readlines()]
        for line in content:
            if line:
                #we get the folder where the raw data is stored and have the default output file name set
                if line[0] == 'sDestFolder':
                    folder_name = line[1]
                    outputFile = folder_name.split('/')[-1] + "_filtered.bpl"
                if line[0] == 'sBigplanetFile':
                    bpl_file = line[1]
                if line[0] == 'sOutputName':
                    outputFile = line[1]
                if line[0] == 'sPrimaryFile':
                    primaryFile = line[1]
                if line[0] == 'bUlysses':
                    thing = line[1]
                if line[0] == "saBodyFiles":
                    bodylist = line[1:]
                    for i, value in enumerate(bodylist):
                        bodylist[i] = value.strip("[]")
                if line[0] == 'saKeyInclude':
                    includelist = line[1:]
                    for i, value in enumerate(includelist):
                        includelist[i] = value.strip("[]")
                if line[0] == 'saKeyExclude':
                    excludelist = line[1:]
                    for i, value in enumerate(excludelist):
                        excludelist[i] = value.strip("[]")

        if bpl_file == None and includelist == [] and excludelist == []:
            print("No BPL Archive file or Include/Exclude List detected. This will create the BPL Archive File.")
            print("WARNING: This may take some time...")


        if verbose:
            print("Folder Name:",folder_name)
            if bpl_file != None and includelist != [] and excludelist != []:
                print("BPL Archive File:",bpl_file)
                print("Include List:",includelist)
                print("Exclude List:",excludelist)
                print("Output File:",outputFile)
            print("Body Files:",bodylist)
            print("Primary File:",primaryFile)


        return folder_name,bpl_file,outputFile,bodylist,primaryFile,includelist,excludelist


def GetDir(vspace_file):
    """ Give it input file and returns name of folder where simulations are located. """

    infiles = []
    # gets the folder name with all the sims
    with open(vspace_file, 'r') as vpl:
        content = [line.strip().split() for line in vpl.readlines()]
        for line in content:
            if line:
                if line[0] == 'destfolder':
                    folder_name = line[1]

                if line[0] == 'bodyfile' or line[0] == 'primaryfile':
                    infiles.append(line[1])
    if folder_name is None:
        raise IOError("Name of destination folder not provided in file '%s'."
                      "Use syntax 'destfolder <foldername>'"% vspace_file)


    if os.path.isdir(folder_name) == False:
        print("ERROR: Folder", folder_name, "does not exist in the current directory.")
        exit()

    return folder_name, infiles

def GetSims(folder_name):
    """ Pass it folder name where simulations are and returns list of simulation folders. """
    #gets the list of sims
    sims = sorted([f.path for f in os.scandir(os.path.abspath(folder_name)) if f.is_dir()])
    return sims

def GetSNames(in_files,sims):
    #get system and the body names
    body_names = []

    for file in in_files:
        #gets path to infile
        full_path = os.path.join(sims[0],file)
        #if the infile is the vpl.in, then get the system name
        if "vpl.in" in file:
            with open(full_path, 'r') as vpl:
                content = [line.strip().split() for line in vpl.readlines()]
                for line in content:
                    if line:
                        if line[0] == 'sSystemName':
                            system_name = line[1]
        else:
            with open(full_path, 'r') as infile:
                content = [line.strip().split() for line in infile.readlines()]
                for line in content:
                    if line:
                        if line[0] == 'sName':
                            body_names.append(line[1])

    return system_name,body_names

def GetVplanetHelp():
    command = "vplanet -H | egrep -v '^$|^\+' | cut -f 2,4 -d '|' | egrep '^ \*\*|^ Cust|^ Type|^ Dim|^ Defa|^Output Parameters'"
    py_ver = sys.version.split()[0]
    if '3.6' in py_ver:
        proc = sub.run(command, shell = True, universal_newlines = True, stdout=sub.PIPE,stderr=sub.PIPE)
    else:
        proc = sub.run(command, shell = True, text = True, stdout=sub.PIPE,stderr=sub.PIPE)
    output = proc.stdout.splitlines()

    vplanet_dict = {}

    for count, line in enumerate(output):
        if ((line.startswith(' **b') or line.startswith(' **d') or line.startswith(' **i') or line.startswith(' **s')) or line.startswith(' **sa') and len(line.split()) == 1):

            option = line.strip("** ")
            #print("Option:",option)
            vplanet_dict[option] = {}
            num = count + 1
            while num != count:
                if "Type" in output[num]:
                    tp = output[num].rpartition('|')[-1].strip()
                    vplanet_dict[option]['Type'] = tp
                    #print("Type:",tp)
                    num += 1

                elif "Custom unit" in output[num]:
                    custom_unit = output[num].rpartition('|')[-1].strip()
                    vplanet_dict[option]['Custom Unit'] = custom_unit
                    #print("Custom Unit:",custom_unit)
                    num += 1

                elif "Dimension(s)" in output[num]:
                    dim = output[num].rpartition('|')[-1].strip()
                    vplanet_dict[option]['Dimension'] = dim
                    #print("Dimension:",dim)
                    num += 1

                elif "Default value" in output[num]:
                    default = output[num].rpartition('|')[-1].strip()
                    vplanet_dict[option]['Default Value'] = default
                    #print("Default Value",default)
                    #print()

                    num += 1

                elif "**" in output[num]:
                    num = count

                else:
                    num += 1

        if "Output Parameters" in line:
            break

    return vplanet_dict
