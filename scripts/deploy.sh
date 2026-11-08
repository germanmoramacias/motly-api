#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
release="${1:?Pass the immutable image revision}"
[[ "$release" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid release revision" >&2; exit 2; }
export MOTLY_API_IMAGE="ghcr.io/germanmoramacias/motly-api:$release"
umask 077
mkdir -p .deploy/backups
exec 9>.deploy/deploy.lock
flock 9
previous="$(docker inspect motly-api --format '{{.Image}}' 2>/dev/null || true)"
if [[ -n "$previous" ]]; then
  rollback_tag="ghcr.io/germanmoramacias/motly-api:rollback-$(date -u +%Y%m%dT%H%M%SZ)"
  docker tag "$previous" "$rollback_tag"
  printf '%s\n' "$rollback_tag" > .deploy/previous-image
  if [[ ! -s .deploy/before-quizzes-image ]]; then
    baseline="$(docker image ls --format '{{.Repository}}:{{.Tag}}' | LC_ALL=C sort | grep -E '^ghcr.io/germanmoramacias/motly-api:rollback-[0-9]{8}T[0-9]{6}Z$' | head -n 1)"
    printf '%s\n' "${baseline:-$rollback_tag}" > .deploy/before-quizzes-image
  fi
fi
printf '%s\n' "$MOTLY_API_IMAGE" > .deploy/current-image
docker compose -f compose.prod.yml pull
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose -f compose.prod.yml run --rm --no-deps \
  -v "$PWD/.deploy/backups:/backups" api \
  python -m app.modules.quiz.maintenance backup --output "/backups/before-$stamp.json.gz"
restore_code() {
  local status=$?
  trap - ERR
  echo "Activation failed; restoring the previous API image. Database schema is retained for recovery." >&2
  docker compose -f compose.prod.yml stop quiz-worker || true
  if [[ -f .deploy/previous-image ]]; then
    MOTLY_API_IMAGE="$(cat .deploy/previous-image)" docker compose -f compose.prod.yml up -d --no-deps api || true
  fi
  exit "$status"
}
trap restore_code ERR
docker compose -f compose.prod.yml run --rm --no-deps api alembic upgrade head
docker compose -f compose.prod.yml up -d api quiz-worker
for attempt in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null; then
    worker="$(docker compose -f compose.prod.yml ps -q quiz-worker)"
    if [[ -n "$worker" ]] && [[ "$(docker inspect "$worker" --format '{{.State.Running}}')" == true ]]; then
      trap - ERR
      echo "API and quiz worker active at $release"
      exit 0
    fi
  fi
  sleep 2
done
false
