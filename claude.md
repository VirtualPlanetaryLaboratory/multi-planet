# MultiPlanet Repository Upgrade Plan

## Executive Summary

This document outlines a comprehensive plan to upgrade the multiplanet repository to full compliance with the VPLanet ecosystem coding standards. The repository currently executes VPLanet simulations in parallel across multiple cores using a checkpoint-based synchronization system. While functionally sound, the codebase exhibits significant style guide violations, insufficient test coverage, and architectural patterns that deviate from established best practices.

**Priority Order:** Testing → Style Compliance → Refactoring → Documentation

---

## Current State Assessment

### Repository Overview

**Purpose:** Execute large batches of VPLanet simulations (created by vspace) in parallel across multiple CPU cores with checkpoint-based restart capability.

**Core Components:**
- `multiplanet.py` (371 lines): Main parallel execution engine
- `mpstatus.py` (51 lines): Status reporting utility
- `multiplanet_module.py` (22 lines): Programmatic API interface
- 5 test modules (all currently disabled)

**Dependencies:** numpy, h5py, pandas, scipy, vspace, bigplanet

---

## Critical Issues Identified

### 1. Testing Infrastructure (CRITICAL)

**Current State:**
- All 5 unit tests are **completely disabled** (assertions commented out)
- Tests only execute vspace; multiplanet calls are commented out
- Zero functional test coverage since commit 6943a5c
- No validation of core functionality (parallel execution, checkpointing, BigPlanet integration)

**Impact:** Cannot verify correctness of any code changes. Regression risk is extremely high.

**Root Cause:** BigPlanet API changes broke compatibility; tests disabled as temporary measure.

---

### 2. Style Guide Violations (HIGH)

The code systematically violates the Hungarian notation style guide across all modules:

#### Variable Naming Violations

| Current Name | Type | Should Be | Location |
|---|---|---|---|
| `folder_name` | str | `sFolder` or `sFolderName` | multiplanet.py:64, 92, 100 |
| `in_files` | list | `listInFiles` | multiplanet.py:57, 92 |
| `infiles` | list | `listInFiles` | multiplanet.py:57 |
| `sims` | list | `listSims` | multiplanet.py:44, 94 |
| `body_names` | list | `listBodyNames` | multiplanet.py:17 |
| `body_list` | list | `listBodies` | multiplanet.py:97, 199 |
| `system_name` | str | `sSystemName` | multiplanet.py:29, 97 |
| `logfile` / `log_file` | str | `sLogFile` | multiplanet.py:98, 200 |
| `checkpoint_file` | str | `sCheckpointFile` | multiplanet.py:100, 196 |
| `datalist` | list | `listData` | multiplanet.py:159, 211 |
| `workers` | list | `listWorkers` | multiplanet.py:113 |
| `lock` | Lock | `lockCheckpoint` | multiplanet.py:112 |
| `cores` | int | `iCores` | multiplanet.py:90, 311 |
| `quiet` | bool | `bQuiet` | multiplanet.py:90 |
| `verbose` | bool | `bVerbose` | multiplanet.py:90, 156 |
| `bigplanet` | bool | `bBigplanet` | multiplanet.py:90, 204 |
| `force` | bool | `bForce` | multiplanet.py:90, 155 |
| `count_done` | int | `iCountDone` | mpstatus.py:18 |
| `count_todo` | int | `iCountTodo` | mpstatus.py:19 |
| `count_ip` | int | `iCountInProgress` | mpstatus.py:20 |
| `input_file` | str | `sInputFile` | multiplanet.py:90, mpstatus.py:6 |
| `full_path` | str | `sFullPath` | multiplanet.py:21 |
| `content` | list | `listContent` | multiplanet.py:25, 26 |
| `vspace_all` | list | `listVspaceAll` | mpstatus.py:9 |
| `dest_line` | str | `sDestLine` | mpstatus.py:10 |

#### Function Naming Violations

| Current Name | Returns | Should Be | Location |
|---|---|---|---|
| `GetDir()` | tuple(str, list) | `ftGetDirectory()` | multiplanet.py:54 |
| `GetSims()` | list | `flistGetSimulations()` | multiplanet.py:41 |
| `GetSNames()` | tuple(str, list) | `ftGetSystemNames()` | multiplanet.py:15 |
| `CreateCP()` | None | `fnCreateCheckpoint()` | multiplanet.py:146 |
| `ReCreateCP()` | None | `fnRecreateCheckpoint()` | multiplanet.py:155 |
| `parallel_run_planet()` | None | `fnRunParallel()` | multiplanet.py:90 |
| `par_worker()` | None | `fnParallelWorker()` | multiplanet.py:196 |
| `Arguments()` | None | `fnArguments()` | multiplanet.py:310, mpstatus.py:43 |
| `mpstatus()` | None | `fnPrintStatus()` | mpstatus.py:6 |
| `RunMultiplanet()` | None | `fnRunMultiplanet()` | multiplanet_module.py:20 |

