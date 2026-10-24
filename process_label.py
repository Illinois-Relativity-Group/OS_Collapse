"""Set a descriptive Linux process/thread label for task monitors.

This changes comm, not argv or the executable path. It is not access control.
"""
import ctypes
import sys


def set_render_label():
    if sys.platform != 'linux':
        return
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_ulong,
                      ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    if prctl(15, b'exe_TOV_peos', 0, 0, 0) != 0:  # PR_SET_NAME
        raise OSError(ctypes.get_errno(), 'Could not set render process label')
