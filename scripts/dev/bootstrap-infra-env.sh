#!/bin/sh

set -eu

ROOT_DIR="${RAGDOLL_ROOT_DIR:-$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)}"
INFRA_ENV_FILE="${RAGDOLL_INFRA_ENV_FILE:-$ROOT_DIR/infra/docker/.env.infra}"
INFRA_ENV_BACKUP_FILE="${RAGDOLL_INFRA_ENV_BACKUP_FILE:-$ROOT_DIR/infra/docker/.env.infra.backup}"
INFRA_ENV_EXAMPLE="${RAGDOLL_INFRA_ENV_EXAMPLE:-$ROOT_DIR/infra/docker/.env.infra.example}"
API_ENV_FILE="${RAGDOLL_API_ENV_FILE:-$ROOT_DIR/apps/api/.env}"
API_ENV_EXAMPLE="${RAGDOLL_API_ENV_EXAMPLE:-$ROOT_DIR/apps/api/.env.example}"
SUPABASE_DB_DATA_DIR="${RAGDOLL_SUPABASE_DB_DATA_DIR:-$ROOT_DIR/infra/supabase/self-hosted/volumes/db/data}"
MODE=full

OLD_LOCAL_POSTGRES_PASSWORD="103659aff166f7b92932fcac7a19c544"
OLD_LOCAL_JWT_SECRET="Ztwiwlm7upEac8YKDIAIvTaVVM+0M8rlSfc7Dd4q"
OLD_LOCAL_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzgyMDIxMDY0LCJleHAiOjE5Mzk3MDEwNjR9.QKjgqwuypilLaOLmiscbpQwwsilpL8a64UbT9dsA7g4"
OLD_LOCAL_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3ODIwMjEwNjQsImV4cCI6MTkzOTcwMTA2NH0.uVb3WGejvxIXUX-671_DpKoUZo2d0h7ZGmBRQaH1INI"
OLD_LOCAL_DASHBOARD_PASSWORD="13e0b0aa46263d49a8f8e967550b04ac"
OLD_LOCAL_SECRET_KEY_BASE="OqMlR0uNlsxaJvuY35UkwRgv1f8mdfuT+WJK0oqn31JdDvdyI6npEABP3C9rG32L"
OLD_LOCAL_VAULT_ENC_KEY="166309a5438f45991c412dd038b0f1da"
OLD_LOCAL_PG_META_CRYPTO_KEY="sEmSiEewCOfyB0EI0O7Ax/1LM0mHDcPA"
OLD_LOCAL_LOGFLARE_PUBLIC_ACCESS_TOKEN="LROqvKRUhMmrttW5zj5WF4X2U18r6zjv"
OLD_LOCAL_LOGFLARE_PRIVATE_ACCESS_TOKEN="UXCiDuKS/bTF8/sTzZzjs92ngiz00hPK"
OLD_LOCAL_S3_PROTOCOL_ACCESS_KEY_ID="1b7d2599e247e36d72b46d97bce10a0a"
OLD_LOCAL_S3_PROTOCOL_ACCESS_KEY_SECRET="850d8a93f421f6ae7a3c77604f9c65210663ac9f357f6ce665544590b6f50e20"
OLD_LOCAL_MINIO_ROOT_PASSWORD="38408239c758e785a388e8a85470f756"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: '$1' is required to bootstrap infra secrets."
    exit 1
  fi
}

env_get() {
  awk -F= -v key="$2" '
    $1 == key {
      print substr($0, index($0, "=") + 1)
      exit
    }
  ' "$1"
}

env_set() {
  file=$1
  key=$2
  value=$3
  tmp_file=$(mktemp "${TMPDIR:-/tmp}/ragdoll-env.XXXXXX")

  awk -v key="$key" -v value="$value" '
    BEGIN {
      found = 0
    }
    index($0, key "=") == 1 {
      print key "=" value
      found = 1
      next
    }
    {
      print
    }
    END {
      if (!found) {
        print key "=" value
      }
    }
  ' "$file" >"$tmp_file"

  mv "$tmp_file" "$file"
}

