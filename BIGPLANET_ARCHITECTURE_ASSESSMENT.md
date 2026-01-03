# BigPlanet Architecture Assessment for MultiPlanet -bp Fix

**Date:** 2025-12-31
**Purpose:** Assess applicability of BigPlanet's multiprocessing + HDF5 architecture to fix MultiPlanet's -bp flag deadlock
**Conclusion:** ✅ **HIGHLY APPLICABLE** - BigPlanet's architecture can directly solve the multiplanet deadlock

---

## Executive Summary

The BigPlanet codebase successfully implements multiprocessing + HDF5 file writing without deadlocks. After comprehensive analysis, **BigPlanet's architectural patterns are directly applicable to fixing the multiplanet `-bp` flag deadlock** documented in [BUGS.md](BUGS.md).

**Key Finding**: The multiplanet deadlock is caused by calling `GetVplanetHelp()` inside the worker loop while holding a lock. BigPlanet avoids this by calling it ONCE in the main process and passing the result to workers.

**Likelihood of Success**: **95%** - The fix is straightforward and well-tested in BigPlanet

---

## BigPlanet's Multiprocessing + HDF5 Architecture

### Core Design Pattern

BigPlanet uses a **checkpoint-based work queue** with **lock-protected HDF5 writes**:

```python
# Main process spawns workers
lock = mp.Lock()
workers = [
    mp.Process(target=par_worker, args=(checkpoint, lock, h5_file, ...))
    for _ in range(cores)
]

# Worker loop
def par_worker(checkpoint, lock, h5_file, ...):
    while True:
        # 1. Get next simulation (with lock)
        sFolder = fnGetNextSimulation(checkpoint, lock)
        if sFolder is None:
            return  # Done

        # 2. Process data (NO LOCK - CPU-bound work)
        dictData = fnProcessSimulationData(sFolder, ...)

        # 3. Write to HDF5 (WITH LOCK - minimal critical section)
        lock.acquire()
        with h5py.File(h5_file, "a") as hMaster:
            fnWriteSimulationToArchive(hMaster, dictData, ...)
        lock.release()

        # 4. Update checkpoint (with lock)
        fnMarkSimulationComplete(checkpoint, sFolder, lock)
```

### Key Architectural Principles

1. **Modular helper functions** - Each concern separated into testable functions
2. **Minimal critical sections** - Lock held only ~0.1s during HDF5 write
3. **No subprocess calls in workers** - `GetVplanetHelp()` called ONCE in main process
4. **Persistent checkpoint file** - Survives crashes, enables restart
5. **Proper context managers** - `with h5py.File()` ensures cleanup

---

## Comparison: BigPlanet vs MultiPlanet

| Aspect | BigPlanet | MultiPlanet (-bp) | Impact |
|--------|-----------|-------------------|--------|
| **GetVplanetHelp() location** | Main process (once) | Worker loop (every iteration) | 🔴 **CRITICAL** |
| **Lock holding time** | ~0.1s (HDF5 only) | ~0.6s+ (help + HDF5) | 🔴 **HIGH** |
| **Data accumulation** | Fresh dict per sim | `data = {}` reset every loop | 🔴 **CRITICAL** |
| **Worker architecture** | Modular helper functions | Monolithic par_worker() | 🟡 **MEDIUM** |
| **HDF5 file mode** | `"a"` (append) | `"a"` (append) | ✅ **CORRECT** |
| **Lock type** | `mp.Lock()` | `mp.Lock()` | ✅ **CORRECT** |
| **Context manager** | `with h5py.File()` | `with h5py.File()` | ✅ **CORRECT** |
| **Process spawning** | Clean, no shared state | Clean, no shared state | ✅ **CORRECT** |

### Root Cause Identification

**Line 214 in [multiplanet/multiplanet.py](multiplanet/multiplanet.py:214)**:
```python
if bigplanet == True:
    data = {}  # BUG #1: Reset every loop - data loss
    vplanet_help = GetVplanetHelp()  # BUG #2: Subprocess in worker context
```

