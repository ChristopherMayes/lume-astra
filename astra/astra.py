#!/usr/bin/env python3

from . import parsers, writers, tools, archive
from .control import ControlGroup
from .fieldmaps import load_fieldmaps, write_fieldmaps
from .generator import AstraGenerator
from .plot import plot_stats_with_layout, plot_fieldmaps


from pmd_beamphysics import ParticleGroup
from pmd_beamphysics.interfaces.astra import parse_astra_phase_file


import numpy as np

import h5py
import yaml

import tempfile
import shutil
import os, platform
from time import time
import traceback

from copy import deepcopy





class Astra:
    """ 
    Astra simulation object. Essential methods:
    .__init__(...)
    .configure()
    .run()
    
    Input deck is held in .input
    Output data is parsed into .output
    .load_particles() will load particle data into .output['particles'][...]
    
    The Astra binary file can be set on init. If it doesn't exist, configure will check the
        $ASTRA_BIN
    environmental variable.
    
    
    """
    
    def __init__(self,
                 input_file=None,
                 initial_particles = None,
                 astra_bin='$ASTRA_BIN',      
                 use_tempdir=True,
                 workdir=None,
                 group=None,
                 verbose=False):
        # Save init
        self.original_input_file = input_file
        self.initial_particles = initial_particles
        self.use_tempdir = use_tempdir
        self.workdir = workdir
        if workdir:
            assert os.path.exists(workdir), 'workdir does not exist: '+workdir        
        self.verbose=verbose
        self.astra_bin = astra_bin

        
        
        # These will be set
        self.log = []
        self.output = {'stats':{}, 'particles':{}, 'run_info':{}}
        self.timeout=None
        self.error = False
        self.group = {}  # Control Groups
        self.fieldmap = {} # Fieldmaps
        
        # Run control
        self.finished = False
        self.configured = False
        self.using_tempdir = False
        
        # Call configure
        if input_file:
            self.load_input(input_file)
            self.configure()
            
            # Add groups, if any. 
            if group:
                for k, v in group.items():
                    self.add_group(k, **v)               
            
        else:
            self.vprint('Warning: Input file does not exist. Not configured.')
            self.original_input_file = 'astra.in'
      
    
    def add_group(self, name, **kwargs):
        """
        Add a control group. See control.py

        Parameters
        ----------
        name : str
            The group name
        """
        assert name not in self.input, f'{name} not allowed to be overwritten by group.'
        if name in self.group:
            self.vprint(f'Warning: group {name} already exists, overwriting.')
     
        g = ControlGroup(**kwargs)
        g.link(self.input)
        self.group[name] = g
        
        return self.group[name]
    
    
    
    
    def clean_output(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.input_file, run_number)
        for f in outfiles:
            os.remove(f)
            
    def clean_particles(self):
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        phase_files = parsers.find_phase_files(self.input_file, run_number)           
        files   = [x[0] for x in phase_files] # This is sorted by approximate z
        for f in files:
            os.remove(f)
                   
                
    # Convenience routines
    @property
    def particles(self):
        return self.output['particles']
    
    def stat(self, key):
        return self.output['stats'][key]
    

    def particle_stat(self, key, alive_only=True):
        """
        Compute a statistic from the particles.
        
        Alive particles have status == 1. By default, statistics will only be computed on these.
        
        n_dead will override the alive_only flag, 
        and return the number of particles with status < -6 (Astra convention)
        """
        
        
        if key == 'n_dead':
            return np.array([len(np.where(P.status < -6)[0]) for P in self.particles])
        
        if key == 'n_alive':
            return np.array([len(np.where(P.status > -6)[0]) for P in self.particles])
        
        pstats = []
        for P in self.particles:
            if alive_only and P.n_dead > 0:
                P = P.where(P.status==1)
            pstats.append(P[key])
        return np.array(pstats)
    
    def configure(self):
        self.configure_astra(workdir=self.workdir)
 
    def configure_astra(self, input_filePath=None, workdir=None):
        
        if input_filePath:
            self.load_input(input_filePath)
        
        # Check that binary exists
        self.astra_bin = tools.full_path(self.astra_bin)
        assert os.path.exists(self.astra_bin), 'ERROR: Astra binary does not exist:'+self.astra_bin
              
        # Set paths
        if self.use_tempdir:
            # Need to attach this to the object. Otherwise it will go out of scope.
            self.tempdir = tempfile.TemporaryDirectory(dir=workdir)
            self.path = self.tempdir.name
        else:
            # Work in place
            self.path = self.original_path            
        
        
        self.input_file = os.path.join(self.path, self.original_input_file)                
        self.configured = True
    
    
    def load_fieldmaps(self, search_paths=[]):
        """
        Loads fieldmaps into Astra.fieldmap as a dict.
        
        Optionally, a list of paths can be included that will search for these. The default will search self.path.
        """
        
        # Do not consider files if fieldmaps have been loaded. 
        if self.fieldmap:
            strip_path=False
        else:
            strip_path=True
        
        if not search_paths:
            [self.path]
        
        self.fieldmap = load_fieldmaps(self.input, fieldmap_dict=self.fieldmap, search_paths=search_paths, verbose=self.verbose, strip_path=strip_path)
        
    
    def load_initial_particles(self, h5):
        """Loads a openPMD-beamphysics particle h5 handle or file"""
        P = ParticleGroup(h5=h5)
        self.initial_particles = P
    
    def load_input(self, input_filePath, absolute_paths=True):
        f = tools.full_path(input_filePath)
        self.original_path, self.original_input_file = os.path.split(f) # Get original path, filename
        self.input = parsers.parse_astra_input_file(f)            
    
        if absolute_paths:
            parsers.fix_input_paths(self.input, root=self.original_path)
            
    
    def load_output(self, include_particles=True):
        """
        Loads Astra output files into .output
        
        .output is a dict with dicts:
            .stats
            .run_info
            .other
            
        and if include_particles,
            .particles = list of ParticleGroup objects
        
        """
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        outfiles = parsers.find_astra_output_files(self.input_file, run_number)
        
        #assert len(outfiles)>0, 'No output files found'
        
        stats = self.output['stats'] = {}
        
        for f in outfiles:
            type = parsers.astra_output_type(f)
            d = parsers.parse_astra_output_file(f)
            if type in ['Cemit', 'Xemit', 'Yemit', 'Zemit']:
                stats.update(d)
            elif type in ['LandF']:
                self.output['other'] = d
            else:
                raise ValueError(f'Unknown output type: {type}')
        
        # Check that the lengths of all arrays are the same
        nlist = {len(stats[k]) for k in stats}
        
        assert len(nlist)==1, f'Stat keys do not all have the same length: { [len(stats[k]) for k in stats]}'
            
            
        if include_particles:
            self.load_particles()

                
    def load_particles(self, end_only=False):
        # Clear existing particles
        self.output['particles'] = []
        
        # Sort files by approximate z
        run_number = parsers.astra_run_extension(self.input['newrun']['run'])
        phase_files = parsers.find_phase_files(self.input_file, run_number)           
        files   = [x[0] for x in phase_files] # This is sorted by approximate z
        zapprox = [x[1] for x in phase_files]
        
        if end_only: 
            files = files[-1:]
        if self.verbose:
            print('loading '+str(len(files))+ ' particle files')
            print(zapprox)
        for f in files:
            pdat = parse_astra_phase_file(f)
            P = ParticleGroup(data=pdat)
            self.output['particles'].append(P)
        
        
        
        
    def run(self):
        if not self.configured:
            print('not configured to run')
            return
        self.run_astra(verbose=self.verbose, timeout=self.timeout)
        
    
        
    def get_run_script(self, write_to_path=True):
        """
        Assembles the run script. Optionally writes a file 'run' with this line to path.
        
        This expect to run with .path as the cwd. 
        """
        
        _, infile = os.path.split(self.input_file) # Expect to run locally. Astra has problems with long paths.
    
        runscript = [self.astra_bin, infile]
            
        if write_to_path:
            with open(os.path.join(self.path, 'run'), 'w') as f:
                f.write(' '.join(runscript))
            
        return runscript

        
    
    def run_astra(self, verbose=False, parse_output=True, timeout=None):
        """
        Runs Astra
        
        Changes directory, so does not work with threads. 
        """
        
        run_info = self.output['run_info'] = {}
        
        
        t1 = time()
        run_info['start_time'] = t1
      
        # Write all input 
        self.write_input()
        
        runscript = self.get_run_script()
        run_info['run_script'] = ' '.join(runscript)
        
        try:
            if timeout:
                res = tools.execute2(runscript, timeout=timeout, cwd=self.path)
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
                for path in tools.execute(runscript, cwd=self.path):
                    self.vprint(path, end="")
                    log.append(path)
    
            self.log = log
                    
            if parse_output:
                self.load_output()
        except Exception as ex:
            
            err = str(traceback.format_exc())
            
            print('Run Aborted', err)
            self.error = True
            run_info['why_error'] = err
        finally:
            run_info['run_time'] = time() - t1
            run_info['run_error'] = self.error           
        
        self.finished = True
    
        self.vprint(run_info)
        
    def fingerprint(self):
        """
        Data fingerprint using the input. 
        """
        return tools.fingerprint(self.input)
                
    def vprint(self, *args, **kwargs):
        # Verbose print
        if self.verbose:
            print(*args, **kwargs)    
    
    def units(self, key):
        if key in parsers.OutputUnits:
            return parsers.OutputUnits[key]
        else:
            return 'unknown unit'
    

    
    def load_archive(self, h5=None):
        """
        Loads input and output from archived h5 file.
        
        See: Astra.archive
        """
        if isinstance(h5, str):
            h5 = os.path.expandvars(h5)
            g = h5py.File(h5, 'r')
            
            glist = archive.find_astra_archives(g)
            n = len(glist)
            if n == 0:
                # legacy: try top level
                message = 'legacy'
            elif n == 1:
                gname = glist[0]
                message = f'group {gname} from'
                g = g[gname]
            else:
                raise ValueError(f'Multiple archives found in file {h5}: {glist}')
            
            self.vprint(f'Reading {message} archive file {h5}')
        else:
            g = h5
        
        self.input = archive.read_input_h5(g['input'])
        self.output = archive.read_output_h5(g['output'])
        if 'initial_particles' in g:
            self.initial_particles = ParticleGroup(h5=g['initial_particles'])
            
        if 'fieldmap' in g:
            self.fieldmap = archive.read_fieldmap_h5(g['fieldmap'])
            
        if 'control_groups' in g:
            self.group = archive.read_control_groups_h5(g['control_groups'], verbose=self.verbose)             
        
        self.vprint('Loaded from archive. Note: Must reconfigure to run again.')
        self.configured = False   
        
        
        # Re-link groups
        # TODO: cleaner logic
        for _, cg  in self.group.items():
            cg.link(self.input)            
    
        

    def archive(self, h5=None):
        """
        Archive all data to an h5 handle or filename.
        
        If no file is given, a file based on the fingerprint will be created.
        
        """
        if not h5:
            h5 = 'astra_'+self.fingerprint()+'.h5'
         
        if isinstance(h5, str):
            h5 = os.path.expandvars(h5)
            g = h5py.File(h5, 'w')
            self.vprint(f'Archiving to file {h5}')
        else:
            # store directly in the given h5 handle
            g = h5
        
        # Write basic attributes
        archive.astra_init(g)
        
        # Initial particles
        if self.initial_particles:
            self.initial_particles.write(g, name='initial_particles')
    
        # Fieldmaps
        if self.fieldmap:
            archive.write_fieldmap_h5(g, self.fieldmap, name='fieldmap')
    
        # All input
        archive.write_input_h5(g, self.input)
    
        # All output
        archive.write_output_h5(g, self.output)    
        
        # Control groups
        if self.group:
             archive.write_control_groups_h5(g, self.group, name='control_groups')        
        
        return h5

    @classmethod
    def from_archive(cls, archive_h5):
        """
        Class method to return an GPT object loaded from an archive file
        """        
        c = cls()
        c.load_archive(archive_h5)
        return c       
    
    
    @classmethod
    def from_yaml(cls, yaml_file):
        """
        Returns an Astra object instantiated from a YAML config file
        
        Will load intial_particles from an h5 file. 
        
        """
        # Try file
        if os.path.exists(os.path.expandvars(yaml_file)):
            config = yaml.safe_load(open(yaml_file))
            
            # The input file might be relative to the yaml file
            if 'input_file' in config:
                f = os.path.expandvars(config['input_file'])
                if not os.path.isabs(f):
                    # Get the yaml file root
                    root, _ = os.path.split(tools.full_path(yaml_file))
                    config['input_file'] = os.path.join(root, f)
                
        else:
            #Try raw string
            config  = yaml.safe_load(yaml_file)
            
        # Form ParticleGroup from file
        if 'initial_particles' in config:
            f = config['initial_particles']
            if not os.path.isabs(f):
                root, _ = os.path.split(tools.full_path(yaml_file))
                f = os.path.join(root, f)
            config['initial_particles'] = ParticleGroup(f)            
        
        return cls(**config)    
    
    
    def write_fieldmaps(self):
        """
        Writes any loaded fieldmaps to path
        """
        
        if self.fieldmap:
            write_fieldmaps(self.fieldmap, self.path)
            self.vprint(f'{len(self.fieldmap)} fieldmaps written to {self.path}')        
    
    
    def write_input(self):
        """
        Writes all input. If fieldmaps have been loaded, these will also be written. 
        """
        
        if self.initial_particles:
            fname = self.write_initial_particles()
            self.input['newrun']['distribution'] = fname           
    
        self.write_fieldmaps()
        
        self.write_input_file()
        
    
    
    def write_input_file(self):
        
        if self.use_tempdir:
            make_symlinks=True
        else:
            make_symlinks=False
        
        writers.write_namelists(self.input, self.input_file, make_symlinks=make_symlinks, verbose=self.verbose)

    def write_initial_particles(self, fname=None):
        if not fname:
            fname = os.path.join(self.path, 'astra.particles')
        self.initial_particles.write_astra(fname)
        self.vprint(f'Initial particles written to {fname}')
        return fname        
        
    def plot(self, y=['sigma_x', 'sigma_y'], x='mean_z', xlim=None, ylim=None, ylim2=None, y2=[],
            nice=True, 
            include_layout=True,
            include_labels=False, 
            include_particles=True,
            include_legend=True,
            return_figure=False, 
             **kwargs):
        """
        Plots stat output multiple keys.
    
        If a list of ykeys2 is given, these will be put on the right hand axis. This can also be given as a single key. 
    
        Logical switches:
            nice: a nice SI prefix and scaling will be used to make the numbers reasonably sized. Default: True
            
            include_legend: The plot will include the legend.  Default: True
            
            include_particles: Plot the particle statistics as dots. Default: True
            
            include_layout: the layout plot will be displayed at the bottom.  Default: True
            
            include_labels: the layout will include element labels.  Default: False
            
            return_figure: return the figure object for further manipulation. Default: False
                
        If there is no output to plot, the fieldmaps will be plotted with .plot_fieldmaps
        
        """
        
        # Just plot fieldmaps if there are no 
        if not self.output['stats']:
            return plot_fieldmaps(self, xlim=xlim, **kwargs)
            
        
        
        return plot_stats_with_layout(self, ykeys=y, ykeys2=y2, 
                           xkey=x, xlim=xlim, ylim=ylim, ylim2=ylim2,
                           nice=nice, 
                           include_layout=include_layout,
                           include_labels=include_labels, 
                           include_particles=include_particles, 
                           include_legend=include_legend,
                           return_figure=return_figure, 
                           **kwargs)   
        
    def plot_fieldmaps(self, **kwargs):
        return plot_fieldmaps(self, **kwargs)

    def copy(self):
        """
        Returns a deep copy of this object.
        
        If a tempdir is being used, will clear this and deconfigure. 
        """
        A2 = deepcopy(self)
        # Clear this 
        if A2.use_tempdir:
            A2.path = None
            A2.configured = False
        
        return A2       
    
    
    def __getitem__(self, key):
        """
        Convenience syntax to get a header or element attribute. 

        Special syntax:
        
        end_X
            will return the final item in a stat array X
            Example:
            'end_norm_emit_x'
            
        particles:N
            will return a ParticleGroup N from the .particles list
            Example:
                'particles:-1'
                returns the readback of the final particles
        particles:N:Y
            ParticleGroup N's property Y
            Example:
                'particles:-1:sigma_x'
            returns sigma_x from the end of the particles list.

        
        See: __setitem__
        """        
        
        # Object attributes
        if hasattr(self, key):
            return getattr(self, key) 
        
        # Send back top level input (namelist) or group object. 
        # Do not add these to __setitem__. The user shouldn't be allowed to change them as a whole, 
        #   because it will break all the links.
        if key in self.group:
            return self.group[key]
        if key in self.input:
            return self.input[key]        
        
        if key.startswith('end_'):
            key2 = key[len('end_'):]
            assert key2 in self.output['stats'], f'{key} does not have valid output stat: {key2}'
            return self.output['stats'][key2][-1]
                
        if key.startswith('particles:'):
            key2 = key[len('particles:'):]
            x = key2.split(':')
            if len(x) == 1:
                return self.particles[int(x[0])]
            else:
                return self.particles[int(x[0])][x[1]]
        
        # key isn't an ele or group, should have property s
        
        x = key.split(':')
        assert len(x) == 2, f'{x} was not found in group or input dict, so should have : '    
        name, attrib = x[0], x[1]        
          
        # Look in input and group    
        if name in self.input:
            return self.input[name][attrib] 
        elif name in self.group:
            return self.group[name][attrib]  
        
    def __setitem__(self, key, item):
        """
        Convenience syntax to set namelist or group attribute. 
        attribute_string should be 'header:key' or 'ele_name:key'
        
        Examples of attribute_string: 'header:Np', 'SOL1:solenoid_field_scale'
        
        Settable attributes can also be given:
        
        ['stop'] = 1.2345 will set Impact.stop = 1.2345
        
        """

        # Set attributes
        if hasattr(self, key):
            setattr(self, key, item)
            return
        
        # Must be in input or group
        name, attrib = key.split(':')
        if name in self.input:
            self.input[name][attrib] = item
        elif name in self.group:
            self.group[name][attrib]  = item
        else:
            raise ValueError(f'{name} does not exist in eles or groups of the Impact object.')            
           


        
