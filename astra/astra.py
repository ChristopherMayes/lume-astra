#!/usr/bin/env python3

from astra import parsers, tools

import tempfile
import shutil
import subprocess
import os
import time
import re





class Astra:
    """ This class allows us to ..."""
    
    def __del__(self):
        if  self.auto_cleanup:
            self.clean() # clean directory before deleting

    def clean(self):   
        # Only remove temporary directory. Never delete anything else!!!
        if self.tempdir:
            print('deleting: ', self.tempdir)
            shutil.rmtree(self.tempdir)
                   
    def __init__(self,
                 astra_bin='Astra',
                 input_file='astra.in',
                 workdir=None,
                 verbose=False):
        # Save init
        self.original_input_file = input_file
        self.workdir = workdir
        self.verbose=verbose
        self.astra_bin = astra_bin
        
        # These will be set
        self.tempdir = None
        self.log = []
        self.output = {}
        self.auto_cleanup = True
        self.timeout=None
        
        # Run control
        self.finished = False
        self.configured = False
        
        # Call configure
        self.configure()
        
    def configure(self):
        self.configure_astra(self.original_input_file, self.workdir)
        self.configured = True
 
    def configure_astra(self, input_file, workdir):
        
        # Get absolute path, then separate to sim_path/input_file
        if not os.path.exists(input_file):
            print('input_file does not exist:', input_file)
            return
        
        # Internal dict of input
        self.input = parsers.parse_astra_input_file(input_file)
        
        self.source_input_file = os.path.abspath(input_file) # Save original source
        self.sim_path, self.sim_input_file = os.path.split(self.source_input_file)
        self.workdir=os.path.abspath(workdir)        
        
                  
        # All paths should be absolute    
        if workdir:
            src = self.sim_path
            if not os.path.exists(src):
                print(src, 'does not exist:')
            dir = os.path.abspath(workdir)
            dest = tempfile.TemporaryDirectory(prefix='astra_', dir=dir).name
            if self.verbose: print(dest)
            shutil.copytree(src, dest)
            self.sim_path = dest
            self.tempdir = dest
            self.sim_input_file = os.path.join(dest, self.sim_input_file)
        else:
            self.sim_input_file = os.path.join(self.sim_path, self.sim_input_file)
            # work in place, do not delete
            self.auto_cleanup=False
            
        self.configured = True
    
    def load_output(self):
        outfiles = find_astra_output_files(self.sim_input_file)
        for f in outfiles:
            self.output.update(parsers.parse_astra_output_full(f))
            # Save errors
            if self.output['error']:
                self.output['why_error'] = 'problem with output file: '+f

    def run(self):
        if not self.configured:
            print('not configured to run')
            return
        self.run_astra(verbose=self.verbose, timeout=self.timeout)
    
    
    def run_astra(self, verbose=False, parse_output=True, timeout=None):
        # Move to local directory
        t1 = time.time()
        # Save init dir
        if verbose: print('init dir: ', os.getcwd())
        init_dir = os.getcwd()
        os.chdir(self.sim_path)
        # Debugging
        if verbose: print('running astra in '+os.getcwd())

        # Write input file from internal dict
        self.write_input()
        _, infile = os.path.split(self.sim_input_file)
        
        runscript = [self.astra_bin, infile]
    
    
        if timeout:
            res = tools.execute2(runscript, timeout=timeout)
            self.log = res['log']
            self.output['run_error'] = res['error']
            self.output['why_run_error'] = res['why_error']
        else:
            # Interactive output, for Jupyter
            log = []
            for path in tools.execute(runscript):
                if verbose:
                    print(path, end="")
                log.append(path)
        
        #with open(self.sim_log_file, 'w') as f:
        #    for line in self.log:
        #        f.write(line)
    
        if parse_output:
            self.load_output()

        t2 = time.time()
        self.output['run_time'] = t2 - t1
        self.output['start_time'] = t1
        
        self.finished = True
        
        
        # Return to init_dir
        os.chdir(init_dir)            
  
        # Option for cleaning on exit
    
    
    def write_input(self):
        parsers.write_namelists(self.input, self.sim_input_file)
        


def find_astra_output_files(input_filePath, 
                            extensions= ['.LandF.001', '.Xemit.001', '.Yemit.001', '.Zemit.001']
                           ):
    """
    Finds the existing output files, based on standard Astra extensions. 
    """
    
    # List of output files
    path, infile = os.path.split(input_filePath)
    prefix = infile.split('.')[0] # Astra uses inputfile to name output
    outfiles = [os.path.join(path, prefix+x) for x in extensions]
    
    return [o for o in outfiles if os.path.exists(o)]
    
    

def find_phase_files(input_filePath):
    """
    Returns a list of the phase space files, sorted by z position
        (filemname , z_approx)
    """
    path, infile = os.path.split(input_filePath)
    prefix = infile.split('.')[0] # Astra uses inputfile to name output    
    phase_import_file = ''
    phase_files = [];
    for file in os.listdir(path):
        if re.match(prefix + '.\d\d\d\d.001', file):
            # Get z position
            z = float(file.replace(prefix+ '.', '').replace('.001',''))
            phase_file=os.path.join(path, file)
            phase_files.append((phase_file, z))
    # Sort by z
    return sorted(phase_files, key=lambda x: x[1])
    
def write_namelists(namelists, filePath):
    with open(filePath, 'w') as f:
        for key in namelists:
            lines = namelist_lines(namelists[key], key)
            for l in lines:
                print(l)
                f.write(l+'\n')



    


  
