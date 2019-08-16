#!/usr/bin/env python3

from astra import parsers, tools, writers

import urllib.request
import tempfile
import shutil
import os
from time import time




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
    
    def __init__(self,
                 input_file='astra.in',
                 astra_bin='$ASTRA_BIN',      
                 workdir=None,
                 path = None, # Actual simulation path. If set on init, will not make a temporary directory. 
                 verbose=False):
        # Save init
        self.original_input_file = input_file
        self.workdir = workdir
        self.verbose=verbose
        self.astra_bin = astra_bin
        self.path = path
        
        # These will be set
        self.log = []
        self.output = {}
        self.screen = [] # list of screens
        self.auto_cleanup = True
        self.timeout=None
        self.error = False
        
        # Run control
        self.finished = False
        self.configured = False
        self.using_tempdir = False
        
        # Call configure
        if input_file:
            self.load_input(input_file)
            self.configure()
        else:
            self.vprint('Warning: Input file does not exist. Not configured.')
    
    
    def __del__(self):
        if self.auto_cleanup:
            self.clean() # clean directory before deleting

    def clean(self, override=False):   
        # Only remove temporary directory. Never delete anything else!!!
        if (self.using_tempdir or override) and os.path.exists(self.path):
            self.vprint('deleting: ', self.path)
            shutil.rmtree(self.path)
        else: 
            self.vprint('Warning: no cleanup because path is not a temporary directory:', self.path)
            
    def clean_output(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.sim_input_file, run_number)
        for f in outfiles:
            os.remove(f)
            
    def clean_screens(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        phase_files = parsers.find_phase_files(self.input_file, run_number)           
        files   = [x[0] for x in phase_files] # This is sorted by approximate z
        for f in files:
            os.remove(f)
                   
    #@property
    #def run_number(self):
    #    return self.input['newrun']['run']
        
    def configure(self):
        self.configure_astra(workdir=self.workdir)
 
    def configure_astra(self, input_filePath=None, workdir=None):
        
        if input_filePath:
            self.load_input(input_filePath)
        
        # Check that binary exists
        self.astra_bin = tools.full_path(self.astra_bin)
        assert os.path.exists(self.astra_bin), 'ERROR: Astra binary does not exist:'+self.astra_bin
                
        # Temporary directory for path
        if not self.path:
            self.path = os.path.abspath(tempfile.TemporaryDirectory(prefix='temp_', dir=workdir).name)
           # os.mkdir(self.path)
            # Copy everything in original_path
            shutil.copytree(self.original_path, self.path, symlinks=True)
            # Form input file
            self.input_file = os.path.join(self.path, self.original_input_file)
            self.using_tempdir = True
        else:
            # Work in place
            self.input_file = os.path.join(self.path, 'temp_'+self.original_input_file)
            self.using_tempdir = False            
                        
        self.configured = True
    
    
    def load_input(self, input_filePath, absolute_paths=True):
        f = tools.full_path(input_filePath)
        self.original_path, self.original_input_file = os.path.split(f) # Get original path, filename
        self.input = parsers.parse_astra_input_file(f)            
    
        if absolute_paths:
            parsers.fix_input_paths(self.input, root=self.original_path)
    
    
    def load_output(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.input_file, run_number)
        
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
        phase_files = parsers.find_phase_files(self.input_file, run_number)           
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
        
        

        
    def get_run_script(self, write_to_path=True):
        """
        Assembles the run script. Optionally writes a file 'run' with this line to path.
        """
        
        _, infile = os.path.split(self.input_file)
        
        runscript = [self.astra_bin, infile]
            
        if write_to_path:
            with open(os.path.join(self.path, 'run'), 'w') as f:
                f.write(' '.join(runscript))
            
        return runscript

        
    
    def run_astra(self, verbose=False, parse_output=True, timeout=None):

        
        run_info = {}
        t1 = time()
        run_info['start_time'] = t1
        
        # Move to local directory

        # Save init dir
        init_dir = os.getcwd()
        self.vprint('init dir: ', init_dir)
        
        os.chdir(self.path)
        # Debugging
        self.vprint('running astra in '+os.getcwd())

        # Write input file from internal dict
        self.write_input_file()
        
        runscript = self.get_run_script()
    
        try:
            if timeout:
                res = tools.execute2(runscript, timeout=timeout)
                log = res['log']
                self.error = res['error']
                run_info['why_error'] = res['why_error']
                # Log file must have this to have finished properly
                if log.find('finished simulation') == -1:
                    run_info['error'] = True
                    run_info.update({'error': True, 'why_error': "Couldn't find finished simulation"})
    
            else:
                # Interactive output, for Jupyter
                log = []
                for path in tools.execute(runscript):
                    self.vprint(path, end="")
                    log.append(path)
    
            self.log = log
                    
            if parse_output:
                self.load_output()
        except Exception as ex:
            print('Run Aborted', ex)
            self.error = True
            run_info['why_error'] = str(ex)
        finally:
            run_info['run_time'] = time() - t1
            run_info['run_error'] = self.error
            
            # Add run_info
            self.output.update(run_info)
            
            # Return to init_dir
            os.chdir(init_dir)                        
        
        self.finished = True
    
    def fingerprint(self):
        """
        Data fingerprint using the input. 
        """
        return tools.fingerprint(self.input)
                
    def vprint(self, *args, **kwargs):
        # Verbose print
        if self.verbose:
            print(*args, **kwargs)    
    
    
    def write_input_file(self):
        parsers.write_namelists(self.input, self.input_file)
        
    # h5 writing
    def write_input(self, h5):
        writers.write_input_h5(h5, self.input)
    
    def write_output(self, h5):
        writers.write_output_h5(h5, self.output)
        
    def write_screens(self, h5):
        writers.write_screens_h5(h5, self.screen)        
        
    def archive(self, h5):
        """
        Archive all data to an h5 handle. 
        """
        
        # All input
        self.write_input(h5)

        # All output
        self.write_output(h5)
            
        # Particles    
        self.write_screens(h5)          
        

        
        

           

  
class AstraGenerator:
    """
    Class to run Astra's particle generator
    
    """
    def __init__(self, 
                 generator_bin = '$GENERATOR_BIN',
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
        
        # Check that binary exists
        self.generator_bin = tools.full_path(self.generator_bin)
        assert os.path.exists(self.generator_bin), 'ERROR: Generator binary does not exist:'+self.generator_bin
        
                
       
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
                             astra_bin='$ASTRA_BIN', generator_bin='$GENERATOR_BIN', timeout=2500, verbose=False,
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
    G = AstraGenerator(generator_bin=generator_bin, input_file=generator_input_file, sim_path=A.path)
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
        
          
  
