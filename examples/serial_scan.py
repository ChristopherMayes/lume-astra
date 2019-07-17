from astra import *
from astra import writers
from functools import partial
import numpy as np
import h5py, os, sys

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

# Location to save h5file with scan data
mydir = '/Users/nneveu/Code/Github/benchmarking/lcls2/astra/'
h5file_name = mydir+'solscan'+'.h5'
h5file      = h5py.File(h5file_name, 'w')

# Solenoid values to scan through
sol_vals = np.around(np.arange(0.054, 0.0605, 0.0005), 6)
#np.array([0.054,0.06])

settings = {}
for value in sol_vals:
    # Settings for astra simulation
    settings['maxb(2)'] = value
    
    # Return astra object with data
    obj = run_astra_with_generator( astra_input_file=astra_input_file,
                                    generator_input_file=generator_input_file, workdir=workdir,
                                    astra_bin=astra_bin, generator_bin=generator_bin, timeout=2500, verbose=True,
                                    auto_set_spacecharge_mesh=True, settings=settings)
    
    groupname = str(obj.input['solenoid']['maxb(2)']) 
    writers.write_output_h5(h5file, obj.output, name=groupname+'/output')
    writers.write_input_h5(h5file, obj.input, name=groupname+'/input')


h5file.close()







