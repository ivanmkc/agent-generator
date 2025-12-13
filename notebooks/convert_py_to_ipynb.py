"""Utility to convert Python benchmark script to a Jupyter Notebook."""

from pathlib import Path

import nbformat as nbf
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def convert(input_filepath: str):
  input_file = Path(input_filepath)
  if not input_file.exists():
    logging.error(f"Input file not found at {input_filepath}")
    sys.exit(1)

  nb = nbf.v4.new_notebook()
  nb.metadata["kernelspec"] = {"display_name": "python3", "language": "python", "name": "python3"}
  nb.cells = []

  logging.info(f"Reading input file: {input_file}")
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

  # Add parameters tag to the cell with the marker
  for cell in nb.cells:
    if "Parameters cell for papermill" in cell.source:
      if "tags" not in cell.metadata:
        cell.metadata["tags"] = []
      cell.metadata["tags"].append("parameters")
    
    # Replace asyncio.run(main()) with await main() for notebook compatibility
    if "asyncio.run(main())" in cell.source:
      cell.source = cell.source.replace("asyncio.run(main())", "await main()")

  output_file = input_file.with_suffix(".ipynb")
  logging.info(f"Writing notebook to: {output_file}")
  with open(output_file, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
  
  logging.info("Conversion successful.")


if __name__ == "__main__":
  if len(sys.argv) < 2:
    logging.error("Usage: python convert_py_to_ipynb.py <input_python_file>")
    sys.exit(1)
  convert(sys.argv[1])