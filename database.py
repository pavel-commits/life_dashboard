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
                    goal_id INTEGER,
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
            if "goal_id" not in columns:
                connection.execute("ALTER TABLE tasks ADD COLUMN goal_id INTEGER")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id)"
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    due_date TEXT,
                    status TEXT NOT NULL DEFAULT 'Active',
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


def create_goal(
    title: str,
    description: str,
    due_date: Optional[str],
    status: str = "Active",
) -> int:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO goals (title, description, due_date, status) VALUES (?, ?, ?, ?)",
                (title, description, due_date, status),
            )
            connection.commit()
            return int(cursor.lastrowid)
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось сохранить цель.") from error


def get_goals(active_only: bool = False) -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            query = "SELECT * FROM goals"
            params: tuple[str, ...] = ()
            if active_only:
                query += " WHERE status = ?"
                params = ("Active",)
            query += " ORDER BY status != 'Active', due_date IS NULL, due_date, id DESC"
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить цели.") from error


def get_goal(goal_id: int) -> Optional[dict[str, Any]]:
    try:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить цель.") from error


def get_goal_tasks(goal_id: int) -> list[dict[str, Any]]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE goal_id = ? ORDER BY status = 'Done', due_date IS NULL, due_date, id DESC",
                (goal_id,),
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось загрузить задачи цели.") from error


def calculate_goal_progress(goal_id: int) -> int:
    try:
        with get_connection() as connection:
            total, completed = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(status = 'Done'), 0) FROM tasks WHERE goal_id = ?",
                (goal_id,),
            ).fetchone()
        return round(completed * 100 / total) if total else 0
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось рассчитать прогресс цели.") from error


def link_task_to_goal(task_id: int, goal_id: Optional[int]) -> None:
    try:
        with get_connection() as connection:
            connection.execute("UPDATE tasks SET goal_id = ? WHERE id = ?", (goal_id, task_id))
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось связать задачу с целью.") from error


def update_goal(goal_id: int, title: str, description: str, due_date: Optional[str], status: str) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                "UPDATE goals SET title = ?, description = ?, due_date = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, description, due_date, status, goal_id),
            )
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось обновить цель.") from error


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


def create_habit(name: str) -> None:
    try:
        with get_connection() as connection:
            connection.execute("INSERT INTO habits (name) VALUES (?)", (name,))
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось сохранить привычку.") from error


def delete_habit(habit_id: int) -> None:
    try:
        with get_connection() as connection:
            connection.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось удалить привычку.") from error


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


def create_note(title: str, content: str) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO notes (title, content) VALUES (?, ?)",
                (title, content),
            )
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось сохранить заметку.") from error


def delete_note(note_id: int) -> None:
    try:
        with get_connection() as connection:
            connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            connection.commit()
    except sqlite3.Error as error:
        raise DatabaseError("Не удалось удалить заметку.") from error


def create_task(
    title: str,
    description: str,
    priority: str,
    due_date: Optional[str],
    status: str,
    category: str = "Other",
    goal_id: Optional[int] = None,
) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO tasks (title, description, priority, due_date, status, category, goal_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, description, priority, due_date, status, category, goal_id),
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
    goal_id: Optional[int] = None,
) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, priority = ?, due_date = ?,
                    status = ?, category = ?, goal_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, description, priority, due_date, status, category, goal_id, task_id),
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
