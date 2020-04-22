from setuptools import setup, find_packages
from os import path, environ

cur_dir = path.abspath(path.dirname(__file__))

with open(path.join(cur_dir, 'requirements.txt'), 'r') as f:
    requirements = f.read().split()



setup(
    name='lume-astra',
    version = '0.4.0',
    packages=find_packages(),  
    package_dir={'xopt':'xopt'},
    url='https://github.com/ChristopherMayes/lume-astra',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=requirements,
    include_package_data=True,
    python_requires='>=3.6'
)
