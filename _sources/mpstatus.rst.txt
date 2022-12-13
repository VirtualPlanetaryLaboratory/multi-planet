Checking the status of the MultiPlanet Simulations
===================================================

To check the status of your simulations, type

.. code-block:: bash

    mpstatus <input file>

where the "input file" **must be the same file** used with :code:`VSPACE` and :code:`MultiPlanet`.
The following will be printed to the command line:

.. code-block:: bash

    --MultiPlanet Status--
    Number of Simulations completed: 10
    Number of Simulations in progress: 5
    Number of Simulations remaining: 20

but with the instantaneous statistics shown.

.. warning::

    If you decide to *rerun* a parameter sweep, you must delete the checkpoint file! 
    The name of this file is ``.sDestFolder``, where sDestFolder is the option in :code:`VSPACE`
    the provdes the name for the directory that contains the simulations. If you do not delete
    this file, the :code:`MultiPlanet` will conclude your sweep has finished and will not restart
    the simulations.