**Additional Naming Issues:**
- Inconsistent capitalization: `Arguments()` vs typical camelCase
- Abbreviations < 8 chars: `sims`, `re`, `wr`, `cp`, `vpl`, `vplf`, `ip`
- Non-descriptive single letters: `f`, `l`, `w`, `i`

---

### 3. Code Architecture Issues (MEDIUM)

#### Function Length Violations

| Function | Lines | Limit | Violation |
|---|---|---|---|
| `fnParallelWorker()` (par_worker) | 113 | 20 | +93 lines |
| `fnRunParallel()` (parallel_run_planet) | 55 | 20 | +35 lines |
| `fnRecreateCheckpoint()` (ReCreateCP) | 39 | 20 | +19 lines |
| `fnGetSystemNames()` (GetSNames) | 24 | 20 | +4 lines |

**Recommended Decomposition:**

**`fnParallelWorker()` → Split into:**
1. `fbAcquireNextSimulation()` - Lock acquisition + find next pending sim
2. `fnUpdateCheckpointInProgress()` - Mark simulation as started
3. `fnExecuteVplanet()` - Run vplanet subprocess
4. `fnUpdateCheckpointComplete()` - Mark simulation complete/failed
5. `fnGatherBigplanetData()` - Optionally collect HDF5 data

**`fnRunParallel()` → Split into:**
1. `fnInitializeCheckpoint()` - Checkpoint creation/recreation logic
2. `flistCreateWorkers()` - Worker process initialization
3. `fnStartWorkers()` - Worker lifecycle management
4. `fnCleanupArchive()` - Remove unwanted BigPlanet files

**`fnRecreateCheckpoint()` → Split into:**
1. `flistReadCheckpoint()` - Parse checkpoint file
2. `fnResetIncomplete()` - Mark incomplete sims as pending
3. `fbCheckAllComplete()` - Verify completion status
4. `fnHandleForceRerun()` - Force flag logic

#### Architectural Concerns

1. **`os.chdir()` usage (multiplanet.py:239, 307):** Changes global process state, not thread-safe if ever expanded to threading. Should use `cwd` parameter in subprocess calls.

2. **`shell=True` in subprocess (multiplanet.py:245):** Security risk if `vpl.in` contains user-controlled data. Should use list form: `["vplanet", "vpl.in"]`.

3. **Text-based checkpoint format:** Inefficient for large sweeps. Consider JSON or pickle for structured data.

4. **Unused `email` parameter (multiplanet_module.py:20):** Defined but not passed through to execution function.

5. **Hardcoded relative path (multiplanet.py:307):** `os.chdir("../../")` assumes specific directory depth. Fragile.

6. **Return code checking bug (multiplanet.py:264):** `vplanet.poll()` called once immediately; should use `vplanet.wait()` or check returncode after process completes.

7. **Missing error handling:** No try/except blocks for I/O operations, subprocess failures, or lock timeouts.

---

### 4. Documentation Issues (LOW)

**Gaps:**
- No docstrings on any functions except 2 brief ones
- No inline comments explaining checkpoint status codes (-1, 0, 1)
- No module-level docstrings
- README references docs but lacks usage examples

**Existing Documentation:**
- Sphinx docs exist for installation and CLI usage
- Well-structured docs/ folder with ReadTheDocs theme

---

## Testing Strategy

### Phase 1: Test Infrastructure Restoration (Priority 1)

**Objective:** Restore all 5 disabled tests to working state with current BigPlanet API.

**Tasks:**

1. **Update BigPlanet integration calls** (multiplanet.py:209-292)
   - Verify current BigPlanet API for `GetVplanetHelp()`, `GatherData()`, `DictToBP()`
   - Update function signatures and parameter passing
   - Test standalone BigPlanet archive creation

2. **Re-enable test_parallel.py**
   - Uncomment multiplanet subprocess call (line 33)
   - Uncomment assertions (lines 35-40)
   - Add assertion for checkpoint file creation
   - Add assertion for correct status codes in checkpoint
   - Verify .bpa file **not** created (no -bp flag)

3. **Re-enable test_serial.py**
   - Uncomment multiplanet subprocess call (line 26)
   - Uncomment assertions (lines 28-33)
   - Verify single-core execution uses `-c 1` flag correctly

4. **Re-enable test_checkpoint.py**
   - Uncomment multiplanet subprocess call (line 33)
   - Uncomment assertions (lines 35-41)
   - Add checkpoint interruption simulation:
     - Run multiplanet
     - Manually edit checkpoint to mark some sims as incomplete (0 → -1)
     - Re-run multiplanet
     - Verify only incomplete sims re-executed

5. **Re-enable test_mpstatus.py**
   - Uncomment multiplanet subprocess call (line 33)
   - Uncomment mpstatus subprocess call (line 34)
   - Capture mpstatus output
   - Parse and verify counts match checkpoint file

