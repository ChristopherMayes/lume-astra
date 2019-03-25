#! /usr/bin/python

import sys
import math
import re
import os
import subprocess
import numpy
#import scipy
#import scipy.stats
#import scipy.optimize as sp
from optparse import OptionParser
#import matplotlib.pyplot as plt
import numpy.polynomial.polynomial as poly

# ---------------------------------------------------------------------------- #
# Get the filename of the final screen (in terms of z position)
# ---------------------------------------------------------------------------- #

def get_final_screen_name(input_directory, input_basename):

  phase_import_file = ''

  phase_files = [];
  for file in os.listdir(input_directory):
    if re.match(input_basename + '.\d\d\d\d.001', file):
      phase_files.append(input_directory + file)
  phase_positions = []
  if (len(phase_files) > 0):

    # Find the last phase file 
    for file in phase_files:
	    decimal_string = file.replace(input_directory + input_basename + '.', '').replace('.001','')
	    phase_positions.append(float(decimal_string))

    last_phase_index = phase_positions.index(max(phase_positions))

    phase_import_file = phase_files[last_phase_index]

  return phase_import_file

# ---------------------------------------------------------------------------- #
# Get screen data
# ---------------------------------------------------------------------------- #

def get_screen_data(phase_import_file, verbose):

  if (verbose):
    print('Loading file: ' + phase_import_file)

  # Import the file
  phase_data = numpy.loadtxt(phase_import_file)

  if (verbose):
    print('Finished loading.')
    print('reference: ', phase_data[0])
  # Note: assumes the reference particle is at index = 0		

  x = phase_data[1:,0]
  y = phase_data[1:,1]
  z = phase_data[1:,2]
  z_ref = phase_data[0,2]
  z_rel = z
  z = z + z_ref

  px = phase_data[1:,3]
  py = phase_data[1:,4]
  pz = phase_data[1:,5]
  pz_ref = phase_data[0,5]
  pz = pz + pz_ref

  qmacro = phase_data[1:,7]
  astra_index = phase_data[1:,8]
  status = phase_data[1:,9]

  good_particles = numpy.where(status == 5) 

  x = x[good_particles]
  y = y[good_particles]
  z = z[good_particles]
  z_rel = z_rel[good_particles]
  px = px[good_particles]
  py = py[good_particles]
  pz = pz[good_particles]
  qmacro = qmacro[good_particles]
  astra_index = astra_index[good_particles]

  MC = 510998.928   # in eV / c
  MC2 = 0.510998928 # in MeV

  GBx = px / MC;
  GBy = py / MC;
  GBz = pz / MC;
  GB2 = GBx**2 + GBy**2 + GBz**2;
  GB = numpy.sqrt(GB2)
  G = numpy.sqrt(GB2 + 1.0);
  Energy = G*MC2
  Bx = GBx/G;
  By = GBy/G;
  Bz = GBz/G;

  c = 0.299792458 # in meters / nanosecond

  if numpy.any(Bz <= 0):
    if verbose:
      print('ERROR: negative or zero velocity detecter')
    return {'error':True}

  t = -z_rel/(Bz * c);
  x = x + (Bx * c)*t;
  y = y + (By * c)*t;

  units={'x':'m','y':'m','z':'m','px':'eV/c','py':'eV/c','pz':'eV/c','t':'ns','Energy':'MeV'}

  screen_data = {}
  screen_data['x'] = x
  screen_data['y'] = y
  screen_data['z'] = z
  screen_data['z_rel'] = z_rel
  screen_data['px'] = px
  screen_data['py'] = py
  screen_data['pz'] = pz
  screen_data['qmacro'] = qmacro
  screen_data['astra_index'] = astra_index
  screen_data['MC'] = MC
  screen_data['MC2'] = MC2
  screen_data['GBx'] = GBx
  screen_data['GBy'] = GBy
  screen_data['G'] = G
  screen_data['GB'] = GB
  screen_data['Energy'] = Energy
  screen_data['Bx'] = Bx
  screen_data['By'] = By
  screen_data['Bz'] = Bz
  screen_data['c'] = c
  screen_data['t'] = t

  screen_data["units"]=units

  screen_data['error'] = False

  return screen_data

