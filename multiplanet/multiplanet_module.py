#!/usr/bin/env python

import csv
import multiprocessing as mp
import os
import subprocess as sub
import sys

import h5py
import numpy as np
from scipy import stats

from multiplanet import parallel_run_planet

"""
Code for Multi-planet Module
"""


def RunMultiplanet(InputFile, cores, quiet=False, bigplanet=False, email=None):
    parallel_run_planet(InputFile, cores, bigplanet, email)