6. **Re-enable test_bigplanet.py**
   - Uncomment multiplanet subprocess call (line 34)
   - Uncomment .bpa file assertion (line 38)
   - Add HDF5 structure validation:
     - Open .bpa file with h5py
     - Verify group count matches simulation count
     - Verify each group contains expected datasets

**Success Criteria:**
- All 5 tests pass on both macOS and Linux
- GitHub Actions CI passes on all supported Python versions (3.9-3.14)
- Test coverage >80% (use pytest-cov)

---

### Phase 2: Expanded Test Coverage (Priority 2)

**Objective:** Add tests for edge cases and error conditions.

**New Test Modules:**

1. **test_error_handling.py**
   - Missing vspace file
   - Malformed vspace file (no destfolder)
   - Non-existent destination folder
   - vplanet executable not in PATH
   - Checkpoint file corruption
   - Disk full during checkpoint write
   - Permission errors on checkpoint file

2. **test_force_flag.py**
   - Force rerun when all sims complete
   - Force flag with incomplete sims (should just run remaining)
   - Verify checkpoint and folder deletion with force

3. **test_verbose_quiet.py**
   - Verify verbose flag produces expected output
   - Verify quiet flag suppresses output
   - Verify mutual exclusivity of flags

4. **test_edge_cases.py**
   - Empty simulation folder (vspace created 0 sims)
   - Single simulation (edge case for parallelism)
   - Simulation failure (vplanet returns non-zero exit code)
   - Mixed success/failure scenarios
   - Very large simulation count (10,000+ folders)

5. **test_module_interface.py**
   - Test `RunMultiplanet()` programmatic interface
   - Verify parameters passed correctly
   - Test integration with other VPLanet ecosystem tools

**Unit Tests for Individual Functions:**

6. **test_checkpoint_operations.py**
   - `fnCreateCheckpoint()`: Verify file format
   - `fnRecreateCheckpoint()`: Test status code updates
   - `flistReadCheckpoint()`: Parse various formats
   - `fnUpdateCheckpointStatus()`: Atomic updates with lock

7. **test_file_parsing.py**
   - `ftGetDirectory()`: Various vspace.in formats
   - `flistGetSimulations()`: Empty/single/many folders
   - `ftGetSystemNames()`: Various vpl.in/body.in formats

**Success Criteria:**
- 15+ test modules covering all major code paths
- Edge case coverage >90%
- All tests pass in <5 minutes on 4-core machine

---

## Style Guide Compliance

### Phase 3: Variable Renaming (Priority 3)

**Objective:** Systematically rename all variables to Hungarian notation.

**Approach:**
1. Create variable renaming map (see Section 2 above)
2. Rename in order of scope (global → module → function → local)
3. Use IDE refactoring tools where possible
4. Run tests after each batch of 10 renames
5. Commit after each module completed

**Renaming Order:**
1. `multiplanet.py` - Main module (largest impact)
2. `mpstatus.py` - Status module
3. `multiplanet_module.py` - Module interface
4. Test files (test_*.py)

**Risk Mitigation:**
- Each rename is a separate commit
- Tests run after every commit
- Use exact string matching (avoid regex)

---

### Phase 4: Function Renaming (Priority 4)

**Objective:** Rename all functions to Hungarian notation with action verbs.

**Renaming Map:**

| Old Name | New Name | Rationale |
|---|---|---|
| `GetDir()` | `ftGetDirectory()` | Returns tuple (str, list) |
| `GetSims()` | `flistGetSimulations()` | Returns list |
| `GetSNames()` | `ftGetSystemNames()` | Returns tuple (str, list) |
| `CreateCP()` | `fnCreateCheckpoint()` | No return (creates file) |
| `ReCreateCP()` | `fnRecreateCheckpoint()` | No return (modifies file) |
| `parallel_run_planet()` | `fnRunParallel()` | No return (orchestrator) |
| `par_worker()` | `fnParallelWorker()` | No return (worker loop) |
| `Arguments()` | `fnParseArguments()` | No return (calls fnRunParallel) |
| `mpstatus()` | `fnPrintStatus()` | No return (prints output) |
| `RunMultiplanet()` | `fnRunMultiplanet()` | No return (wrapper) |

**Public API Consideration:**
- `RunMultiplanet()` may be used by external scripts
- Add deprecation warning for 1 release cycle
- Maintain old name as alias: `RunMultiplanet = fnRunMultiplanet`

**Approach:**
1. Rename function definitions
2. Update all call sites in same commit
3. Update entry points in setup.py
4. Update documentation
5. Run full test suite

---

## Code Refactoring

### Phase 5: Function Decomposition (Priority 5)

**Objective:** Break functions >20 lines into single-purpose units.

#### 5.1 Refactor `fnParallelWorker()` (113 lines → 6 functions)

