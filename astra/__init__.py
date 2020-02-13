from .astra import *
from .generator import AstraGenerator
from .evaluate import evaluate_astra_with_generator, evaluate_astra_with_distgen
from .astra_distgen import run_astra_with_distgen

import os
# Used to access data directory
root, _ = os.path.split(__file__)
template_dir = os.path.join(root, '../templates/')