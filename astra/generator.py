#!/usr/bin/env python3

import os
import traceback

from lume import tools as lumetools
from lume.base import CommandWrapper
from pmd_beamphysics import ParticleGroup

from astra import parsers, writers, tools


class AstraGenerator(CommandWrapper):
    """
    Class to run Astra's particle generator
    
    
    The file for Astra is written in:
    .output_file

    """
    COMMAND = "$GENERATOR_BIN"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Save init
        self.original_input_file = self.input_file

        # These will be filled
        self.input = {}
        self.output = {}

        # Call configure
        if self.input_file:
            self.load_input(self.input_file)
            self.configure()

    def load_input(self, input_filepath, absolute_paths=True):
        f = lumetools.full_path(input_filepath)
        self.original_path, self.original_input_file = os.path.split(f)  # Get original path, filename
        self.input = parsers.parse_astra_input_file(f)['input']

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
                print('AstraGenerator.output_file {self.output_file} does not exist.')
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
        data = parsers.parse_astra_phase_file(pfile)
        # Clock time is used when at cathode
        data['t'] = data['t_clock']
        P = ParticleGroup(data=data)

        self.output['particles'] = P

    def write_input_file(self):
        writers.write_namelists({'input': self.input}, self.input_file)
