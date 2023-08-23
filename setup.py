# -*- coding: utf-8 -*-
import os

from setuptools import setup

# Setup!
setup(
    name="multiplanet",
    description="VPLANET parameter sweep helper",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/VirtualPlanetaryLaboratory/multi-planet",
    author="Caitlyn Wilhelm",
    author_email="cwilhelm@uw.edu",
    license="MIT",
    packages=["multiplanet"],
    include_package_data=True,
    use_scm_version={
        "write_to": os.path.join("multiplanet", "multiplanet_version.py"),
        "write_to_template": '__version__ = "{version}"\n',
    },
    install_requires=[
        "numpy",
        "h5py",
        "argparse",
        "pandas",
        "scipy",
        "vspace",
        "bigplanet",
    ],
    entry_points={
        "console_scripts": [
            "multiplanet = multiplanet.multiplanet:Arguments",
            "mpstatus = multiplanet.mpstatus:Arguments",
        ],
    },
    setup_requires=["setuptools_scm"],
    zip_safe=False,
)
