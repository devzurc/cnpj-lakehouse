"""CLI do CNPJ Lakehouse: um lote mensal até Gold no DuckDB local."""

from __future__ import annotations

from pathlib import Path

import typer

from cnpj_lakehouse.settings import default_pipeline_output_path, resolve_official_runtime_root

app = typer.Typer(
    no_args_is_help=True,
    help="CNPJ Lakehouse: ingestão mensal local (Prefect + dbt + DuckDB).",
)


@app.command("create-demo-sources")
def create_demo_sources_command(
    output_path: Path = typer.Option(..., help="Diretório vazio para ZIPs sintéticos de teste."),
) -> None:
    """Gera o contrato de fonte completo com registros claramente sintéticos (só testes)."""
    from cnpj_lakehouse.demo_sources import DEMO_NOTICE, create_demo_sources

    archives = create_demo_sources(output_path)
    typer.echo(f"{DEMO_NOTICE} Created {len(archives)} archives in {output_path.resolve()}")


@app.command()
def run(
    source_period: str | None = typer.Option(
        None,
        help="Mês do lote YYYYMM. Vazio = mês calendário anterior em America/Sao_Paulo.",
    ),
    sample_size: int | None = typer.Option(
        None,
        min=1,
        help="Empresas por job. Padrão: env, config/sampling.toml ou 10000.",
    ),
    parallel_jobs: int | None = typer.Option(
        None,
        min=1,
        help="Jobs paralelos disjuntos. Padrão: env, config/sampling.toml ou 1.",
    ),
    ingestion_workers: int | None = typer.Option(
        None,
        min=1,
        max=4,
        help="Processos locais para validação e filtragem de arquivos; padrão 2.",
    ),
    output_path: Path | None = typer.Option(
        None,
        help="Raiz Linux da execução; padrão $CNPJ_LAKEHOUSE_RUNTIME_ROOT/run.",
    ),
    reference_date: str | None = typer.Option(None, help="Data da partição Gold (YYYY-MM-DD)."),
    full_refresh: bool = typer.Option(False, help="Reconstrói incrementais dbt (--full-refresh)."),
    source_dir: Path | None = typer.Option(None, help="Pasta local com os ZIPs; vazio baixa do espelho."),
    base_url: str | None = typer.Option(None, help="URL alternativa do índice do espelho."),
    skip_dbt: bool = typer.Option(False, help="Para após a Bronze."),
) -> None:
    """Executa o flow canônico: fontes → Bronze → dbt Silver/snapshot/Gold → testes."""
    from cnpj_lakehouse.flows.cnpj_lakehouse import DEFAULT_ARCHIVE_INDEX, run_local_pipeline

    result = run_local_pipeline(
        source_period=source_period,
        sample_size=sample_size,
        parallel_jobs=parallel_jobs,
        ingestion_workers=ingestion_workers,
        output_path=str(output_path or default_pipeline_output_path()),
        reference_date=reference_date,
        full_refresh=full_refresh,
        source_dir=str(source_dir) if source_dir else None,
        base_url=base_url or DEFAULT_ARCHIVE_INDEX,
        run_dbt_steps=not skip_dbt,
    )
    status = "skipped: already ingested" if result.skipped else "loaded"
    typer.echo(f"Bronze {status}; sample_id={result.sample_id}; rows={result.row_counts}")


@app.command("plan")
def plan_command(
    source_period: str = typer.Option(..., help="Mês do lote YYYYMM."),
    output_path: Path | None = typer.Option(
        None,
        help="Raiz Linux da execução; padrão $CNPJ_LAKEHOUSE_RUNTIME_ROOT/run.",
    ),
    sample_size: int | None = typer.Option(
        None,
        min=1,
        help="Empresas por job. Padrão: env, config/sampling.toml ou 10000.",
    ),
    parallel_jobs: int | None = typer.Option(
        None,
        min=1,
        help="Jobs paralelos disjuntos. Padrão: env, config/sampling.toml ou 1.",
    ),
) -> None:
    """Mostra ZIPs presentes/faltantes e amostras Bronze do período, sem baixar e sem imprimir linhas."""
    import json

    from cnpj_lakehouse.inventory import plan_local_ingestion
    from cnpj_lakehouse.settings import resolve_sampling_plan

    plan = resolve_sampling_plan(sample_size, parallel_jobs)
    payload = plan_local_ingestion(
        output_path or default_pipeline_output_path(),
        source_period,
        plan.total_companies,
    )
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("list-source-periods")
def list_source_periods_command(
    year: int = typer.Option(..., min=2000, max=2100, help="Ano calendário a varrer no índice."),
    base_url: str | None = typer.Option(None, help="URL alternativa do índice do espelho."),
) -> None:
    """Lista YYYYMM que têm exatamente um diretório YYYY-MM-DD no índice."""
    from cnpj_lakehouse.tasks.source_resolution import (
        DEFAULT_ARCHIVE_INDEX,
        list_source_periods,
    )

    for period in list_source_periods(year, base_url or DEFAULT_ARCHIVE_INDEX):
        typer.echo(period)


@app.command("backfill-year")
def backfill_year_command(
    year: int = typer.Option(..., min=2000, max=2100, help="Ano a ingerir em série a partir do índice."),
    from_period: str | None = typer.Option(None, help="YYYYMM inicial inclusive; meses anteriores são omitidos."),
    sample_size: int = typer.Option(
        10_000,
        min=1,
        help="Empresas na amostra (sempre 1 job; ignora CNPJ_LAKEHOUSE_PARALLEL_JOBS).",
    ),
    ingestion_workers: int | None = typer.Option(
        None,
        min=1,
        max=4,
        help="Processos locais por arquivo; padrão env/config ou 2. Não muda a amostra.",
    ),
    runtime_root: Path | None = typer.Option(
        None,
        help="Runtime Linux isolado; padrão $CNPJ_LAKEHOUSE_RUNTIME_ROOT ou ~/.local/share/cnpj-lakehouse-official.",
    ),
    base_url: str | None = typer.Option(None, help="URL alternativa do índice do espelho."),
    skip_verify: bool = typer.Option(False, help="Não roda os verificadores Bronze/Warehouse/Gold."),
) -> None:
    """Ingere cada mês inequívoco do ano, em ordem, no mesmo warehouse."""
    from cnpj_lakehouse.backfill import run_year_backfill
    from cnpj_lakehouse.tasks.source_resolution import DEFAULT_ARCHIVE_INDEX

    root = runtime_root or resolve_official_runtime_root()
    periods = run_year_backfill(
        year,
        runtime_root=root,
        sample_size=sample_size,
        ingestion_workers=ingestion_workers,
        from_period=from_period,
        base_url=base_url or DEFAULT_ARCHIVE_INDEX,
        skip_verify=skip_verify,
    )
    typer.echo("backfill complete: " + ",".join(periods))
