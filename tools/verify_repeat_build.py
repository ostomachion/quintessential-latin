"""Build in an isolated checkout and compare all manifested outputs byte for byte."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    output=ROOT/"resources/fonts/QuintessentialSerif"
    expected=json.loads((output/"build-manifest.json").read_text(encoding="utf-8"))
    expected_hash=sha(output/"build-manifest.json")
    scratch=ROOT/".tmp";scratch.mkdir(exist_ok=True)
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="repeat-font-build-",dir=scratch) as temporary:
        stage=Path(temporary)
        for name in expected["sources"]:
            source=ROOT/name;target=stage/name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        donor=ROOT/"resources/fonts/STIXTwoText"
        shutil.copytree(donor,stage/"resources/fonts/STIXTwoText")
        subprocess.run([sys.executable,str(stage/"tools/build_quintessential_font.py")],check=True,cwd=stage)
        actual=stage/"resources/fonts/QuintessentialSerif"
        assert sha(actual/"build-manifest.json")==expected_hash,"Build manifest is not reproducible"
        for name,record in expected["outputs"].items():
            assert sha(actual/name)==record["sha256"],name
        result={"schemaVersion":1,"status":"passed","seconds":round(time.monotonic()-started,3),"manifestSha256":expected_hash,"sourceFiles":len(expected["sources"]),"outputs":{name:record["sha256"] for name,record in expected["outputs"].items()}}
    target=ROOT/"resources/provenance/repeat-build.json"
    target.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(result))
if __name__=="__main__":main()
