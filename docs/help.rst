Running MultiPlanet
====================

To run :code:`MultiPlanet` on a large number of simulations, first run :code:`VSPACE` to
create the simulation folders. Then, in that same directory, type:

.. code-block:: bash

    multiplanet <input file> -c [number of cores] -q -bp -m [email]

Where the "input file" **must be the same file** used with :code:`VSPACE`. You can
specify the number of cores, but the default is the maximum number of cores.

There are three optional arguments for :code:`MultiPlanet`:

:code:`-q`: there will be no output in the command line

 :code:`-bp`: `BigPlanet`_ will be ran in conjunction with :code:`MultiPlanet`.

 .. BigPlanet: https://github.com/VirtualPlanetaryLaboratory/bigplanet

:code:`-m`: emails the users at :code:`email` when the simulations are complete

:code:`MultiPlanet` keeps track of the status of the parameter sweep. Should the run halt 
early for any reason,  simply run :code:`MultiPlanet` again it will restart all the simulations
that crashed and continue on with the parameter sweep. You can also check the status
of the parameter sweep with `mpstatus <mpstatus>`_.

.. warning::

    If you decide to *rerun* a parameter sweep, you must delete the checkpoint file! 
    The name of this file is ``.sDestFolder``, where sDestFolder is the option in :code:`VSPACE`
    the provdes the name for the directory that contains the simulations. If you do not delete
    this file, the :code:`MultiPlanet` will conclude your sweep has finished and will not restart
    the simulations.