# V015 deviation log

- No scope deviation.
- System Python lacked pytest; the existing project venv was reused without installing dependencies.
- One pre-freeze test assertion grouped comparison incorrectly; corrected without changing implementation or contract.
- A pre-freeze SHA-lineage defect was corrected by rejecting non-canonical question input; no product responsibility or acceptance term changed.