**New Function Signatures:**

```python
def fbAcquireNextSimulation(sCheckpointFile, lockCheckpoint):
    """
    Acquire lock and find next pending simulation.

    Returns: (bSuccess, sSimFolder)
    """
    pass

def fnUpdateCheckpointStatus(sCheckpointFile, sSimFolder, iStatus, lockCheckpoint):
    """
    Atomically update simulation status in checkpoint file.

    Status codes: -1=pending, 0=in progress, 1=complete
    """
    pass

def fiExecuteVplanet(sSimFolder, bVerbose):
    """
    Execute vplanet in simulation folder.

    Returns: iReturnCode (0=success, non-zero=failure)
    """
    pass

def fnGatherBigplanetData(sSimFolder, sSystemName, listBodies, sLogFile,
                          listInFiles, h5File, bVerbose):
    """
    Collect vplanet output into BigPlanet HDF5 archive.
    """
    pass

def fnParallelWorker(sCheckpointFile, sSystemName, listBodies, sLogFile,
                     listInFiles, bVerbose, lockCheckpoint, bBigplanet, sH5File):
    """
    Worker process loop: acquire sim, execute, update status.
    """
    while True:
        bSuccess, sSimFolder = fbAcquireNextSimulation(sCheckpointFile, lockCheckpoint)
        if not bSuccess:
            return

        fnUpdateCheckpointStatus(sCheckpointFile, sSimFolder, 0, lockCheckpoint)
        iReturnCode = fiExecuteVplanet(sSimFolder, bVerbose)

        if iReturnCode == 0:
            fnUpdateCheckpointStatus(sCheckpointFile, sSimFolder, 1, lockCheckpoint)
            if bBigplanet:
                fnGatherBigplanetData(sSimFolder, sSystemName, listBodies,
                                      sLogFile, listInFiles, sH5File, bVerbose)
        else:
            fnUpdateCheckpointStatus(sCheckpointFile, sSimFolder, -1, lockCheckpoint)
```

**Benefits:**
- Each function <20 lines
- Single responsibility principle
- Easier to unit test
- Lock management isolated

#### 5.2 Refactor `fnRunParallel()` (55 lines → 4 functions)

**New Function Signatures:**

```python
def fnInitializeCheckpoint(sCheckpointFile, sInputFile, listSims,
                           bVerbose, bForce, sFolder):
    """
    Create new checkpoint or restore existing one.
    """
    pass

def flistCreateWorkers(iCores, sCheckpointFile, sSystemName, listBodies,
                       sLogFile, listInFiles, bVerbose, lockCheckpoint,
                       bBigplanet, sH5File):
    """
    Create worker processes for parallel execution.

    Returns: listWorkers
    """
    pass

def fnExecuteWorkers(listWorkers, bVerbose):
    """
    Start workers, wait for completion.
    """
    pass

def fnCleanupArchive(sH5File, bBigplanet):
    """
    Remove BigPlanet archive if not requested.
    """
    pass

def fnRunParallel(sInputFile, iCores, bQuiet, bVerbose, bBigplanet, bForce):
    """
    Orchestrate parallel VPLanet simulation execution.
    """
    sFolder, listInFiles = ftGetDirectory(sInputFile)
    listSims = flistGetSimulations(sFolder)
    sSystemName, listBodies = ftGetSystemNames(listInFiles, listSims)

    sLogFile = sSystemName + ".log"
    sCheckpointFile = os.getcwd() + "/." + sFolder

    fnInitializeCheckpoint(sCheckpointFile, sInputFile, listSims,
                          bVerbose, bForce, sFolder)

    lockCheckpoint = mp.Lock()
    sH5File = os.getcwd() + "/" + sFolder + ".bpa"

    listWorkers = flistCreateWorkers(iCores, sCheckpointFile, sSystemName,
                                     listBodies, sLogFile, listInFiles,
                                     bVerbose, lockCheckpoint, bBigplanet, sH5File)

    fnExecuteWorkers(listWorkers, bVerbose)
    fnCleanupArchive(sH5File, bBigplanet)
```

#### 5.3 Refactor `fnRecreateCheckpoint()` (39 lines → 3 functions)

**New Function Signatures:**

```python
def flistReadCheckpoint(sCheckpointFile):
    """
    Parse checkpoint file into list of [path, status] pairs.

    Returns: listData
    """
    pass

def fnResetIncompleteSimulations(listData):
    """
    Mark in-progress simulations (status=0) as pending (status=-1).
    """
    pass

def fnWriteCheckpoint(sCheckpointFile, listData):
    """
    Write checkpoint data to file.
    """
    pass

def fbCheckCompletionStatus(listData, sFolder, sCheckpointFile,
                            sInputFile, listSims, bForce, bVerbose):
    """
    Check if all sims complete; handle force rerun if requested.

    Returns: bShouldExit
    """
    pass

def fnRecreateCheckpoint(sCheckpointFile, sInputFile, bVerbose, listSims,
                         sFolder, bForce):
    """
    Restore checkpoint from previous run, handling incomplete sims.
    """
    if bVerbose:
        print("WARNING: multi-planet checkpoint file already exists!")

    listData = flistReadCheckpoint(sCheckpointFile)
    fnResetIncompleteSimulations(listData)
    fnWriteCheckpoint(sCheckpointFile, listData)

    bShouldExit = fbCheckCompletionStatus(listData, sFolder, sCheckpointFile,
                                          sInputFile, listSims, bForce, bVerbose)
    if bShouldExit:
        exit()
```

