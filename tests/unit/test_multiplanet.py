"""
Unit tests for multiplanet module helper functions.

Tests the core functionality including checkpoint management, simulation
marking, and helper utilities.
"""

import os
import tempfile
import multiprocessing as mp
import pytest

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
