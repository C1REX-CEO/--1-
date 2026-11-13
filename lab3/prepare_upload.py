"""Create a small, source-only lab3 archive for WinSCP; no credentials or binaries."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'lab3/common/matrix.hpp',
    'lab3/main.cpp', 'lab3/serial.cpp',
    'lab3/build_linux.sh', 'lab3/job.pbs',
    'lab3/run_cluster.sh', 'lab3/korolev_mpirun.sh',
    'lab3/START_HERE.md',
    'lab3/experiments/run.py', 'lab3/experiments/check.py', 'lab3/experiments/summarize.py',
    'lab3/experiments/requirements.txt',
]

def main():
    destination = ROOT/'build'/'lab3-korolev-upload.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            # Normalize line endings for Bash/PBS regardless of Git's Windows checkout.
            data = (ROOT/name).read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8')
            archive.writestr('lab3-upload/'+name, data)
            manifest[name] = hashlib.sha256(data).hexdigest()
        archive.writestr('lab3-upload/manifest.json',json.dumps(manifest,indent=2)+'\n')
    print(destination)

if __name__=='__main__': main()
