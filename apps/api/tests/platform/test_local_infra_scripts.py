from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


INFRA_ENV_EXAMPLE_TEXT = """\
POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password
JWT_SECRET=
ANON_KEY=
SERVICE_ROLE_KEY=
SUPABASE_PUBLISHABLE_KEY=sb_publishable_test
SUPABASE_SECRET_KEY=sb_secret_test
ANON_KEY_ASYMMETRIC=anon_test
SERVICE_ROLE_KEY_ASYMMETRIC=service_test
JWT_KEYS=[{"kty":"oct"}]
JWT_JWKS=[{"kty":"oct"}]
DASHBOARD_PASSWORD=replace-with-generated-dashboard-password
SECRET_KEY_BASE=replace-with-generated-secret-key-base
VAULT_ENC_KEY=your-32-character-encryption-key
PG_META_CRYPTO_KEY=your-encryption-key-32-chars-min
LOGFLARE_PUBLIC_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-public
LOGFLARE_PRIVATE_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-private
S3_PROTOCOL_ACCESS_KEY_ID=replace-with-generated-s3-access-key-id
S3_PROTOCOL_ACCESS_KEY_SECRET=replace-with-generated-s3-access-key-secret
MINIO_ROOT_PASSWORD=replace-with-generated-minio-root-password
REDIS_HOST_PORT=16379
SUPABASE_STORAGE_BUCKET=documents
OLLAMA_MODEL=qwen3.5:0.8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
"""

API_ENV_EXAMPLE_TEXT = """\
SUPABASE_DB_URL=postgresql://postgres:replace-with-local-postgres-password@db:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace-with-local-service-role-key
SUPABASE_STORAGE_BUCKET=
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_WORKER_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=
DOCUMENT_PROCESSING_QUEUE_NAME=
REDIS_URL=
"""


