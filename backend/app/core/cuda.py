"""Make CUDA runtime DLLs installed in this virtual environment discoverable on Windows."""

import os
import sys
import sysconfig
import ctypes
from pathlib import Path


_DLL_DIRECTORY_HANDLES: list[object] = []
_LOADED_LIBRARIES: list[object] = []


def configure_cuda_dll_directories() -> None:
    if sys.platform != "win32" or _DLL_DIRECTORY_HANDLES:
        return

    site_packages = Path(sysconfig.get_paths()["purelib"])
    for relative_path in ("nvidia/cublas/bin", "nvidia/cuda_runtime/bin", "ctranslate2"):
        directory = site_packages / relative_path
        if directory.is_dir():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))

    for relative_path in (
        "nvidia/cuda_runtime/bin/cudart64_12.dll",
        "nvidia/cublas/bin/cublasLt64_12.dll",
        "nvidia/cublas/bin/cublas64_12.dll",
        "ctranslate2/cudnn64_9.dll",
    ):
        library = site_packages / relative_path
        if library.is_file():
            _LOADED_LIBRARIES.append(ctypes.WinDLL(str(library)))
