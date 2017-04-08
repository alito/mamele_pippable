from __future__ import print_function

import multiprocessing
import os
import subprocess
import sys
from distutils.command.build import build as DistutilsBuild

from setuptools import setup
from setuptools.command.install import install as SetuptoolsInstall
from setuptools.command.sdist import sdist as SetuptoolsSdist

MaxCPUs = 4

current_directory = os.path.dirname(__file__)
bindings_directory = os.path.join(current_directory, 'mamele', 'mamele_src', 'learning_environment', 'example_agents')
mame_binary_directory = os.path.join(current_directory, 'mamele', 'mamele_src')

package_data = [
    'mamele_src/mame64',
    'mamele_src/learning_environment/example_agents/pythonbinding.so',
    'mamele_src/learning_environment/gameover_description.txt',
    'mamele_src/learning_environment/score_description.txt',
    ]


class Build(DistutilsBuild):
    def run(self):
        cores_to_use = min(MaxCPUs, max(1, multiprocessing.cpu_count() - 1))

        print("Compiling MAME, this takes a while", file=sys.stderr)
        # Compile main MAME
        cmd = ['make', '-C', mame_binary_directory, '-j', str(cores_to_use)]
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            print("Could not build mamele: %s." % e, file=sys.stderr)
            raise
        except OSError as e:
            print("Unable to execute '{}'. HINT: are you sure `make` is installed?".format(' '.join(cmd)), file=sys.stderr)
            raise

        # Compile Python bindings
        cmd = ['make', '-C', bindings_directory , '-j', str(cores_to_use)]
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            print("Could not build mamele's Python bindings: %s." % e, file=sys.stderr)
            raise
        except OSError as e:
            print("Unable to execute '{}'. HINT: are you sure `make` is installed?\n".format(' '.join(cmd)), file=sys.stderr)
            raise

        DistutilsBuild.run(self)

class Install(SetuptoolsInstall):
    def run(self):
        SetuptoolsInstall.run(self)
        print("Put your ROMs under ~/.le/roms or make that directory a link to your ROM collection", file=sys.stderr)


class Sdist(SetuptoolsSdist):
    def make_distribution(self):
        # Exclude the binaries
        self.filelist.exclude_pattern('mamele/mamele_src/mame64')
        self.filelist.exclude_pattern('mamele_src/learning_environment/example_agents/pythonbinding.so')
        SetuptoolsSdist.make_distribution(self)

setup(name='mamele',
      version='0.4.1.183',
      description='Python bindings to MAME games',
      long_description='This is a Python wrapper around mamele, a framework for putting computer programs as players of games supported by MAME',
      url='https://github.com/alito/mamele_pippable',
      author='Alejandro Dubrovsky',
      author_email='alito@organicrobot.com',
      license='GPL-v2,BSD-3',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',

      ],
      packages=['mamele'],
      package_data={ 'mamele' : package_data },
      data_files=[('share/mamele/examples', ['examples/randomplayer.py'])],
      cmdclass={'build': Build, 'install' : Install, 'sdist' : Sdist},
      install_requires=['numpy', 'pillow'],
      zip_safe=False,
      tests_require=[],
)
