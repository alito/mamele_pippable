#!/usr/bin/env python2

"""
All of this just because git encodes UTF-8 in escaped code format and setuptools wants them in whatever
non-normalised form is called
"""

import os
import sys
import logging
import subprocess
import codecs

base_directory = os.path.abspath(os.path.dirname(__file__))

def main(args):
    src_directory = os.path.join(base_directory, 'mamele', 'mamele_src')

    command = 'git ls-tree -r master --name-only'
    try:
        output = subprocess.check_output(command.split(), cwd=src_directory, close_fds=True)
    except subprocess.CalledProcessError as error:
        logging.error("Failed to call '%s': %s. Do you have git installed?" % (command, error))
        raise

    with codecs.open(os.path.join(base_directory, 'MANIFEST.in'), 'w', 'utf-8') as manifest_file:
        for line in output.splitlines():
            if line.startswith('"'):
                # aha, normalised
                decoded = line[1:-1].decode('string_escape').decode('utf-8')
            else:
                decoded = line.decode('utf-8')
            decoded = decoded.replace(' ', '?')  # because there's no way to quote a space
            manifest_file.write('include mamele/mamele_src/')
            manifest_file.write(decoded)
            manifest_file.write('\n')

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))