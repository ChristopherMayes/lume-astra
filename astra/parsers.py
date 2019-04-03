#!/usr/bin/env python3

import os
from numbers import Number
from math import isnan
import numpy as np
import re

# ------ Astra output parsing--------



XemitColumnNames   = ['z', 't',  'x_average', 'x_rms', 'xp_rms', 'x_normemit', 'xxp_average']
XemitColumnUnits   = ['m', 'ns', 'mm',  'mm', 'mrad', 'mm-mrad',   'mrad' ]
XemitColumnFactors = [1,    1e-9, 1e-3,  1e-3, 1e-3,   1e-6,   1e-3] # Factors to make standard units
XemitColumn = dict( zip(XemitColumnNames, list(range(1, 1+len(XemitColumnNames) ) ) ) )
XemitUnits  = dict( zip(XemitColumnNames, XemitColumnUnits) )

YemitColumnNames   = ['z', 't',  'y_average', 'y_rms', 'yp_rms', 'y_normemit', 'yyp_average']
YemitColumnUnits   = ['m', 'ns', 'mm',  'mm', 'mrad', 'mm-mrad',   'mrad' ]
YemitColumnFactors = [1,   1e-9, 1e-3,  1e-3, 1e-3, 1e-6,   1e-3] # Factors to make standard units
YemitColumn = dict( zip(YemitColumnNames, list(range(1, 1+len(YemitColumnNames) ) ) ) )
YemitUnits  = dict( zip(YemitColumnNames, YemitColumnUnits) )

ZemitColumnNames   = ['z', 't',  'E_kinetic', 'z_rms', 'deltaE_rms', 'z_normemit', 'zEp_average']
ZemitColumnUnits   = ['m', 'ns', 'MeV',       'mm',    'keV',        'mm-keV',  'keV' ]
ZemitColumnFactors = [1,   1e-9,  1e6,        1e-3,    1e3,           1,   1e3] # Factors to make standard units
ZemitColumn = dict( zip(ZemitColumnNames, list(range(1, 1+len(ZemitColumnNames) ) ) ) )
ZemitUnits  = dict( zip(ZemitColumnNames, ZemitColumnUnits) )

# New style
OutputColumnNames = {}
OutputColumnUnits = {}
OutputColumnFactors = {}

OutputColumnNames['Xemit'] = XemitColumnNames
OutputColumnNames['Yemit'] = YemitColumnNames
OutputColumnNames['Zemit'] = ZemitColumnNames

OutputColumnFactors['Xemit'] = XemitColumnFactors
OutputColumnFactors['Yemit'] = YemitColumnFactors
OutputColumnFactors['Zemit'] = ZemitColumnFactors

OutputColumnNames['LandF']   = ['z', 'Npart', 'charge', 'n_lost', 'energy_deposited', 'energy exchange']
OutputColumnUnits['LandF']   = ['m', '1', 'nC', '1', 'J', 'J']
OutputColumnFactors['LandF'] = [1, 1, 1e-9, 1, 1, 1]

ERROR = {'error': True}



def astra_run_extension(run_number):
    """
    Astra adds an extension according to the run number: 1 -> '001'
    """
    return str(run_number).zfill(3)




