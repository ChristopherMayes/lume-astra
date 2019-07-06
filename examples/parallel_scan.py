#!/usr/bin/env python
# coding: utf-8

# Parallel Parameter Scan
# Using mpi4py

# Run on command line:
# mpirun -n 2 python parallel_scan.py

from astra import *
from functools import partial
import numpy as np
import os
#from concurrent.futures import ThreadPoolExecutor as PoolExecutor
#If on HPC cluster, use this(??):
from mpi4py.futures import MPIPoolExecutor
from mpi4py import MPI

# Path to ASTRA executable file
astra_bin = os.path.expandvars('$HOME/Code/astra/Astra')
# Path to ASTRA executable file
generator_bin = os.path.expandvars('$HOME/Code/astra/generator')
# Directory where simulations will run
workdir = os.path.expandvars('$HOME/Code/Github/benchmarking/lcls2/astra/')
# Input template file 
astra_input_file = os.path.expandvars('$HOME/Code/Github/benchmarking/lcls2/astra/gunb/gunb.in')
# Input generator template file 
generator_input_file = os.path.expandvars('$HOME/Code/Github/benchmarking/lcls2/astra/gunb/generator.in')
# Making clean working directory
tools.mkdir_p(workdir)
# Checking that all files / folders exist
os.path.exists(astra_bin), os.path.exists(astra_input_file), os.path.exists(workdir)


# Initialize simulation templates
#A = Astra(astra_bin=astra_bin, input_file=astra_input_file, workdir=workdir)
#A.timeout= 300
#A.verbose = True
#G = AstraGenerator(generator_bin=generator_bin, input_file=generator_input_file, sim_path=A.sim_path)
#G.verbose = True
# Solenoid values to scan: 
#sol_vals = np.arange(0.0548, 0.059, 0.00042) # Tesla
sol_vals = np.array([0.0548, 0.059])
#print('solenoid values:', sol_vals)

'''
Provide input array with settings to scan. 
Return requested data by key.

settings     = dictionary of values i.e.: settings['key'] = [0,1,2]
return_data  = data requested from simulation
astra_object = object containing simulation template set up
'''

settings = {}
settings['maxb(2)'] = 0


partial_run = partial( run_astra_with_generator, astra_input_file=astra_input_file, 
        generator_input_file=generator_input_file, workdir=workdir,
        astra_bin=astra_bin, generator_bin=generator_bin, timeout=2500, verbose=False,
        auto_set_spacecharge_mesh=True)


def run_1d_scan(value):
    #Only works if there's only 1 parameter key
    for key in settings:
        settings[key] = value
    return partial_run(settings=settings)
    

with MPIPoolExecutor(max_workers=2) as executor:
    for result in executor.map(run_1d_scan, sol_vals):
        print(result) 



