"""Run complete font acceptance and portable preservation suites."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent.parent
def main():
    for filename in ("restore_font_proof.py","verify_font_preservation.py","test_project_glyph.py","test_quintessential_font.py","test_additions_font.py"):
        subprocess.run([sys.executable,str(ROOT/"tools"/filename),"-v"],cwd=ROOT,check=True)
if __name__=="__main__":main()