---

### Phase 6: Architecture Improvements (Priority 6)

**Objective:** Fix architectural issues and improve robustness.

#### 6.1 Remove `os.chdir()` Dependency

**Current Issue:** multiplanet.py:239, 307

**Solution:**
```python
# OLD (multiplanet.py:239-256)
os.chdir(sSimFolder)
with open("vplanet_log", "a+") as vplf:
    vplanet = sub.Popen("vplanet vpl.in", shell=True, ...)
os.chdir("../../")

# NEW
sLogPath = os.path.join(sSimFolder, "vplanet_log")
with open(sLogPath, "a+") as vplf:
    vplanet = sub.Popen(["vplanet", "vpl.in"], cwd=sSimFolder, ...)
```

**Benefits:**
- No global state changes
- Thread-safe (future-proof)
- No hardcoded relative paths

#### 6.2 Eliminate `shell=True` Security Risk

**Current Issue:** multiplanet.py:245

**Solution:**
```python
# OLD
sub.Popen("vplanet vpl.in", shell=True, ...)

# NEW
sub.Popen(["vplanet", "vpl.in"], cwd=sSimFolder, ...)
```

#### 6.3 Fix Subprocess Return Code Checking

**Current Issue:** multiplanet.py:250, 264

**Solution:**
```python
# OLD
vplanet = sub.Popen(...)
return_code = vplanet.poll()  # Returns None if still running!
# ... later
if return_code is None:  # WRONG: means "still running", not "success"
    # mark complete

# NEW
vplanet = sub.Popen(...)
for line in vplanet.stderr:
    vplf.write(line)
for line in vplanet.stdout:
    vplf.write(line)
iReturnCode = vplanet.wait()  # Wait for completion, get return code

if iReturnCode == 0:  # Explicit success check
    # mark complete
else:
    # mark failed
```

#### 6.4 Add Comprehensive Error Handling

**Locations Needing try/except:**

```python
# File I/O operations
def flistReadCheckpoint(sCheckpointFile):
    try:
        with open(sCheckpointFile, "r") as f:
            # ...
    except FileNotFoundError:
        raise IOError(f"Checkpoint file not found: {sCheckpointFile}")
    except PermissionError:
        raise IOError(f"Permission denied reading checkpoint: {sCheckpointFile}")

# Subprocess calls
def fiExecuteVplanet(sSimFolder, bVerbose):
    try:
        vplanet = sub.Popen(["vplanet", "vpl.in"], cwd=sSimFolder, ...)
        # ...
    except FileNotFoundError:
        raise OSError("vplanet executable not found. Is it in PATH?")
    except PermissionError:
        raise OSError(f"Permission denied executing vplanet in {sSimFolder}")

# Lock operations (add timeout)
lockCheckpoint.acquire(timeout=300)  # 5 min timeout
if not lockCheckpoint.acquire(timeout=300):
    raise TimeoutError("Failed to acquire checkpoint lock after 5 minutes")
```

#### 6.5 Structured Checkpoint Format

**Current:** Text file with space-separated values
**Proposed:** JSON for structure, readability, and extensibility

```python
# Current format (.MP_Folder):
Vspace File: /path/to/vspace.in
Total Number of Simulations: 100
/path/to/sim1 -1
/path/to/sim2 1
...
THE END

# Proposed JSON format (.MP_Folder.json):
{
    "vspace_file": "/path/to/vspace.in",
    "total_simulations": 100,
    "simulations": [
        {"path": "/path/to/sim1", "status": "pending"},
        {"path": "/path/to/sim2", "status": "complete"},
        ...
    ],
    "status_codes": {
        "pending": -1,
        "in_progress": 0,
        "complete": 1
    }
}
```

**Benefits:**
- Self-documenting status codes
- Easier to extend (add timestamps, error messages, etc.)
- Standard library support (no dependencies)
- Validation with JSON schema

**Implementation:**
- Maintain backward compatibility: detect format, auto-convert
- Add `--checkpoint-format` flag (text, json)
- Default to JSON for new runs

#### 6.6 Implement `email` Parameter

**Current:** Defined in `multiplanet_module.py:20` but unused

**Options:**
1. **Remove parameter** (simplest, breaks API)
2. **Implement email notifications:**
   - Send email on completion
   - Send email on failure
   - Use `smtplib` (stdlib) or external service (sendgrid, mailgun)

