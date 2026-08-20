import sqlite3
from pathlib import Path
from typing import Any, Optional

DATABASE_PATH = Path(__file__).with_name("life_dashboard.db")


class DatabaseError(RuntimeError):
    """User-facing database operation failure."""


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    category TEXT NOT NULL DEFAULT 'Other',
                    due_date TEXT,
                    status TEXT NOT NULL DEFAULT 'Todo',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
            }
            if "category" not in columns:
                connection.execute(
                    "ALTER TABLE tasks ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    streak INTEGER NOT NULL DEFAULT 0,
                    last_completed TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось инициализировать базу данных.") from error


def get_tasks() -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY status = 'Done', due_date IS NULL, due_date, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить задачи.") from error


def get_dashboard_stats() -> dict[str, int]:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM tasks WHERE due_date = date('now')) AS tasks_today,
                    (SELECT COUNT(*) FROM tasks
                     WHERE status = 'Done' AND date(updated_at) >= date('now', '-6 days'))
                    AS completed_week,
                    (SELECT COUNT(*) FROM habits WHERE active = 1) AS active_habits,
                    (SELECT COALESCE(MAX(streak), 0) FROM habits WHERE active = 1) AS current_streak
                """
            ).fetchone()
        return dict(row)
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить показатели dashboard.") from error


def get_habits() -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM habits WHERE active = 1 ORDER BY streak DESC, name"
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить привычки.") from error


def get_recent_notes(limit: int = 5) -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM notes ORDER BY datetime(updated_at) DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить заметки.") from error


def create_task(
    title: str,
    description: str,
    priority: str,
    due_date: Optional[str],
    status: str,
    category: str = "Other",
) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO tasks (title, description, priority, due_date, status, category) VALUES (?, ?, ?, ?, ?, ?)",
                (title, description, priority, due_date, status, category),
            )
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось сохранить задачу.") from error


def update_task(
    task_id: int,
    title: str,
    description: str,
    priority: str,
    due_date: Optional[str],
    status: str,
    category: str = "Other",
) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, priority = ?, due_date = ?,
                    status = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, description, priority, due_date, status, category, task_id),
            )
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось обновить задачу.") from error


def delete_task(task_id: int) -> None:
    try:
        with get_connection() as connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось удалить задачу.") from error
