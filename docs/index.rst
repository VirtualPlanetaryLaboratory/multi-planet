multi-planet Documentation
==========================

``multi-planet`` manages the exectution of a suite of `VPLanet https://github.com/VirtualPlanetaryLaboratory/multi-planet>`_
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

    To maximize ``multi-planet``'s power, run ``vspace`` and ``mulit-planet -bp`` to automatically
    build a bigplanet archive immediately after the simulations finish.  Then create 
    bigplanet files from the archive as needed, and use ``bigplanet``'s scripting functions to 
    extract vectors and matrices for plotting, statistical analyses, etc.