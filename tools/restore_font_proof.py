"""Restore the generated full proof for font validation without tracking a large JSON file."""
from pathlib import Path
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parent.parent
folder=ROOT/"resources/fonts/QuintessentialSerif"
target=folder/"proof-data.json"
manifest=json.loads((folder/"build-manifest.json").read_text(encoding="utf-8"))
expected=manifest["outputs"]["proof-data.json"]["sha256"]
if not target.exists():
    target.write_bytes(gzip.decompress((folder/"proof-data.json.gz").read_bytes()))
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,"Proof does not match build manifest"
print("Full font proof restored and hash-verified.")
