#!/usr/bin/env python3

import os
import traceback

from lume import tools as lumetools
from lume.base import CommandWrapper
from astra import archive
from pmd_beamphysics import ParticleGroup
from pmd_beamphysics.interfaces.astra import parse_astra_phase_file
import h5py

from astra import parsers, writers, tools


class AstraGenerator(CommandWrapper):
    """
    Class to run Astra's particle generator
    
    
    The file for Astra is written in:
    .output_file

    """
    COMMAND = "$GENERATOR_BIN"

    def __init__(self, input_file=None, **kwargs):
        super().__init__(input_file=input_file, **kwargs)
        # Save init
        
        if isinstance(input_file, str):
            self.original_input_file = self.input_file
        else:
            self.original_input_file = 'generator.in'
            
        # These will be filled
        self.input = {}
        self.output = {}

        # Call configure
        if self.input_file:
            self.load_input(self.input_file)
            self.configure()

    def load_input(self, input_filepath, absolute_paths=True, **kwargs):
        # Allow dict
        if isinstance(input_filepath, dict):
            self.input = input_filepath
            return
    
        super().load_input(input_filepath, **kwargs)
        if absolute_paths:
            parsers.fix_input_paths(self.input, root=self.original_path)
        self.input = self.input['input']
            
            
    def input_parser(self, path):
        return parsers.parse_astra_input_file(path)

    def configure(self):
        # Check that binary exists
        self.command = lumetools.full_path(self.command)
        self.setup_workdir(self.path)

        self.input_file = os.path.join(self.path, self.original_input_file)

        # We will change directories to work in the local directory
        self.input['fname'] = 'generator.part'

        self.configured = True

    def run(self):
        """
        Runs Generator
        
        Note: do not use os.chdir
        """
        self.write_input_file()

        runscript = self.get_run_script()

        try:
            res = tools.execute2(runscript, timeout=None, cwd=self.path)
            self.log = res['log']

            self.vprint(self.log)

            # This is the file that should be written
            if os.path.exists(self.output_file):
                self.finished = True
            else:
                print(f'AstraGenerator.output_file {self.output_file} does not exist.')
                print(f'Here is what the current working dir looks like: {os.listdir(self.path)}')
            self.load_output()

        except Exception as ex:
            print('AstraGenerator.run exception:', traceback.format_exc())
            self.error = True
        finally:
            pass

    @property
    def output_file(self):
        return os.path.join(self.path, self.input['fname'])

    def load_output(self):
        pfile = self.output_file
        data = parse_astra_phase_file(pfile)
        # Clock time is used when at cathode
        data['t'] = data['t_clock']
        P = ParticleGroup(data=data)

        self.output['particles'] = P

    def write_input_file(self):
        writers.write_namelists({'input': self.input}, self.input_file)

    # Methods from CommandWrapper not implemented here
    def archive(self, h5=None):
        """
        Archive all data to an h5 handle or filename.

        If no file is given, a file based on the fingerprint will be created.

        """
        if not h5:
            h5 = 'astra_generator_' + self.fingerprint() + '.h5'

        if isinstance(h5, str):
            h5 = os.path.expandvars(h5)
            g = h5py.File(h5, 'w')
            self.vprint(f'Archiving to file {h5}')
        else:
            # store directly in the given h5 handle
            g = h5

        # Write basic attributes
        archive.astra_init(g)

        # All input
        g2 = g.create_group('generator_input')
        for k, v in self.input.items():
            g2.attrs[k] = v
            
        return h5
    
    def load_archive(self, h5, configure=True):
        """
        Loads input and output from archived h5 file.
        """
        if isinstance(h5, str):
            h5 = os.path.expandvars(h5)
            g = h5py.File(h5, 'r')  
        else:
            g = h5
            
        attrs = dict(g['generator_input'].attrs)
        self.input = {}
        for k, v, in attrs.items():
            self.input[k] = tools.native_type(v)
        
        if configure:
            self.configure()        
        

    def plot(self, y=..., x=None, xlim=None, ylim=None, ylim2=None, y2=..., nice=True, include_layout=True, include_labels=False, include_particles=True, include_legend=True, return_figure=False):
        return super().plot(y=y, x=x, xlim=xlim, ylim=ylim, ylim2=ylim2, y2=y2, nice=nice, include_layout=include_layout, include_labels=include_labels, include_particles=include_particles, include_legend=include_legend, return_figure=return_figure)

    def write_input(self, input_filename):
        return super().write_input(input_filename)
