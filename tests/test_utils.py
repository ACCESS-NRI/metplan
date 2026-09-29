import os
import tempfile
from pathlib import Path

from distributed import Client, LocalCluster, Status

import metplan.utils as mu
from metplan.utils.files import list_nc_files


def test_extract_storage_directive():
    """Test to extract storage directives from various paths."""

    project = "abc123"

    # gdata
    assert f"gdata/{project}" == mu.extract_storage_directive(
        f"/g/data/{project}/test/test"
    )

    # scratch
    assert f"scratch/{project}" == mu.extract_storage_directive(
        f"/scratch/{project}/test/test"
    )

    # None
    assert None == mu.extract_storage_directive("should/be/none")


def test_assemble_storage_directives():
    """Test assemble_storage_directives returns for dynamic directives."""

    # Mock the project
    project = "abc123"
    os.environ["PROJECT"] = project

    # Mock the executable path
    exectuable_path = "/g/data/xp65/path/to/metplan"

    # Mock the config
    config = {"project": project, "directories": ["/g/data/zz93/inputs"]}

    expected = sorted(
        [f"gdata/{project}", f"scratch/{project}", "gdata/xp65", "gdata/zz93"]
    )

    assert mu.assemble_storage_directives(config, exectuable_path) == expected


def test_deep_update():
    """Test deep_update"""
    dict1 = dict(a=dict(a=1), b=1)
    dict2 = dict(a=dict(a=2))
    expected = dict(a=dict(a=2), b=1)
    assert mu.deep_update(dict1, dict2) == expected


def test_load_config_env():
    """Test load_config with environment var interpolation."""

    # Load some defaults into the environment
    os.environ["PROJECT"] = "TEST_PROJECT"
    os.environ["USER"] = "TEST_USER"

    # Load the default config
    config = mu.load_config()

    assert config.get("output_dir") == "/scratch/TEST_PROJECT/TEST_USER/metplan"


def test_load_config_user():
    """Test load_config with user overrides."""
    # Create a temp dir
    with tempfile.TemporaryDirectory() as td:

        user_config_path = td + "/user.yml"

        # Write a user config file
        with open(user_config_path, "w") as fp:
            fp.write("output_dir: TEST")

        # Load it
        config = mu.load_config(user_config=user_config_path)

        # Ensure it replaced the internal defaults
        assert config.get("output_dir") == "TEST"


def test_startstop_dask_client():
    """Test start_dask_client"""
    # Start the client and cluster
    client, cluster = mu.start_dask_client(mu.load_config())
    assert isinstance(client, Client)
    assert isinstance(cluster, LocalCluster)

    # Stop them and ensure they are indeed stopped
    mu.stop_dask_client(client, cluster)

    # Allow for closing status due to sluggish runners.
    assert client.status in ["closed", "closing"]
    assert cluster.status in [Status.closed, Status.closing]


class TestListNcFiles:
    """Test suite for list_nc_files function.

    Tests cover:
    - Single file handling
    - Directory traversal
    - File filtering (only .nc files)
    - Edge cases (empty directories, nested structures)
    """

    def test_list_nc_files_with_single_nc_file(self):
        """Test listing a single .nc file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nc_file = Path(tmpdir) / "test.nc"
            nc_file.touch()

            result = list_nc_files(str(nc_file))

            assert len(result) == 1
            assert str(nc_file) in result

    def test_list_nc_files_with_multiple_nc_files_in_directory(self):
        """Test finding multiple .nc files in a single directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nc_file1 = Path(tmpdir) / "data1.nc"
            nc_file2 = Path(tmpdir) / "data2.nc"
            nc_file1.touch()
            nc_file2.touch()

            result = list_nc_files(tmpdir)

            assert len(result) == 2
            assert str(nc_file1) in result
            assert str(nc_file2) in result

    def test_list_nc_files_with_nested_directories(self):
        """Test discovering .nc files in nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            deep_dir = subdir / "deep"
            deep_dir.mkdir()

            nc_file1 = Path(tmpdir) / "root.nc"
            nc_file2 = subdir / "sub.nc"
            nc_file3 = deep_dir / "deep.nc"
            nc_file1.touch()
            nc_file2.touch()
            nc_file3.touch()

            result = list_nc_files(tmpdir)

            assert len(result) == 3
            assert str(nc_file1) in result
            assert str(nc_file2) in result
            assert str(nc_file3) in result

    def test_list_nc_files_ignores_non_nc_files(self):
        """Test that non-.nc files are excluded from results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nc_file = Path(tmpdir) / "data.nc"
            txt_file = Path(tmpdir) / "readme.txt"
            csv_file = Path(tmpdir) / "metadata.csv"
            json_file = Path(tmpdir) / "config.json"

            nc_file.touch()
            txt_file.touch()
            csv_file.touch()
            json_file.touch()

            result = list_nc_files(tmpdir)

            assert len(result) == 1
            assert str(nc_file) in result
            assert str(txt_file) not in result
            assert str(csv_file) not in result
            assert str(json_file) not in result

    def test_list_nc_files_with_empty_directory(self):
        """Test listing files in an empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_nc_files(tmpdir)

            assert result == []
