# lume-astra
Python wrapper for Astra (A Space Charge Tracking Algorithm, DESY) for use in LUME

[Astra website](http://www.desy.de/~mpyflo/)



## Installation
Clone this repository to `/path/to/lume-astra`, and add that to your path:

`export PYTHONPATH=/path/to/lume-astra:$PYTHONPATH`

For convenience, you can set `$ASTRA_BIN` and `$GENERATOR_BIN` to point to the Astra and generator binaries for your system. See the [install_astraipynb](./examples/install_astra.ipynb) example for easy installation.


## Basic usage

See [simple_astra_run.ipynb](./examples/simple_astra_run.ipynb). In short:

```python
from astra import Astra

A = Astra('../templates/Astra.in', workdir='work')

A.verbose = True
A.run()
...
output = A.output
```


