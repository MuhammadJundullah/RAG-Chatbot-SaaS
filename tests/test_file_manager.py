import io
import os
import tempfile

import pytest
from fastapi import UploadFile

from app.utils.file_manager import save_uploaded_file, delete_static_file


@pytest.mark.asyncio
async def test_save_uploaded_file_creates_file_and_returns_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        upload = UploadFile(filename="sample.txt", file=io.BytesIO(b"hello"))

        saved_path = await save_uploaded_file(upload, tmpdir)

        # Path returned should start with '/' because save_uploaded_file prefixes it
        assert saved_path.startswith("/")
        local_path = saved_path.lstrip("/")
        assert os.path.exists(local_path)


def test_delete_static_file_removes_existing_file():
    # Use a temporary working directory to align with delete_static_file's expectation of relative paths.
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            os.makedirs("static", exist_ok=True)
            local_file = os.path.join("static", "to_delete.txt")
            with open(local_file, "w") as f:
                f.write("content")

            delete_static_file("/" + local_file)

            assert not os.path.exists(local_file)
        finally:
            os.chdir(cwd)
