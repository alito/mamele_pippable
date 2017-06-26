from __future__ import print_function

import multiprocessing
import os
import subprocess
import sys
from distutils.command.build import build as DistutilsBuild

from setuptools import setup
from setuptools.command.install import install as SetuptoolsInstall
from setuptools.command.sdist import sdist as SetuptoolsSdist

# The makefile used in the mamele package isn't quite correct I think, 
# so having a high level of concurrency in the build process sometimes 
# leads it to fail
MaxCPUs = 4

# tag to request
mamele_version = 'v4.2.183'

current_directory = os.path.dirname(__file__)
module_directory = os.path.join(current_directory, 'mamele')
mamele_versioned = os.path.join(module_directory, 'mamele_%s' % mamele_version)
mamele_base_directory = os.path.join(module_directory, 'mamele_real')
bindings_directory = os.path.join(mamele_base_directory, 'learning_environment', 'example_agents')
description_file_directory = os.path.join(mamele_base_directory, 'learning_environment')
mame_binary_directory = mamele_base_directory

def module_relative(path):
    return os.path.relpath(path, module_directory)

package_data = [
    module_relative(os.path.join(mamele_base_directory, 'mame64')),
    module_relative(os.path.join(bindings_directory, 'pythonbinding.so')),
    module_relative(os.path.join(description_file_directory, 'gameover_description.txt')),
    module_relative(os.path.join(description_file_directory, 'score_description.txt')),
    ]


class Build(DistutilsBuild):
    def run(self):

        # Do a checkout of the relevant mamele directory and compile it
        # Ugly af I know, but the combination of PyPI's 60MB limit and pip's
        # increasing reticence to installing anything from outside of PyPI
        # don't leave me many choices.
        # If you know of a way around it, please tell. The main requirement
        # is that 'pip install <name>' should work where name can be 
        # 'mamele' or some URL, and that 'pip install .[mame]' work from gym
        # (https://github.com/openai/gym)

        if not os.path.exists(mamele_versioned):
            # do a shallow clone
            git_command = ['git', 'clone', '-b', mamele_version, '--depth', '1', 'https://github.com/alito/mamele.git', mamele_versioned]
            try:
                subprocess.check_call(git_command)
            except subprocess.CalledProcessError as e:
                print("Could not do a git clone of the mamele source: %s." % e, file=sys.stderr)
                raise
            except OSError as e:
                print("Unable to execute '{}'. You need to have a working 'git' command for this to work".format(" ".join(git_command)), file=sys.stderr)
                raise

        if os.path.lexists(mamele_base_directory):
            if os.path.islink(mamele_base_directory) and not os.path.abspath(os.readlink(mamele_base_directory)) != os.path.abspath(mamele_versioned):
                # Assume we are pointing to an outdated version
                # Remove and relink
                os.remove(mamele_base_directory)
                os.symlink(os.path.relpath(mamele_versioned, os.path.dirname(mamele_base_directory)), mamele_base_directory)
            # if it is not a link, we can assume the user knows better
        else:
            os.symlink(os.path.relpath(mamele_versioned, os.path.dirname(mamele_base_directory)), mamele_base_directory)


        cores_to_use = min(MaxCPUs, max(1, multiprocessing.cpu_count() - 1))

        print("Compiling MAME, this takes a while", file=sys.stderr)
        # Compile main MAME
        cmd = ['make', '-C', mamele_base_directory, '-j', str(cores_to_use)]
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
    """
    Exclude the package data from the sdist
    """
    def make_distribution(self):
        # Exclude the binaries
        for filename in package_data:
            self.filelist.exclude_pattern(os.path.join('mamele', filename))
        SetuptoolsSdist.make_distribution(self)


setup(name='mamele',
      version='4.2.183',
      description='Python bindings to MAME games',
      long_description='This is a Python wrapper around mamele, a framework for putting computer programs as players of games supported by MAME',
      url='https://github.com/alito/mamele_pippable',
      download_url='https://github.com/alito/mamele_pippable/releases',
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
