from .astra import *
from .evaluate import evaluate_astra_with_generator

import os
# Used to access data directory
root, _ = os.path.split(__file__)
template_dir = os.path.join(root, '../templates/')