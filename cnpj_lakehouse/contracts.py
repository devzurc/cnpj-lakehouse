"""Stable contracts for the Receita Federal monthly CNPJ sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceContract:
    dataset: str
    table_name: str
    filename_pattern: str
    expected_fields: tuple[str, ...]
    sharded: bool = False


COMPANIES = SourceContract(
    dataset="companies",
    table_name="raw_companies",
    filename_pattern="Empresas{index}.zip",
    sharded=True,
    expected_fields=(
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social_raw",
        "porte_empresa",
        "ente_federativo_responsavel",
    ),
)

ESTABLISHMENTS = SourceContract(
    dataset="establishments",
    table_name="raw_establishments",
    filename_pattern="Estabelecimentos{index}.zip",
    sharded=True,
    expected_fields=(
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "identificador_matriz_filial",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral_raw",
        "motivo_situacao_cadastral",
        "nome_cidade_exterior",
        "pais",
        "data_inicio_atividade_raw",
        "cnae_fiscal_principal",
        "cnae_fiscal_secundaria",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "uf",
        "municipio",
        "ddd_1",
        "telefone_1",
        "ddd_2",
        "telefone_2",
        "ddd_fax",
        "fax",
        "correio_eletronico",
        "situacao_especial",
        "data_situacao_especial_raw",
    ),
)

PARTNERS = SourceContract(
    dataset="partners",
    table_name="raw_partners",
    filename_pattern="Socios{index}.zip",
    sharded=True,
    expected_fields=(
        "cnpj_basico",
        "identificador_socio",
        "nome_socio",
        "cnpj_cpf_socio",
        "qualificacao_socio",
        "data_entrada_sociedade_raw",
        "pais",
        "representante_legal",
        "nome_representante",
        "qualificacao_representante_legal",
        "faixa_etaria",
    ),
)

SIMPLES = SourceContract(
    dataset="simples",
    table_name="raw_simples",
    filename_pattern="Simples.zip",
    expected_fields=(
        "cnpj_basico",
        "opcao_simples",
        "data_opcao_simples_raw",
        "data_exclusao_simples_raw",
        "opcao_mei",
        "data_opcao_mei_raw",
        "data_exclusao_mei_raw",
    ),
)

CNAE = SourceContract(
    dataset="cnae",
    table_name="raw_cnae",
    filename_pattern="Cnaes.zip",
    expected_fields=("cnae_code", "cnae_description"),
)

CONTRACTS = (ESTABLISHMENTS, COMPANIES, PARTNERS, SIMPLES, CNAE)
CONTRACT_BY_DATASET = {contract.dataset: contract for contract in CONTRACTS}
