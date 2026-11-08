# Activate and recover persistent quizzes

The production deployment uses immutable image tags (`<git SHA>`) and retains the
previous running image under a local `rollback-<timestamp>` tag. Private checkpoints
and data backups live under `.deploy/` on each server and are excluded from Git.

Backend deployment runs PostgreSQL tests before building. Before applying migrations,
it saves a consistent compressed snapshot of application tables in `public`, using a
read-only repeatable-read transaction. Files have mode 0600 and are not published as
GitHub artifacts. This is an application-data snapshot; it does not replace Supabase
backups of Auth, Storage or the entire database.

## Normal activation

Publish the backend first and wait for its deployment to succeed, then publish the
frontend. The backend workflow runs `bash scripts/deploy.sh <40-character commit SHA>`.
It creates the backup, applies `alembic upgrade head`, and starts both API and worker.
The web workflow similarly records the previous frontend image and checks `/login`.

## Fast rollback (keep the database schema)

On the web server, in `/home/german/server/apps/motly-web`:

```bash
bash scripts/rollback.sh --before-quizzes
```

Then on the API server, in `/home/german/server/apps/motly-api`:

```bash
bash scripts/rollback-quizzes.sh --code-only
```

This stops the worker and restores the prior API image, leaving quiz data and the
additive schema available for reactivation. The migration version stays at 0005.

## Full database rollback with data preservation

First roll back the frontend, then execute from the API repository:

```bash
bash scripts/rollback-quizzes.sh --database
```

This stops both writers, saves another private application-data backup, uses the new
image to run `alembic downgrade 20260612_0004`, then restores the previous API image.
The downgrade moves the four quiz tables into `public_quiz_0005_archive` and saves
result links/normalized scores there. Existing material, legacy results and the
quiz graph are retained. No archive data is granted to browser roles.

## Reactivation

Run the deployment script with the new release SHA again. `alembic upgrade
20261108_0005` detects the archive, moves quiz tables back to `public`, reinstates
result links and scores, and removes the now-empty archive schema. Sessions and
history remain available. Upgrade/downgrade/upgrade is tested with a populated quiz,
answers, job, verified result and an unrelated legacy result on PostgreSQL.

Never use `alembic stamp` as a substitute for applying/reversing these changes. Stop
API and worker before a manual schema downgrade. Keep the migration code from the
new release available until rollback/recovery has completed.

The pre-quizzes baseline is pinned separately in `.deploy/before-quizzes-image`.
It is never overwritten by later visual fixes. `.deploy/previous-image` remains the
immediately preceding release for ordinary code-only recovery. The manual GitHub
workflow **Quiz recovery checkpoint** captures/verifies the original baseline without
changing any running container. Use `--before-quizzes` on the web before a database
downgrade; the API `--database` mode selects its corresponding original baseline.
