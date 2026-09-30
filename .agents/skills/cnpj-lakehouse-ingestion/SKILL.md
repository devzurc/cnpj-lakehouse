---
name: cnpj-lakehouse-ingestion
description: Build or review CNPJ source ingestion, deterministic sampling, immutable Bronze lineage, and DuckDB raw loading. Do not use for dbt-only modeling.
---

# CNPJ ingestion

Read `project/specifications/source-contracts.md` and `project/specifications/sampling-and-bronze.md` before changing ingestion code.

Discover all shards for the requested source period. Stream downloads and members; do not hold full archives or CSVs in memory. Preserve raw source values, leading-zero CNPJs, source lineage, checksums, and record hashes.

Validate every required shard, ZIP member, CRC, field count, byte size, and checksum before sampling. Promote downloads atomically and remove `.part` files after failures. Persist a content-addressed source manifest only after the whole source set passes; reuse it only when filenames, sizes, and checksums still match.

Select companies by the accepted hash-ranking algorithm, retain every related child row, and load every CNAE row. Use retries only for transient network failures. Load the bounded sample transactionally in DuckDB bulk operations while preserving the canonical record hash. A completed `sample_id` is a no-op on rerun. Inventory the 32 contracted archives versus Bronze before downloading: reuse local ZIPs, skip a matching company cohort, and refuse a second sample size for the same `source_period`.

Use `scripts/verify_bronze.py` for official evidence. It must confirm the exact distinct-company count, manifest agreement, complete lineage, non-empty CNAE domain, and absence of child orphans.
