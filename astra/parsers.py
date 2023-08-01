"""
Astra output parsing
 
References:

PHYSICAL REVIEW SPECIAL TOPICS - ACCELERATORS AND BEAMS,VOLUME 6, 034202 (2003)
https://journals.aps.org/prab/pdf/10.1103/PhysRevSTAB.6.034202

"""

from pmd_beamphysics.units import unit

import os

from math import isnan
import numpy as np
import re

# ------------


def unit_dict(keys, unit_symbols):
    """
    Forms a dict mapping keys to pmd_unit objects
    """
    d = {}
    for k, s in zip(keys, unit_symbols):
        d[k] = unit(s)
    return d


# New style
OutputColumnNames = {}
OutputColumnFactors = {}
OutputUnits = {}  # This collects all units

CemitColumnNames   = ['mean_z',  'norm_emit_x', 'core_emit_95percent_x', 'core_emit_90percent_x', 'core_emit_80percent_x',
                            'norm_emit_y', 'core_emit_95percent_y', 'core_emit_90percent_y', 'core_emit_80percent_y',
                            'norm_emit_z', 'core_emit_95percent_z', 'core_emit_905percent_z', 'core_emit_80percent_z']
CemitOriginalUnits   = ['m'] + 8*['mm-mrad'] + 4*['kev-mm'] # Units that Astra writes
CemitColumnFactors = [1] + 12*[1e-6]  # Factors to make standard units
CemitColumnUnits   = ['m'] + 8*['m'] + 4*['eV*m']
CemitColumn = dict( zip(CemitColumnNames, list(range(1, 1+len(CemitColumnNames) ) ) ) )
OutputUnits.update(unit_dict(CemitColumnNames, CemitColumnUnits))

XemitColumnNames   = ['mean_z', 'mean_t',  'mean_x', 'sigma_x', 'sigma_xp', 'norm_emit_x', 'cov_x__xp/sigma_x']
XemitOriginalUnits = ['m', 'ns',  'mm',    'mm',      'mrad',     'mm-mrad',     'mrad' ]  # Units that Astra writes
XemitColumnFactors = [1,    1e-9, 1e-3,    1e-3,      1e-3,        1e-6,         1e-3]     # Factors to make standard units
XemitColumnUnits   = ['m',  's',  'm',     'm',       '1',         'm',          'rad' ]
XemitColumn = dict( zip(XemitColumnNames, list(range(1, 1+len(XemitColumnNames) ) ) ) )
OutputUnits.update(unit_dict(XemitColumnNames, XemitColumnUnits))


YemitColumnNames     = ['mean_z', 'mean_t',  'mean_y', 'sigma_y', 'sigma_yp', 'norm_emit_y', 'cov_y__yp/sigma_y']
YemitOriginalUnits   = ['m', 'ns', 'mm',  'mm', 'mrad', 'mm-mrad',   'mrad' ] # Units that Astra writes
YemitColumnFactors   = [1,   1e-9, 1e-3,  1e-3, 1e-3, 1e-6,   1e-3] # Factors to make standard units
YemitColumnUnits     = ['m', 's', 'm',  'm', '1', 'm',   'rad' ]
YemitColumn = dict( zip(YemitColumnNames, list(range(1, 1+len(YemitColumnNames) ) ) ) )
OutputUnits.update(unit_dict(YemitColumnNames, YemitColumnUnits) )

ZemitColumnNames   = ['mean_z', 'mean_t',  'mean_kinetic_energy', 'sigma_z', 'sigma_energy', 'norm_emit_z', 'cov_z__energy/sigma_z']
ZemitOriginalUnits = ['m', 'ns', 'MeV',            'mm',     'keV',           'mm-keV',      'keV' ]
ZemitColumnFactors = [1,   1e-9, 1e6,              1e-3,     1e3,              1,             1e3] # Factors to make standard units
ZemitColumnUnits   = ['m', 's',  'eV',             'm',      'eV',            'm*eV',         'eV' ]
ZemitColumn = dict( zip(ZemitColumnNames, list(range(1, 1+len(ZemitColumnNames) ) ) ) )
OutputUnits.update(unit_dict(ZemitColumnNames, ZemitColumnUnits))

LandFColumnNames =   ['landf_z', 'landf_n_particles', 'landf_total_charge', 'landf_n_lost', 'landf_energy_deposited', 'landf_energy_exchange']
LandFOriginalUnits = ['m', '1', 'nC', '1', 'J', 'J']
LandFColumnFactors = [1, 1, -1e-9, 1, 1, 1]
LandFColumnUnits =   ['m', '1', 'C', '1', 'J', 'J']
OutputUnits.update(unit_dict(LandFColumnNames, LandFColumnUnits))

