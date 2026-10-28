"""Build the standalone nexscope binary for this machine and package it for a GitHub release.

Run from the repository root inside an environment that has the CLI, its locked dependencies
and packaging/requirements.txt installed. Writes dist/release/nexscope_<version>_<os>_<arch>.(tar.gz|zip).
"""
from pathlib import Path
import platform
import shutil
import sys
import tarfile
import zipfile

import PyInstaller.__main__

from nexscope_cli import __version__

ROOT = Path(__file__).resolve().parents[1]
OS = {'darwin': 'darwin', 'linux': 'linux', 'win32': 'windows'}[sys.platform]
ARCH = {'x86_64': 'amd64', 'amd64': 'amd64', 'arm64': 'arm64', 'aarch64': 'arm64'}[platform.machine().lower()]
NOTICES = ['LICENSE', 'NOTICE', 'ASSET-NOTICES.md', 'THIRD-PARTY-NOTICES.md', 'third-party-notices']


def main():
    work = ROOT / 'build' / 'pyinstaller'
    PyInstaller.__main__.run([
        str(ROOT / 'packaging' / 'entry.py'), '--name', 'nexscope', '--onefile', '--clean', '--noconfirm',
        '--distpath', str(work / 'dist'), '--workpath', str(work / 'build'), '--specpath', str(work),
        # Package resources, skills and runner.py are read from disk at run time.
        '--collect-all', 'nexscope_cli',
        # doctor compares installed metadata with the loaded code.
        '--copy-metadata', 'nexscope-cli',
        # keyring finds OS credential backends through entry points.
        '--copy-metadata', 'keyring', '--collect-submodules', 'keyring',
    ])
    binary = work / 'dist' / ('nexscope.exe' if OS == 'windows' else 'nexscope')
    out = ROOT / 'dist' / 'release'
    out.mkdir(parents=True, exist_ok=True)
    name = f'nexscope_{__version__}_{OS}_{ARCH}'
    files = [(binary, binary.name)] + [(ROOT / n, n) for n in NOTICES]
    if OS == 'windows':
        archive = out / f'{name}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path, arc in files:
                for item in ([path] if path.is_file() else sorted(path.rglob('*'))):
                    if item.is_file():
                        zf.write(item, arc if item == path else f'{arc}/{item.relative_to(path).as_posix()}')
    else:
        archive = out / f'{name}.tar.gz'
        with tarfile.open(archive, 'w:gz') as tf:
            for path, arc in files:
                tf.add(path, arc)
    print(archive)


if __name__ == '__main__':
    main()