ensure_env_file() {
  target_file=$1
  example_file=$2

  if [ ! -f "$target_file" ] && [ ! -f "$example_file" ]; then
    echo "Error: missing required example file ${example_file#$ROOT_DIR/}"
      exit 1
  fi

  if [ ! -f "$target_file" ]; then
    if [ "$target_file" = "$INFRA_ENV_FILE" ] && [ -f "$INFRA_ENV_BACKUP_FILE" ]; then
      cp "$INFRA_ENV_BACKUP_FILE" "$target_file"
      echo "Restored ${target_file#$ROOT_DIR/} from ${INFRA_ENV_BACKUP_FILE#$ROOT_DIR/}"
      return 0
    fi

    cp "$example_file" "$target_file"
    echo "Created ${target_file#$ROOT_DIR/} from ${example_file#$ROOT_DIR/}"

    if [ "$target_file" = "$INFRA_ENV_FILE" ] && is_existing_supabase_db_initialized; then
      restore_legacy_infra_defaults
      echo "Recovered legacy local infra secrets because initialized Supabase data was found and no local infra env backup existed."
    fi
  fi
}

is_existing_supabase_db_initialized() {
  [ -f "$SUPABASE_DB_DATA_DIR/PG_VERSION" ]
}

restore_legacy_infra_defaults() {
  env_set "$INFRA_ENV_FILE" POSTGRES_PASSWORD "$OLD_LOCAL_POSTGRES_PASSWORD"
  env_set "$INFRA_ENV_FILE" JWT_SECRET "$OLD_LOCAL_JWT_SECRET"
  env_set "$INFRA_ENV_FILE" ANON_KEY "$OLD_LOCAL_ANON_KEY"
  env_set "$INFRA_ENV_FILE" SERVICE_ROLE_KEY "$OLD_LOCAL_SERVICE_ROLE_KEY"
  env_set "$INFRA_ENV_FILE" DASHBOARD_PASSWORD "$OLD_LOCAL_DASHBOARD_PASSWORD"
  env_set "$INFRA_ENV_FILE" SECRET_KEY_BASE "$OLD_LOCAL_SECRET_KEY_BASE"
  env_set "$INFRA_ENV_FILE" VAULT_ENC_KEY "$OLD_LOCAL_VAULT_ENC_KEY"
  env_set "$INFRA_ENV_FILE" PG_META_CRYPTO_KEY "$OLD_LOCAL_PG_META_CRYPTO_KEY"
  env_set "$INFRA_ENV_FILE" LOGFLARE_PUBLIC_ACCESS_TOKEN "$OLD_LOCAL_LOGFLARE_PUBLIC_ACCESS_TOKEN"
  env_set "$INFRA_ENV_FILE" LOGFLARE_PRIVATE_ACCESS_TOKEN "$OLD_LOCAL_LOGFLARE_PRIVATE_ACCESS_TOKEN"
  env_set "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_ID "$OLD_LOCAL_S3_PROTOCOL_ACCESS_KEY_ID"
  env_set "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_SECRET "$OLD_LOCAL_S3_PROTOCOL_ACCESS_KEY_SECRET"
  env_set "$INFRA_ENV_FILE" MINIO_ROOT_PASSWORD "$OLD_LOCAL_MINIO_ROOT_PASSWORD"
}

is_placeholder_infra_value() {
  key=$1
  value=${2:-}

  case "$key" in
    POSTGRES_PASSWORD)
      [ -z "$value" ] || [ "$value" = "your-super-secret-and-long-postgres-password" ]
      ;;
    JWT_SECRET)
      [ -z "$value" ]
      ;;
    ANON_KEY)
      [ -z "$value" ]
      ;;
    SERVICE_ROLE_KEY)
      [ -z "$value" ]
      ;;
    SUPABASE_PUBLISHABLE_KEY|SUPABASE_SECRET_KEY|JWT_KEYS|JWT_JWKS|ANON_KEY_ASYMMETRIC|SERVICE_ROLE_KEY_ASYMMETRIC)
      [ -z "$value" ]
      ;;
    DASHBOARD_PASSWORD)
      [ -z "$value" ] || [ "$value" = "replace-with-generated-dashboard-password" ]
      ;;
    SECRET_KEY_BASE)
      [ -z "$value" ] || [ "$value" = "replace-with-generated-secret-key-base" ]
      ;;
    VAULT_ENC_KEY)
      [ -z "$value" ] || [ "$value" = "your-32-character-encryption-key" ]
      ;;
    PG_META_CRYPTO_KEY)
      [ -z "$value" ] || [ "$value" = "your-encryption-key-32-chars-min" ]
      ;;
    LOGFLARE_PUBLIC_ACCESS_TOKEN)
      [ -z "$value" ] || [ "$value" = "your-super-secret-and-long-logflare-key-public" ]
      ;;
    LOGFLARE_PRIVATE_ACCESS_TOKEN)
      [ -z "$value" ] || [ "$value" = "your-super-secret-and-long-logflare-key-private" ]
      ;;
    S3_PROTOCOL_ACCESS_KEY_ID)
      [ -z "$value" ] || [ "$value" = "replace-with-generated-s3-access-key-id" ]
      ;;
    S3_PROTOCOL_ACCESS_KEY_SECRET)
      [ -z "$value" ] || [ "$value" = "replace-with-generated-s3-access-key-secret" ]
      ;;
    MINIO_ROOT_PASSWORD)
      [ -z "$value" ] || [ "$value" = "replace-with-generated-minio-root-password" ]
      ;;
    *)
      return 1
      ;;
  esac
}