def find_astra_output_files(input_filePath, run_number,
                            types= ['Xemit', 'Yemit', 'Zemit'] #'LandF', 
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
    


def parse_table_output(filename, headerlines=0, header=[]):
  """
  Gets general table data and converts to floats.
  'headerlines' number of lines are stored in the optional header
  blank lines are ignored
  """
  f = open(filename, 'r')
  dat = []
  if headerlines > 0:
    for dummy in range(headerlines):
      header.append(f.readline().split())
  for line in f:
    s = line.split()
    if len(s) > 0:
      dat.append( [float(x) for x in s ] )
  f.close()
  return  dat


def astra_output_type(filename):
  return filename.split('.')[-2]
  

def parse_astra_output_file(filePath):   
    """
    Simple parsing of tabular output files, according to names in this file. 
    """
    data = np.loadtxt(filePath)
    if data.shape == ():
        return ERROR
    
    if len(data) == 0:
        return ERROR
        
    
    d = {}
    type = astra_output_type(filePath)
    
    if type == 'LandF':
    # Quick hack to get the bunch charge and lost particles. Enable in Astra with LandFS = T
        d['Qbunch'] = abs(data[-1][2]) * 1e-9 # nC -> C
        n_lost = int(data[0][1] - data[-1][1])
        d['n_lost'] = n_lost
        return d
    
    
    keys = OutputColumnNames[type]
    factors = OutputColumnFactors[type]
    
    
    for i in range(len(keys)):
        d[keys[i]] = data[:,i]*factors[i]
    return d


def old_parse_astra_output_full(filename):
  """
  Returns a dict with information from an astra file
  
  Any NaNs detected will return ERROR
  Uses the last line of Emit files only!!!
  """
  
  if not os.path.exists(filename):
    return ERROR
  
  type = astra_output_type(filename)
  
  dat = parse_table_output(filename)
  if len(dat) == 0:
    return ERROR
  lastdat = dat[-1]
  res = {'error': False}
  if type   == 'Xemit':
    columns = XemitColumn
  elif type == 'Yemit':
    columns = YemitColumn
  elif type == 'Zemit':
    columns = ZemitColumn
  elif type == 'LandF':
    # Quick hack to get the bunch charge and lost particles. Enable in Astra with LandFS = T
    res['Qbunch'] = abs(lastdat[2])
    n_lost = int(dat[0][1] - dat[-1][1])
    res['n_lost'] = n_lost
    return res
  else:
    print('unkown astra file type: ', type)
    return ERROR

  headers = list(columns.keys())

  for header in headers:
     res[header]=[]

  for ii in range(len(dat)):
     for jj in range(len(headers)):
        res[headers[jj]].append(dat[ii][columns[headers[jj]]-1])

  return res





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
    
    """
    z = line.split('=')
    # Make key lower case, strip
    return z[0].strip().lower()+' = '+''.join(z[1:])

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




def namelist_lines(namelist_dict, name):
    """
    Converts namelist dict to output lines, for writing to file
    """
    lines = []
    lines.append('&'+name)
    # parse
    for key, value in namelist_dict.items():
        #if type(value) == type(1) or type(value) == type(1.): # numbers
        if isinstance(value, Number): # numbers
            line= key + ' = ' + str(value) 
        elif type(value) == type([]): # lists
            liststr = ''
            for item in value:
                liststr += str(item) + ' '
            line = key + ' = ' + liststr 
        elif type(value) == type('a'): # strings
            line = key + ' = ' + "'" + value.strip("''") + "'"  # input may need apostrophes
        else:
            #print 'skipped: key, value = ', key, value
            pass
        lines.append(line)
    
    lines.append('/')
    return lines


def write_namelists(namelists, filePath):
    """
    Simple function to write namelist lines to a file
    
    """
    with open(filePath, 'w') as f:
        for key in namelists:
            lines = namelist_lines(namelists[key], key)
            for l in lines:
                f.write(l+'\n')



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



astra_species_names = {1:'electron', 2:'positrion', 3:'proton', 4:'hydrogen'}

astra_particle_status_names = {-1:'standard particle, at the cathode',
                        3:'trajectory probe particle',
                        5:'standard particle'}

def parse_astra_phase_file(filePath):
    """

    Parses astra particle dumps to numpy arrays, in m, eV/c, and s.
    
    """
    
    #
    # Internal Astra Columns
    # x   y   z   px   py   pz   t macho_charge astra_index status_flag
    # m   m   m   eV/c eV/c eV/c ns    nC           1              1
    
    #  The first line is the reference particle in absolute corrdinate. Subsequent particles have:
    #  z pz t
    #  relative to the reference. 
    #
    #
    # astra_index represents the species: 1:electrons, 2:positrons, 3:protons, 4:hydroger, ...
    # There is a large table of status. Status_flag = 5 is a standard particle. 
    
    data = np.loadtxt(filePath)
    ref = data[0,:] # Reference particle. 

    # position in m
    x = data[1:,0]
    y = data[1:,1]
    
    z_rel = data[1:,2]    
    z_ref = ref[2]
    #z = z_rel + z_ref
    
    # momenta in eV/c
    px = data[1:,3]
    py = data[1:,4]
    pz_rel = data[1:,5]
    
    pz_ref = ref[5]
    #pz = pz_rel + pz_ref
    
    # Time in seconds
    t_ref = ref[6]*1e-9
    t_rel = data[1:,6]*1e-9
    #t = t_rel + t_ref
    
    # macro charge in Coulomb
    qmacro = data[1:,7]*1e-9
    
    species_index = data[1:,8].astype(np.int)
    status = data[1:,9].astype(np.int)  
    
    # Select particle by status 
    #probe_particles = np.where(status == 3) 
    #good_particles  = np.where(status == 5) 

    d = {}
    d['x'] = x
    d['y'] = y
    #d['z'] = z
    d['z_ref'] = z_ref
    d['z_rel'] = z_rel
    d['px'] = px
    d['py'] = py
    #d['pz'] = pz
    d['pz_ref'] = pz_ref
    d['pz_rel'] = pz_rel
    #d['t'] = t
    d['t_ref']=t_ref
    d['t_rel'] = t_rel
    d['qmacro'] = qmacro
    d['status'] = status
    d['species_index'] = species_index
    
    return d
    
    
    
    
    
    

