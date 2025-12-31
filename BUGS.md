# Known Bugs in MultiPlanet

This document tracks critical bugs discovered during the testing infrastructure restoration.

## Critical #1: BigPlanet + Multiprocessing Deadlock ✅ FIXED

**Location:** [multiplanet/multiplanet.py](multiplanet/multiplanet.py) (original lines 212-292)

**Severity:** CRITICAL - Caused infinite hang when using `-bp` flag

**Discovered:** 2025-12-31 during pytest execution

**Fixed:** 2025-12-31 by adopting BigPlanet's architecture

**Status:** ✅ **RESOLVED** - All tests passing with -bp flag enabled

### Description

The `multiplanet -bp` command hangs indefinitely due to a deadlock in the multiprocessing + HDF5 interaction. The issue occurs when multiple worker processes attempt to write to the same HDF5 archive file.

### Symptoms

- Test hangs for 12+ hours without completing
- BigPlanet archive file created but remains empty (800 bytes - header only)
- No error messages or warnings
- Simulations appear to start but never complete

### Root Cause

Multiple compounding issues:

1. **`GetVplanetHelp()` called inside worker loop** (line 214)
   - Called on every iteration while holding the lock
   - Spawns subprocess `vplanet -H` from within multiprocessing context
   - Can cause file descriptor issues or deadlocks

2. **`data = {}` reinitialized on every loop** (line 213)
   - BigPlanet data accumulation broken
   - Each iteration loses previous simulation data

3. **HDF5 file opened in multiprocessing context** (line 272)
   - Multiple processes writing to same HDF5 file
   - HDF5 is not fully multiprocessing-safe despite locks
   - Can deadlock on file operations

4. **Lock held during expensive operations**
   - GetVplanetHelp() takes ~0.6 seconds
   - Blocks all other workers unnecessarily

### Evidence

```bash
# Process listing showed zombie vplanet processes
$ ps aux | grep vplanet
python /usr/bin/vplanet vpl.in    # State: UE (uninterruptible sleep)

# Empty HDF5 archive created
$ ls -l MP_Bigplanet.bpa
-rw-r--r-- 800 bytes  # Header only, no data

# Test hung indefinitely
$ pytest tests/Bigplanet/test_bigplanet.py
# Running for 12+ hours...
```

### Impact

- **Cannot test BigPlanet integration** in multiplanet
- **Cannot use multiplanet -bp flag** reliably in production
- Test suite cannot validate BigPlanet archive creation
- Silent hang makes debugging difficult (no error message)

### Temporary Workaround

Disabled `-bp` flag in test_bigplanet.py:
```python
# OLD (hangs):
subprocess.check_output(["multiplanet", "vspace.in", "-bp"], cwd=path)

# NEW (works):
subprocess.check_output(["multiplanet", "vspace.in"], cwd=path)
# TODO: Re-enable after fixing multiprocessing architecture
```

### Recommended Fix (Sprint 4)

**Option 1: Single-threaded BigPlanet Archive Creation (Safest)**
```python
def fnRunParallel(...):
    # Run simulations in parallel WITHOUT BigPlanet
    fnExecuteWorkers(listWorkers, bVerbose)

    # Create BigPlanet archive in main process AFTER all sims complete
    if bBigplanet:
        fnCreateBigplanetArchive(sFolder, sSystemName, listBodies, ...)
```

**Benefits:**
- No multiprocessing + HDF5 conflicts
- Simpler, more reliable
- GetVplanetHelp() called only once

**Drawback:**
- BigPlanet archive created after all sims complete (slower)
- But safer and actually works!

**Option 2: Process-Safe Queue (More Complex)**
```python
# Use multiprocessing.Manager() to create shared queue
manager = mp.Manager()
queue = manager.Queue()

# Workers add simulation paths to queue
def fnParallelWorker(...):
    # After simulation completes
    if bBigplanet:
        queue.put(sSimFolder)

# Dedicated BigPlanet writer process
def fnBigplanetWriter(queue, sH5File, ...):
    vplanet_help = GetVplanetHelp()  # Called once
    with h5py.File(sH5File, 'w') as Master:
        while True:
            sSimFolder = queue.get()
            if sSimFolder is None:  # Poison pill
                break
            # Process folder and write to HDF5
```

**Benefits:**
- Archive built concurrently with simulations
- Single HDF5 writer (no conflicts)

**Drawback:**
- More complex architecture
- Requires significant refactoring

### Fix Applied (2025-12-31)

Adopted BigPlanet's architecture to resolve all root causes:

**1. Moved `GetVplanetHelp()` to main process:**
```python
# NEW: Called ONCE in main process
def parallel_run_planet(..., bigplanet, ...):
    if bigplanet:
        vplanet_help = GetVplanetHelp()  # ONCE, before spawning workers
    else:
        vplanet_help = None

    # Passed to workers as immutable parameter
    for i in range(cores):
        workers.append(
            mp.Process(target=par_worker, args=(..., vplanet_help))
        )
```