OutputColumnNames['Cemit'] = CemitColumnNames
OutputColumnNames['Xemit'] = XemitColumnNames
OutputColumnNames['Yemit'] = YemitColumnNames
OutputColumnNames['Zemit'] = ZemitColumnNames
OutputColumnNames['LandF'] = LandFColumnNames

OutputColumnFactors['Cemit'] = CemitColumnFactors
OutputColumnFactors['Xemit'] = XemitColumnFactors
OutputColumnFactors['Yemit'] = YemitColumnFactors
OutputColumnFactors['Zemit'] = ZemitColumnFactors
OutputColumnFactors['LandF'] = LandFColumnFactors

ERROR = {'error': True}


# Special additions
OutputUnits['cov_x__xp'] = unit('m')
OutputUnits['cov_y__yp'] = unit('m')
OutputUnits['cov_z__energy'] = unit('m*eV')


def astra_run_extension(run_number):
    """
    Astra adds an extension according to the run number: 1 -> '001'
    """
    return str(run_number).zfill(3)




def find_astra_output_files(input_filePath, run_number,
                            types= ['Cemit', 'Xemit', 'Yemit', 'Zemit', 'LandF']
                           ):
    """
    Finds the existing output files, based on standard Astra extensions. 
    """
    
    extensions = ['.'+x+'.'+astra_run_extension(run_number) for x in types]
    
    # List of output files
    path, infile = os.path.split(input_filePath)
    prefix = infile.split('.')[0] # Astra uses inputfile to name output
    outfiles = [os.path.join(path, prefix+x) for x in extensions]
    
    return [o for o in outfiles if os.path.exists(o)]
    


def astra_output_type(filename):
  return filename.split('.')[-2]
  

    
    
    
def parse_astra_output_file(filePath, standardize_labels=True,):   
    """
    Simple parsing of tabular output files, according to names in this file. 
    
    If standardize labels, the covariance labels and data will be simplified. 
    
    """
    
    # Check for empty file
    if os.stat(filePath).st_size == 0:
        raise ValueError(f'ERROR: Empty output file: {filePath}')
    
    data = np.loadtxt(filePath, ndmin=2)
    if data.shape == ():
        raise ValueError(f'No data in file: {filePath}')
    
    if len(data) == 0:
        raise ValueError(f'No data in file (zero length): {filePath}')
    
    d = {}
    type = astra_output_type(filePath) 
    
    # Get the appropriate keys and factors 
    keys = OutputColumnNames[type]
    factors = OutputColumnFactors[type]
     
    for i in range(len(keys)):
        #print(filePath, keys[i])
        
        d[keys[i]] = data[:,i]*factors[i]

    
    if standardize_labels:
        if type == 'Xemit':
            d['cov_x__xp'] = d.pop('cov_x__xp/sigma_x')*d['sigma_x']
            
        if type == 'Yemit':
            d['cov_y__yp'] = d.pop('cov_y__yp/sigma_y')*d['sigma_y']     
            
        if type == 'Zemit':
            d['cov_z__energy'] = d.pop('cov_z__energy/sigma_z')*d['sigma_z']                   
        
    # Special modifications
    #if type in ['Xemit', 'Yemit', 'Zemit']:
        
        
    return d







# ------ Number parsing ------
def isfloat(value):
      try:
            float(value)
            return True
      except ValueError:
            return False

def isbool(x):        
    z = x.strip().strip('.').upper()
    if  z in ['T', 'TRUE', 'F', 'FALSE']:
        return True
    else:
        return False
    
def try_int(x):
    if x == int(x):
        return int(x)
    else:
        return x

def try_bool(x):
    z = x.strip().strip('.').upper()
    if  z in ['T', 'TRUE']:
        return True
    elif z in ['F', 'FALSE']:
        return False
    else:
        return x
    
    
# Simple function to try casting to a float, bool, or int
def number(x):
    z = x.replace('D', 'E') # Some floating numbers use D
    if isfloat(z):
        val =  try_int(float(z))
    elif isbool(x):
        val = try_bool(x)
    else:
        # must be a string. Strip quotes.
        val = x.strip().strip('\'').strip('\"')
    return val    


# ------ Astra input file (namelist format) parsing

def clean_namelist_key_value(line):
    """
    Cleans up a namelist "key = value line"
    
    Removes all spaces, and makes the key lower case.
    
    """
    z = line.split('=')
    # Make key lower case, strip
    
    key = z[0].strip().lower().replace(' ', '')
    value = ''.join(z[1:])
    
    return f'{key} = {value}'

