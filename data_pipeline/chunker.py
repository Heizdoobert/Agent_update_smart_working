"""
data_pipeline.chunker
---------------------
Production-grade Quote-Aware CSV Chunker implementing RFC 4180 invariants.
Prevents the Naive Chunking Trap by never splitting across multiline quoted fields.
"""

import os
from typing import List, Tuple, Optional


class QuoteAwareChunker:
    """Calculates byte-offset slice boundaries [start_offset, end_offset) for CSV files

    guaranteeing that cuts only occur on clean line breaks outside quoted fields.
    """

    def __init__(self, target_chunk_size_bytes: int = 64 * 1024 * 1024):
        self.target_chunk_size = target_chunk_size_bytes

    def split_file(self, file_path: str) -> List[Tuple[int, int, int]]:
        """Scan a CSV file and return a list of (start_offset, end_offset, chunk_index) tuples.

        Guarantees that no slice begins or ends inside an RFC 4180 quoted string.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return []

        chunks: List[Tuple[int, int, int]] = []
        buffer_size = 1024 * 1024  # 1MB buffer
        chunk_start = 0
        in_quotes = False
        bytes_scanned = 0
        chunk_idx = 0

        with open(file_path, "rb") as f:
            while True:
                chunk_bytes = f.read(buffer_size)
                if not chunk_bytes:
                    break

                for i, byte in enumerate(chunk_bytes):
                    current_offset = bytes_scanned + i

                    # Double quote character (0x22 / '"')
                    if byte == 0x22:
                        in_quotes = not in_quotes

                    # Newline character (0x0A / '\n') outside quotation
                    elif byte == 0x0A and not in_quotes:
                        accumulated = (current_offset + 1) - chunk_start
                        if accumulated >= self.target_chunk_size:
                            chunk_end = current_offset + 1  # include newline
                            chunks.append((chunk_start, chunk_end, chunk_idx))
                            chunk_idx += 1
                            chunk_start = chunk_end

                bytes_scanned += len(chunk_bytes)

        # Final trailing chunk
        if chunk_start < file_size:
            if in_quotes:
                raise ValueError(
                    f"Corrupted CSV: file {file_path} ended with an unclosed quotation mark (RFC 4180 violation)."
                )
            chunks.append((chunk_start, file_size, chunk_idx))

        return chunks

    @staticmethod
    def extract_header(file_path: str) -> bytes:
        """Extract RFC 4180 compliant header from CSV file as bytes, supporting multiline quoted fields."""
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return b""

        header_bytes = bytearray()
        in_quotes = False
        buffer_size = 64 * 1024

        with open(file_path, "rb") as f:
            while True:
                buf = f.read(buffer_size)
                if not buf:
                    break
                for byte in buf:
                    header_bytes.append(byte)
                    if byte == 0x22:  # '"'
                        in_quotes = not in_quotes
                    elif byte == 0x0A and not in_quotes:  # '\n'
                        return bytes(header_bytes)

        if in_quotes:
            raise ValueError(
                f"Corrupted CSV header: file {file_path} ended with an unclosed quotation mark (RFC 4180 violation)."
            )
        return bytes(header_bytes)

    @staticmethod
    def read_chunk_payload(
        file_path: str,
        start_offset: int,
        end_offset: int,
        header_bytes: Optional[bytes] = None,
    ) -> bytes:
        """Read a chunk slice from disk, prepending header bytes if this is not the first chunk."""
        with open(file_path, "rb") as f:
            f.seek(start_offset)
            data = f.read(end_offset - start_offset)

        if start_offset > 0 and header_bytes:
            # Ensure newline between header and chunk data if not present
            if not header_bytes.endswith(b"\n") and not header_bytes.endswith(b"\r"):
                header_bytes += b"\n"
            return header_bytes + data
        return data
