#!/usr/bin/env python3

from astra import parsers, tools

import urllib.request
import tempfile
import shutil
import os
import time


class Astra:
    """ 
    Astra simulation object. Essential methods:
    .__init__(...)
    .configure()
    .run()
    
    Input deck is held in .input
    Output data is parsed into .output
    .load_screens() will load particle data into .screen[...]
    
    The Astra binary file can be set on init. If it doesn't exist, configure will check the
        $ASTRA_BIN
    environmental variable.
    
    
    """
    
    def __del__(self):
        if  self.auto_cleanup:
            self.clean() # clean directory before deleting

    def clean(self):   
        # Only remove temporary directory. Never delete anything else!!!
        if self.tempdir:
            if self.verbose:
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
        self.original_input_file = os.path.abspath(os.path.expandvars(self.original_input_file))
        self.configure_astra(self.original_input_file, self.workdir)
        self.configured = True
 
    def configure_astra(self, input_file, workdir):
        
        # Search for Astra executable
        if not os.path.exists(self.astra_bin):
            if 'ASTRA_BIN' in os.environ:
                self.astra_bin = os.environ['ASTRA_BIN']        
        
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
            self.sim_input_file = os.path.join(self.sim_path, 'temp_'+self.sim_input_file)
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
            self.error = res['error']
            self.output['run_error'] = self.error
            self.output['why_run_error'] = res['why_error']
            # Log file must have this to have finished properly
            if log.find('finished simulation') == -1:
                self.error = True
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
                 generator_bin = 'generator',
                 input_file = None,
                 sim_path=None,
                 verbose=False
                ):
        # Save init
        self.generator_bin = generator_bin 
        self.original_input_file = input_file
        self.sim_path = sim_path
        self.verbose=verbose  
        
        # Run control
        self.configured = False
        self.finished = False
        
        # Call configure
        self.input_file = None # This will be made
        self.configure()
        
    def configure(self):
        self.original_input_file = os.path.abspath(os.path.expandvars(self.original_input_file))
        # Search for generator executable
        if not os.path.exists(self.generator_bin):
            if 'GENERATOR_BIN' in os.environ:
                self.generator_bin = os.environ['GENERATOR_BIN']             
        
       
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
            print(self.input['fname'])
            print('The input file already exists! This is a problem!')
            print('Here is what the current working dir looks like:')
            os.listdir()
        # Return to init_dir
        os.chdir(init_dir)     
        
    def write_input_file(self):
        parsers.write_namelists({'input':self.input}, self.input_file)        
        
          
        
def set_astra(astra_input, generator_input, settings, verbose=False):
    """
    Searches astra and generator objects for keys in settings, and sets their values to the appropriate input
    """
    for k, v in settings.items():
        found=False
        for nl in astra_input:
            if k in astra_input[nl]:
                found = True
                if verbose:
                    print(k, 'is in astra', nl)
                astra_input[nl][k] = settings[k]
        if not found:
            if k in generator_input:
                found = True
                generator_input[k] = settings[k]
                if verbose:
                    print(k, 'is in generator')
        assert found
        if not found and verbose:
            print(k, 'not found')


def recommended_spacecharge_mesh(n_particles):
    """
    ! --------------------------------------------------------
    ! Suggested Nrad, Nlong_in settings
    !
    ! Nrad = 35,    Nlong_in = 75  !28K
    ! Nrad = 29,    Nlong_in = 63  !20K
    ! Nrad = 20,    Nlong_in = 43  !10K
    ! Nrad = 13,    Nlong_in = 28  !4K
    ! Nrad = 10,    Nlong_in = 20  !2K
    ! Nrad = 8,     Nlong_in = 16  !1K
    !
    ! Nrad ~ round(3.3*(n_particles/1000)^(2/3) + 5)
    ! Nlong_in ~ round(9.2*(n_particles/1000)^(0.603) + 6.5)
    
    """
    if n_particles < 1000:
        # Set a minimum
        nrad = 8
        nlong_in = 16
    else:
        # Prefactors were recalculated from above note. 
        nrad = round(3.3e-2*n_particles**(2/3) + 5)
        nlong_in = round(0.143*n_particles**(0.603) + 6.5)
    return {'nrad':nrad, 'nlong_in':nlong_in}
           
            
def run_astra_with_generator(settings=None, astra_input_file=None, generator_input_file=None, workdir=None, 
                             astra_bin='Astra', generator_bin='generator', timeout=2500, verbose=False,
                             auto_set_spacecharge_mesh=True):
    """
    Run Astra with particles generated by Astra's generator. 
    
        settings: dict with keys that can appear in an Astra or Generator input file. 
    """
    if verbose:
        print('run_astra_with_generator') 

    # Make astra and generator objects
    A = Astra(astra_bin=astra_bin, input_file=astra_input_file, workdir=workdir)
    A.timeout=timeout
    A.verbose = verbose
    G = AstraGenerator(generator_bin=generator_bin, input_file=generator_input_file, sim_path=A.sim_path)
    G.verbose = verbose
    
    # Link particle files
    A.input['newrun']['distribution'] = G.input['fname']
    A.input['newrun']['l_rm_back'] = True # Remove backwards particles
      
    # Set inputs
    if settings:
        set_astra(A.input, G.input, settings, verbose=verbose)
        
        
    if auto_set_spacecharge_mesh:
        n_particles = G.input['ipart']
        sc_settings = recommended_spacecharge_mesh(n_particles)
        A.input['charge'].update(sc_settings)
        if verbose:
            print('set spacecharge mesh for n_particles:', n_particles, 'to', sc_settings)        
    
    # Run
    G.run()
    A.run()
    
    return A
# Usage:
#Aout = run_astra_with_generator(settings={'zstop':2, 'lspch':False}, astra_input_file=ASTRA_TEMPLATE,generator_input_file=GENERATOR_TEMPLATE, astra_bin=ASTRA_BIN, generator_bin=GENERATOR_BIN, verbose=True)                        
        
              
        
def install_astra(dest, source_url='http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/Astra'):
    """
    Simple Astra download
    """
    print('Installing Astra into:', dest)
    urllib.request.urlretrieve(source_url, dest)

def install_generator(dest, source_url='http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/generator'):
    """
    Simple Astra generator download
    """
    print('Installing Astra generator into:', dest)
    urllib.request.urlretrieve(source_url, dest)                 
        
          
  
