#!/usr/bin/env python

import os
import multiprocessing as mp
import sys
import subprocess as sub
import h5py
import numpy as np
import csv
from scipy import stats
from multiplanet import parallel_run_planet

"""
Code for Multi-planet Module
"""


def RunMultiplanet(InputFile,cores, quiet=False, bigplanet=False,email=None):
    parallel_run_planet(InputFile,cores,bigplanet,email)
