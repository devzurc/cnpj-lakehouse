from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from cnpj_lakehouse.settings import WAREHOUSE_FILENAME, warehouse_database_path


def test_uses_one_unambiguous_legacy_warehouse(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    legacy = warehouse / "previous.duckdb"
    with duckdb.connect(str(legacy)) as connection:
        connection.execute("CREATE SCHEMA ops")
        connection.execute("CREATE TABLE ops.sample_manifests (sample_id VARCHAR)")
        connection.execute("CREATE SCHEMA bronze")
        for table in ("companies", "establishments", "partners", "simples", "cnae"):
            connection.execute(f"CREATE TABLE bronze.{table} (id VARCHAR)")
    assert warehouse_database_path(tmp_path) == legacy


def test_rejects_ambiguous_runtime_warehouses(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "one.duckdb").touch()
    (warehouse / "two.duckdb").touch()
    with pytest.raises(RuntimeError, match="multiple DuckDB"):
        warehouse_database_path(tmp_path)


def test_rejects_canonical_and_legacy_warehouse(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    canonical = warehouse / WAREHOUSE_FILENAME
    canonical.touch()
    (warehouse / "previous.duckdb").touch()
    with pytest.raises(RuntimeError, match="multiple DuckDB"):
        warehouse_database_path(tmp_path)


def test_rejects_incompatible_legacy_warehouse(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "previous.duckdb").touch()
    with pytest.raises(RuntimeError, match="legacy DuckDB warehouse is incompatible"):
        warehouse_database_path(tmp_path)
