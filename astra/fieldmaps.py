"""
Tools for loading fieldmap data
"""
import numpy as np
import re


# Prefix helpers

POS_PREFIX = {'cavity':'c_pos', 'solenoid':'s_pos'}
def pos_(section='cavity', index=1):
    prefix = POS_PREFIX[section]
    
    return f'{prefix}({index})'

FILE_PREFIX = {'cavity':'file_efield', 'solenoid':'file_bfield'}

def file_(section='cavity', index=1):
    prefix = FILE_PREFIX[section]
    
    return f'{prefix}({index})'

MAX_PREFIX = {'cavity':'maxe', 'solenoid':'maxb'}
def max_(section='cavity', index=1):
    prefix =MAX_PREFIX[section]
    
    return f'{prefix}({index})'


def find_fieldmap_ixlist(astra_input, section='cavity'):
    """
    
    Looks for the appropriage file_efield(i) and extracts the integer i
    """
    
    dat = astra_input[section]
    prefix = FILE_PREFIX[section]
    ixlist = []
    for k in astra_input[section]:
        if k.startswith(prefix):
            m = re.search(r"\(([0-9]+)\)", k)
            ix = int(m.group(1))
            ixlist.append(ix)
    return ixlist

def load_fieldmaps(astra_input, sections=['cavity', 'solenoid'], verbose=False):
    """
    Loads all found fieldmaps into a dict with the filenames as keys
    """
    fmap = {}
    for sec in sections:
        ixlist = find_fieldmap_ixlist(astra_input, sec) 
        for ix in ixlist:
            k = file_(section=sec, index=ix)
            file = astra_input[sec][k]
            if file not in fmap:
                if verbose:
                    print(f'Loading fieldmap file {file}')
                fmap[file] = np.loadtxt(file)
    return fmap


def fieldmap_data(astra_input, section='cavity', index=1, fieldmaps={}, verbose=False):
    """
    Loads the fieldmap in absolute coordinates.
    
    If a fieldmaps dict is given, thes will be used instead of loading the file.
    
    """
    
    adat = astra_input[section] # convenience pointer
    
    # Position
    k = pos_(section, index)
    if k in adat:
        offset = adat[k]
    else:
        offset = 0
        
    file = adat[file_(section, index)]
    
    # Scaling
    k = max_(section, index)
    if k in adat:
        scale = adat[k]
    else:
        scale = 1
    
    
    if file in fieldmaps:
        dat = fieldmaps[file].copy()
    else:
        print(f'loading from file {file}')
        dat = np.loadtxt(file)
    dat[:,0] += offset
    dat[:,1] *= scale/max(abs(dat[:,1]))
    
    return dat