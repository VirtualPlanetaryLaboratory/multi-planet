Running Multi-Planet
====================

To run `multi-planet` on a large number of simulations, first run `vspace` to
create the simulation folders. Then, in that same directory, type:

.. code-block:: bash

    multi-planet <input file> -c [number of cores] -q -bp -m [email]

Where the "input file" **must be the same file** used with `vspace`. You can
specify the number of cores, but the default is the maximum number of cores.

There are three optional arguments for multi-planet:
 :code:`-q`: there will be no output in the command line
 :code:`-bp`: bigplanet will be ran in conjuction with multi-planet. See the
       `bigplanet documentation <https://github.com/VirtualPlanetaryLaboratory/bigplanet>` for more information
 `-m`: emails the users at `email` when the simulations are complete

Should your run be interrupted for whatever reason, just run `multi-planet` again and it should restart where it left off.

Checking the status of the Multi-Planet Simulations
===================================================

To check the status of your simulations, type

.. code-block:: bash

    mpstatus <input file>

where the "input file" **must be the same file** used with :code:`vspace` and code:`multi-planet`.
The following will be printed to the command line:

.. code-block:: bash

    --Multi-Planet Status--
    Number of Simulations completed: 10
    Number of Simulations in progress: 5
    Number of Simulations remaining: 20
    
but with the proper statistics shown.
