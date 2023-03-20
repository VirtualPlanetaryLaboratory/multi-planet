Installation Guide
==================

There are two ways to install ``MultiPlanet``: 1) in conjunction with
`VPLanet <https://github.com/VirtualPlanetaryLaboratory/vplanet>`_ and
its other support scripts, or 2) from source.

To install MultiPlanet and the other ``VPLanet`` packages, use the command:

.. code-block:: bash

    python -m pip install vplanet

To install from source, first close the repo:

.. code-block:: bash

    git clone https://github.com/VirtualPlanetaryLaboratory/multi-planet.git

and then go into the directory (MultiPlanet) and run the setup script:

.. code-block:: bash

    cd multi-planet/
    python setup.py install

The setup script installs the various dependencies, creates the ``MultiPlanet`` and ``mpstatus``
executables, and adds them to your PATH.