def set_astra(astra_object, generator_input, settings, verbose=False):
    """
    Searches astra and generator objects for keys in settings, and sets their values to the appropriate input
    """
    astra_input = astra_object.input # legacy syntax
    
    for k, v in settings.items():
        found = False
        
        # Check for direct settable attribute
        if ':' in k:
            astra_object[k] = v
            continue
        
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
        
        if not found and verbose:
            print(k, 'not found')
        assert found    


def recommended_spacecharge_mesh(n_particles):
    """
    ! --------------------------------------------------------
    ! Suggested Nrad, Nlong_in settings from:
    !    A. Bartnik and C. Gulliford (Cornell University)
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
    !
    ! 
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
           
    
    
def run_astra(settings=None, 
              astra_input_file=None, 
              workdir=None, 
              astra_bin='$ASTRA_BIN', 
              timeout=2500, 
              verbose=False):
    """
    Run Astra. 
    
        settings: dict with keys that can appear in an Astra input file. 
    """
    if verbose:
        print('run_astra') 

    # Make astra object
    A = Astra(astra_bin=astra_bin, input_file=astra_input_file, workdir=workdir)
    
    A.timeout=timeout
    A.verbose = verbose
    
    A.input['newrun']['l_rm_back'] = True # Remove backwards particles
      
    # Set inputs
    if settings:
        set_astra(A, {}, settings, verbose=verbose)
            
    # Run
    A.run()
    
    return A  
    
            
def run_astra_with_generator(settings=None,
                             astra_input_file=None,
                             generator_input_file=None,
                             workdir=None, 
                             astra_bin='$ASTRA_BIN',
                             generator_bin='$GENERATOR_BIN',
                             timeout=2500, verbose=False,
                             auto_set_spacecharge_mesh=True):
    """
    Run Astra with particles generated by Astra's generator. 
    
        settings: dict with keys that can appear in an Astra or Generator input file. 
    """

    assert astra_input_file, 'No astra input file'
    
    # Call simpler evaluation if there is no generator:
    if not generator_input_file:
        return run_astra(settings=settings, 
                         astra_input_file=astra_input_file, 
                         workdir=workdir,
                         astra_bin=astra_bin, 
                         timeout=timeout, 
                         verbose=verbose)
        
    
    if verbose:
        print('run_astra_with_generator') 

    # Make astra and generator objects
    A = Astra(astra_bin=astra_bin, input_file=astra_input_file, workdir=workdir)
    A.timeout=timeout
    A.verbose = verbose
    G = AstraGenerator(generator_bin=generator_bin, input_file=generator_input_file, workdir=workdir)
    G.verbose = verbose
    
    A.input['newrun']['l_rm_back'] = True # Remove backwards particles
      
    # Set inputs
    if settings:
        set_astra(A, G.input, settings, verbose=verbose)
            
    if auto_set_spacecharge_mesh:
        n_particles = G.input['ipart']
        sc_settings = recommended_spacecharge_mesh(n_particles)
        A.input['charge'].update(sc_settings)
        if verbose:
            print('set spacecharge mesh for n_particles:', n_particles, 'to', sc_settings)        
    
    # Run Generator
    G.run()     
    A.initial_particles = G.output['particles']
    A.run()
    if verbose:
        print('run_astra_with_generator finished')     
    
    return A
# Usage:
#Aout = run_astra_with_generator(settings={'zstop':2, 'lspch':False}, astra_input_file=ASTRA_TEMPLATE,generator_input_file=GENERATOR_TEMPLATE, astra_bin=ASTRA_BIN, generator_bin=GENERATOR_BIN, verbose=True)                        
        
              
        
          
        
          
  