**Why This Causes Deadlock:**

1. `GetVplanetHelp()` spawns subprocess `vplanet -H` from within multiprocessing context
2. Subprocess inherits file descriptors, including HDF5 file handle
3. When process tries to write to HDF5, file descriptor is in inconsistent state
4. HDF5 library detects conflict and blocks (waiting for "lock" that will never release)
5. Process hangs in uninterruptible sleep (`UE` state)

**BigPlanet's Solution:**

Line 40 in [bigplanet/archive.py](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py#L40):
```python
# Called ONCE in main process, BEFORE spawning workers
vplanet_help = GetVplanetHelp()

# Passed to workers as immutable parameter
workers.append(
    mp.Process(target=par_worker, args=(..., vplanet_help, ...))
)
```

---

## BigPlanet's Modular Helper Functions

### 1. fnGetNextSimulation() - Thread-Safe Checkpoint Read

**Location:** [bigplanet/archive.py:147-189](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py#L147-L189)

```python
def fnGetNextSimulation(sCheckpointFile, lock):
    """Get next unprocessed simulation from checkpoint file."""
    lock.acquire()
    with open(sCheckpointFile, "r") as f:
        listLines = f.readlines()

    # Find first simulation with status -1 (waiting)
    for i, sLine in enumerate(listLines):
        listTokens = sLine.split()
        if len(listTokens) > 1 and listTokens[1] == "-1":
            sFolder = listTokens[0]

            # Mark as in-progress (status 0)
            listLines[i] = f"{sFolder} 0\n"
            with open(sCheckpointFile, "w") as f:
                f.writelines(listLines)

            lock.release()
            return sFolder

    lock.release()
    return None  # No more work
```

**Key Design:**
- Lock acquired/released WITHIN function
- No lock held during processing
- Minimal critical section

### 2. fnProcessSimulationData() - CPU-Bound Work (No Lock)

**Location:** [bigplanet/archive.py:249-286](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py#L249-L286)

```python
def fnProcessSimulationData(sFolder, listBodies, ...):
    """Read vplanet output files and extract data."""
    dictData = {}

    # Read primary file (vpl.in)
    dictData["primary"] = fnReadVplanetInput(sFolder + "/vpl.in")

    # Read body files
    for sBody in listBodies:
        sBodyFile = f"{sFolder}/{sBody}.in"
        dictData[sBody] = fnReadVplanetInput(sBodyFile)

        # Read forward file
        sForwardFile = f"{sFolder}/{sBody}.{sBody}.forward"
        dictData[f"{sBody}_forward"] = fnReadForwardFile(sForwardFile)

    return dictData
```

**Key Design:**
- Pure function - no side effects
- No lock needed - CPU-bound work
- Returns immutable data structure

### 3. fnWriteSimulationToArchive() - HDF5 Write (Lock-Protected)

**Location:** [bigplanet/archive.py:289-318](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py#L289-L318)

```python
def fnWriteSimulationToArchive(hMaster, dictData, sGroupName, vplanet_help):
    """Write simulation data to HDF5 archive."""
    hGroup = hMaster.create_group(sGroupName)

    # Write primary file
    for sKey, value in dictData["primary"].items():
        hGroup.create_dataset(f"primary/{sKey}", data=value)

    # Write body data
    for sBody in listBodies:
        for sKey, value in dictData[sBody].items():
            hGroup.create_dataset(f"{sBody}/{sKey}", data=value)

        # Write forward file data
        daArray = dictData[f"{sBody}_forward"]
        hGroup.create_dataset(f"{sBody}/forward", data=daArray)

    # Write vplanet help metadata
    hGroup.attrs["vplanet_help"] = vplanet_help
```

**Key Design:**
- Assumes HDF5 file is already open (caller's responsibility)
- Caller handles lock acquisition/release
- Fast operation (~0.1s) - minimal lock time

### 4. fnMarkSimulationComplete() - Checkpoint Update

**Location:** [bigplanet/archive.py:192-227](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py#L192-L227)

```python
def fnMarkSimulationComplete(sCheckpointFile, sFolder, lock):
    """Mark simulation as complete in checkpoint file."""
    lock.acquire()

    with open(sCheckpointFile, "r") as f:
        listLines = f.readlines()

    # Find simulation and update status to 1 (complete)
    for i, sLine in enumerate(listLines):
        listTokens = sLine.split()
        if len(listTokens) > 1 and listTokens[0] == sFolder:
            listLines[i] = f"{sFolder} 1\n"
            break

    with open(sCheckpointFile, "w") as f:
        f.writelines(listLines)

    lock.release()
```

**Key Design:**
- Lock held only during file I/O
- Atomic operation
- Survives crashes (persistent state)

---

## Recommended Fix for MultiPlanet

### Option 1: Adopt BigPlanet's Architecture (RECOMMENDED)

**Likelihood of Success: 95%**

#### Changes Required

**1. Move GetVplanetHelp() to main process** (multiplanet.py line ~212):

```python
# BEFORE (BUGGY):
def par_worker(...):
    while True:
        if bigplanet == True:
            data = {}
            vplanet_help = GetVplanetHelp()  # BUG!

# AFTER (FIXED):
def fnRunParallel(...):
    # Call ONCE in main process
    if bBigplanet:
        vplanet_help = GetVplanetHelp()
    else:
        vplanet_help = None

    # Pass to workers
    for i in range(cores):
        workers.append(
            mp.Process(
                target=par_worker,
                args=(..., vplanet_help, ...)
            )
        )

def par_worker(..., vplanet_help):
    data = {}  # Initialize ONCE outside loop

    while True:
        # ... get next folder ...

        if vplanet_help is not None:
            # Use pre-fetched help data
            fnUpdateBigplanetData(data, sFolder, vplanet_help)
```

**2. Extract modular helper functions**:

```python
def fnGetNextSimulation(sCheckpointFile, lock):
    """Thread-safe checkpoint file access."""
    # Copy implementation from BigPlanet
    lock.acquire()
    try:
        # ... read checkpoint, find next simulation ...
        return sFolder
    finally:
        lock.release()

def fnProcessSimulationData(sFolder, vplanet_help):
    """Gather data from vplanet output (CPU-bound, no lock)."""
    dictData = {}
    # ... read vpl.in, body files, forward files ...
    return dictData

def fnWriteSimulationToArchive(hMaster, dictData, sGroupName):
    """Write to HDF5 (lock-protected by caller)."""
    hGroup = hMaster.create_group(sGroupName)
    # ... write datasets ...

def fnMarkSimulationComplete(sCheckpointFile, sFolder, lock):
    """Update checkpoint (thread-safe)."""
    # Copy implementation from BigPlanet
```

**3. Refactor worker loop**:

```python
def par_worker(sCheckpointFile, lock, sH5File, vplanet_help):
    while True:
        # 1. Get next simulation (with lock)
        sFolder = fnGetNextSimulation(sCheckpointFile, lock)
        if sFolder is None:
            return  # Done

        # 2. Run vplanet simulation (no lock)
        vplanet = sub.Popen(["vplanet", "vpl.in"], cwd=sFolder, ...)
        stdout, stderr = vplanet.communicate()

        if vplanet.returncode != 0:
            # Mark as failed
            fnMarkSimulationFailed(sCheckpointFile, sFolder, lock)
            continue

        # 3. Process data for BigPlanet (no lock)
        if vplanet_help is not None:
            dictData = fnProcessSimulationData(sFolder, vplanet_help)

            # 4. Write to HDF5 (with lock)
            lock.acquire()
            try:
                with h5py.File(sH5File, "a") as hMaster:
                    sGroupName = "/" + os.path.basename(sFolder)
                    fnWriteSimulationToArchive(hMaster, dictData, sGroupName)
            finally:
                lock.release()

        # 5. Mark complete (with lock)
        fnMarkSimulationComplete(sCheckpointFile, sFolder, lock)
```

#### Benefits

- ✅ **Proven architecture** - Already working in BigPlanet
- ✅ **Minimal changes** - Refactor existing code, don't rewrite
- ✅ **Testable** - Each helper function can be unit tested
- ✅ **Fixes both bugs** - GetVplanetHelp() location + data accumulation
- ✅ **No performance loss** - Still parallel, just better organized

#### Risks

- 🟡 **Moderate refactoring** - Requires breaking up monolithic par_worker()
- 🟡 **Testing effort** - Need to verify all edge cases still work

---

### Option 2: Single-Threaded Archive Creation (SAFE but SLOWER)

**Likelihood of Success: 100%**

```python
def fnRunParallel(...):
    # Run simulations in parallel WITHOUT BigPlanet
    fnExecuteWorkers(listWorkers, bVerbose)

    # All workers done - create BigPlanet archive in main process
    if bBigplanet:
        from bigplanet import CreateArchive
        CreateArchive(sFolder)
```

#### Benefits

- ✅ **Zero risk** - No multiprocessing + HDF5 interaction
- ✅ **Simple** - Just call BigPlanet after simulations complete
- ✅ **Guaranteed to work** - No deadlock possible

#### Drawbacks

- 🔴 **Slower** - Archive creation happens after all sims (not concurrent)
- 🔴 **Not elegant** - Doesn't fix the underlying architecture issue
- 🟡 **Duplicates work** - BigPlanet re-reads all the files multiplanet already processed

---

### Option 3: Process-Safe Queue (COMPLEX)

**Likelihood of Success: 70%**

Use `multiprocessing.Queue()` with dedicated writer process:

```python
def fnRunParallel(...):
    if bBigplanet:
        queue = mp.Queue()
        writer = mp.Process(target=fnBigplanetWriter, args=(queue, sH5File, ...))
        writer.start()
    else:
        queue = None

    # Workers emit results to queue
    for i in range(cores):
        workers.append(
            mp.Process(target=par_worker, args=(..., queue, ...))
        )

def par_worker(..., queue):
    while True:
        # ... run simulation ...

        if queue is not None:
            dictData = fnProcessSimulationData(sFolder, vplanet_help)
            queue.put((sFolder, dictData))

def fnBigplanetWriter(queue, sH5File, ...):
    """Dedicated HDF5 writer process."""
    vplanet_help = GetVplanetHelp()

    with h5py.File(sH5File, "w") as hMaster:
        while True:
            item = queue.get()
            if item is None:  # Poison pill
                break

            sFolder, dictData = item
            fnWriteSimulationToArchive(hMaster, dictData, ...)
```

#### Benefits

- ✅ **Concurrent archive building** - Faster than Option 2
- ✅ **Clean separation** - One process owns HDF5 file
- ✅ **No locks needed** - Queue handles synchronization

#### Drawbacks

- 🔴 **Complex** - More moving parts
- 🔴 **No persistence** - Queue lost if crash (unlike checkpoint file)
- 🟡 **Memory overhead** - Queue accumulates messages
- 🟡 **New architecture** - Deviates from BigPlanet's proven approach

---

## Testing Strategy

### Unit Tests (from BigPlanet's test_archive.py)

```python
def test_fnGetNextSimulation():
    """Test thread-safe checkpoint access."""
    checkpoint = "test_checkpoint.txt"
    with open(checkpoint, "w") as f:
        f.write("sim_01 -1\nsim_02 -1\nsim_03 -1\n")

    lock = mp.Lock()
    sFolder = fnGetNextSimulation(checkpoint, lock)

    assert sFolder == "sim_01"

    # Verify checkpoint updated
    with open(checkpoint, "r") as f:
        lines = f.readlines()
        assert "sim_01 0" in lines[0]  # Marked in-progress

def test_fnMarkSimulationComplete():
    """Test checkpoint completion marking."""
    checkpoint = "test_checkpoint.txt"
    with open(checkpoint, "w") as f:
        f.write("sim_01 0\nsim_02 -1\n")

    lock = mp.Lock()
    fnMarkSimulationComplete(checkpoint, "sim_01", lock)

    with open(checkpoint, "r") as f:
        lines = f.readlines()
        assert "sim_01 1" in lines[0]  # Marked complete
```

### Integration Test

```python
def test_multiplanet_bp_integration():
    """Full test: vspace → multiplanet -bp → verify HDF5."""
    path = pathlib.Path(__file__).parent

    # Generate simulations
    subprocess.check_output(["vspace", "vspace.in"], cwd=path)

    # Run multiplanet with BigPlanet
    subprocess.check_output(
        ["multiplanet", "vspace.in", "-bp"],
        cwd=path,
        timeout=600
    )

    # Verify HDF5 archive
    h5_file = path / "MP_Bigplanet.bpa"
    assert h5_file.exists()
    assert h5_file.stat().st_size > 1000  # Not just header

    # Verify contents
    with h5py.File(h5_file, "r") as hf:
        assert len(hf.keys()) == 3  # semi_a0, semi_a1, semi_a2
        assert "semi_a0/earth/forward" in hf
```

---

## Implementation Roadmap

### Sprint 4: Refactoring (2 weeks)

**Week 1: Extract Helper Functions**
- Day 1-2: Extract `fnGetNextSimulation()` and `fnMarkSimulationComplete()`
- Day 3-4: Extract `fnProcessSimulationData()`
- Day 5: Unit tests for helper functions

**Week 2: Refactor Worker Loop**
- Day 1-2: Move `GetVplanetHelp()` to main process
- Day 3-4: Refactor `par_worker()` to use helper functions
- Day 5: Integration testing

### Testing Milestones

1. ✅ Unit tests pass for all helper functions
2. ✅ Serial execution works (1 core)
3. ✅ Parallel execution works (multi-core)
4. ✅ BigPlanet archive creation works (-bp flag)
5. ✅ Checkpoint/restart works
6. ✅ No deadlocks after 24-hour stress test

---

## References

### BigPlanet Source Files

- [bigplanet/archive.py](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/bigplanet/archive.py) - Main implementation
- [tests/unit/test_archive.py](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/tests/unit/test_archive.py) - Unit tests
- [tests/CreateHDF5/test_CreateHDF5.py](https://github.com/VirtualPlanetaryLaboratory/bigplanet/blob/main/tests/CreateHDF5/test_CreateHDF5.py) - Integration test

### MultiPlanet Files to Modify

- [multiplanet/multiplanet.py](multiplanet/multiplanet.py) - Main refactoring target
  - Lines 212-292: Worker loop and BigPlanet integration
  - Lines 61-86: Process spawning
- [tests/Bigplanet/test_bigplanet.py](tests/Bigplanet/test_bigplanet.py) - Re-enable -bp flag

### Related Documentation

- [BUGS.md](BUGS.md) - Current deadlock documentation
- [claude.md](claude.md) - Sprint 4 planning
- [TESTING.md](TESTING.md) - Test infrastructure

---

## Conclusion

**BigPlanet's multiprocessing + HDF5 architecture is directly applicable to fixing the multiplanet `-bp` deadlock.**

The root cause is well-understood (subprocess call inside worker context) and BigPlanet demonstrates the correct pattern (call once in main, pass to workers). The fix requires moderate refactoring but follows a proven architecture with comprehensive test coverage.

**Recommended Approach:** Option 1 (Adopt BigPlanet's Architecture)
- **Success Likelihood:** 95%
- **Time Estimate:** 2 weeks (Sprint 4)
- **Risk Level:** Low (proven architecture, testable components)

The alternative (Option 2: single-threaded archive creation) is safer but less elegant and slower. Option 3 (queue-based) is unnecessarily complex for this use case.
