#!/usr/bin/env python3

from astra import parsers, tools

import tempfile
import shutil
import os
import time


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
            
    def clean_output(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.sim_input_file, run_number)
        for f in outfiles:
            os.remove(f)
            
    def clean_screens(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        phase_files = parsers.find_phase_files(self.sim_input_file, run_number)           
        files   = [x[0] for x in phase_files] # This is sorted by approximate z
        for f in files:
            os.remove(f)
                   
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
        self.screen = [] # list of screens
        self.auto_cleanup = True
        self.timeout=None
        self.error = False
        
        # Run control
        self.finished = False
        self.configured = False
        
        # Call configure
        self.configure()
        
    #@property
    #def run_number(self):
    #    return self.input['newrun']['run']
        
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
             
        # All paths should be absolute    
        if workdir:
            self.workdir=os.path.abspath(workdir)   
            src = self.sim_path
            if not os.path.exists(src):
                print(src, 'does not exist:')
            dir = os.path.abspath(workdir)
            dest = tempfile.TemporaryDirectory(prefix='astra_', dir=dir).name
            if self.verbose: print(dest)
            shutil.copytree(src, dest, symlinks=True)
            self.sim_path = dest
            self.tempdir = dest
            self.sim_input_file = os.path.join(dest, self.sim_input_file)
        else:
            self.sim_input_file = os.path.join(self.sim_path, self.sim_input_file)
            # work in place, do not delete
            self.auto_cleanup=False
            
        self.configured = True
    
    def load_output(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.sim_input_file, run_number)
        
        for f in outfiles:
            self.output.update(parsers.parse_astra_output_file(f))
            # Save errors
            #if self.output['error']:
            #self.output['why_error'] = 'problem with output file: '+f
                
    def load_screens(self, end_only=False):
        # Clear existing screens
        self.screen = []
        
        # Sort files by approximate z
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        phase_files = parsers.find_phase_files(self.sim_input_file, run_number)           
        files   = [x[0] for x in phase_files] # This is sorted by approximate z
        zapprox = [x[1] for x in phase_files]
        
        if end_only: 
            files = files[-1:]
        if self.verbose:
            print('loading '+str(len(files))+ ' screens')
            print(zapprox)
        for f in files:
            pdat = parsers.parse_astra_phase_file(f)
            self.screen.append(pdat)
        
        
        
        
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
        self.write_input_file()
        _, infile = os.path.split(self.sim_input_file)
        
        runscript = [self.astra_bin, infile]
    
    
        if timeout:
            res = tools.execute2(runscript, timeout=timeout)
            log = res['log']
            self.output['run_error'] = res['error']
            self.output['why_run_error'] = res['why_error']
            # Log file must have this to have finished properly
            if log.find('finished simulation') == -1:
                self.output.update({'error': True, 'why_error': "Couldn't find finished simulation"})

        else:
            # Interactive output, for Jupyter
            log = []
            for path in tools.execute(runscript):
                if verbose:
                    print(path, end="")
                log.append(path)

        self.log = log
                
        
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
    
    
    def write_input_file(self):
        parsers.write_namelists(self.input, self.sim_input_file)
        
    # h5 writing
    def write_input(self, h5):
        writers.write_input_h5(h5, a.input)
    
    def write_output(self, h5):
        writers.write_output_h5(h5, a.output)
        
    def write_screens(self, h5):
        writers.write_screens_h5(h5, a.screen)        
        
  
  
  
  
class AstraGenerator:
    """
    Class to run Astra's particle generator
    
    """
    def __init__(self, 
                 generator_bin = None,
                 input_file = None,
                 sim_path=None,
                 verbose=False
                ):
        # Save init
        self.generator_bin = generator_bin 
        self.original_input_file = os.path.abspath(input_file)  
        self.sim_path = sim_path
        self.verbose=verbose  
        
        # Run control
        self.configured = False
        self.finished = False
        
        # Call configure
        self.input_file = None # This will be made
        self.configure()
        
    def configure(self):
       
        if not os.path.exists(self.original_input_file):
            print('input_file does not exist:', self.input_file)
            return
        
        # Get absolute path, then separate to sim_path/input_file
        # Parse
        self.input = parsers.parse_astra_input_file(self.original_input_file)['input']       
        
        # File, path setup
        # Split file
        path, file = os.path.split(self.original_input_file)
        if not self.sim_path:
            # Use original path
            self.sim_path = path
        self.input_file = 'temp_'+file
              
        if not os.path.exists(self.sim_path):
            print('sim_path does not exist:', self.sim_path)
            return
        
        self.configured = True
        
    def run(self):
        # Save initil directory
        init_dir = os.getcwd()
        os.chdir(self.sim_path)
        
        self.write_input_file()
        
        runscript = [self.generator_bin, self.input_file]
        res = tools.execute2(runscript, timeout=None)
        self.log = res['log']
        if self.verbose:
            print(self.log)
        
        # This is the file that should be written
        if os.path.exists(self.input['fname']):
            self.finished = True
        else:
            print('problem!')
             
        # Return to init_dir
        os.chdir(init_dir)     
        
    def write_input_file(self):
        parsers.write_namelists({'input':self.input}, self.input_file)        
        
              
        
             
        
          
  