**2. Extracted modular helper functions:**
- `fnGetNextSimulation()` - Thread-safe checkpoint file access
- `fnMarkSimulationComplete()` - Mark simulation as complete
- `fnMarkSimulationFailed()` - Mark simulation as failed

**3. Refactored worker loop with minimal critical sections:**
```python
def par_worker(..., vplanet_help):  # Receives pre-fetched help
    while True:
        # Get next sim (with lock)
        sFolder = fnGetNextSimulation(checkpoint, lock)
        if sFolder is None:
            return

        # Run vplanet (NO LOCK - independent work)
        vplanet = sub.Popen(["vplanet", "vpl.in"], cwd=sFolder, ...)
        stdout, stderr = vplanet.communicate()  # WAIT for completion

        # Process BigPlanet data (NO LOCK - CPU-bound)
        if vplanet.returncode == 0 and vplanet_help:
            data = GatherData(...)

            # Write to HDF5 (WITH LOCK - minimal critical section)
            lock.acquire()
            try:
                with h5py.File(h5_file, "a") as Master:
                    DictToBP(data, vplanet_help, Master, ...)
            finally:
                lock.release()

        # Update checkpoint (with lock)
        fnMarkSimulationComplete(checkpoint, sFolder, lock)
```

**4. Fixed subprocess return code handling:**
- Changed from `poll()` (returns None if running) to `communicate()` (waits for completion)
- Now properly detects failed simulations via `returncode`

**5. Eliminated `os.chdir()` calls:**
- Use `cwd=sFolder` parameter in `Popen()` instead
- No more global state pollution

### Test Results

**Before Fix:**
```bash
$ pytest tests/Bigplanet/test_bigplanet.py
# Hung for 12+ hours, killed manually
# Archive: 800 bytes (header only, no data)
```

**After Fix:**
```bash
$ pytest tests/Bigplanet/test_bigplanet.py
tests/Bigplanet/test_bigplanet.py::test_bigplanet PASSED [100%]
1 passed in 15.86s

$ ls -lh tests/Bigplanet/MP_Bigplanet.bpa
-rw-r--r--  2.0M  MP_Bigplanet.bpa

$ h5ls tests/Bigplanet/MP_Bigplanet.bpa
semi_a0    Group
semi_a1    Group
semi_a2    Group
```

**Full Test Suite:**
```bash
$ pytest tests/ -v
tests/Bigplanet/test_bigplanet.py::test_bigplanet PASSED     [ 20%]
tests/Checkpoint/test_checkpoint.py::test_checkpoint PASSED  [ 40%]
tests/MpStatus/test_mpstatus.py::test_mpstatus PASSED        [ 60%]
tests/Parallel/test_parallel.py::test_parallel PASSED        [ 80%]
tests/Serial/test_serial.py::test_serial PASSED              [100%]

5 passed in 63.89s
```

### Testing Status

✅ **FIXED AND VALIDATED**
- BigPlanet integration test re-enabled with -bp flag
- All 5 tests passing consistently
- HDF5 archive created successfully (2.0 MB with data)
- No deadlocks observed

### Related Issues

- Bug #2 (subprocess return code) - ✅ **ALSO FIXED** in this refactoring
- Architecture redesign - ✅ **COMPLETED** using BigPlanet's proven patterns

---

## Critical #2: Incorrect Subprocess Return Code Handling ✅ FIXED

**Location:** [multiplanet/multiplanet.py](multiplanet/multiplanet.py) (original lines 250-264)

**Severity:** HIGH - Caused incorrect success/failure classification of simulations

**Discovered:** 2025-12-28 during test restoration

**Fixed:** 2025-12-31 during architecture refactoring

**Status:** ✅ **RESOLVED** - Now using communicate() with proper returncode checking

### Description

The `par_worker()` function incorrectly checks the return code of vplanet subprocess calls using `poll()` immediately after starting the process, rather than after the process completes.

### Current Buggy Code

```python
# Line 243-255
vplanet = sub.Popen(
    "vplanet vpl.in",
    shell=True,
    stdout=sub.PIPE,
    stderr=sub.PIPE,
    universal_newlines=True,
)
return_code = vplanet.poll()  # BUG: Returns None if process still running!
for line in vplanet.stderr:
    vplf.write(line)

for line in vplanet.stdout:
    vplf.write(line)

# Lines 264-299
if return_code is None:  # WRONG: This means "still running", NOT "success"
    # Mark as complete (status = 1)
    for l in datalist:
        if l[0] == folder:
            l[1] = "1"
            break
else:
    # Mark as failed (status = -1)
    for l in datalist:
        if l[0] == folder:
            l[1] = "-1"
            break
```

### The Problem

