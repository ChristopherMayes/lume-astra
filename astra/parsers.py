#!/usr/bin/env python3

import os
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

  res = {}
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


  

