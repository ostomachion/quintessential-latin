"""Export compact compiled availability and sampled metric envelopes."""
from pathlib import Path
import hashlib, json, sys
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parent.parent
FONTS=ROOT/"resources/fonts/QuintessentialSerif"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def create():
    allocation=json.loads((ROOT/"resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    proof=json.loads((FONTS/"proof-data.json").read_text(encoding="utf-8"))
    result={"schemaVersion":1,"version":proof["version"],"sampledWeights":[400,500,600,700],"fontHashes":{},"entries":{}}
    for posture,filename in (("Roman","QuintessentialSerif-Variable.ttf"),("Italic","QuintessentialSerif-Italic-Variable.ttf")):
        result["fontHashes"][filename]=digest(FONTS/filename)
        with TTFont(FONTS/filename) as font:
            cmap=font.getBestCmap()
            assert {k:v for k,v in cmap.items() if k!=32}=={e["codePoint"]:e["glyphName"] for e in allocation["entries"] if posture in e["postures"]}
        faces=[f for f in proof["faces"] if f["italic"]==(posture=="Italic")]
        assert sorted(f["weight"] for f in faces)==result["sampledWeights"]
        by_face=[{g["id"]:g for g in f["glyphs"]} for f in faces]
        for entry in allocation["entries"]:
            if entry["codePoint"] not in cmap:continue
            records=[f[entry["glyphId"]] for f in by_face]
            bounds=[min(g["bounds"][0] for g in records),min(g["bounds"][1] for g in records),max(g["bounds"][2] for g in records),max(g["bounds"][3] for g in records)]
            result["entries"].setdefault(entry["glyphId"],{})[posture]={"advance":max(g["advance"] for g in records),"bounds":bounds}
    return result
if __name__=="__main__":
    target=ROOT/"resources/font-coverage.json"
    text=json.dumps(create(),indent=2,ensure_ascii=False)+"\n"
    if "--check" in sys.argv:assert target.read_text(encoding="utf-8")==text,"Stale font coverage"
    else:target.write_text(text,encoding="utf-8",newline="\n")
    print("Verified compact font availability and sampled metric envelopes.")
