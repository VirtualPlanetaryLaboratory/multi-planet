Running Multi-Planet
====================

To run :code:`multi-planet` on a large number of simulations, first run :code:`vspace` to
create the simulation folders. Then, in that same directory, type:

.. code-block:: bash

    multi-planet <input file> -c [number of cores] -q -bp -m [email]

Where the "input file" **must be the same file** used with :code:`vspace`. You can
specify the number of cores, but the default is the maximum number of cores.

There are three optional arguments for multi-planet:

 :code:`-q`: there will be no output in the command line

 :code:`-bp`: `bigplanet`_ will be ran in conjunction with multi-planet.

 .. _bigplanet: https://github.com/VirtualPlanetaryLaboratory/bigplanet

 :code:`-m`: emails the users at :code:`email` when the simulations are complete

Should your run be interrupted for whatever reason, just run `multi-planet` again and it should restart where it left off.
