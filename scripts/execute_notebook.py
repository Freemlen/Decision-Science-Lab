"""Execute the current notebook in this interpreter; no global kernel install."""

import os
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpec
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))
path = ROOT / "notebooks" / "decision_science_lab_case_study.ipynb"
notebook = nbformat.read(path, as_version=4)
manager = KernelManager()
# Use the same virtualenv as the command, independent of installed kernelspecs.
manager._kernel_spec = KernelSpec(
    argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
    display_name="Decision Science Lab", language="python",
)
client = NotebookClient(
    notebook, km=manager, timeout=180, resources={"metadata": {"path": str(ROOT)}},
)
try:
    client.execute()
finally:
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
    manager.cleanup_resources()
nbformat.write(notebook, path)
print(f"Executed {path.name} with {sys.executable}")