is_placeholder_api_value() {
  key=$1
  value=${2:-}

  case "$key" in
    SUPABASE_DB_URL)
      [ -z "$value" ] || [ "$value" = "postgresql://postgres:your_password@db.example.supabase.co:5432/postgres" ] || [ "$value" = "postgresql://postgres:replace-with-local-postgres-password@db:5432/postgres" ] || [ "$value" = "postgresql://postgres:$OLD_LOCAL_POSTGRES_PASSWORD@db:5432/postgres" ]
      ;;
    SUPABASE_SERVICE_ROLE_KEY)
      [ -z "$value" ] || [ "$value" = "your_supabase_service_role_key_here" ] || [ "$value" = "replace-with-local-service-role-key" ] || [ "$value" = "$OLD_LOCAL_SERVICE_ROLE_KEY" ]
      ;;
    SUPABASE_URL)
      [ -z "$value" ] || [ "$value" = "https://your-project.supabase.co" ]
      ;;
    OLLAMA_BASE_URL|OLLAMA_WORKER_BASE_URL)
      [ -z "$value" ] || [ "$value" = "http://host.docker.internal:11434" ]
      ;;
    OLLAMA_MODEL)
      [ -z "$value" ] || [ "$value" = "llama3.1:8b" ]
      ;;
    OLLAMA_EMBEDDING_MODEL|SUPABASE_STORAGE_BUCKET)
      [ -z "$value" ]
      ;;
    DOCUMENT_PROCESSING_QUEUE_NAME)
      [ -z "$value" ]
      ;;
    REDIS_URL)
      [ -z "$value" ] || [ "$value" = "redis://localhost:6379/0" ]
      ;;
    *)
      return 1
      ;;
  esac
}

generate_base64() {
  openssl rand -base64 "$1"
}

generate_hex() {
  openssl rand -hex "$1"
}

base64_url_encode() {
  openssl enc -base64 -A | tr '+/' '-_' | tr -d '='
}

build_hs256_token() {
  jwt_secret=$1
  payload=$2
  header='{"alg":"HS256","typ":"JWT"}'
  payload_base64=$(printf '%s' "$payload" | base64_url_encode)
  header_base64=$(printf '%s' "$header" | base64_url_encode)
  signed_content="${header_base64}.${payload_base64}"
  signature=$(printf '%s' "$signed_content" | openssl dgst -binary -sha256 -hmac "$jwt_secret" | base64_url_encode)
  printf '%s' "${signed_content}.${signature}"
}

