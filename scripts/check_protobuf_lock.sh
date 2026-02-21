#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$HOME/Projects/arqon}"

# Locked Python matrix
PY_PROTOBUF_REGEX='protobuf==4\.25\.8|protobuf>=4\.25\.8,<5\.0(dev)?'
PY_GRPC_REGEX='grpcio==1\.62\.3|grpcio>=1\.62\.3,<1\.63\.0'
PY_GRPCTOOLS_REGEX='grpcio-tools==1\.62\.3|grpcio-tools>=1\.62\.3,<1\.63\.0'
PY_GRPCHC_REGEX='grpcio-health-checking==1\.62\.3|grpcio-health-checking>=1\.62\.3,<1\.63\.0'

echo "[audit] scanning: $ROOT_DIR"

mapfile -t dep_files < <(
  find "$ROOT_DIR" -type f \
    \( -name "requirements*.txt" -o -name "pyproject.toml" -o -name "Cargo.toml" \) \
    -not -path "*/.git/*"
)

if [[ ${#dep_files[@]} -eq 0 ]]; then
  echo "[audit] no dependency files found"
  exit 0
fi

fail=0

# 1) Hard fail any Python protobuf declarations whose primary spec targets >=5
if printf '%s\n' "${dep_files[@]}" | xargs rg -n 'protobuf\s*(==|>=|>|~=)\s*([5-9]|\d{2,})(\.\d+)?' -S; then
  echo "[fail] found protobuf >=5 declaration(s)"
  fail=1
fi

# 2) Check known Arqon Python files for required lock patterns
check_file_contains() {
  local file="$1"
  local regex="$2"
  local label="$3"
  if [[ -f "$file" ]]; then
    if ! rg -n "$regex" "$file" -S >/dev/null; then
      echo "[fail] $label lock missing or mismatched in $file"
      fail=1
    fi
  fi
}

check_file_contains "$ROOT_DIR/ArqonCore/python/arqon_narrative/pyproject.toml" "$PY_PROTOBUF_REGEX" "protobuf"
check_file_contains "$ROOT_DIR/ArqonCore/python/arqon_narrative/pyproject.toml" "$PY_GRPC_REGEX" "grpcio"
check_file_contains "$ROOT_DIR/ArqonCore/python/arqon_narrative/pyproject.toml" "$PY_GRPCTOOLS_REGEX" "grpcio-tools"
check_file_contains "$ROOT_DIR/ArqonCore/python/arqon_narrative/pyproject.toml" "$PY_GRPCHC_REGEX" "grpcio-health-checking"
check_file_contains "$ROOT_DIR/ArqonConstitutiveEngine/server/requirements.txt" '^protobuf==4\.25\.8$' "protobuf"

# 3) Informational: Rust prost versions currently allowed (0.12 and 0.13 lanes)
if printf '%s\n' "${dep_files[@]}" | xargs rg -n 'prost\s*=\s*"(0\.14|0\.15|1\.)' -S; then
  echo "[fail] found unsupported prost major/minor lane"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "[audit] FAILED"
  exit 1
fi

echo "[audit] OK - protobuf/grpc lock policy satisfied"
