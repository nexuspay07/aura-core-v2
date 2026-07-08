# AURA ONE

## Single Source of Truth

This document defines the official architecture of Aura Business.

Only the components listed here are considered production architecture.

------------------------------------------------------------

DATABASE

Official Database Layer

app/db/

Status

ACTIVE

------------------------------------------------------------

MODELS

app/models/

Status

ON HOLD

Reason

Migration to SQLAlchemy ORM will be performed later as one complete migration.

Do not build new production features here.

------------------------------------------------------------

AUTHENTICATION

Official

app/api/auth_routes.py

Status

ACTIVE

------------------------------------------------------------

ORGANIZATIONS

Official

app/api/organization_routes.py

Status

ACTIVE

------------------------------------------------------------

WORKSPACES

Official

app/db/workspace_table.py

Status

ACTIVE

------------------------------------------------------------

INTELLIGENCE

Official Entry Point

app/api/chat_routes.py

Status

ACTIVE

------------------------------------------------------------

SERVICES

Current

chat_service.py

memory_service.py

openai_service.py

Status

ACTIVE

Future Goal

Move business logic from routes into services.

------------------------------------------------------------

RULES

1. Never build duplicate systems.

2. Always extend existing production code.

3. Every feature must have exactly one implementation.

4. Routes should remain thin.

5. Business logic belongs in services.

6. Aura Core performs intelligence.

7. Database architecture is app/db until a full ORM migration is approved.