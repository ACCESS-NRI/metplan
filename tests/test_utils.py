import os
import tempfile
from pathlib import Path

import pytest

from met_preprocessor.utils import list_nc_files


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