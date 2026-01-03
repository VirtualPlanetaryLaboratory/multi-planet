# Testing MultiPlanet

This document describes how to run the test suite for MultiPlanet.

## Prerequisites

### VPLanet Version Requirement

The test suite works with **vplanet v2.5+** (public release from PyPI).

**Installation:**
```bash
pip install vplanet vspace bigplanet
```

**Compatibility:**
- ✅ Works with public vplanet v2.5+ (PyPI)
- ✅ Also works with vplanet v3.0 (private development branch)
- ✅ Tests use `dTCore` input parameter (compatible with all versions)
- ✅ Tests request `TCMB` and `TCore` output parameters (compatible with all versions)

### Python Dependencies

```bash
pip install pytest pytest-cov pytest-timeout
```

## Running Tests

### Quick Start

To run all tests:

```bash
cd /Users/rory/src/multi-planet
python -m pytest tests/ -v
```

**Note:** Tests will automatically use the vplanet executable in your PATH (typically from `pip install vplanet`).

### Run Individual Tests

```bash
# Serial execution test
python -m pytest tests/Serial/test_serial.py -v

# Parallel execution test
python -m pytest tests/Parallel/test_parallel.py -v

# Checkpoint/restart test
python -m pytest tests/Checkpoint/test_checkpoint.py -v

# Status reporting test
python -m pytest tests/MpStatus/test_mpstatus.py -v

# BigPlanet integration test
python -m pytest tests/Bigplanet/test_bigplanet.py -v
```

## Test Suite Overview

| Test | Description | Duration |
|------|-------------|----------|
| `test_serial.py` | Single-core execution | ~9s |
| `test_parallel.py` | Multi-core parallel execution | ~6s |
| `test_checkpoint.py` | Checkpoint/restart functionality | ~12s |
| `test_mpstatus.py` | Status reporting with `mpstatus` command | ~12s |
| `test_bigplanet.py` | BigPlanet HDF5 archive creation (disabled) | ~10s |

**Total runtime**: ~60 seconds (with private vplanet v3.0)

## Test Details

### Test Parameters

Each test uses a small parameter sweep with 3 simulations:
- Semi-major axis: `dSemi [1, 2, n3] a` (generates semi_a0, semi_a1, semi_a2)
- Evolution time: 4.5 Gyr (`dStopTime 4.5e9`)
- Output interval: 10 Myr (`dOutputTime 1e7`)

### Expected Output

All tests verify that simulation output files are created:
- Each simulation folder should contain `earth.earth.forward`
- Checkpoint file `.MP_*` tracks simulation status
- Simulations marked with status=1 (complete) in checkpoint

## Known Issues

### BigPlanet Integration Test ✅ WORKING

The `test_bigplanet.py` test runs multiplanet **with** the `-bp` flag successfully:

- **Status**: ✅ WORKING - Deadlock issue fixed (December 2025)
- **Fix**: Adopted BigPlanet's architecture (see [BUGS.md](BUGS.md))
- **Verification**: Creates 2.0 MB HDF5 archive with simulation data
- **Runtime**: ~16 seconds for 3 simulations

## Troubleshooting

### VPLanet Not Found

**Cause**: vplanet not installed

**Solution**:
```bash
pip install vplanet
```

### Tests Fail with "Missing output file"

**Cause**: vplanet simulation failed

**Solution**: Check vplanet_log in the simulation folder:
```bash
cat tests/Serial/MP_Serial/semi_a0/vplanet_log
```

### Parameter Name Reference

In vplanet v2.5+ and v3.0:
- **Input parameter**: `dTCore` (Initial Core Temperature)
- **Output parameters**: Both `TCMB` (CMB Temperature) and `TCore` (Core Temperature)

The test files use compatible parameter names that work with all vplanet versions v2.5+.

## Test Restoration History

The test suite was restored in December 2025 after being disabled for an extended period:

1. **Original issue**: Tests disabled due to outdated parameter names
2. **Root cause**: vplanet v3.0 parameter changes not reflected in test files
3. **Fix**: Updated to use `dTCore` input parameter, request `TCMB` as output
4. **Validation**: All 5 tests pass with vplanet v3.0

See [TEST_INFRASTRUCTURE_STATUS.md](TEST_INFRASTRUCTURE_STATUS.md) for detailed restoration report.

## CI/CD Integration

**TODO**: Update GitHub Actions workflow to use vplanet-private v3.0

The current CI workflow likely fails because it uses the public vplanet release. Future work:
- Add vplanet-private as git submodule OR
- Build vplanet v3.0 from source in CI OR
- Wait for v3.0 public release

## Developer Notes

### Test Structure

Each test follows the same pattern:
1. Get test directory path
2. Clean up previous test artifacts
3. Run `vspace vspace.in` to generate simulation folders
4. Run `multiplanet vspace.in` to execute simulations
5. Verify output files exist in each simulation folder
6. (Optional) Verify checkpoint file status

### Adding New Tests

When adding new tests:
1. Create new test directory under `tests/`
2. Include `vspace.in`, `vpl.in`, and body files (e.g., `earth.in`, `sun.in`)
3. Create `test_*.py` with pytest test function
4. Follow existing pattern for cleanup and assertions
5. Update this document with new test description

### Code Quality Improvements

During test restoration, the following improvements were made:
- Removed `os.chdir()` calls (not thread-safe)
- Replaced with `os.path.join()` for path construction
- Added 600s timeout for BigPlanet test (prevents infinite hangs)
- Added descriptive assertion messages

See [claude.md](claude.md) for comprehensive upgrade roadmap.
