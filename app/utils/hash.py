"""Streaming SHA256 hash computation utilities."""

import hashlib
from typing import BinaryIO, Union


def compute_sha256_stream(file_obj: BinaryIO, chunk_size: int = 8192) -> str:
    """
    Compute SHA256 hash of a file-like object using streaming reads.

    Args:
        file_obj: File-like object to hash
        chunk_size: Size of chunks to read at a time (default 8KB)

    Returns:
        Hexadecimal string representation of SHA256 hash
    """
    sha256_hash = hashlib.sha256()

    # Reset file position to beginning
    file_obj.seek(0)

    while chunk := file_obj.read(chunk_size):
        sha256_hash.update(chunk)

    # Reset file position to beginning for subsequent reads
    file_obj.seek(0)

    return sha256_hash.hexdigest()


def compute_sha256_bytes(data: Union[bytes, bytearray]) -> str:
    """
    Compute SHA256 hash of bytes data.

    Args:
        data: Bytes data to hash

    Returns:
        Hexadecimal string representation of SHA256 hash
    """
    return hashlib.sha256(data).hexdigest()
