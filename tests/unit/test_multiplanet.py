"""
Unit tests for multiplanet module helper functions.

Tests the core functionality including checkpoint management, simulation
marking, and helper utilities.
"""

import os
import tempfile
import multiprocessing as mp
import pytest
from unittest import mock

from multiplanet import multiplanet


class TestCheckpointFunctions:
    """Tests for checkpoint file management functions."""

    def test_get_next_simulation_basic(self):
        """
        Given: Checkpoint file with pending simulations
        When: fnGetNextSimulation is called
        Then: Returns first pending simulation and marks it in-progress
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("sim_folder_1 -1\n")
            f.write("sim_folder_2 -1\n")
            f.write("sim_folder_3 -1\n")
            checkpoint_file = f.name

        try:
            lock = mp.Lock()

            # Get first simulation
            folder = multiplanet.fnGetNextSimulation(checkpoint_file, lock)

            assert folder == os.path.abspath("sim_folder_1")

            # Verify checkpoint file was updated
            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()
            assert "sim_folder_1 0\n" in lines
            assert "sim_folder_2 -1\n" in lines

        finally:
            os.unlink(checkpoint_file)

    def test_get_next_simulation_all_complete(self):
        """
        Given: Checkpoint file with all simulations complete
        When: fnGetNextSimulation is called
        Then: Returns None
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("sim_folder_1 1\n")
            f.write("sim_folder_2 1\n")
            checkpoint_file = f.name

        try:
            lock = mp.Lock()
            folder = multiplanet.fnGetNextSimulation(checkpoint_file, lock)
            assert folder is None

        finally:
            os.unlink(checkpoint_file)

    def test_mark_simulation_complete(self):
        """
        Given: Checkpoint file with in-progress simulation
        When: fnMarkSimulationComplete is called
        Then: Marks simulation as complete (status 1)
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("sim_folder_1 0\n")
            f.write("sim_folder_2 -1\n")
            checkpoint_file = f.name

        try:
            lock = mp.Lock()
            multiplanet.fnMarkSimulationComplete(checkpoint_file, "sim_folder_1", lock)

            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()
            assert "sim_folder_1 1\n" in lines
            assert "sim_folder_2 -1\n" in lines

        finally:
            os.unlink(checkpoint_file)

    def test_mark_simulation_failed(self):
        """
        Given: Checkpoint file with in-progress simulation
        When: fnMarkSimulationFailed is called
        Then: Marks simulation as failed (status -1 for retry)
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("sim_folder_1 0\n")
            f.write("sim_folder_2 -1\n")
            checkpoint_file = f.name

        try:
            lock = mp.Lock()
            multiplanet.fnMarkSimulationFailed(checkpoint_file, "sim_folder_1", lock)

            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()
            assert "sim_folder_1 -1\n" in lines  # Failed simulations reset to -1 for retry
            assert "sim_folder_2 -1\n" in lines

        finally:
            os.unlink(checkpoint_file)


class TestGetSNames:
    """Tests for GetSNames function."""

    def test_get_snames_exists(self):
        """
        Test that GetSNames function exists and is callable.
        """
        assert hasattr(multiplanet, 'GetSNames')
        assert callable(multiplanet.GetSNames)


class TestCreateCP:
    """Tests for CreateCP function."""

    def test_create_cp_basic(self):
        """Create checkpoint file with correct format."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            checkpoint_file = f.name

        try:
            input_file = "test_vspace.in"
            sims = ["sim_001", "sim_002", "sim_003"]

            # Call CreateCP
            multiplanet.CreateCP(checkpoint_file, input_file, sims)

            # Read checkpoint file
            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()

            # Verify header
            assert "Vspace File:" in lines[0]
            assert input_file in lines[0]
            assert "Total Number of Simulations: 3" in lines[1]

            # Verify each sim has status -1
            assert "sim_001 -1" in lines[2]
            assert "sim_002 -1" in lines[3]
            assert "sim_003 -1" in lines[4]

            # Verify ends with "THE END"
            assert "THE END" in lines[5]

        finally:
            os.unlink(checkpoint_file)

    def test_create_cp_header_format(self):
        """Verify header contains vspace file path and count."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            checkpoint_file = f.name

        try:
            input_file = "my_vspace.in"
            sims = ["sim_a", "sim_b"]

            multiplanet.CreateCP(checkpoint_file, input_file, sims)

            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()

            # Verify line 1 format
            assert lines[0].startswith("Vspace File:")
            assert os.getcwd() in lines[0]
            assert input_file in lines[0]

            # Verify line 2 format
            assert lines[1].strip() == "Total Number of Simulations: 2"

        finally:
            os.unlink(checkpoint_file)


