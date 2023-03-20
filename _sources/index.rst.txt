MultiPlanet Documentation
=======

``multi-planet`` manages the exectution of a suite of `VPLanet <https://github.com/VirtualPlanetaryLaboratory/multi-planet>`_
simulations that were built with `VSPACE <https://github.com/VirtualPlanetaryLaboratory/vspace>`_.
``multi-planet`` performs simulations across multi-core computers and can be used to restart jobs that fail for any reason.
This repository also includes ``mpstatus``, which returns the current status of the parameter sweep.

.. toctree::
   :maxdepth: 1

   install
   help
   mpstatus
   GitHub <https://github.com/VirtualPlanetaryLaboratory/multi-planet>

.. note::

    To maximize MultiPlanet's power, run ``VSPACE`` with the ``-bp`` option to automatically
    build the `BigPlanet <https://github.com/VirtualPlanetaryLaboratory/bigplanet>`_ archive 
    immediately after the simulations finish.  Then create  BigPlanet files from the 
    archive as needed, and use ``BigPlanet``'s scripting functions to 
    extract vectors and matrices for plotting, statistical analyses, etc.

