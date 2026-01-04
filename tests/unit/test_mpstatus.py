"""
Unit tests for mpstatus module.

Tests the mpstatus function and CLI argument parsing.
"""

import os
import tempfile
import pytest
from unittest import mock

from multiplanet import mpstatus


class TestMpstatus:
    """Tests for mpstatus function."""

    def test_mpstatus_all_pending(self, tmp_path, capsys):
        """Count all simulations as pending (status -1)."""
        # Create vspace.in
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "destfolder TestSims\n"
        )

        # Create checkpoint file with all pending
        checkpoint_file = tmp_path / ".TestSims"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 3\n"
            "sim_001 -1\n"
            "sim_002 -1\n"
            "sim_003 -1\n"
            "THE END\n"
        )

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mpstatus.mpstatus(str(vspace_file))
            captured = capsys.readouterr()

            assert "Number of Simulations completed: 0" in captured.out
            assert "Number of Simulations in progress: 0" in captured.out
            assert "Number of Simulations remaining: 3" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_mpstatus_mixed_status(self, tmp_path, capsys):
        """Count simulations with mixed statuses."""
        # Create vspace.in (mpstatus reads line [1], so need header line)
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("header line\ndestfolder MixedSims\n")

        # Create checkpoint with mixed statuses
        checkpoint_file = tmp_path / ".MixedSims"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 5\n"
            "sim_001 1\n"
            "sim_002 0\n"
            "sim_003 -1\n"
            "sim_004 -1\n"
            "sim_005 1\n"
            "THE END\n"
        )

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mpstatus.mpstatus(str(vspace_file))
            captured = capsys.readouterr()

            assert "Number of Simulations completed: 2" in captured.out
            assert "Number of Simulations in progress: 1" in captured.out
            assert "Number of Simulations remaining: 2" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_mpstatus_no_checkpoint(self, tmp_path):
        """Raise exception if checkpoint file missing."""
        # Create vspace.in but no checkpoint (need header line)
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("header line\ndestfolder NoCheckpoint\n")

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            with pytest.raises(Exception, match="Multi-Planet must be running"):
                mpstatus.mpstatus(str(vspace_file))
        finally:
            os.chdir(original_cwd)

    def test_mpstatus_folder_parsing(self, tmp_path, capsys):
        """Parse destination folder from vspace file."""
        # Create vspace.in with custom folder name (need header line)
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("header line\ndestfolder CustomFolderName\n")

        # Create checkpoint for custom folder
        checkpoint_file = tmp_path / ".CustomFolderName"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 1\n"
            "sim_001 1\n"
            "THE END\n"
        )

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            mpstatus.mpstatus(str(vspace_file))
            captured = capsys.readouterr()

            # Verify it successfully parsed and read the checkpoint
            assert "Number of Simulations completed: 1" in captured.out
        finally:
            os.chdir(original_cwd)


class TestMpstatusArguments:
    """Tests for mpstatus Arguments function."""

    def test_mpstatus_arguments_parsing(self, tmp_path):
        """Parse input file argument correctly."""
        # Create vspace.in and checkpoint
        vspace_file = tmp_path / "test_vspace.in"
        vspace_file.write_text("destfolder TestArgs\n")

        checkpoint_file = tmp_path / ".TestArgs"
        checkpoint_file.write_text(
            "Vspace File: /test/vspace.in\n"
            "Total Number of Simulations: 1\n"
            "sim_001 -1\n"
            "THE END\n"
        )

        # Mock sys.argv
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            with mock.patch('sys.argv', ['mpstatus', str(vspace_file)]):
                # Mock mpstatus function to verify it's called
                with mock.patch('multiplanet.mpstatus.mpstatus') as mock_mpstatus:
                    mpstatus.Arguments()
                    mock_mpstatus.assert_called_once_with(str(vspace_file))
        finally:
            os.chdir(original_cwd)