generate_modern_auth_bundle() {
  jwt_secret=$1
  tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/ragdoll-infra-auth.XXXXXX")
  trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

  cat >"$tmp_dir/generate-auth-keys.js" <<'EOF'
const crypto = require("crypto");

const jwtSecret = process.argv[2];

const { privateKey } = crypto.generateKeyPairSync("ec", {
  namedCurve: "prime256v1",
});
const jwkPrivate = privateKey.export({ format: "jwk" });

const kid = crypto.randomUUID();
const octKey = {
  kty: "oct",
  k: Buffer.from(jwtSecret).toString("base64url"),
  alg: "HS256",
};

const jwksKeypair = {
  keys: [
    {
      kty: "EC",
      kid,
      use: "sig",
      key_ops: ["sign", "verify"],
      alg: "ES256",
      ext: true,
      crv: jwkPrivate.crv,
      x: jwkPrivate.x,
      y: jwkPrivate.y,
      d: jwkPrivate.d,
    },
    octKey,
  ],
};

const jwksPublic = {
  keys: [
    {
      kty: "EC",
      kid,
      use: "sig",
      key_ops: ["verify"],
      alg: "ES256",
      ext: true,
      crv: jwkPrivate.crv,
      x: jwkPrivate.x,
      y: jwkPrivate.y,
    },
    octKey,
  ],
};

function signES256(payload) {
  const header = { alg: "ES256", typ: "JWT", kid };
  const b64Header = Buffer.from(JSON.stringify(header)).toString("base64url");
  const b64Payload = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const data = `${b64Header}.${b64Payload}`;
  const sig = crypto
    .sign("SHA256", Buffer.from(data), {
      key: privateKey,
      dsaEncoding: "ieee-p1363",
    })
    .toString("base64url");
  return `${data}.${sig}`;
}

const iat = Math.floor(Date.now() / 1000);
const exp = iat + 5 * 365 * 24 * 3600;

const anonJwt = signES256({ role: "anon", iss: "supabase", iat, exp });
const serviceJwt = signES256({ role: "service_role", iss: "supabase", iat, exp });

const PROJECT_REF = "ragdoll-local";

function generateOpaqueKey(prefix) {
  const random = crypto.randomBytes(17).toString("base64url").slice(0, 22);
  const intermediate = prefix + random;
  const checksum = crypto
    .createHash("sha256")
    .update(`${PROJECT_REF}|${intermediate}`)
    .digest("base64url")
    .slice(0, 8);
  return `${intermediate}_${checksum}`;
}

console.log("SUPABASE_PUBLISHABLE_KEY=" + generateOpaqueKey("sb_publishable_"));
console.log("SUPABASE_SECRET_KEY=" + generateOpaqueKey("sb_secret_"));
console.log("ANON_KEY_ASYMMETRIC=" + anonJwt);
console.log("SERVICE_ROLE_KEY_ASYMMETRIC=" + serviceJwt);
console.log("JWT_KEYS=" + JSON.stringify(jwksKeypair.keys));
console.log("JWT_JWKS=" + JSON.stringify(jwksPublic));
EOF

  output_file="$tmp_dir/output"

  if command -v node >/dev/null 2>&1; then
    if node "$tmp_dir/generate-auth-keys.js" "$jwt_secret" >"$output_file"; then
      :
    elif command -v docker >/dev/null 2>&1; then
      docker run --rm \
        -v "$tmp_dir:/work" \
        -w /work \
        docker.io/library/node:20-bookworm-slim \
        node /work/generate-auth-keys.js "$jwt_secret" >"$output_file"
    else
      echo "Error: host node failed while generating modern Supabase auth keys, and Docker is not available for the fallback Node container."
      exit 1
    fi
  elif command -v docker >/dev/null 2>&1; then
    docker run --rm \
      -v "$tmp_dir:/work" \
      -w /work \
      docker.io/library/node:20-bookworm-slim \
      node /work/generate-auth-keys.js "$jwt_secret" >"$output_file"
  else
    echo "Error: node is required to generate modern Supabase auth keys, or Docker must be available for the fallback Node container."
    exit 1
  fi

  cat "$output_file"
  rm -rf "$tmp_dir"
  trap - EXIT HUP INT TERM
}

