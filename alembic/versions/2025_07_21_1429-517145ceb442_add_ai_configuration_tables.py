"""add ai configuration tables

Revision ID: [ЗАМЕНИТЬ_НА_СГЕНЕРИРОВАННЫЙ_ID]
Revises: f8a433be1115
Create Date: 2025-07-21 14:22:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "[ЗАМЕНИТЬ_НА_СГЕНЕРИРОВАННЫЙ_ID]"
down_revision: Union[str, None] = "f8a433be1115"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицы
    op.create_table(
        "ai_api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("api_key", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    
    op.create_table(
        "ai_agents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("agent_id", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["ai_api_keys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Добавляем дефолтные данные
    op.execute("""
        INSERT INTO ai_api_keys (name, api_key, description) 
        VALUES ('Main API Key', '4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9', 'Primary Mistral API key')
    """)
    
    op.execute("""
        INSERT INTO ai_agents (name, agent_id, description, api_key_id) VALUES
        ('Original Agent', 'ag:55c24037:20241028:untitled-agent:701d2cd7', 'Original content analysis agent', 1),
        ('Redactor 1', 'ag:9885ec37:20250720:redactor1:5dacb8af', 'Additional content analysis agent', 1),
        ('Redactor 2', 'ag:9885ec37:20250720:redactor2:6d68cfdd', 'Additional content analysis agent', 1),
        ('Redactor 3', 'ag:9885ec37:20250720:redactor3-07:1f951206', 'Additional content analysis agent', 1)
    """)


def downgrade() -> None:
    op.drop_table("ai_agents")
    op.drop_table("ai_api_keys")