# ---------------------------------------------------------------------------- #
# Compute the 6x6 Sigma (Second Moment) Matrix
# ---------------------------------------------------------------------------- #
def calc_sigma_matrix(screen_data, verbose, variables=None):

   if(variables is None):
      variables = ['x','GBx','y','GBy','t','Energy'] # Note: t is arrival time

   # Use relative energy coordinates:
   if(variables[5]=="deltaE"):
      screen_data["deltaE"]=screen_data["Energy"]/screen_data["Energy"].mean()
   elif(variables[5]=="deltaP"):
      screen_data["deltaP"]=screen_data["GB"]/screen_data["GB"].mean()

   sigma = numpy.empty(shape=(6,6))   
   sigma[:] = numpy.NAN  

   for ii in range(6):
      for jj in range(6):

         if(numpy.isnan(sigma[ii,jj])): 
   
            ustr = variables[ii]
            vstr = variables[jj]

            sigma[ii,jj] = numpy.mean( (screen_data[ustr]-screen_data[ustr].mean()) * (screen_data[vstr]-screen_data[vstr].mean()) )
            sigma[jj,ii] = sigma[ii,jj]

   return sigma

def calc_avg_norm_Lz(screen_data,verbose,sigma=None):

   if(sigma==None):
      sigma = calc_sigma_matrix(screen_data,verbose)
   
   avg_norm_Lz = sigma[0,3] - sigma[2,1]
   return avg_norm_Lz

def calc_uncorr_espread(sigma2x2):
 
   sig_t = numpy.sqrt(sigma2x2[0,0])
   sig_E = numpy.sqrt(sigma2x2[1,1])

   sig_max = max([sig_t,sig_E])
   sig_min = min([sig_t,sig_E])

   if(sig_max/sig_min < 10):
      print("Warning in calc_uncorr_epsread -> may have bad scaling of phase space variables.")

   # Compute the eigenvalues of 2x2 sigma matrix:
   #a = sigma2x2[0,0]
   #b = sigma2x2[0,1]
   #c = sigma2x2[1,1]
   #eps = a*c - b*b
 
   #lp = 0.5*( (a+c) + numpy.sqrt( (a+c)*(a+c) - 4*eps*eps) )
   #lm = 0.5*( (a+c) - numpy.sqrt( (a+c)*(a+c) - 4*eps*eps) )

   eigs = numpy.linalg.eig(sigma2x2)
   ls = eigs[0]
   lp = max(ls)
   lm = min(ls)

   if(sig_t > sig_E):
      sig_E_uncorr = math.sqrt(lm)
   else:
      sig_E_uncorr = math.sqrt(lp)

   return sig_E_uncorr

# ---------------------------------------------------------------------------- #
# Fits a quadratic to the Energy vs. time, subtracts it, finds the rms of the residual in keV
# ---------------------------------------------------------------------------- #

def calc_ho_energy_spread(screen_data, verbose):

  Energy = screen_data["Energy"]
  t = screen_data["t"]

  # Calculate higher order energy spread
  best_fit_coeffs = poly.polyfit(t, Energy, 2)
  best_fit = poly.polyval(t, best_fit_coeffs)

  #if (verbose):
    #t_plot = numpy.linspace(min(t), max(t), 100)
    #Energy_plot = poly.polyval(t_plot, best_fit_coeffs)
    #plt.plot(t, Energy, '.', t_plot, Energy_plot, '-')
    #plt.show()

  Energy_higher_order = Energy - best_fit

  energy_ho_rms = numpy.std(Energy_higher_order)*1000.0 # in keV

  if (verbose):
    print("Energy rms (higher order) = " + str(energy_ho_rms) )

  return energy_ho_rms

# ---------------------------------------------------------------------------- #
# Returns peak current in amps
# ---------------------------------------------------------------------------- #

def calc_peak_current(screen_data, verbose):
  t = screen_data["t"]
  qmacro = screen_data["qmacro"]  # handles cases where macro particle charge varies

  # Calculate peak current

  hist_bins = 20  # number of histogram bins. 2000 particles -> 20 bins

  hist_edges = numpy.linspace(min(t), max(t), hist_bins)
  dt = hist_edges[1] - hist_edges[0] 
  hist_edges = numpy.linspace(min(t)-0.5*dt, max(t)+0.5*dt, hist_bins+1)
  dt = hist_edges[1] - hist_edges[0] 

  bin_index = numpy.searchsorted(hist_edges,t, "right")	
  current = numpy.bincount(bin_index-1, weights=numpy.abs(qmacro))/dt

  peak_current = max(current)

  if (verbose):
    print("Peak current = " + str(peak_current) + " Amps")

  #if (verbose):
    #t_plot = hist_edges[0:-1] + 0.5*dt
    #print str(len(t_plot)) + " " + str(len(current))
    #plt.plot(t_plot, current, '-')
    #plt.show()

  return peak_current