class TestReCreateCP:
    """Tests for ReCreateCP function."""

    def test_recreate_cp_reset_in_progress(self):
        """Reset in-progress simulations (0 → -1)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Vspace File: /test/vspace.in\n")
            f.write("Total Number of Simulations: 3\n")
            f.write("sim_001 0\n")  # in-progress
            f.write("sim_002 -1\n")  # pending
            f.write("sim_003 0\n")  # in-progress
            f.write("THE END\n")
            checkpoint_file = f.name

        try:
            sims = ["sim_001", "sim_002", "sim_003"]
            multiplanet.ReCreateCP(checkpoint_file, "vspace.in", False, sims, "folder", False)

            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()

            # Verify all status=0 changed to -1
            assert "sim_001 -1" in lines[2]
            assert "sim_002 -1" in lines[3]
            assert "sim_003 -1" in lines[4]

        finally:
            os.unlink(checkpoint_file)

    def test_recreate_cp_append_missing_sims(self):
        """Append simulations added after initial checkpoint."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Vspace File: /test/vspace.in\n")
            f.write("Total Number of Simulations: 2\n")
            f.write("sim_001 -1\n")
            f.write("sim_002 -1\n")
            # Missing "THE END" - this triggers append behavior
            checkpoint_file = f.name

        try:
            # Provide 4 sims, but checkpoint only has 2
            sims = ["sim_001", "sim_002", "sim_003", "sim_004"]
            multiplanet.ReCreateCP(checkpoint_file, "vspace.in", False, sims, "folder", False)

            with open(checkpoint_file, 'r') as f:
                content = f.read()

            # Verify new simulations were appended
            assert "sim_003 -1" in content
            assert "sim_004 -1" in content
            assert "THE END" in content

        finally:
            os.unlink(checkpoint_file)

    def test_recreate_cp_missing_end_marker(self):
        """Handle 'THE END' marker missing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Vspace File: /test/vspace.in\n")
            f.write("Total Number of Simulations: 2\n")
            f.write("sim_001 -1\n")
            f.write("sim_002 -1\n")
            # No "THE END" marker
            checkpoint_file = f.name

        try:
            sims = ["sim_001", "sim_002", "sim_003"]
            multiplanet.ReCreateCP(checkpoint_file, "vspace.in", False, sims, "folder", False)

            with open(checkpoint_file, 'r') as f:
                lines = f.readlines()

            # Verify "THE END" was appended
            assert any("THE END" in line for line in lines)
            # Verify sim_003 was added
            assert any("sim_003" in line for line in lines)

        finally:
            os.unlink(checkpoint_file)

    def test_recreate_cp_all_complete(self, capsys):
        """Detect when all simulations finished."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Vspace File: /test/vspace.in\n")
            f.write("Total Number of Simulations: 2\n")
            f.write("sim_001 1\n")
            f.write("sim_002 1\n")
            f.write("THE END\n")
            checkpoint_file = f.name

        try:
            sims = ["sim_001", "sim_002"]

            # Should exit when all complete and force=False
            with pytest.raises(SystemExit):
                multiplanet.ReCreateCP(checkpoint_file, "vspace.in", False, sims, "folder", False)

            captured = capsys.readouterr()
            assert "All simulations have been ran" in captured.out

        finally:
            if os.path.exists(checkpoint_file):
                os.unlink(checkpoint_file)

    def test_recreate_cp_force_flag_deletes(self):
        """Force recreates checkpoint when all complete."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Vspace File: /test/vspace.in\n")
            f.write("Total Number of Simulations: 2\n")
            f.write("sim_001 1\n")
            f.write("sim_002 1\n")
            f.write("THE END\n")
            checkpoint_file = f.name

        # Create a dummy folder file to be removed
        folder_file = tempfile.mktemp()
        with open(folder_file, 'w') as f:
            f.write("dummy")

        try:
            sims = ["sim_001", "sim_002"]

            # Call with force=True
            multiplanet.ReCreateCP(checkpoint_file, "vspace.in", False, sims, folder_file, True)

            # Verify checkpoint was recreated (all sims reset to -1)
            with open(checkpoint_file, 'r') as f:
                content = f.read()

            assert "sim_001 -1" in content
            assert "sim_002 -1" in content

        finally:
            if os.path.exists(checkpoint_file):
                os.unlink(checkpoint_file)
            if os.path.exists(folder_file):
                os.unlink(folder_file)


class TestArguments:
    """Tests for Arguments CLI function."""

    def test_arguments_default_cores(self):
        """Use all CPU cores by default."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            f.write("destfolder TestSims\n")
            vspace_file = f.name

        try:
            # Mock sys.argv and subprocess calls
            with mock.patch('sys.argv', ['multiplanet', vspace_file]):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        # Verify parallel_run_planet was called
                        assert mock_run.called
                        # Verify cores argument equals cpu_count
                        call_args = mock_run.call_args[0]
                        assert call_args[1] == mp.cpu_count()

        finally:
            os.unlink(vspace_file)

    def test_arguments_custom_cores(self):
        """Accept custom core count."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            with mock.patch('sys.argv', ['multiplanet', vspace_file, '-c', '4']):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        call_args = mock_run.call_args[0]
                        assert call_args[1] == 4

        finally:
            os.unlink(vspace_file)

    def test_arguments_bigplanet_flag(self):
        """Enable bigplanet mode with -bp flag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            with mock.patch('sys.argv', ['multiplanet', vspace_file, '-bp']):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        # bigplanet is the 5th argument (index 4)
                        call_args = mock_run.call_args[0]
                        assert call_args[4] == True

        finally:
            os.unlink(vspace_file)

    def test_arguments_force_flag(self):
        """Enable force mode with -f flag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            with mock.patch('sys.argv', ['multiplanet', vspace_file, '-f']):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        # force is the 6th argument (index 5)
                        call_args = mock_run.call_args[0]
                        assert call_args[5] == True

        finally:
            os.unlink(vspace_file)

    def test_arguments_quiet_mode(self):
        """Enable quiet mode with -q flag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            with mock.patch('sys.argv', ['multiplanet', vspace_file, '-q']):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        call_args = mock_run.call_args[0]
                        # quiet is 3rd arg, verbose is 4th arg
                        assert call_args[2] == True  # quiet=True
                        assert call_args[3] == False  # verbose=False

        finally:
            os.unlink(vspace_file)

    def test_arguments_verbose_mode(self):
        """Enable verbose mode with -v flag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            with mock.patch('sys.argv', ['multiplanet', vspace_file, '-v']):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet') as mock_run:
                        multiplanet.Arguments()

                        call_args = mock_run.call_args[0]
                        # quiet is 3rd arg, verbose is 4th arg
                        assert call_args[2] == False  # quiet=False
                        assert call_args[3] == True  # verbose=True

        finally:
            os.unlink(vspace_file)

    def test_arguments_vplanet_check(self):
        """Verify vplanet executable check."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            vspace_file = f.name

        try:
            # Test successful vplanet check
            with mock.patch('sys.argv', ['multiplanet', vspace_file]):
                with mock.patch('subprocess.getoutput', return_value="vplanet help"):
                    with mock.patch('multiplanet.multiplanet.parallel_run_planet'):
                        # Should not raise exception
                        multiplanet.Arguments()

            # Test failed vplanet check
            with mock.patch('sys.argv', ['multiplanet', vspace_file]):
                with mock.patch('subprocess.getoutput', side_effect=OSError("command not found")):
                    with pytest.raises(Exception, match="Unable to call VPLANET"):
                        multiplanet.Arguments()

        finally:
            os.unlink(vspace_file)