**Recommendation:** Remove parameter with deprecation warning. Email functionality better suited for external orchestration layer (cron, Airflow, etc.) rather than core library.

---

## Documentation Updates

### Phase 7: Inline Documentation (Priority 7)

**Objective:** Add docstrings and comments per style guide ("use sparingly").

**Docstring Standard:**

```python
def ftGetDirectory(sVspaceFile):
    """
    Extract destination folder and input file list from vspace file.

    Parameters
    ----------
    sVspaceFile : str
        Path to vspace input file

    Returns
    -------
    tuple (str, list)
        Destination folder name and list of body input files

    Raises
    ------
    IOError
        If destfolder not specified in vspace file
        If destination folder does not exist
    """
```

**Key Locations for Comments:**

1. **Checkpoint status codes** (multiplanet.py:151, 165, 223, etc.)
   ```python
   # Status codes: -1=pending, 0=in progress, 1=complete
   sStatus = "-1"
   ```

2. **Lock acquisition rationale** (multiplanet.py:210, 257)
   ```python
   # Acquire lock to prevent race condition when reading/updating checkpoint
   lockCheckpoint.acquire()
   ```

3. **BigPlanet integration** (multiplanet.py:271-292)
   ```python
   # Gather simulation output into BigPlanet HDF5 archive group
   if bBigplanet:
       # ...
   ```

**Docstring Coverage Goal:** >80% of public functions

---

### Phase 8: README and Sphinx Updates (Priority 8)

**Objective:** Update documentation to reflect refactored code.

**README Updates:**

1. Add usage example:
   ```bash
   # Generate parameter sweep
   vspace vspace.in

   # Run simulations in parallel (uses all cores)
   multiplanet vspace.in

   # Check status
   mpstatus vspace.in

   # Run with BigPlanet archive creation
   multiplanet vspace.in --bigplanet

   # Force rerun if complete
   multiplanet vspace.in --force
   ```

2. Add troubleshooting section:
   - Checkpoint file location
   - How to reset runs
   - Common errors

3. Update Python version badge (3.9-3.14)

**Sphinx Documentation Updates:**

1. **help.rst:** Update function names, add examples
2. **mpstatus.rst:** Add checkpoint format documentation
3. Add **api.rst** with module reference:
   - `multiplanet` module
   - `mpstatus` module
   - `multiplanet_module` module
4. Add **architecture.rst** explaining:
   - Checkpoint system
   - Worker pool design
   - BigPlanet integration
   - Lock-based synchronization

---

## Implementation Timeline

### Sprint 1: Testing Foundation (Weeks 1-2)

| Task | Estimated Effort | Assignee | Dependencies |
|---|---|---|---|
| Update BigPlanet API calls | 2 days | Developer | BigPlanet docs |
| Re-enable test_parallel.py | 1 day | Developer | BigPlanet update |
| Re-enable test_serial.py | 0.5 day | Developer | BigPlanet update |
| Re-enable test_checkpoint.py | 1 day | Developer | BigPlanet update |
| Re-enable test_mpstatus.py | 0.5 day | Developer | BigPlanet update |
| Re-enable test_bigplanet.py | 1 day | Developer | BigPlanet update |
| Verify CI passes | 1 day | Developer | All tests re-enabled |

**Deliverable:** All 5 tests passing on macOS/Linux/Python 3.9-3.14

---

### Sprint 2: Expanded Testing (Weeks 3-4)

| Task | Estimated Effort | Assignee | Dependencies |
|---|---|---|---|
| test_error_handling.py | 2 days | Developer | Sprint 1 |
| test_force_flag.py | 1 day | Developer | Sprint 1 |
| test_verbose_quiet.py | 1 day | Developer | Sprint 1 |
| test_edge_cases.py | 2 days | Developer | Sprint 1 |
| test_module_interface.py | 1 day | Developer | Sprint 1 |
| test_checkpoint_operations.py | 1 day | Developer | Sprint 1 |
| test_file_parsing.py | 1 day | Developer | Sprint 1 |
| Coverage analysis | 0.5 day | Developer | All new tests |

**Deliverable:** 15+ test modules, >90% coverage

---

### Sprint 3: Style Compliance (Weeks 5-6)

| Task | Estimated Effort | Assignee | Dependencies |
|---|---|---|---|
| Rename variables in multiplanet.py | 3 days | Developer | Sprint 2 |
| Rename variables in mpstatus.py | 0.5 day | Developer | Sprint 2 |
| Rename variables in multiplanet_module.py | 0.5 day | Developer | Sprint 2 |
| Rename functions in all modules | 2 days | Developer | Variable renames |
| Update setup.py entry points | 0.5 day | Developer | Function renames |
| Update test files | 1 day | Developer | Function renames |
| Full test suite validation | 1 day | Developer | All renames |

