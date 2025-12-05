"""Utility to convert Python benchmark script to a Jupyter Notebook."""

from pathlib import Path

import nbformat as nbf


import sys

def convert(input_filepath: str):
  input_file = Path(input_filepath)
  if not input_file.exists():
    print(f"Error: Input file not found at {input_filepath}")
    sys.exit(1)

  nb = nbf.v4.new_notebook()
  nb.metadata["kernelspec"] = {"display_name": "python3", "language": "python", "name": "python3"}
  nb.cells = []

  with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

  current_cell_source = []

  for line in lines:
    if line.strip().startswith("# %%"):
      if current_cell_source:
        nb.cells.append(
            nbf.v4.new_code_cell("".join(current_cell_source).strip())
        )
        current_cell_source = []
    else:
      current_cell_source.append(line)

  if current_cell_source:
    nb.cells.append(nbf.v4.new_code_cell("".join(current_cell_source).strip()))

  # Post-processing: Unwrap _run_full_analysis and remove main block
  processed_cells = []

  for cell in nb.cells:
    if cell.source.strip().startswith("async def _run_full_analysis():"):
      # Unwrap the function body
      lines = cell.source.splitlines()
      # Skip the first line (def definition)
      body_lines = lines[1:]
      # Unindent (assuming 2 spaces indentation)
      unindented_lines = []
      for line in body_lines:
        if 'if __name__ == "__main__":' in line:
          # Stop processing if we hit the main block
          break
        if line.startswith("  "):
          unindented_lines.append(line[2:])
        else:
          unindented_lines.append(line)

      cell.source = "\n".join(unindented_lines).strip()
      processed_cells.append(cell)

    elif 'if __name__ == "__main__":' in cell.source:
      # Skip the main execution block entirely
      continue
    else:
      processed_cells.append(cell)

  nb.cells = processed_cells

  # Add parameters tag to the cell with the marker
  for cell in nb.cells:
    if "Parameters cell for papermill" in cell.source:
      if "tags" not in cell.metadata:
        cell.metadata["tags"] = []
      cell.metadata["tags"].append("parameters")

  output_file = input_file.with_suffix(".ipynb")
  with open(output_file, "w", encoding="utf-8") as f:
    nbf.write(nb, f)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("Usage: python convert_py_to_ipynb.py <input_python_file>")
    sys.exit(1)
  convert(sys.argv[1])
