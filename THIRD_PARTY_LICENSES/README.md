# Third-party license notices

The project source is Apache-2.0; these external components retain their own licenses. `repl_skin.py` comes from HKUDS/CLI-Anything (Apache-2.0). Python, Click, prompt_toolkit and wcwidth notices cover the CLI runtime. PyInstaller (including its bootloader exception), hooks-contrib, altgraph and macholib notices cover build/bundling components. Native Python dependencies bundled in the separately delivered test ZIP include OpenSSL 3.6.4 (Apache-2.0), mpdecimal 4.0.1 (BSD), liblzma from XZ 5.8.4 (0BSD), and SQLite 3.53.4 (public domain).

This source repository contains no bundled application or runtime binaries. A future binary build may resolve different native dependency versions; verify their versions and preserve their actual notices before redistribution. The local test ZIP ships these notices outside the signed app so the existing app signature remains unchanged.
