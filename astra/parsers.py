#!/usr/bin/env python3

import os
from numbers import Number
from math import isnan

# ------ Astra output parsing--------

XemitColumnNames   = ['z', 't',  'x_average', 'x_rms', 'xp_rms', 'x_normemit', 'xxp_average']
XemitColumnUnits   = ['m', 'ns', 'mm',  'mm', 'mrad', 'mm-mrad',   'mrad' ]
XemitColumn = dict( zip(XemitColumnNames, list(range(1, 1+len(XemitColumnNames) ) ) ) )
XemitUnits  = dict( zip(XemitColumnNames, XemitColumnUnits) )

YemitColumnNames   = ['z', 't',  'y_average', 'y_rms', 'yp_rms', 'y_normemit', 'yyp_average']
YemitColumnUnits   = ['m', 'ns', 'mm',  'mm', 'mrad', 'mm-mrad',   'mrad' ]
YemitColumn = dict( zip(YemitColumnNames, list(range(1, 1+len(YemitColumnNames) ) ) ) )
YemitUnits  = dict( zip(YemitColumnNames, YemitColumnUnits) )

ZemitColumnNames   = ['z', 't',  'E_kinetic', 'z_rms', 'deltaE_rms', 'z_normemit', 'zEp_average']
ZemitColumnUnits   = ['m', 'ns', 'MeV',       'mm',    'keV',        'mm-keV',  'keV' ]
ZemitColumn = dict( zip(ZemitColumnNames, list(range(1, 1+len(ZemitColumnNames) ) ) ) )
ZemitUnits  = dict( zip(ZemitColumnNames, ZemitColumnUnits) )


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
  
ERROR = {'error': True}

def parse_astra_output_full(filename):
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

  #print(res["E_kinetic"])

  return res

def parse_astra_output(filename):
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

  for key in columns:
    x = lastdat[ columns[key] -1 ]  # 1 is the first column.
    if isnan(x):  
      return ERROR
    else:
      res[key] = x

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



