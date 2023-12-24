import sys


def readline():
    """
    Ignores errors when reading lines from stdin.
    """
    while True:
        try:
            sys.stdin.buffer.flush()
            return sys.stdin.buffer.readline().decode('utf-8').replace("\n", "")
        except:
            pass  # might not be a utf-8 string!

