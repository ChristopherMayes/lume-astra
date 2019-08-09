from astra import *
from astra import writers
from functools import partial
import numpy as np
import h5py, os, sys


# Path where you have saved lume-astra:
lume_path = os.path.expandvars('$HOME/Code/Github/lume-astra/')

# Path where you have ASTRA executables saved
astra_exec = os.path.expandvars('$HOME/Code/astra/')

# Path to ASTRA executable file
astra_bin = astra_exec + 'Astra'
# Path to ASTRA executable file
generator_bin = astra_exec + 'generator'

# Input template file 
astra_input_file = lume_path + 'templates/srfgun/srfgun_astra.in'
# Input generator template file 
generator_input_file = lume_path + 'templates/srfgun/srfgun_generator.in'

# Checking that all files / folders exist
os.path.exists(astra_bin), os.path.exists(astra_input_file)

# Name of file to save scan data to
# Data file will be saved in working dir 
# i.e. same location as this script
h5file      = h5py.File('solscan.h5', 'w')

# Solenoid values to scan through
sol_vals = np.around(np.arange(0.1, 0.3, 0.1), 6)


settings = {}
settings['zstop']=0.5

for value in sol_vals:
    # Setting that will be scanned in astra simulation
    settings['maxb(1)'] = value
    
    # Return astra object with data
    obj = run_astra_with_generator( astra_input_file=astra_input_file,
                                    generator_input_file=generator_input_file, 
                                    astra_bin=astra_bin, generator_bin=generator_bin, timeout=2500, verbose=True,
                                    auto_set_spacecharge_mesh=True, settings=settings)
    
    groupname = str(obj.input['solenoid']['maxb(1)']) 
    writers.write_output_h5(h5file, obj.output, name=groupname+'/output')
    writers.write_input_h5(h5file, obj.input, name=groupname+'/input')


h5file.close()







