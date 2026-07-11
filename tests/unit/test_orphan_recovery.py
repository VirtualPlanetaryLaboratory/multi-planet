"""
Unit tests for orphaned-simulation detection, re-dispatch, and reporting.

A worker killed mid-simulation (e.g. OOM/SIGKILL under CPU core
oversubscription) leaves its simulation stranded at checkpoint status "0"
and never re-dispatches it. Historically the run then reported success with
fewer simulations than requested, silently biasing results. These tests cover
the detection, bounded re-dispatch, loud warning, and non-zero exit code that
close that gap.
"""

import os
import tempfile
import multiprocessing as mp
import pytest
from unittest import mock

from multiplanet import multiplanet, mpstatus


@pytest.fixture(autouse=True)
def fnRestoreCwd():
    """Restore the working directory after tests that chdir into tmp_path."""
    sOriginal = os.getcwd()
    yield
    os.chdir(sOriginal)


def fnWriteCheckpoint(sPath, listRows):
    """Write a checkpoint file from a list of (folder, status) rows."""
    with open(sPath, "w") as f:
        f.write("Vspace File: /test/vspace.in\n")
        f.write("Total Number of Simulations: %d\n" % len(listRows))
        for sFolder, sStatus in listRows:
            f.write("%s %s\n" % (sFolder, sStatus))
        f.write("THE END\n")


def fnSetStatuses(sPath, dictStatus):
    """Rewrite checkpoint statuses for the given folders (simulate workers)."""
    listOut = []
    with open(sPath, "r") as f:
        for sLine in f:
            listParts = sLine.strip().split()
            if len(listParts) > 1 and listParts[0] in dictStatus:
                listParts[1] = dictStatus[listParts[0]]
            listOut.append(" ".join(listParts))
    with open(sPath, "w") as f:
        f.write("\n".join(listOut) + "\n")


class TestCountingHelpers:
    """Tests for the checkpoint-counting helpers."""

    def test_count_incomplete_counts_zero_and_pending(self, tmp_path):
        """Status 0 (in-progress/orphaned) and -1 (pending) count as incomplete."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "0"), ("c", "-1"), ("d", "1")])
        assert multiplanet.fiCountIncompleteSimulations(sCp) == 2

    def test_count_incomplete_all_done_is_zero(self, tmp_path):
        """A fully completed run has zero incomplete simulations."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "1")])
        assert multiplanet.fiCountIncompleteSimulations(sCp) == 0

    def test_count_total_ignores_header_and_end(self, tmp_path):
        """Total counts only simulation rows, not header or THE END markers."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "0"), ("c", "-1")])
        assert multiplanet.fiCountTotalSimulations(sCp) == 3


class TestRequeueOrphans:
    """Tests for fnRequeueOrphanedSimulations."""

    def test_requeue_resets_only_orphans(self, tmp_path):
        """Status 0 becomes -1; completed (1) and pending (-1) are untouched."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "0"), ("c", "-1"), ("d", "0")])
        multiplanet.fnRequeueOrphanedSimulations(sCp, mp.Lock())

        with open(sCp, "r") as f:
            sContent = f.read()
        assert "a 1" in sContent
        assert "b -1" in sContent  # orphan requeued
        assert "c -1" in sContent
        assert "d -1" in sContent  # orphan requeued
        assert " 0" not in sContent