**Deliverable:** 100% style guide compliance, all tests passing

---

### Sprint 4: Refactoring (Weeks 7-8)

| Task | Estimated Effort | Assignee | Dependencies |
|---|---|---|---|
| Refactor fnParallelWorker() | 2 days | Developer | Sprint 3 |
| Refactor fnRunParallel() | 1 day | Developer | Sprint 3 |
| Refactor fnRecreateCheckpoint() | 1 day | Developer | Sprint 3 |
| Remove os.chdir() | 1 day | Developer | Worker refactor |
| Fix subprocess return code | 0.5 day | Developer | Worker refactor |
| Eliminate shell=True | 0.5 day | Developer | Worker refactor |
| Add error handling | 2 days | Developer | All refactors |
| JSON checkpoint format | 1 day | Developer | All refactors |
| Full test suite validation | 1 day | Developer | All refactors |

**Deliverable:** All functions <20 lines, architecture improvements implemented

---

### Sprint 5: Documentation (Weeks 9-10)

| Task | Estimated Effort | Assignee | Dependencies |
|---|---|---|---|
| Add docstrings to all public functions | 2 days | Developer | Sprint 4 |
| Add inline comments | 1 day | Developer | Sprint 4 |
| Update README with examples | 1 day | Developer | Sprint 4 |
| Update Sphinx help.rst | 1 day | Developer | Sprint 4 |
| Update Sphinx mpstatus.rst | 0.5 day | Developer | Sprint 4 |
| Create api.rst | 1 day | Developer | Sprint 4 |
| Create architecture.rst | 1 day | Developer | Sprint 4 |
| Build and review docs | 0.5 day | Developer | All doc updates |

**Deliverable:** Complete documentation matching refactored code

---

## Success Metrics

### Code Quality Metrics

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Test coverage | 0% | >90% | pytest-cov |
| Style guide compliance | ~20% | 100% | Manual review |
| Functions >20 lines | 4 | 0 | Manual count |
| Docstring coverage | ~5% | >80% | interrogate |
| Pylint score | Unknown | >8.5/10 | pylint |

### Functional Metrics

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Tests passing | 0/5 | 15+/15+ | pytest |
| CI passing | No | Yes | GitHub Actions |
| Python versions supported | 3.6-3.9 | 3.9-3.14 | CI matrix |
| Platform support | macOS, Linux | macOS, Linux | CI matrix |

### Performance Metrics (should not regress)

| Metric | Baseline | Post-Refactor | Measurement |
|---|---|---|---|
| 100-sim execution time | TBD | ±5% | time multiplanet |
| Memory per worker | TBD | ±10% | memory_profiler |
| Checkpoint I/O latency | TBD | ±20% | Custom timer |

---

## Risk Assessment

### High Risk

1. **BigPlanet API compatibility**
   - **Mitigation:** Coordinate with BigPlanet maintainers, verify API stability
   - **Contingency:** Pin BigPlanet version in requirements

2. **Test infrastructure complexity**
   - **Mitigation:** Start with simplest test (serial), build incrementally
   - **Contingency:** Mock vplanet calls if integration tests too fragile

### Medium Risk

3. **Variable renaming introduces bugs**
   - **Mitigation:** Rename in small batches, run tests after each batch
   - **Contingency:** Git revert if tests fail

4. **Function decomposition changes behavior**
   - **Mitigation:** Extensive unit tests before refactoring
   - **Contingency:** Feature flag to enable/disable refactored code paths

### Low Risk

5. **Documentation updates lag code changes**
   - **Mitigation:** Update docs in same commit as code changes
   - **Contingency:** Dedicated documentation sprint at end

6. **Performance regression from refactoring**
   - **Mitigation:** Profile before and after, optimize hot paths
   - **Contingency:** Inline critical functions if needed

---

## Open Questions for Discussion

1. **JSON vs text checkpoint format:** Should we maintain text format for backward compatibility, or force migration to JSON?

2. **Email parameter:** Remove entirely or implement? If implement, what service?

3. **Python version support:** README says 3.6-3.9, but environment.yml and CI only test 3.6-3.9. Should we drop 3.6-3.8 support (EOL) and add 3.10-3.14?

4. **Deprecation policy:** Should we maintain old function names as aliases for one release cycle, or break API immediately?

5. **BigPlanet integration:** Should BigPlanet archive creation be moved to a separate command (`multiplanet` → `bigplanet`) or kept as flag?

6. **Test data:** Should we use actual VPLanet simulations in tests (slow, realistic) or mocked executables (fast, fragile)?

7. **Lock timeout:** What timeout is appropriate for checkpoint lock acquisition? Current: no timeout (infinite wait)

---

## Future Enhancements (Post-Upgrade)

These are **not** part of the current upgrade plan but should be considered for future development:

