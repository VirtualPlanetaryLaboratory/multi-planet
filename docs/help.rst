Running MultiPlanet
====================

To run :code:`MultiPlanet` on a large number of simulations, first run :code:`VSPACE` to
create the simulation folders. Then, in that same directory, type:

.. code-block:: bash

    multiplanet <input file> -c [number of cores] -q -bp -m [email]

Where the "input file" **must be the same file** used with :code:`VSPACE`. You can
specify the number of cores, but the default is the maximum number of cores.

There are three optional arguments for ``MultiPlanet``:

:code:`-q`: there will be no output in the command line

 :code:`-bp`: `BigPlanet`_ will be ran in conjunction with MultiPlanet.

 .. BigPlanet: https://github.com/VirtualPlanetaryLaboratory/bigplanet

:code:`-m`: emails the users at :code:`email` when the simulations are complete


``MultiPlanet`` keeps track of the status of the parameter sweep. Should the run halt 
early for any reason,  simply run ``MultiPlanet`` again it will restart all the simulations
that crashed and continue on with the parameter sweep. You can also check the status
of the parameter sweep with `mpstatus <mpstatus>`_.