def _run_script(script_relative_path: str, *args: str, env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        ["sh", str(REPO_ROOT / script_relative_path), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_bootstrap_infra_env_creates_env_and_hydrates_api_placeholders(tmp_path):
    infra_env = tmp_path / ".env.infra"
    infra_backup = tmp_path / ".env.infra.backup"
    infra_example = tmp_path / ".env.infra.example"
    api_env = tmp_path / "api.env"
    api_example = tmp_path / "api.env.example"

    infra_example.write_text(INFRA_ENV_EXAMPLE_TEXT)
    api_example.write_text(API_ENV_EXAMPLE_TEXT)

    result = _run_script(
        "scripts/dev/bootstrap-infra-env.sh",
        "--hydrate-only",
        env_overrides={
            "RAGDOLL_INFRA_ENV_FILE": str(infra_env),
            "RAGDOLL_INFRA_ENV_BACKUP_FILE": str(infra_backup),
            "RAGDOLL_INFRA_ENV_EXAMPLE": str(infra_example),
            "RAGDOLL_API_ENV_FILE": str(api_env),
            "RAGDOLL_API_ENV_EXAMPLE": str(api_example),
            "RAGDOLL_SUPABASE_DB_DATA_DIR": str(tmp_path / "db-data"),
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert infra_env.exists()
    assert infra_backup.exists()
    assert api_env.exists()

    infra_text = infra_env.read_text()
    api_text = api_env.read_text()

    assert "POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password" not in infra_text
    assert "SERVICE_ROLE_KEY=\n" not in infra_text
    assert "SUPABASE_DB_URL=postgresql://postgres:replace-with-local-postgres-password@db:5432/postgres" not in api_text
    assert "SUPABASE_SERVICE_ROLE_KEY=replace-with-local-service-role-key" not in api_text
    assert "OLLAMA_BASE_URL=http://ollama:11434" in api_text
    assert "OLLAMA_WORKER_BASE_URL=http://ollama:11434" in api_text
    assert "DOCUMENT_PROCESSING_QUEUE_NAME=document-processing" in api_text
    assert "REDIS_URL=redis://redis:6379/0" in api_text


def test_bootstrap_infra_env_restores_backup_when_env_missing(tmp_path):
    infra_env = tmp_path / ".env.infra"
    infra_backup = tmp_path / ".env.infra.backup"
    infra_example = tmp_path / ".env.infra.example"
    api_env = tmp_path / "api.env"
    api_example = tmp_path / "api.env.example"

    infra_example.write_text(INFRA_ENV_EXAMPLE_TEXT)
    api_example.write_text(API_ENV_EXAMPLE_TEXT)
    infra_backup.write_text("POSTGRES_PASSWORD=restored-from-backup\n")

    result = _run_script(
        "scripts/dev/bootstrap-infra-env.sh",
        "--ensure-env-only",
        env_overrides={
            "RAGDOLL_INFRA_ENV_FILE": str(infra_env),
            "RAGDOLL_INFRA_ENV_BACKUP_FILE": str(infra_backup),
            "RAGDOLL_INFRA_ENV_EXAMPLE": str(infra_example),
            "RAGDOLL_API_ENV_FILE": str(api_env),
            "RAGDOLL_API_ENV_EXAMPLE": str(api_example),
            "RAGDOLL_SUPABASE_DB_DATA_DIR": str(tmp_path / "db-data"),
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert infra_env.read_text() == "POSTGRES_PASSWORD=restored-from-backup\n"


def test_bootstrap_infra_env_hydrate_preserves_existing_real_api_values(tmp_path):
    infra_env = tmp_path / ".env.infra"
    infra_backup = tmp_path / ".env.infra.backup"
    infra_example = tmp_path / ".env.infra.example"
    api_env = tmp_path / "api.env"
    api_example = tmp_path / "api.env.example"

    infra_example.write_text(INFRA_ENV_EXAMPLE_TEXT)
    api_example.write_text(API_ENV_EXAMPLE_TEXT)
    api_env.write_text(
        "\n".join(
            [
                "SUPABASE_DB_URL=postgresql://postgres:custom@db:5432/postgres",
                "SUPABASE_URL=http://custom-kong:8000",
                "SUPABASE_SERVICE_ROLE_KEY=custom-service-role",
                "SUPABASE_STORAGE_BUCKET=custom-bucket",
                "OLLAMA_BASE_URL=http://custom-ollama:11434",
                "OLLAMA_WORKER_BASE_URL=http://custom-worker:11434",
                "OLLAMA_MODEL=custom-model",
                "OLLAMA_EMBEDDING_MODEL=custom-embedding",
                "DOCUMENT_PROCESSING_QUEUE_NAME=custom-processing",
                "REDIS_URL=redis://custom-redis:6379/2",
            ]
        )
        + "\n"
    )

    result = _run_script(
        "scripts/dev/bootstrap-infra-env.sh",
        "--hydrate-only",
        env_overrides={
            "RAGDOLL_INFRA_ENV_FILE": str(infra_env),
            "RAGDOLL_INFRA_ENV_BACKUP_FILE": str(infra_backup),
            "RAGDOLL_INFRA_ENV_EXAMPLE": str(infra_example),
            "RAGDOLL_API_ENV_FILE": str(api_env),
            "RAGDOLL_API_ENV_EXAMPLE": str(api_example),
            "RAGDOLL_SUPABASE_DB_DATA_DIR": str(tmp_path / "db-data"),
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    api_text = api_env.read_text()
    assert "SUPABASE_DB_URL=postgresql://postgres:custom@db:5432/postgres" in api_text
    assert "SUPABASE_URL=http://custom-kong:8000" in api_text
    assert "SUPABASE_SERVICE_ROLE_KEY=custom-service-role" in api_text
    assert "OLLAMA_BASE_URL=http://custom-ollama:11434" in api_text
    assert "OLLAMA_EMBEDDING_MODEL=custom-embedding" in api_text
    assert "DOCUMENT_PROCESSING_QUEUE_NAME=custom-processing" in api_text
    assert "REDIS_URL=redis://custom-redis:6379/2" in api_text


def test_bootstrap_supabase_upstream_populates_missing_tree_from_overridden_git_remote(tmp_path):
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=remote_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Codex"], cwd=remote_repo, check=True)
    subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=remote_repo, check=True)
    docker_dir = remote_repo / "docker"
    docker_dir.mkdir()
    (docker_dir / "docker-compose.yml").write_text("services:\n  db:\n    image: postgres:16\n")
    subprocess.run(["git", "add", "docker/docker-compose.yml"], cwd=remote_repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed", "-q"], cwd=remote_repo, check=True)
    git_sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=remote_repo, check=True, text=True, capture_output=True)
        .stdout.strip()
    )

    upstream_dir = tmp_path / "self-hosted"
    result = _run_script(
        "scripts/dev/bootstrap-supabase-upstream.sh",
        "ensure",
        env_overrides={
            "RAGDOLL_SUPABASE_UPSTREAM_DIR": str(upstream_dir),
            "SUPABASE_UPSTREAM_GIT_REMOTE": remote_repo.as_uri(),
            "SUPABASE_UPSTREAM_GIT_SHA": git_sha,
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (upstream_dir / "docker-compose.yml").exists()
    assert "postgres:16" in (upstream_dir / "docker-compose.yml").read_text()


def test_infra_script_selects_expected_ollama_compose_file(tmp_path):
    infra_env = tmp_path / ".env.infra"
    infra_env.write_text("OLLAMA_RUNTIME=amd\n")

    result = _run_script(
        "scripts/dev/infra.sh",
        "status",
        env_overrides={
            "RAGDOLL_INFRA_ENV_FILE": str(infra_env),
            "RAGDOLL_ECHO_OLLAMA_RUNTIME_COMPOSE": "1",
        },
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip().endswith("infra/docker/compose.ollama.amd.yml")


def test_compose_and_docs_use_document_vector_service_name():
    compose_dev = (REPO_ROOT / "infra/docker/compose.dev.yml").read_text()
    compose_e2e = (REPO_ROOT / "infra/docker/compose.e2e.yml").read_text()
    infra_readme = (REPO_ROOT / "infra/docker/README.md").read_text()

    assert "  document-vector:\n" in compose_dev
    assert "  worker:\n" not in compose_dev
    assert "  document-vector:\n" in compose_e2e
    assert "--scale document-vector=3" in infra_readme