# ---------------------------------------------------------------------------- #
# Returns skewness of the temporal distribution (see wikipedia on 'skewness')
# ---------------------------------------------------------------------------- #

def calc_skewness(screen_data, verbose):
  t = screen_data["t"]

  skewness = 0 ###FIXME numpy.abs(scipy.stats.skew(t))
                        
  if (verbose):
    print("Skewness = " + str(skewness) + " (unitless)")

  return skewness

# ---------------------------------------------------------------------------- #
# Main function
# ---------------------------------------------------------------------------- #

def main():

  parser = OptionParser()
  parser.add_option("-v", "--verbose",
              action="store_true", dest="verbose", default=False,
              help="don't print status messages to stdout")
  parser.add_option("-n", "--noastra",
              action="store_true", dest="noastra", default=False,
              help="don't run astra")
  parser.add_option("-a", "--astra", dest="astra_name", default="astra",
              help="name of astra executable", metavar="FILE")

  (options, args) = parser.parse_args()

  verbose = options.verbose
  noastra = options.noastra
  astra_name = options.astra_name

  if (verbose):
    print("")
    print("Beginning Astra wrapper...")

  # Interpret input arguments
  path_to_input_file = args[0]

  # Directory / Filenames

  script_directory = os.path.dirname(sys.argv[0]) + '/'
  input_directory = os.path.dirname(path_to_input_file) + '/'
  script_name = os.path.basename(sys.argv[0])
  input_name = os.path.basename(path_to_input_file)
  astra_binary = script_directory + astra_name
  input_basename = input_name.replace('.in', '')
  merit_name = input_basename + '.merit'

  # Call Astra

  if (noastra == False):
    command = astra_binary + ' ' + path_to_input_file
    subprocess.call(command.split());


  # Get Output

  energy_ho_rms = 0; # Default good value
  peak_current = 3e14; # Default good value
  skewness = 0;

  phase_import_file = get_final_screen_name(input_directory, input_basename)
  
  if (len(phase_import_file) > 0):

    screen_data = get_screen_data(phase_import_file, verbose)

    energy_ho_rms = calc_ho_energy_spread(screen_data, verbose)

    peak_current = calc_peak_current(screen_data, verbose)

    skewness = calc_skewness(screen_data, verbose)
 
    variables = ['x','GBx','y','GBy','t','deltaE']

    sigma = calc_sigma_matrix(screen_data, verbose,variables)
    avgLz = calc_avg_norm_Lz(None,verbose,sigma)
    uncorr_epsread = calc_uncorr_espread(sigma[4:,4:])

    for ii in range(6):
      for jj in range(6):
         if(sigma[ii,jj]!=sigma[jj,ii]):
            print("sigma matrix is not symetric!")

  else:
    # File did not exist, so something got screwed up. Output a bad number
    energy_ho_rms = 3e14
    peak_current = 0.0
    skewness = 3e14

  # Output merit file

  merit = []

  merit.append(energy_ho_rms)
  merit.append(peak_current)
  merit.append(skewness)

  output_file = open(input_directory + merit_name, "w")
  for value in merit:
    output_file.write( str(value) + " ")
  output_file.write('\n')
  output_file.close()

  # Test function for calculating uncorrelated energy spread:
  sigT = 10
  sigE = 1e-4
  npart = 100000

  t = numpy.random.normal(0,sigT,(1,npart))
  E = numpy.random.normal(0,sigE,(1,npart))

  theta = 35*(math.pi/180)
  C = math.cos(theta)
  S = math.sin(theta)

  tr =  C*t + S*E
  Er = -S*t + C*E

  dt = tr-tr.mean()
  dE = Er-Er.mean()

  t2 = numpy.mean(dt*dt)
  E2 = numpy.mean(dE*dE)
  tE = numpy.mean(dt*dE)

  sigma2x2 = numpy.array([[t2, tE],[tE, E2]]) 
  print(sigma2x2)
  espread = calc_uncorr_espread(sigma2x2)
  print( (espread-sigE)/sigE )

# ---------------------------------------------------------------------------- #
# This allows the main function to be at the beginning of the file
# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
  main()

