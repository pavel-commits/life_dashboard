import tempfile
import unittest
from pathlib import Path

import database


class GoalDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.database_path = database.DATABASE_PATH
        database.DATABASE_PATH = Path(tempfile.mkdtemp()) / "test.db"
        database.init_db()

    def tearDown(self):
        database.DATABASE_PATH = self.database_path

    def test_progress_is_percentage_of_completed_linked_tasks(self):
        goal_id = database.create_goal("Цель", "", "2026-09-01")
        database.create_task("Готово", "", "Low", None, "Done", "Work", goal_id)
        database.create_task("В работе", "", "Low", None, "Todo", "Work", goal_id)

        self.assertEqual(database.calculate_goal_progress(goal_id), 50)

    def test_task_can_be_linked_to_only_one_goal(self):
        first_goal = database.create_goal("Первая", "", None)
        second_goal = database.create_goal("Вторая", "", None)
        database.create_task("Задача", "", "Low", None, "Todo", "Work", first_goal)
        task_id = database.get_goal_tasks(first_goal)[0]["id"]

        database.link_task_to_goal(task_id, second_goal)

        self.assertEqual(database.get_goal_tasks(first_goal), [])
        self.assertEqual(len(database.get_goal_tasks(second_goal)), 1)


if __name__ == "__main__":
    unittest.main()