class TestReportCompletion:
    """Tests for the completion report / exit-code logic."""

    def test_report_incomplete_warns_and_returns_nonzero(self, tmp_path, capsys):
        """An incomplete run prints a loud warning and returns exit code 1."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "0"), ("c", "1")])
        iCode = multiplanet.fiReportCompletion(sCp, bQuiet=False)

        captured = capsys.readouterr()
        assert iCode == 1
        assert "WARNING" in captured.out
        assert "1 of 3 simulations did not complete" in captured.out
        assert "NOT byte-reproducible" in captured.out

    def test_report_complete_returns_zero(self, tmp_path, capsys):
        """A fully completed run returns exit code 0 with no warning."""
        sCp = str(tmp_path / ".cp")
        fnWriteCheckpoint(sCp, [("a", "1"), ("b", "1")])
        iCode = multiplanet.fiReportCompletion(sCp, bQuiet=False)

        captured = capsys.readouterr()
        assert iCode == 0
        assert "WARNING" not in captured.out
        assert "completed successfully" in captured.out


class TestParallelRunOrphanRecovery:
    """End-to-end tests of parallel_run_planet's orphan handling (worker pool mocked)."""

    def _setup(self, tmp_path):
        os.chdir(tmp_path)
        patcher_dir = mock.patch(
            "multiplanet.multiplanet.GetDir",
            return_value=("TestSims", ["vpl.in", "earth.in"]),
        )
        patcher_sims = mock.patch(
            "multiplanet.multiplanet.GetSims",
            return_value=["sim_001", "sim_002", "sim_003"],
        )
        patcher_names = mock.patch(
            "multiplanet.multiplanet.GetSNames",
            return_value=("Sys", ["Earth"]),
        )
        return patcher_dir, patcher_sims, patcher_names

    def test_orphaned_sim_is_redispatched_and_completes(self, tmp_path, capsys):
        """
        Given: first worker pass leaves one sim orphaned at status 0
        When: parallel_run_planet runs
        Then: the orphan is requeued, re-dispatched, completes, exit code 0
        """
        pd, ps, pn = self._setup(tmp_path)
        with pd, ps, pn:
            # First pass leaves sim_003 orphaned at status 0 (killed worker);
            # the recovery pass then completes it.
            listPasses = [
                {"sim_001": "1", "sim_002": "1", "sim_003": "0"},
                {"sim_003": "1"},
            ]

            def fnPool(iCores, tWorkerArgs, bVerbose):
                fnSetStatuses(tWorkerArgs[0], listPasses.pop(0))

            with mock.patch(
                "multiplanet.multiplanet.fnRunWorkerPool",
                side_effect=fnPool,
            ) as mockPool:
                iCode = multiplanet.parallel_run_planet(
                    "vspace.in", 3, False, False, False, False
                )

        assert iCode == 0
        # Pool ran once, then once more to recover the orphan.
        assert mockPool.call_count == 2
        assert "completed successfully" in capsys.readouterr().out

    def test_persistent_orphan_warns_and_returns_nonzero(self, tmp_path, capsys):
        """
        Given: every worker pass keeps leaving a sim killed at status 0
        When: parallel_run_planet runs
        Then: after bounded retries it warns loudly and returns exit code 1
        """
        pd, ps, pn = self._setup(tmp_path)
        with pd, ps, pn:
            with mock.patch(
                "multiplanet.multiplanet.fnRunWorkerPool"
            ) as mockPool:
                mockPool.side_effect = lambda c, a, v: fnSetStatuses(
                    a[0], {"sim_001": "1", "sim_002": "1", "sim_003": "0"}
                )
                iCode = multiplanet.parallel_run_planet(
                    "vspace.in", 3, False, False, False, False
                )

        assert iCode == 1
        # Initial pass + iMaxOrphanRetries recovery attempts.
        assert mockPool.call_count == 1 + multiplanet.iMaxOrphanRetries
        assert "WARNING" in capsys.readouterr().out

    def test_clean_run_returns_zero_without_retry(self, tmp_path, capsys):
        """
        Given: the worker pass completes every sim on the first try
        When: parallel_run_planet runs
        Then: no re-dispatch occurs and it returns exit code 0
        """
        pd, ps, pn = self._setup(tmp_path)
        with pd, ps, pn:
            with mock.patch(
                "multiplanet.multiplanet.fnRunWorkerPool"
            ) as mockPool:
                mockPool.side_effect = lambda c, a, v: fnSetStatuses(
                    a[0], {"sim_001": "1", "sim_002": "1", "sim_003": "1"}
                )
                iCode = multiplanet.parallel_run_planet(
                    "vspace.in", 3, False, False, False, False
                )

        assert iCode == 0
        assert mockPool.call_count == 1  # no recovery needed
        assert "completed successfully" in capsys.readouterr().out


class TestArgumentsExitCode:
    """Tests that the CLI propagates a non-zero exit code on incomplete runs."""

    def test_arguments_exits_nonzero_on_incomplete(self, tmp_path):
        """Arguments() raises SystemExit(1) when the run reports incompletion."""
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("destfolder TestSims\n")

        with mock.patch("sys.argv", ["multiplanet", str(vspace_file)]):
            with mock.patch("subprocess.getoutput", return_value="help"):
                with mock.patch(
                    "multiplanet.multiplanet.parallel_run_planet",
                    return_value=1,
                ):
                    with pytest.raises(SystemExit) as excinfo:
                        multiplanet.Arguments()
        assert excinfo.value.code == 1

    def test_arguments_no_exit_on_complete(self, tmp_path):
        """Arguments() returns normally (no SystemExit) when the run completes."""
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("destfolder TestSims\n")

        with mock.patch("sys.argv", ["multiplanet", str(vspace_file)]):
            with mock.patch("subprocess.getoutput", return_value="help"):
                with mock.patch(
                    "multiplanet.multiplanet.parallel_run_planet",
                    return_value=0,
                ):
                    multiplanet.Arguments()  # must not raise


class TestMpstatusIncompleteSignal:
    """Tests that mpstatus surfaces incomplete runs and exits non-zero."""

    def test_warn_helper_flags_incomplete(self, capsys):
        """fiWarnIfIncomplete warns and returns 1 when sims remain."""
        iCode = mpstatus.fiWarnIfIncomplete(count_done=2, count_ip=1, count_todo=1)
        captured = capsys.readouterr()
        assert iCode == 1
        assert "WARNING" in captured.out
        assert "2 of 4 simulations have not completed" in captured.out

    def test_warn_helper_silent_when_complete(self, capsys):
        """fiWarnIfIncomplete returns 0 with no warning when all done."""
        iCode = mpstatus.fiWarnIfIncomplete(count_done=3, count_ip=0, count_todo=0)
        assert iCode == 0
        assert "WARNING" not in capsys.readouterr().out

    def test_mpstatus_returns_nonzero_on_orphan(self, tmp_path, capsys):
        """mpstatus returns 1 and warns when a sim is stuck in progress."""
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("header line\ndestfolder OrphanSims\n")
        checkpoint_file = tmp_path / ".OrphanSims"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 3\n"
            "sim_001 1\n"
            "sim_002 0\n"
            "sim_003 1\n"
            "THE END\n"
        )
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            iCode = mpstatus.mpstatus(str(vspace_file))
        finally:
            os.chdir(original_cwd)
        assert iCode == 1
        assert "WARNING" in capsys.readouterr().out

    def test_mpstatus_returns_zero_when_complete(self, tmp_path, capsys):
        """mpstatus returns 0 with no warning when all sims are done."""
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("header line\ndestfolder DoneSims\n")
        checkpoint_file = tmp_path / ".DoneSims"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 2\n"
            "sim_001 1\n"
            "sim_002 1\n"
            "THE END\n"
        )
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            iCode = mpstatus.mpstatus(str(vspace_file))
        finally:
            os.chdir(original_cwd)
        assert iCode == 0
        assert "WARNING" not in capsys.readouterr().out
