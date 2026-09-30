#!/usr/bin/env bash
# Resolve the CNPJ Lakehouse runtime on Linux-native storage.
cnpj_default_runtime_root() {
  if [[ -n "${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-}" ]]; then
    printf '%s\n' "$CNPJ_LAKEHOUSE_RUNTIME_ROOT"
    return
  fi
  printf '%s\n' "$HOME/.local/share/cnpj-lakehouse"
}

cnpj_official_runtime_root() {
  if [[ -n "${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-}" ]]; then
    printf '%s\n' "$CNPJ_LAKEHOUSE_RUNTIME_ROOT"
    return
  fi
  printf '%s\n' "$HOME/.local/share/cnpj-lakehouse-official"
}

cnpj_default_duckdb_path() {
  local root="$1"
  if [[ -n "${CNPJ_LAKEHOUSE_DUCKDB_PATH:-}" ]]; then
    printf '%s\n' "$CNPJ_LAKEHOUSE_DUCKDB_PATH"
    return
  fi
  printf '%s\n' "$root/run/warehouse/cnpj_lakehouse.duckdb"
}
