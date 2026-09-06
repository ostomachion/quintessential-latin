"""Verify exact extraction identities, masters, donors, and twelve compiled binaries."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify():
    record=json.loads((ROOT/"resources/provenance/extraction-preservation.json").read_text(encoding="utf-8"))
    for name,digest in record["fontSources"].items():assert sha(ROOT/name)==digest,name
    for name,digest in record["fontBinaries"].items():assert sha(ROOT/"resources/fonts/QuintessentialSerif"/name)==digest,name
    for name,digest in record["donors"].items():assert sha(ROOT/"resources/fonts/STIXTwoText"/name)==digest,name
    allocation=json.loads((ROOT/"resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    assert allocation["displayOrder"]==record["displayOrder"]
    assert len(allocation["entries"])==len(record["identities"])==832
    for current,before in zip(allocation["entries"],record["identities"]):
        assert all(current[key]==value for key,value in before.items()),before["glyphId"]
        assert not any(key in current for key in ("model","language","role"))
    return {"sourceFiles":len(record["fontSources"]),"fontBinaries":len(record["fontBinaries"]),"identities":832,"status":"passed"}
if __name__=="__main__":print(json.dumps(verify()))
