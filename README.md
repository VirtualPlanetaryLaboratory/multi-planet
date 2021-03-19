# Multi-Planet: Multi-Core Simulations with VPLanet

Use `multi-planet` to run a large number of simulations, created with [vspace](../vspace>), on one or more cores.  The included script `mpstatus` can provide the current status of the simulations. Note that `multi-planet` cannot be used to run simulations across multiple computers.

## Multi-Planet Setup

The easiest way to use `multi-planet` is to add it to your PATH. To do so, navigate to the multi-planet directory and execute the following command:

```
python setup.py
```

which also places `mpstatus` in your PATH.

## Running Multi-Planet

To run `multi-planet` on a large number of simulations, first run `vspace` to create the simulation folders. Then, in that same directory, type:
```
multi-planet <input file> -c [number of cores] -q -bp -m [email]
```
Where the "input file" **must be the same file** used with `vspace`. You can specify the number of cores, but the default is the maximum number of cores.
There are three optional arguments for multi-planet:
 `-q`: there will be no output in the command line
 `-bp`: bigplanet will be ran in conjuction with multi-planet. See the `bigplanet` [documentation](https://github.com/VirtualPlanetaryLaboratory/vplanet/tree/master/bigplanet) for more information
 `-m`: emails the users at `email` when the simulations are complete

Should your run be interrupted for whatever reason, just run `multi-planet` again and it should restart where it left off.

## Checking the status of the Multi-Planet Simulations

To check the status of your simulations, type
```
mpstatus <input file>
```
where the "input file" **must be the same file** used with `vspace` and `multi-planet`.
The following will be printed to the command line:

```
--Multi-Planet Status--
Number of Simulations completed:
Number of Simulations in progress:
Number of Simulations remaining:
```
but with the proper statistics shown.