bootstrap_infra_secrets() {
  require_command openssl

  current_jwt_secret=$(env_get "$INFRA_ENV_FILE" JWT_SECRET || true)
  current_anon_key=$(env_get "$INFRA_ENV_FILE" ANON_KEY || true)
  current_service_role_key=$(env_get "$INFRA_ENV_FILE" SERVICE_ROLE_KEY || true)

  if is_placeholder_infra_value JWT_SECRET "$current_jwt_secret" && { ! is_placeholder_infra_value ANON_KEY "$current_anon_key" || ! is_placeholder_infra_value SERVICE_ROLE_KEY "$current_service_role_key"; }; then
    echo "Error: infra/docker/.env.infra has a placeholder JWT secret but non-placeholder legacy API keys."
    echo "Delete the file or reset the legacy auth fields to placeholders, then rerun './dev-setup.sh infra up'."
    exit 1
  fi

  if is_placeholder_infra_value JWT_SECRET "$current_jwt_secret"; then
    current_jwt_secret=$(generate_base64 30)
    env_set "$INFRA_ENV_FILE" JWT_SECRET "$current_jwt_secret"
  fi

  if is_placeholder_infra_value POSTGRES_PASSWORD "$(env_get "$INFRA_ENV_FILE" POSTGRES_PASSWORD || true)"; then
    env_set "$INFRA_ENV_FILE" POSTGRES_PASSWORD "$(generate_hex 16)"
  fi

  if is_placeholder_infra_value ANON_KEY "$current_anon_key"; then
    iat=$(date +%s)
    exp=$((iat + 5 * 3600 * 24 * 365))
    anon_payload="{\"role\":\"anon\",\"iss\":\"supabase\",\"iat\":$iat,\"exp\":$exp}"
    env_set "$INFRA_ENV_FILE" ANON_KEY "$(build_hs256_token "$current_jwt_secret" "$anon_payload")"
  fi

  if is_placeholder_infra_value SERVICE_ROLE_KEY "$current_service_role_key"; then
    iat=$(date +%s)
    exp=$((iat + 5 * 3600 * 24 * 365))
    service_payload="{\"role\":\"service_role\",\"iss\":\"supabase\",\"iat\":$iat,\"exp\":$exp}"
    env_set "$INFRA_ENV_FILE" SERVICE_ROLE_KEY "$(build_hs256_token "$current_jwt_secret" "$service_payload")"
  fi

  if is_placeholder_infra_value SECRET_KEY_BASE "$(env_get "$INFRA_ENV_FILE" SECRET_KEY_BASE || true)"; then
    env_set "$INFRA_ENV_FILE" SECRET_KEY_BASE "$(generate_base64 48)"
  fi

  if is_placeholder_infra_value VAULT_ENC_KEY "$(env_get "$INFRA_ENV_FILE" VAULT_ENC_KEY || true)"; then
    env_set "$INFRA_ENV_FILE" VAULT_ENC_KEY "$(generate_hex 16)"
  fi

  if is_placeholder_infra_value PG_META_CRYPTO_KEY "$(env_get "$INFRA_ENV_FILE" PG_META_CRYPTO_KEY || true)"; then
    env_set "$INFRA_ENV_FILE" PG_META_CRYPTO_KEY "$(generate_base64 24)"
  fi

  if is_placeholder_infra_value LOGFLARE_PUBLIC_ACCESS_TOKEN "$(env_get "$INFRA_ENV_FILE" LOGFLARE_PUBLIC_ACCESS_TOKEN || true)"; then
    env_set "$INFRA_ENV_FILE" LOGFLARE_PUBLIC_ACCESS_TOKEN "$(generate_base64 24)"
  fi

  if is_placeholder_infra_value LOGFLARE_PRIVATE_ACCESS_TOKEN "$(env_get "$INFRA_ENV_FILE" LOGFLARE_PRIVATE_ACCESS_TOKEN || true)"; then
    env_set "$INFRA_ENV_FILE" LOGFLARE_PRIVATE_ACCESS_TOKEN "$(generate_base64 24)"
  fi

  if is_placeholder_infra_value S3_PROTOCOL_ACCESS_KEY_ID "$(env_get "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_ID || true)"; then
    env_set "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_ID "$(generate_hex 16)"
  fi

  if is_placeholder_infra_value S3_PROTOCOL_ACCESS_KEY_SECRET "$(env_get "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_SECRET || true)"; then
    env_set "$INFRA_ENV_FILE" S3_PROTOCOL_ACCESS_KEY_SECRET "$(generate_hex 32)"
  fi

  if is_placeholder_infra_value MINIO_ROOT_PASSWORD "$(env_get "$INFRA_ENV_FILE" MINIO_ROOT_PASSWORD || true)"; then
    env_set "$INFRA_ENV_FILE" MINIO_ROOT_PASSWORD "$(generate_hex 16)"
  fi

  if is_placeholder_infra_value DASHBOARD_PASSWORD "$(env_get "$INFRA_ENV_FILE" DASHBOARD_PASSWORD || true)"; then
    env_set "$INFRA_ENV_FILE" DASHBOARD_PASSWORD "$(generate_hex 16)"
  fi

  modern_placeholder_count=0
  modern_real_count=0

  for modern_key in SUPABASE_PUBLISHABLE_KEY SUPABASE_SECRET_KEY ANON_KEY_ASYMMETRIC SERVICE_ROLE_KEY_ASYMMETRIC JWT_KEYS JWT_JWKS; do
    modern_value=$(env_get "$INFRA_ENV_FILE" "$modern_key" || true)
    if is_placeholder_infra_value "$modern_key" "$modern_value"; then
      modern_placeholder_count=$((modern_placeholder_count + 1))
    else
      modern_real_count=$((modern_real_count + 1))
    fi
  done

  if [ "$modern_placeholder_count" -gt 0 ] && [ "$modern_real_count" -gt 0 ]; then
    echo "Error: infra/docker/.env.infra has a partially populated modern Supabase auth key set."
    echo "Delete the file or reset all modern auth fields to placeholders, then rerun './dev-setup.sh infra up'."
    exit 1
  fi

  if [ "$modern_placeholder_count" -gt 0 ]; then
    modern_bundle=$(generate_modern_auth_bundle "$current_jwt_secret")
    printf '%s\n' "$modern_bundle" | while IFS='=' read -r modern_key modern_value; do
      env_set "$INFRA_ENV_FILE" "$modern_key" "$modern_value"
    done
  fi
}

