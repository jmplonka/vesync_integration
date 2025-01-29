def reinstall_pyvesync() -> None:
    import sys
    import logging
    from subprocess import Popen, PIPE
    from pathlib import Path

    _LOGGER = logging.getLogger(__name__)

    working_dir = Path(__file__).parent.absolute()
    buf = []
    with Popen(f'{sys.executable} -m pip install "{working_dir}/pyvesync-2.1.17-py3-none-any.whl" --force-reinstall', stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            buf.append(line)
    _LOGGER.warning("VeSync: (re-)installing pyvesync %s", ''.join(buf))

