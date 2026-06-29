from __future__ import annotations


class FormatError(Exception):
    pass


class CrcMismatchError(FormatError):
    pass


class TruncatedFileError(FormatError):
    pass


class UnsupportedVersionError(FormatError):
    pass


class InvalidMagicError(FormatError):
    pass