sync_api_env() {
  ensure_env_file "$API_ENV_FILE" "$API_ENV_EXAMPLE"

  if is_placeholder_api_value SUPABASE_DB_URL "$(env_get "$API_ENV_FILE" SUPABASE_DB_URL || true)"; then
    postgres_password=$(env_get "$INFRA_ENV_FILE" POSTGRES_PASSWORD)
    env_set "$API_ENV_FILE" SUPABASE_DB_URL "postgresql://postgres:${postgres_password}@db:5432/postgres"
  fi

  if is_placeholder_api_value SUPABASE_URL "$(env_get "$API_ENV_FILE" SUPABASE_URL || true)"; then
    env_set "$API_ENV_FILE" SUPABASE_URL "http://kong:8000"
  fi

  if is_placeholder_api_value SUPABASE_SERVICE_ROLE_KEY "$(env_get "$API_ENV_FILE" SUPABASE_SERVICE_ROLE_KEY || true)"; then
    env_set "$API_ENV_FILE" SUPABASE_SERVICE_ROLE_KEY "$(env_get "$INFRA_ENV_FILE" SERVICE_ROLE_KEY)"
  fi

  if is_placeholder_api_value SUPABASE_STORAGE_BUCKET "$(env_get "$API_ENV_FILE" SUPABASE_STORAGE_BUCKET || true)"; then
    env_set "$API_ENV_FILE" SUPABASE_STORAGE_BUCKET "$(env_get "$INFRA_ENV_FILE" SUPABASE_STORAGE_BUCKET)"
  fi

  if is_placeholder_api_value OLLAMA_BASE_URL "$(env_get "$API_ENV_FILE" OLLAMA_BASE_URL || true)"; then
    env_set "$API_ENV_FILE" OLLAMA_BASE_URL "http://ollama:11434"
  fi

  if is_placeholder_api_value OLLAMA_WORKER_BASE_URL "$(env_get "$API_ENV_FILE" OLLAMA_WORKER_BASE_URL || true)"; then
    env_set "$API_ENV_FILE" OLLAMA_WORKER_BASE_URL "http://ollama:11434"
  fi

  if is_placeholder_api_value OLLAMA_MODEL "$(env_get "$API_ENV_FILE" OLLAMA_MODEL || true)"; then
    env_set "$API_ENV_FILE" OLLAMA_MODEL "$(env_get "$INFRA_ENV_FILE" OLLAMA_MODEL)"
  fi

  if is_placeholder_api_value OLLAMA_EMBEDDING_MODEL "$(env_get "$API_ENV_FILE" OLLAMA_EMBEDDING_MODEL || true)"; then
    env_set "$API_ENV_FILE" OLLAMA_EMBEDDING_MODEL "$(env_get "$INFRA_ENV_FILE" OLLAMA_EMBEDDING_MODEL)"
  fi

  if is_placeholder_api_value DOCUMENT_PROCESSING_QUEUE_NAME "$(env_get "$API_ENV_FILE" DOCUMENT_PROCESSING_QUEUE_NAME || true)"; then
    env_set "$API_ENV_FILE" DOCUMENT_PROCESSING_QUEUE_NAME "document-processing"
  fi

  if is_placeholder_api_value REDIS_URL "$(env_get "$API_ENV_FILE" REDIS_URL || true)"; then
    env_set "$API_ENV_FILE" REDIS_URL "redis://redis:6379/0"
  fi
}

persist_infra_env_backup() {
  cp "$INFRA_ENV_FILE" "$INFRA_ENV_BACKUP_FILE"
}

ensure_env_file "$INFRA_ENV_FILE" "$INFRA_ENV_EXAMPLE"

if [ $# -gt 0 ]; then
  case "$1" in
    --ensure-env-only)
      MODE=ensure
      ;;
    --hydrate-only)
      MODE=hydrate
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: scripts/dev/bootstrap-infra-env.sh [--ensure-env-only|--hydrate-only]"
      exit 1
      ;;
  esac
fi

case "$MODE" in
  ensure)
    ;;
  hydrate|full)
    bootstrap_infra_secrets
    sync_api_env
    persist_infra_env_backup
    ;;
esac