1. **Line 250:** `vplanet.poll()` is called immediately after `Popen()`, which returns `None` if the process is still running
2. **Lines 251-255:** Reading from stdout/stderr causes the process to complete, but we never re-check the return code
3. **Line 264:** The condition `if return_code is None` is interpreted as "success", but it actually means "process was still running at line 250"
4. **Result:** ALL simulations are marked as complete (status=1), even if vplanet failed with a non-zero exit code

### Impact

- Failed vplanet simulations are incorrectly marked as successful
- Checkpoint file shows status=1 for failed runs
- No indication to user that simulations failed
- Corrupted results may be included in BigPlanet archives
- Silent failures make debugging difficult

### Evidence

When running the test suite, simulations marked as complete (status=1) in checkpoint file sometimes lack expected output files (`earth.earth.forward`), indicating vplanet failed but was marked successful.

### Correct Fix

Replace `poll()` with `wait()` to get the actual return code after process completes:

```python
# Corrected code
vplanet = sub.Popen(
    "vplanet vpl.in",
    shell=True,
    stdout=sub.PIPE,
    stderr=sub.PIPE,
    universal_newlines=True,
)

# Read output streams (this allows process to complete)
for line in vplanet.stderr:
    vplf.write(line)

for line in vplanet.stdout:
    vplf.write(line)

# NOW get the return code after process completes
return_code = vplanet.wait()  # CORRECT: Waits for completion and returns exit code

if return_code == 0:  # EXPLICIT check for success
    # Mark as complete (status = 1)
    for l in datalist:
        if l[0] == folder:
            l[1] = "1"
            break
else:
    # Mark as failed (status = -1)
    for l in datalist:
        if l[0] == folder:
            l[1] = "-1"
            break
```

### Alternative Fix (More Pythonic)

Use `communicate()` instead of manual stream reading:

```python
vplanet = sub.Popen(
    "vplanet vpl.in",
    shell=True,
    stdout=sub.PIPE,
    stderr=sub.PIPE,
    universal_newlines=True,
)

# communicate() waits for completion and returns (stdout, stderr)
stdout, stderr = vplanet.communicate()

with open("vplanet_log", "a+") as vplf:
    vplf.write(stderr)
    vplf.write(stdout)

return_code = vplanet.returncode  # Now contains actual exit code

if return_code == 0:
    # Mark complete
    pass
else:
    # Mark failed
    pass
```

### Fix Applied (2025-12-31)

Implemented the "Alternative Fix" using `communicate()`:

```python
# NEW: Refactored par_worker() subprocess handling
vplanet_log_path = os.path.join(sFolder, "vplanet_log")

with open(vplanet_log_path, "a+") as vplf:
    vplanet = sub.Popen(
        ["vplanet", "vpl.in"],
        cwd=sFolder,  # No shell=True, no os.chdir()
        stdout=sub.PIPE,
        stderr=sub.PIPE,
        universal_newlines=True,
    )
    # communicate() waits for completion and returns output
    stdout, stderr = vplanet.communicate()

    vplf.write(stderr)
    vplf.write(stdout)

# Check actual return code
return_code = vplanet.returncode

if return_code == 0:
    # Process succeeded - mark complete
    fnMarkSimulationComplete(checkpoint_file, sFolder, lock)
else:
    # Process failed - mark for retry
    fnMarkSimulationFailed(checkpoint_file, sFolder, lock)
```

**Additional fixes in same refactoring:**
- Removed `shell=True` (security improvement)
- Removed `os.chdir()` (thread-safety improvement)
- Use `cwd=sFolder` parameter instead
- Explicit `returncode == 0` check (not `is None`)

### Testing Status

✅ **FIXED AND VALIDATED**
- All simulations now correctly classified as success/failure
- Failed simulations marked with status=-1 for retry
- Successful simulations marked with status=1
- Tests verify output files exist only for successful runs

### Workaround

No longer needed - bug is fixed.

### Previous Workaround

Manual verification was required:
```bash
# Check if simulation actually completed
ls MP_Serial/*/earth.earth.forward
```

### Related Issues

This bug is part of a broader architectural issue documented in [claude.md Section 3: Code Architecture Issues](claude.md):
- Uses `shell=True` (security risk)
- Uses `os.chdir()` (not thread-safe)
- No error handling for subprocess failures

All will be addressed together in Sprint 4.

---

## Additional Security Concern: shell=True

**Location:** [multiplanet/multiplanet.py:245](multiplanet/multiplanet.py:245)

**Severity:** MEDIUM - Potential command injection if vpl.in is user-controlled

### Current Code
```python
vplanet = sub.Popen("vplanet vpl.in", shell=True, ...)
```

### Recommended Fix
```python
vplanet = sub.Popen(["vplanet", "vpl.in"], shell=False, cwd=folder, ...)
```

This will be fixed in Sprint 4 alongside the return code bug.

---

## Document Metadata

- **Created:** 2025-12-28
- **Author:** Development Team
- **Related Planning Document:** [claude.md](claude.md)
- **Sprint for Fix:** Sprint 4 (Refactoring, Weeks 7-8)
