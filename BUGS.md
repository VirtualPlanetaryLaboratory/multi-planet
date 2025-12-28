# Known Bugs in MultiPlanet

This document tracks critical bugs discovered during the testing infrastructure restoration.

## Critical: Incorrect Subprocess Return Code Handling

**Location:** [multiplanet/multiplanet.py:250-264](multiplanet/multiplanet.py:250-264)

**Severity:** HIGH - Causes incorrect success/failure classification of simulations

**Discovered:** 2025-12-28 during test restoration

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

### Testing Status

**NOT YET FIXED** - This bug will be addressed in Sprint 4 (Refactoring phase) as documented in [claude.md](claude.md). The current test restoration work accepts this bug to maintain separation between testing and refactoring phases.

### Workaround

Currently, tests may show false positives. Manual verification of output files is recommended:
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
