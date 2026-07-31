# Database migrations

Run `python -m alembic upgrade head` before starting Aura. SQLite is for local development; production uses a PostgreSQL `DATABASE_URL`.

Run validation with `python -m pytest tests/migrations`. The tests create temporary SQLite databases, run the complete Alembic chain, verify the head revision, and compare generated tables, columns, and indexes with canonical SQLAlchemy metadata. They never modify `aura.db`.

Deploy by backing up the database, running migrations as a release step, then starting the application. The baseline migration intentionally has no downgrade because it represents existing schema and protects data.
