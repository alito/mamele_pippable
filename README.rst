======
mamele
======

This is a thin Python wrapper around mamele https://github.com/alito/mamele
It lets you treat mamele as a Python module instead of calling mame manually and dealing with all the path
and subprocess issues. Balancing out this convenience, this method of calling mamele is much slower
since the data is transferred through a pipe between processes, instead of it being handed over
to another section of the same process.

You need to put your roms under ~/.le/roms or to make that a link to your ROM collection for them to be
available. Some ROMs are available from the MAME Dev page: http://mamedev.org/roms/



Common installation issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

pip install "hangs"
-------------------

It probably isn't hanging. It just takes a long time (ie many hours). It is
compiling mame. Run it in verbose mode (-v) to see what it's doing. If it 
is actually hanging, then create an issue in the GitHub tracker.

pip install fails
-----------------

If you run it with -v, you should be able to scroll up to try to find what failed. pip install compiles 
mame, so you'll likely need quite a few dev packages. For Ubuntu, you'll need at least mesa-common-dev 
and libsdl2-ttf-dev. This last one will pull in a lot of other required dependencies.


