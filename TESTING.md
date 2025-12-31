# Testing MultiPlanet

This document describes how to run the test suite for MultiPlanet.

## Prerequisites

### VPLanet Version Requirement

**CRITICAL**: The test suite requires **vplanet v3.0** from the private repository, NOT the public release.

- **Required executable**: `/Users/rory/src/vplanet-private/bin/vplanet` (branch: v3.0)
- **Will NOT work with**: Public vplanet in anaconda (`/Users/rory/opt/anaconda3/bin/vplanet`)

The v3.0 tests use the `dTCore` input parameter and request `TCMB` and `TCore` as output parameters, which are only fully supported in the private v3.0 branch.

### Python Dependencies

```bash
pip install pytest
```

## Running Tests

### Quick Start

To run all tests with the correct vplanet executable:

```bash
export PATH="/Users/rory/src/vplanet-private/bin:$PATH"
cd /Users/rory/src/multi-planet
python -m pytest tests/ -v
```

### Run Individual Tests

```bash
export PATH="/Users/rory/src/vplanet-private/bin:$PATH"

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

### BigPlanet Integration Test (DISABLED)

The `test_bigplanet.py` test currently runs multiplanet **without** the `-bp` flag due to a critical deadlock issue:

- **Issue**: `multiplanet -bp` hangs indefinitely due to multiprocessing + HDF5 conflicts
- **Documented in**: [BUGS.md](BUGS.md) (Critical Bug #1)
- **Current workaround**: Test runs simulations but skips BigPlanet archive creation
- **TODO**: Re-enable after fixing multiprocessing architecture (Sprint 4)

## Troubleshooting

### All Tests Fail with "Missing output file"

**Cause**: Using wrong vplanet executable (public vs private v3.0)

**Solution**:
```bash
# Check which vplanet is being used
which vplanet

# Should show: /Users/rory/src/vplanet-private/bin/vplanet
# If not, set PATH correctly:
export PATH="/Users/rory/src/vplanet-private/bin:$PATH"
```

### Tests Fail with "ERROR: Unrecognized option 'dTCMB'"

**Cause**: Input files have incorrect parameter name

**Solution**: Input parameter should be `dTCore`, not `dTCMB` or `TCMB`:
```
# Correct (in earth.in line 37):
dTCore         6000

# Wrong:
dTCMB         6000
TCMB         6000
```

### Parameter Name Clarification

In vplanet v3.0:
- **Input parameter**: `dTCore` (Initial Core Temperature)
- **Output parameters**: Both `TCMB` (CMB Temperature) and `TCore` (Core Temperature) are available

The output parameter name changed from `TCore` to `TCMB`, but the **input** parameter remains `dTCore`.

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
