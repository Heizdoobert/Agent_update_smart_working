import os
import tempfile
import pytest
from data_pipeline.chunker import QuoteAwareChunker
from data_pipeline.worker import DuckDBWorker


def test_quote_aware_chunker_multiline_fields():
    # Construct a CSV where line 2 has newlines inside quotes
    csv_content = (
        'id,customer,review,status\n'
        '1,"Alice","Great service!","active"\n'
        '2,"Bob","Line 1 of complaint.\nLine 2 of complaint.\nLine 3 of complaint.","pending"\n'
        '3,"Charlie","VIP Member","active"\n'
        '4,"David","Excellent product","active"\n'
    )
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        # Use small chunk size (e.g. 50 bytes) to force splitting
        chunker = QuoteAwareChunker(target_chunk_size_bytes=50)
        chunks = chunker.split_file(tmp_path)

        assert len(chunks) >= 2
        header = chunker.extract_header(tmp_path)
        assert header.startswith(b"id,customer")

        # Verify each chunk parses cleanly with DuckDB
        worker = DuckDBWorker(max_memory_mb=256)
        total_rows_parsed = 0
        for start, end, idx in chunks:
            chunk_bytes = chunker.read_chunk_payload(tmp_path, start, end, header_bytes=header)
            # Query the chunk
            res = worker.process_csv_payload(
                chunk_bytes,
                "SELECT COUNT(*) as cnt FROM chunk_data"
            )
            total_rows_parsed += res[0]["cnt"]

        # All 4 rows must be parsed without any quote fracture or drop
        assert total_rows_parsed == 4
        worker.close()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_quote_aware_chunker_unclosed_quote_error():
    corrupted_csv = 'id,name\n1,"Alice\n2,"Bob"\n'
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write(corrupted_csv)
        tmp_path = tmp.name

    try:
        chunker = QuoteAwareChunker(target_chunk_size_bytes=10)
        with pytest.raises(ValueError, match="unclosed quotation mark"):
            chunker.split_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_duckdb_worker_aggregation_and_spilling():
    worker = DuckDBWorker(max_memory_mb=128, threads=2)
    # Generate in-memory synthetic table with 5,000 rows
    worker._con.execute("""
        CREATE TABLE test_orders AS 
        SELECT 
            range as order_id, 
            (range % 5) as category_id, 
            (range * 1.5) as amount 
        FROM range(5000);
    """)

    results = worker.query("""
        SELECT 
            category_id, 
            COUNT(*) as total_orders, 
            ROUND(SUM(amount), 2) as total_amount 
        FROM test_orders 
        GROUP BY category_id 
        ORDER BY category_id;
    """)

    assert len(results) == 5
    for r in results:
        assert r["total_orders"] == 1000
    worker.close()


def test_duckdb_worker_ddl_dml_and_empty_payload():
    worker = DuckDBWorker(max_memory_mb=128)
    # DDL statement returning None description
    res_ddl = worker.query("CREATE TABLE sample_tbl (id INT, val TEXT);")
    assert res_ddl == []

    # PRAGMA statement
    res_pragma = worker.query("PRAGMA threads=1;")
    assert res_pragma == []

    # Empty and whitespace CSV payloads
    assert worker.process_csv_payload(b"", "SELECT 1") == []
    assert worker.process_csv_payload(b"   \n  \t  ", "SELECT 1") == []
    worker.close()


def test_quote_aware_chunker_multiline_header():
    # Header contains multiline quoted field
    csv_content = '"first\nheader\ncol",second_col\n"data1",data2\n'
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        chunker = QuoteAwareChunker(target_chunk_size_bytes=100)
        header = chunker.extract_header(tmp_path)
        assert header == b'"first\nheader\ncol",second_col\n'
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