def unroll_namelist_line(line, commentchar='!', condense=False ):
    """
    Unrolls namelist lines. Looks for vectors, or multiple keys per line. 
    """
    lines = [] 
    # Look for comments
    x = line.strip().strip(',').split(commentchar)
    if len(x) ==1:
        # No comments
        x = x[0].strip()
    else:
        # Unroll comment first
        comment = ''.join(x[1:])
        if not condense:
            lines.append('!'+comment)
        x = x[0].strip()
    if x == '':
        pass    
    elif x[0] == '&' or x[0]=='/':
        # This is namelist control. Write.
        lines.append(x.lower())
    else:
        # Content line. Should contain = 
        # unroll.
        # Check for multiple keys per line, or vectors.
        # TODO: handle both
        n_keys = len(x.split('='))
        if n_keys ==2:
            # Single key
            lines.append(clean_namelist_key_value(x))
        elif n_keys >2:
            for y in x.strip(',').split(','):
                lines.append(clean_namelist_key_value(y))

    return lines
    
def parse_simple_namelist(filePath, commentchar='!', condense=False ):
    """
    Unrolls namelist style file. Returns lines.
    makes keys lower case
    
    Example:
    
    &my_namelist
    
        x=1, YY  = 4 ! this is a comment:
    /
    
    unrolls to:
    &my_namelist
    ! this is a comment
        x = 1
        yy = 4
    /
    
    """
    
    lines = []
    with open(filePath, 'r') as f:
        if condense:
            pad = ''
        else:
            pad = '    '
        
        for line in f:
            ulines = unroll_namelist_line(line, commentchar=commentchar, condense=condense)
            lines = lines + ulines

            
    return lines





def parse_unrolled_namelist(unrolled_lines):
    """
    Parses an unrolled namelist into a dict
    
    """
    namelists={}
    for line in unrolled_lines:
        if line[0]=='1' or line[0]=='/' or line[0]=='!':
            # Ignore
            continue
        if line[0]=='&':
            name = line[1:].lower()
            namelists[name]={}
            # point to current namelist
            n = namelists[name]
            continue
        # content line
        key, val = line.split('=')
        
        # look for vector
        vals = val.split()
        if len(vals) == 1:
            val = number(vals[0])
        else:
            if isfloat(vals[0].replace(',',' ')):
                # Vector. Remove commas
                val = [number(z) for z in val.replace(',',' ').split()] 
            else:
                # This is just a string. Just strip
                val = val.strip()
        n[key.strip()] = val
        
        
    return namelists


def parse_astra_input_file(filePath, condense=False):
    """
    Parses an Astra input file into separate dicts for each namelist. 
    Returns a dict of namelists. 
    """
    lines = parse_simple_namelist(filePath, condense=condense)
    namelists = parse_unrolled_namelist(lines)
    return namelists







def fix_input_paths(input_dict, root='', prefixes=['file_', 'distribution', 'q_type']):
    """
    Looks for keys in the input dict of dicts, that start with any strings as in the prefixes list.
    This should indicate a file. Then, fill in the absoulute path. 
    root should be the original input file path.
    
    Does not replace absolute paths, or paths where the file does not exist. 
    
    """
    for nl in input_dict:
        for key in input_dict[nl]:
            if any([key.startswith(prefix) for prefix in prefixes]):
                val = input_dict[nl][key]
                
                # Skip absolute paths
                if os.path.isabs(val):
                    continue
                newval = os.path.abspath(os.path.join(root, val))

                # Skip if does not exist
                if not os.path.exists(newval):
                    continue
                
                #assert os.path.exists(newval)
                #print(key, val, newval)
                input_dict[nl][key] = newval                
                
                

# ------------------------------------------------------------------ 
# ------------------------- Astra particles ------------------------ 
def find_phase_files(input_filePath, run_number=1):
    """
    Returns a list of the phase space files, sorted by z position
        (filemname , z_approx)
    """
    path, infile = os.path.split(input_filePath)
    prefix = infile.split('.')[0] # Astra uses inputfile to name output    
    phase_import_file = ''
    phase_files = [];
    run_extension = astra_run_extension(run_number)
    for file in os.listdir(path):
        if re.match(prefix + '.\d\d\d\d.'+run_extension, file):
            # Get z position
            z = float(file.replace(prefix+ '.', '').replace('.'+run_extension,''))
            phase_file=os.path.join(path, file)
            phase_files.append((phase_file, z))
    # Sort by z
    return sorted(phase_files, key=lambda x: x[1])





    
    
    
    
    
    

