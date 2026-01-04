import pytest
import tempfile
import os


@pytest.fixture
def temp_vspace_file():
    """Create temporary vspace.in file with standard content."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
        f.write("destfolder TestSims\n")
        f.write("file vpl.in\n")
        f.write("file earth.in\n")
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_checkpoint_file():
    """Create temporary checkpoint file with test data."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Vspace File: /test/path/vspace.in\n")
        f.write("Total Number of Simulations: 3\n")
        f.write("sim_001 -1\n")
        f.write("sim_002 -1\n")
        f.write("sim_003 -1\n")
        f.write("THE END\n")
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_sim_directory(tmp_path):
    """Create temporary directory with mock simulation folders."""
    sim_dir = tmp_path / "TestSims"
    sim_dir.mkdir()
    (sim_dir / "sim_001").mkdir()
    (sim_dir / "sim_002").mkdir()
    (sim_dir / "sim_003").mkdir()
    return sim_dir


@pytest.fixture
def temp_vpl_in_file(tmp_path):
    """Create temporary vpl.in file with system name."""
    vpl_file = tmp_path / "vpl.in"
    vpl_file.write_text("sSystemName TestSystem\n")
    return vpl_file


@pytest.fixture
def temp_body_in_file(tmp_path):
    """Create temporary body.in file with body name."""
    def _create_body_file(body_name):
        body_file = tmp_path / f"{body_name}.in"
        body_file.write_text(f"sName {body_name}\n")
        return body_file
    return _create_body_file
