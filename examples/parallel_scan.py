#!/usr/bin/env python
# coding: utf-8

# Parallel Parameter Scan
# Using mpi4py

# Run on command line:
# mpirun -n 2 python parallel_scan.py

from astra import *
from astra import writers
from functools import partial
import numpy as np
import h5py, os, sys
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

#obj = run_1d_scan(sol_vals[1])
#groupname = str(obj.input['solenoid']['maxb(2)']) 

#mydir = '/Users/nneveu/Code/Github/benchmarking/lcls2/astra/'
#
#h5file_name = mydir+'solscan'+'.h5'

#h5file      = h5py.File(h5file_name, 'w')
#
#writers.write_output_h5(h5file, obj.output, name=groupname+'/output')
#writers.write_input_h5(h5file, obj.input, name=groupname+'/input')

'''
Provide input array with settings to scan. 
Return requested data by key.

settings     = dictionary of values i.e.: settings['key'] = [0,1,2]
return_data  = data requested from simulation
astra_object = object containing simulation template set up


keys for astra.output:

dict_keys(['run_error', 'why_run_error', 'z_for_coreemit', 'x_normemit', 'x_coreemit_95percent', 'x_coreemit_90percent', 'x_coreemit_80percent', 
'y_normemit', 'y_coreemit_95percent', 'y_coreemit_90percent', 'y_coreemit_80percent', 
'z_normemit', 'z_coreemit_95percent', 'z_coreemit_90percent', 'z_coreemit_80percent', 
'z', 't', 'x_average', 'x_rms', 'xp_rms', 'xxp_average', 'y_average', 'y_rms', 'yp_rms', 'yyp_average', 
'E_kinetic', 'z_rms', 'deltaE_rms', 'zEp_average', 'run_time', 'start_time'])

'''

def run_1d_scan(value, key='maxb(2)'): 
    #Only works for 1 parameter key
    settings = {}
    settings['zstop'] = 0.01
    settings[key] = value
    astra_obj = partial_run(settings=settings)
    return astra_obj

mydir = '/Users/nneveu/Code/Github/benchmarking/lcls2/astra/'
h5file_name = mydir+'solscan'+'.h5'
    
partial_run = partial( run_astra_with_generator, astra_input_file=astra_input_file, 
    generator_input_file=generator_input_file, workdir=workdir,
    astra_bin=astra_bin, generator_bin=generator_bin, timeout=2500, verbose=True,
    auto_set_spacecharge_mesh=True )

# Solenoid values to scan: 
#sol_vals = np.around(np.arange(0.054, 0.0605, 0.0005), 6) # Tesla
sol_vals = np.array([0.025, 0.06])
#print('solenoid values:', sol_vals)


def main():

    with MPIPoolExecutor(max_workers=2) as executor:
        
        # Opening H5 file that will hold output 
        h5file  = h5py.File(h5file_name, 'w')
        
        # Map object 
        outputs = executor.map(run_1d_scan, sol_vals)

        for obj in outputs: 
            #print('x_rms', obj.output['x_rms']) #['x_rms'])
   
            groupname = str(obj.input['solenoid']['maxb(2)']) 
            print(groupname)
            sys.stdout.flush()
            writers.write_output_h5(h5file, obj.output, name=groupname+'/output')
            writers.write_input_h5(h5file, obj.input, name=groupname+'/input')
        
            #writers.write_output_h5(h5file, astra_obj.output, name='output')
            #h5file.close()


USE_MPI = True
if __name__ == '__main__' and USE_MPI:
    main()
