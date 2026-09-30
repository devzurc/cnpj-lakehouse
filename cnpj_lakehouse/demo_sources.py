"""Generate a tiny, contract-valid CNPJ source set for local demonstrations."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from cnpj_lakehouse.contracts import (
    CNAE,
    COMPANIES,
    ESTABLISHMENTS,
    PARTNERS,
    SIMPLES,
    SourceContract,
)
from cnpj_lakehouse.privacy import ensure_private_directory, ensure_private_file

DEMO_NOTICE = "DEMO-ONLY: synthetic records; not Receita Federal source data."


def _row(contract: SourceContract, **values: str) -> list[str]:
    return [values.get(field, "") for field in contract.expected_fields]


def _write_archive(path: Path, contract: SourceContract, rows: list[list[str]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", quotechar='"', lineterminator="\n")
    writer.writerows(rows)
    member = f"{path.stem}.csv"
    with zipfile.ZipFile(ensure_private_file(path), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, buffer.getvalue().encode("cp1252"))


def create_demo_sources(output_path: Path) -> tuple[Path, ...]:
    """Create the complete 32-archive source contract in a dedicated empty directory."""
    output_path = output_path.resolve()
    if output_path.exists() and any(output_path.iterdir()):
        raise ValueError(f"demo output directory must be empty: {output_path}")
    ensure_private_directory(output_path)

    generated: list[Path] = []
    for index in range(10):
        cnpj_basico = f"{index + 1:08d}"
        company = _row(
            COMPANIES,
            cnpj_basico=cnpj_basico,
            razao_social=f"DEMO EMPRESA {index + 1:02d}",
            natureza_juridica="2062",
            qualificacao_responsavel="49",
            capital_social_raw=f"{(index + 1) * 1000},00",
            porte_empresa="03",
        )
        establishment = _row(
            ESTABLISHMENTS,
            cnpj_basico=cnpj_basico,
            cnpj_ordem="0001",
            cnpj_dv=f"{index:02d}",
            identificador_matriz_filial="1",
            nome_fantasia=f"DEMO {index + 1:02d}",
            situacao_cadastral="02",
            data_situacao_cadastral_raw="20260101",
            data_inicio_atividade_raw="20200101",
            cnae_fiscal_principal="6201501",
            cnae_fiscal_secundaria="6202300,6311900",
            tipo_logradouro="RUA",
            logradouro="EXEMPLO",
            numero=str(index + 1),
            bairro="CENTRO",
            cep="88000000",
            uf="SC" if index % 2 == 0 else "SP",
            municipio="0001",
            correio_eletronico=f"demo{index + 1}@example.invalid",
        )
        partner = _row(
            PARTNERS,
            cnpj_basico=cnpj_basico,
            identificador_socio="2",
            nome_socio=f"SOCIO DEMO {index + 1:02d}",
            cnpj_cpf_socio="***000000**",
            qualificacao_socio="49",
            data_entrada_sociedade_raw="20200101",
            faixa_etaria="5",
        )
        for contract, filename, rows in (
            (COMPANIES, f"Empresas{index}.zip", [company]),
            (ESTABLISHMENTS, f"Estabelecimentos{index}.zip", [establishment]),
            (PARTNERS, f"Socios{index}.zip", [partner]),
        ):
            archive_path = output_path / filename
            _write_archive(archive_path, contract, rows)
            generated.append(archive_path)

    simples_rows = [
        _row(
            SIMPLES,
            cnpj_basico=f"{index + 1:08d}",
            opcao_simples="S" if index % 2 == 0 else "N",
            data_opcao_simples_raw="20200101" if index % 2 == 0 else "",
            opcao_mei="N",
        )
        for index in range(10)
    ]
    cnae_rows = [
        _row(CNAE, cnae_code="6201501", cnae_description="Desenvolvimento de programas"),
        _row(CNAE, cnae_code="6202300", cnae_description="Desenvolvimento customizavel"),
        _row(CNAE, cnae_code="6311900", cnae_description="Tratamento de dados"),
    ]
    for contract, filename, rows in (
        (SIMPLES, "Simples.zip", simples_rows),
        (CNAE, "Cnaes.zip", cnae_rows),
    ):
        archive_path = output_path / filename
        _write_archive(archive_path, contract, rows)
        generated.append(archive_path)

    ensure_private_file(output_path / "DEMO_ONLY.json").write_text(
        json.dumps(
            {
                "notice": DEMO_NOTICE,
                "source_period": "202601",
                "company_count": 10,
                "archive_count": len(generated),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return tuple(sorted(generated))