1. **Progress bar integration:** Add tqdm progress bar for better UX
2. **Distributed execution:** Support for multiple machines (Dask, Ray)
3. **Checkpoint compression:** gzip checkpoint for large sweeps
4. **Simulation prioritization:** Allow user to specify execution order
5. **Automatic retry logic:** Retry failed simulations N times before marking failed
6. **Resource limits:** CPU/memory limits per worker
7. **Web dashboard:** Real-time status monitoring via web interface
8. **Logging infrastructure:** Replace print() with proper logging module
9. **Configuration file:** .multiplanetrc for default settings
10. **Integration tests:** Test interaction with vspace, bigplanet, vplot in realistic workflows

---

## Appendix A: File Inventory

### Source Code Files

| File | Lines | Functions | Test Coverage |
|---|---|---|---|
| multiplanet/multiplanet.py | 371 | 7 | 0% |
| multiplanet/mpstatus.py | 51 | 2 | 0% |
| multiplanet/multiplanet_module.py | 22 | 1 | 0% |
| **Total** | **444** | **10** | **0%** |

### Test Files

| File | Status | Assertions |
|---|---|---|
| tests/Parallel/test_parallel.py | Disabled | 0 (3 commented) |
| tests/Serial/test_serial.py | Disabled | 0 (3 commented) |
| tests/Checkpoint/test_checkpoint.py | Disabled | 0 (3 commented) |
| tests/MpStatus/test_mpstatus.py | Disabled | 0 (3 commented) |
| tests/Bigplanet/test_bigplanet.py | Disabled | 0 (2 commented) |

### Documentation Files

| File | Purpose | Status |
|---|---|---|
| README.md | Project overview | Current |
| docs/index.rst | Main landing page | Current |
| docs/install.rst | Installation guide | Current |
| docs/help.rst | Usage documentation | Current |
| docs/mpstatus.rst | Status command docs | Current |

---

## Appendix B: Code Complexity Analysis

### Cyclomatic Complexity

| Function | Complexity | Classification |
|---|---|---|---|
| `par_worker()` | 12 | High (should be <10) |
| `parallel_run_planet()` | 6 | Medium |
| `ReCreateCP()` | 8 | Medium |
| `GetSNames()` | 7 | Medium |
| `GetDir()` | 5 | Low |
| `GetSims()` | 2 | Low |
| `CreateCP()` | 2 | Low |
| `mpstatus()` | 6 | Medium |
| `Arguments()` | 3 | Low |
| `RunMultiplanet()` | 1 | Low |

**Target:** All functions <10 complexity after refactoring

---

## Appendix C: Dependency Analysis

### Direct Dependencies

| Package | Current Version | Purpose | Risk |
|---|---|---|---|
| numpy | Any | Array operations (minimal use) | Low |
| h5py | Any | HDF5 file I/O for BigPlanet | Low |
| pandas | Any | Data manipulation (minimal use) | Low |
| scipy | Any | Scientific computing (minimal use) | Low |
| argparse | stdlib | CLI argument parsing | None |
| multiprocessing | stdlib | Parallel execution | None |
| subprocess | stdlib | vplanet process spawning | None |
| os | stdlib | File system operations | None |
| **vspace** | Latest | Parameter sweep generation | **Medium** |
| **bigplanet** | Latest | Archive creation | **High** |

### Dependency Concerns

1. **BigPlanet API stability:** Tests disabled due to API changes. Need to coordinate upgrades.
2. **Unused dependencies:** pandas, scipy imported but barely used. Consider removing.
3. **Version pinning:** No version constraints in setup.py. Should pin major versions.

---

## Appendix D: Git History Analysis

### Recent Commits

| Commit | Date | Message | Impact |
|---|---|---|---|
| b5b83b2 | Recent | "Merge pull request #17 from VirtualPlanetaryLaboratory/BPCompat" | BigPlanet compatibility |
| 6943a5c | Recent | "Temporarily not testing multiplanet at all." | **All tests disabled** |
| 84ad95e | Recent | "Temporary commit that removes tests' references to bigplanet..." | BigPlanet breakage |
| 6a7e03d | Recent | "Updated files to account for name changes in bigplanet." | BigPlanet API change |

**Key Insight:** Recent BigPlanet refactoring broke multiplanet tests. Coordination needed for future changes.

---

## Appendix E: Comparison with Sibling Repositories

### vspace Style Compliance

**Assessed:** Should verify vspace follows same style guide for consistency.

### bigplanet Style Compliance

**Assessed:** Should verify bigplanet follows same style guide for consistency.

### Consistency Recommendation

Once multiplanet achieves 100% compliance, use it as template for upgrading vspace and bigplanet. Consider creating shared style guide enforcement tools:
- Pre-commit hooks for Hungarian notation
- Pylint custom plugin to check function length
- Automated variable name validator

---

## Document Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2025-12-28 | Claude | Initial comprehensive assessment and upgrade plan |

---

**End of Upgrade Plan**
