======
mamele
======

This is a thin Python wrapper around mamele https://github.com/alito/mamele
It lets you treat mamele as a Python module instead of calling mame manually and dealing with all the path
and subprocess issues. Balancing out this convenience, this method of calling mamele is much slower
since the data is transferred through a pipe between processes, instead of it being handed over
to another section of the same process.

You need to put your roms under ~/.le/roms or to make that a link to your ROM collection for them to be
available.
