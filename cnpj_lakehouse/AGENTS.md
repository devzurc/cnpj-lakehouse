# Pipeline-area instructions

The Prefect and ingestion code must stream archives and CSV members; it must not load a full source file into memory. Validate the complete source set before promotion, limit retries to transient network failures, and leave no `.part` files after failure.

DuckDB writes are serial and transactional. Preserve raw strings, full physical lineage, checksums, content-addressed source manifests, and canonical record hashes. Reuse a manifest only when filenames, sizes, and checksums match; a completed `sample_id` is a no-op. Load the bounded sample with DuckDB bulk operations.

Keep dbt commands serial and retain each command's manifest, results, stdout, and stderr under the actual Prefect `flow_run_id`. Never add a second transformation path outside dbt.

Read `project/specifications/sampling-and-bronze.md` and `project/specifications/prefect-flow.md` before changing this area.
