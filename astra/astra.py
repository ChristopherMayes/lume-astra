#!/usr/bin/env python3

from astra import parsers, tools

import tempfile
import shutil
import subprocess
import os

class Astra:
    """ This class allows us to ..."""
    
    def __del__(self):
        if  self.auto_cleanup:
            self.clean() # clean directory before deleting

    def clean(self):   
        if self.using_tempdir:
            shutil.rmtree(self.sim_path)
        else:
            print('Error: trying to delete original input file! Aborting cleanup.')
        
            
    def __init__(self,
                 astra_bin='Astra',
                 input_file='astra.in',
                 workdir=None,
                 verbose=False):
        
        self.astra_bin = astra_bin
        self.sim_log_file = 'astra.log'
        self.finished = False
        self.output = {}
        
        
        # Get absolute path, then separate to sim_path/input_file
        self.source_input_file = os.path.abspath(input_file) # Save original source
        self.sim_path, self.sim_input_file = os.path.split(self.source_input_file)
        self.workdir=os.path.abspath(workdir)        
        self.auto_cleanup = True
                  
        # All paths should be absolute    
        if workdir:
            self.using_tempdir = True
            src = self.sim_path
            if not os.path.exists(src):
                print(src, 'does not exist:')
            dir = os.path.abspath(workdir)
            dest = tempfile.TemporaryDirectory(prefix='astra_', dir=dir).name
            if verbose: print(dest)
            shutil.copytree(src, dest)
            self.sim_path = dest
            self.sim_input_file = os.path.join(dest, self.sim_input_file)
        else:
            self.using_tempdir = False
            self.sim_input_file = os.path.join(self.sim_path, self.sim_input_file)
            # work in place, do not delete
            self.auto_cleanup=False
    
    def load_output(self):
        outfiles = find_astra_output_files(self.sim_input_file)
        for f in outfiles:
            self.output.update(parsers.parse_astra_output(f))
            # Save errors
            if self.output['error']:
                self.output['why_error'] = 'problem with output file: '+f

        
    
    
    def run_astra(self, verbose=False, parse_output=True):
        # Move to local directory
        # Save init dir
        if verbose: print('init dir: ', os.getcwd())
        init_dir = os.getcwd()
        os.chdir(self.sim_path)
        # Debugging
        if verbose: print('running astra in '+os.getcwd())

        _, infile = os.path.split(self.sim_input_file)
        
        runscript = [self.astra_bin, infile]
    
        log = []
        for path in tools.execute(runscript):
            if verbose:
                print(path, end="")
            log.append(path)
        with open(self.sim_log_file, 'w') as f:
            for line in log:
                f.write(line)
    
        if parse_output:
            self.load_output()


        self.finished = True
        
        
        # Return to init_dir
        os.chdir(init_dir)            
  
        # Option for cleaning on exit

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
    
    
    
    


  
