#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mode="${1:---code-only}"
[[ "$mode" == --code-only || "$mode" == --database ]] || { echo "Use --code-only or --database" >&2; exit 2; }
checkpoint=.deploy/previous-image
if [[ "$mode" == --database ]]; then checkpoint=.deploy/before-quizzes-image; fi
[[ -s "$checkpoint" ]] || { echo "No matching recovery checkpoint. Capture the pre-quizzes baseline first." >&2; exit 2; }
umask 077
exec 9>.deploy/deploy.lock
flock 9
export MOTLY_API_IMAGE="$(cat .deploy/current-image)"
if [[ "$mode" == --database ]]; then
  # Stop both writers before archiving the quiz schema. The new image knows the migration.
  docker compose -f compose.prod.yml stop api quiz-worker
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  docker compose -f compose.prod.yml run --rm --no-deps \
    -v "$PWD/.deploy/backups:/backups" api \
    python -m app.modules.quiz.maintenance backup --output "/backups/before-rollback-$stamp.json.gz"
  docker compose -f compose.prod.yml run --rm --no-deps api alembic downgrade 20260612_0004
else
  docker compose -f compose.prod.yml stop quiz-worker
fi
export MOTLY_API_IMAGE="$(cat "$checkpoint")"
docker compose -f compose.prod.yml up -d --no-deps api
curl --retry 20 --retry-connrefused --retry-delay 2 -fsS http://127.0.0.1:8000/api/v1/health
printf '\nPrevious API restored. Archived quizzes can be recovered with upgrade 20261108_0005.\n'
