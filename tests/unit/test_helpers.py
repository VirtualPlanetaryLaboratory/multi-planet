"""
Unit tests for multiplanet helper functions.

Tests GetSNames, GetSims, and GetDir functions for parsing vspace files
and simulation directories.
"""

import os
import tempfile
import pytest

from multiplanet import multiplanet


class TestGetSNames:
    """Tests for GetSNames function."""

    def test_get_snames_single_body(self, tmp_path):
        """Parse system name and single body name from input files."""
        # Create vpl.in with system name
        vpl_file = tmp_path / "vpl.in"
        vpl_file.write_text("sSystemName SolarSystem\n")

        # Create earth.in with body name
        earth_file = tmp_path / "earth.in"
        earth_file.write_text("sName Earth\n")

        # Call GetSNames
        system_name, body_names = multiplanet.GetSNames(
            ["vpl.in", "earth.in"],
            [str(tmp_path)]
        )

        assert system_name == "SolarSystem"
        assert body_names == ["Earth"]

    def test_get_snames_multiple_bodies(self, tmp_path):
        """Parse system name and multiple body names."""
        # Create vpl.in
        vpl_file = tmp_path / "vpl.in"
        vpl_file.write_text("sSystemName MultiBody\n")

        # Create three body files
        venus = tmp_path / "venus.in"
        venus.write_text("sName Venus\n")

        earth = tmp_path / "earth.in"
        earth.write_text("sName Earth\n")

        mars = tmp_path / "mars.in"
        mars.write_text("sName Mars\n")

        # Call GetSNames
        system_name, body_names = multiplanet.GetSNames(
            ["vpl.in", "venus.in", "earth.in", "mars.in"],
            [str(tmp_path)]
        )

        assert system_name == "MultiBody"
        assert body_names == ["Venus", "Earth", "Mars"]

    def test_get_snames_order_preservation(self, tmp_path):
        """Ensure body names maintain order from file list."""
        # Create vpl.in
        vpl_file = tmp_path / "vpl.in"
        vpl_file.write_text("sSystemName Test\n")

        # Create body files
        mars = tmp_path / "mars.in"
        mars.write_text("sName Mars\n")

        earth = tmp_path / "earth.in"
        earth.write_text("sName Earth\n")

        venus = tmp_path / "venus.in"
        venus.write_text("sName Venus\n")

        # Call with specific order: mars, earth, venus
        system_name, body_names = multiplanet.GetSNames(
            ["vpl.in", "mars.in", "earth.in", "venus.in"],
            [str(tmp_path)]
        )

        # Verify order matches input order
        assert body_names == ["Mars", "Earth", "Venus"]


class TestGetSims:
    """Tests for GetSims function."""

    def test_get_sims_returns_sorted_directories(self, tmp_path):
        """Returns sorted list of simulation directories."""
        # Create directories in non-sorted order
        (tmp_path / "sim_003").mkdir()
        (tmp_path / "sim_001").mkdir()
        (tmp_path / "sim_002").mkdir()

        # Call GetSims
        sims = multiplanet.GetSims(str(tmp_path))

        # Verify sorted order and absolute paths
        assert len(sims) == 3
        assert sims[0].endswith("sim_001")
        assert sims[1].endswith("sim_002")
        assert sims[2].endswith("sim_003")
        assert all(os.path.isabs(s) for s in sims)

    def test_get_sims_ignores_files(self, tmp_path):
        """Ignores files, only returns directories."""
        # Create directories
        (tmp_path / "sim_001").mkdir()
        (tmp_path / "sim_002").mkdir()

        # Create files
        (tmp_path / "vpl.in").write_text("test")
        (tmp_path / "README.md").write_text("test")

        # Call GetSims
        sims = multiplanet.GetSims(str(tmp_path))

        # Verify only directories returned
        assert len(sims) == 2
        assert all("sim_" in s for s in sims)

    def test_get_sims_empty_folder(self, tmp_path):
        """Returns empty list for folder with no subdirs."""
        # Create some files but no directories
        (tmp_path / "file.txt").write_text("test")

        # Call GetSims
        sims = multiplanet.GetSims(str(tmp_path))

        # Verify empty list
        assert sims == []


class TestGetDir:
    """Tests for GetDir function."""

    def test_get_dir_valid_vspace_file(self, tmp_path):
        """Parse folder name and input files from vspace file."""
        # Create the destination folder first
        dest_folder = tmp_path / "TestSims"
        dest_folder.mkdir()

        # Create vspace.in file
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text(
            "destfolder TestSims\n"
            "file vpl.in\n"
            "sBodyFile earth.in\n"
            "sPrimaryFile sun.in\n"
        )

        # Change to tmp_path so relative path works
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Call GetDir
            folder_name, in_files = multiplanet.GetDir(str(vspace_file))

            assert folder_name == "TestSims"
            assert "vpl.in" in in_files
            assert "earth.in" in in_files
            assert "sun.in" in in_files
        finally:
            os.chdir(original_cwd)

    def test_get_dir_missing_destfolder(self, tmp_path):
        """Raise IOError if destfolder not specified."""
        # Create vspace.in without destfolder
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text(
            "file vpl.in\n"
            "sBodyFile earth.in\n"
        )

        # Call GetDir and expect IOError
        with pytest.raises(IOError, match="destination folder not provided"):
            multiplanet.GetDir(str(vspace_file))

    def test_get_dir_folder_not_exists(self, tmp_path):
        """Exit gracefully if destination folder missing."""
        # Create vspace.in with non-existent folder
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text("destfolder NonExistentFolder\n")

        # Call GetDir and expect SystemExit
        with pytest.raises(SystemExit):
            multiplanet.GetDir(str(vspace_file))

    def test_get_dir_alternate_syntax(self, tmp_path):
        """Support both 'destfolder' and 'sDestFolder' syntax."""
        # Create the destination folder first
        dest_folder = tmp_path / "AltSims"
        dest_folder.mkdir()

        # Create vspace.in with sDestFolder syntax
        vspace_file = tmp_path / "vspace.in"
        vspace_file.write_text(
            "sDestFolder AltSims\n"
            "file vpl.in\n"
        )

        # Change to tmp_path so relative path works
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Call GetDir
            folder_name, in_files = multiplanet.GetDir(str(vspace_file))

            assert folder_name == "AltSims"
            assert "vpl.in" in in_files
        finally:
            os.chdir(original_cwd)
