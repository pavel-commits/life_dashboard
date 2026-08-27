from datetime import date, datetime, timedelta
from typing import Optional

import streamlit as st

from database import (
    DatabaseError,
    calculate_goal_progress,
    create_goal,
    create_habit,
    create_note,
    create_task,
    delete_habit,
    delete_note,
    delete_task,
    get_goal,
    get_goal_tasks,
    get_goals,
    get_dashboard_stats,
    get_habits,
    get_recent_notes,
    get_tasks,
    init_db,
    link_task_to_goal,
    update_goal,
    update_task,
)

CATEGORY_LABELS = {
    "Work": "Работа",
    "Personal": "Личное",
    "Learning": "Обучение",
    "Other": "Другое",
}
PRIORITY_LABELS = {"Low": "Низкий", "Medium": "Средний", "High": "Высокий"}
GOAL_STATUS_LABELS = {"Active": "Активная", "Completed": "Завершена", "Archived": "В архиве"}


st.set_page_config(
    page_title="Личный дашборд",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink: #17211b; --muted: #6b786f; --line: #dce5dd; --mint: #dff3e7; --coral: #ef8064; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; }
    .block-container { max-width: 1220px; padding-top: 3rem; padding-bottom: 4rem; }
    .eyebrow { color: var(--coral); font-size: .75rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
    .hero { display: flex; justify-content: space-between; align-items: end; gap: 2rem; margin-bottom: 2.5rem; }
    .hero h1 { font-size: clamp(2.4rem, 5vw, 4.5rem); line-height: .98; margin: .35rem 0 .8rem; }
    .hero p { color: var(--muted); font-size: 1.05rem; margin: 0; }
    .top-nav { border-bottom: 1px solid var(--line); margin-bottom: 2rem; padding-bottom: .8rem; }
    .date-mark { background: var(--mint); border-radius: 18px; padding: 1rem 1.2rem; min-width: 145px; text-align: right; }
    .date-mark strong { display: block; font-family: 'Space Grotesk'; font-size: 1.5rem; }
    .date-mark span { color: var(--muted); font-size: .8rem; }
    .panel { border: 1px solid var(--line); border-radius: 14px; padding: 1.25rem; height: 220px; min-height: 220px; box-sizing: border-box; background: #fff; }
    .panel h3 { margin: 0 0 .35rem; font-size: 1.25rem; }
    .panel-caption { color: var(--muted); font-size: .9rem; margin-bottom: 1.3rem; }
    .metric { font-family: 'Space Grotesk'; font-size: 2.3rem; font-weight: 700; }
    .metric-label { color: var(--muted); font-size: .82rem; }
    .stat-card { border: 1px solid var(--line); border-radius: 14px; padding: 1.1rem 1.2rem; background: #fff; min-height: 128px; }
    .stat-card .metric { display: block; margin-top: .45rem; }
    .stat-card small { color: var(--muted); font-size: .82rem; }
    .list-item { border-bottom: 1px solid var(--line); padding: .75rem 0; }
    .list-item:last-child { border-bottom: 0; }
    .list-item strong { display: block; }
    .list-item span { color: var(--muted); font-size: .82rem; }
    div[data-baseweb="select"] { min-height: 42px; }
    div.stButton > button { border-radius: 8px; border-color: var(--line); }
    div.stButton > button[kind="primary"] { background: var(--coral); border-color: var(--coral); }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_due_date(value: Optional[str]) -> str:
    if not value:
        return "Без дедлайна"
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return "Некорректная дата"
    return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"


def parse_due_date(value: Optional[str]) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError:
        return date.today()


def task_form(task: Optional[dict] = None) -> None:
    is_editing = task is not None
    if is_editing:
        prefix = f"edit_{task['id']}"
    else:
        form_version = st.session_state.get("new_task_form_version", 0)
        prefix = f"new_{form_version}"
    title = st.text_input(
        "Название", value=task["title"] if task else "", max_chars=120, key=f"{prefix}_title"
    )
    description = st.text_area(
        "Описание", value=task["description"] if task else "", height=90,
        max_chars=1000, key=f"{prefix}_description",
    )
    first, second = st.columns(2)
    with first:
        selected_priority = st.selectbox(
            "Приоритет", list(PRIORITY_LABELS.values()),
            index=["Low", "Medium", "High"].index(task["priority"])
            if task and task.get("priority") in ["Low", "Medium", "High"] else 0,
            key=f"{prefix}_priority",
        )
        priority = next(code for code, label in PRIORITY_LABELS.items() if label == selected_priority)
    with second:
        selected_category = st.selectbox(
            "Категория", list(CATEGORY_LABELS.values()),
            index=list(CATEGORY_LABELS).index(task.get("category", "Other"))
            if task and task.get("category") in CATEGORY_LABELS else 0,
            key=f"{prefix}_category",
        )
        category = next(code for code, label in CATEGORY_LABELS.items() if label == selected_category)
    third, fourth = st.columns(2)
    with third:
        status_labels = {"Todo": "К выполнению", "In progress": "В процессе", "Done": "Готово"}
        selected_status = st.selectbox(
            "Статус", list(status_labels.values()),
            index=["Todo", "In progress", "Done"].index(task["status"])
            if task and task.get("status") in ["Todo", "In progress", "Done"] else 0,
            key=f"{prefix}_status",
        )
        status = next(code for code, label in status_labels.items() if label == selected_status)
    with fourth:
        has_deadline = st.checkbox(
            "Есть дедлайн", value=bool(task and task.get("due_date")),
            key=f"{prefix}_has_deadline",
        )
        due_date = st.date_input(
            "Дедлайн", value=parse_due_date(task.get("due_date") if task else None),
            disabled=not has_deadline, key=f"{prefix}_due_date",
        )
    available_goals = get_goals(active_only=True)
    goal_options = {None: "Без цели"}
    goal_options.update({goal["id"]: goal["title"] for goal in available_goals})
    goal_ids = list(goal_options)
    selected_goal = st.selectbox(
        "Цель", list(goal_options.values()),
        index=goal_ids.index(task.get("goal_id"))
        if task and task.get("goal_id") in goal_ids else 0,
        key=f"{prefix}_goal",
    )
    goal_id = next(goal_id for goal_id, label in goal_options.items() if label == selected_goal)
    submitted = st.button(
        "Сохранить задачу", type="primary", use_container_width=True, key=f"{prefix}_save"
    )
    if submitted:
        if not title.strip():
            st.error("Укажите название задачи.")
            return
        due_value = due_date.isoformat() if has_deadline else None
        try:
            if is_editing:
                update_task(task["id"], title.strip(), description.strip(), priority,
                            due_value, status, category, goal_id)
            else:
                create_task(title.strip(), description.strip(), priority, due_value, status,
                            category, goal_id)
        except DatabaseError as error:
            st.error(str(error))
            return
        if not is_editing:
            st.session_state.new_task_form_version = (
                st.session_state.get("new_task_form_version", 0) + 1
            )
        st.rerun()


def render_task(task: dict) -> None:
    priority_icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(
        task.get("priority"), "⚪"
    )
    status_labels = {"Todo": "К выполнению", "In progress": "В процессе", "Done": "Готово"}
    status_label = status_labels.get(task.get("status"), "Неизвестный статус")
    category_label = CATEGORY_LABELS.get(task.get("category"), "Другое")
    with st.expander(
        f"{priority_icon}  {task.get('title', 'Без названия')}  ·  "
        f"{status_label}  ·  {category_label}"
    ):
        st.caption(
            f"{task.get('description') or 'Без описания'}  |  "
            f"{format_due_date(task.get('due_date'))}"
        )
        action, remove = st.columns([5, 1])
        with action:
            task_form(task)
        with remove:
            if st.button("Удалить", key=f"delete_{task['id']}"):
                try:
                    delete_task(task["id"])
                except DatabaseError as error:
                    st.error(str(error))
                    return
                st.rerun()


def render_navigation() -> str:
    pages = {
        "Дашборд": "dashboard",
        "Задачи": "tasks",
        "Цели": "goals",
        "Привычки": "habits",
        "Заметки": "notes",
        "О себе": "about",
    }
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    st.markdown("<div class='top-nav'></div>", unsafe_allow_html=True)
    columns = st.columns(6)
    for column, (label, page) in zip(columns, pages.items()):
        with column:
            if st.button(
                label,
                key=f"nav_{page}",
                type="primary" if st.session_state.page == page else "secondary",
                use_container_width=True,
            ):
                st.session_state.page = page
                st.rerun()
    return st.session_state.page


def render_about_page() -> None:
    st.markdown(
        "<div class='hero'><div><div class='eyebrow'>О проекте</div>"
        "<h1>Жизнь, собранная<br>в одном месте.</h1>"
        "<p>Личный дашборд, который превращает хаос дел в понятный следующий шаг.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    first, second = st.columns(2)
    with first:
        st.markdown("### Зачем он нужен")
        st.write(
            "Life Dashboard помогает держать важное перед глазами: задачи не "
            "теряются, привычки получают ритм, а хорошие мысли не растворяются "
            "в бесконечных вкладках."
        )
    with second:
        st.markdown("### Маленький личный штаб")
        st.write(
            "Добавляйте задачи, расставляйте приоритеты, следите за прогрессом и "
            "возвращайтесь к заметкам тогда, когда это действительно нужно. "
            "Без лишнего шума, регистраций и сложных настроек."
        )
    st.divider()
    st.success("Ваш день не обязан быть идеальным. Достаточно сделать следующий хороший шаг.")
    st.divider()
    st.subheader("Контакты")
    contact_telegram, contact_github = st.columns(2)
    with contact_telegram:
        st.markdown(
            "<a href='https://t.me/pavelkozlov_ae' target='_blank' "
            "style='text-decoration:none; font-size:1.05rem; display:flex; "
            "align-items:center; gap:.5rem;'>"
            "<svg width='28' height='28' viewBox='0 0 28 28' aria-label='Telegram' "
            "role='img'><circle cx='14' cy='14' r='14' fill='#229ED9'/>"
            "<path d='M21 7.5 17.8 21c-.24.95-.78 1.18-1.58.74l-4.34-3.2-2.1 2.02c-.23.23-.42.42-.86.42l.31-4.42 8.04-7.26c.35-.31-.08-.48-.55-.17L6.78 15.8l-4.3-1.35c-.94-.3-.96-.94.2-1.4L19.5 7.1c.78-.29 1.47.18 1.5.4Z' fill='white'/></svg>"
            "@pavelkozlov_ae</a>",
            unsafe_allow_html=True,
        )
    with contact_github:
        st.markdown(
            "<a href='https://github.com/pavel-commits' target='_blank' "
            "style='text-decoration:none; font-size:1.05rem; display:flex; "
            "align-items:center; gap:.5rem;'>"
            "<svg width='28' height='28' viewBox='0 0 24 24' aria-label='GitHub' "
            "role='img' fill='currentColor'><path d='M12 .3a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.04c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.33-1.76-1.33-1.76-1.09-.75.08-.74.08-.74 1.2.09 1.84 1.23 1.84 1.23 1.07 1.83 2.8 1.3 3.48.99.11-.77.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.23-3.22-.12-.3-.53-1.52.12-3.17 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.3-1.55 3.3-1.23 3.3-1.23.65 1.65.24 2.87.12 3.17.76.84 1.23 1.91 1.23 3.22 0 4.61-2.8 5.62-5.48 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58A12 12 0 0 0 12 .3Z'/></svg>"
            "pavel-commits</a>",
            unsafe_allow_html=True,
        )


def render_habits_page(habits: list[dict]) -> None:
    st.markdown(
        "<div class='hero'><div><div class='eyebrow'>Ежедневный ритм</div>"
        "<h1>Привычки.</h1>"
        "<p>Небольшие повторяющиеся действия, из которых складывается хороший день.</p></div></div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Добавить привычку")
        version = st.session_state.get("new_habit_form_version", 0)
        with st.form(f"new_habit_{version}"):
            name = st.text_input("Название", max_chars=100)
            submitted = st.form_submit_button(
                "Сохранить привычку", type="primary", use_container_width=True
            )
        if submitted:
            if not name.strip():
                st.error("Укажите название привычки.")
            else:
                try:
                    create_habit(name.strip())
                except DatabaseError as error:
                    st.error(str(error))
                else:
                    st.session_state.new_habit_form_version = version + 1
                    st.rerun()
    with right:
        st.subheader("Активные привычки")
        if habits:
            for habit in habits:
                item, remove = st.columns([5, 1])
                with item:
                    st.markdown(
                        f"**{habit['name']}**  \nСерия: {habit['streak']} дн."
                    )
                with remove:
                    if st.button("Удалить", key=f"delete_habit_{habit['id']}"):
                        try:
                            delete_habit(habit["id"])
                        except DatabaseError as error:
                            st.error(str(error))
                        else:
                            st.rerun()
        else:
            st.info("Привычек пока нет. Добавьте первую слева.")


def render_notes_page(notes: list[dict]) -> None:
    st.markdown(
        "<div class='hero'><div><div class='eyebrow'>Место для мыслей</div>"
        "<h1>Заметки.</h1>"
        "<p>Сохраняйте идеи, наблюдения и всё, к чему хочется вернуться.</p></div></div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Добавить заметку")
        version = st.session_state.get("new_note_form_version", 0)
        with st.form(f"new_note_{version}"):
            title = st.text_input("Заголовок", max_chars=120)
            content = st.text_area("Текст", height=150, max_chars=5000)
            submitted = st.form_submit_button(
                "Сохранить заметку", type="primary", use_container_width=True
            )
        if submitted:
            if not title.strip():
                st.error("Укажите заголовок заметки.")
            else:
                try:
                    create_note(title.strip(), content.strip())
                except DatabaseError as error:
                    st.error(str(error))
                else:
                    st.session_state.new_note_form_version = version + 1
                    st.rerun()
    with right:
        st.subheader("Последние заметки")
        if notes:
            for note in notes:
                with st.expander(note["title"]):
                    st.write(note["content"] or "Пустая заметка")
                    if st.button("Удалить", key=f"delete_note_{note['id']}"):
                        try:
                            delete_note(note["id"])
                        except DatabaseError as error:
                            st.error(str(error))
                        else:
                            st.rerun()
        else:
            st.info("Заметок пока нет. Добавьте первую слева.")


def render_goals_page(goals: list[dict], tasks: list[dict]) -> None:
    selected_goal_id = st.session_state.get("selected_goal_id")
    if selected_goal_id:
        goal = get_goal(selected_goal_id)
        if not goal:
            st.session_state.pop("selected_goal_id")
            st.rerun()
        if st.button("← Все цели", key="back_to_goals"):
            st.session_state.pop("selected_goal_id")
            st.rerun()
        st.markdown(f"### {goal['title']}")
        st.write(goal["description"] or "Без описания")
        progress = calculate_goal_progress(goal["id"])
        linked_tasks = get_goal_tasks(goal["id"])
        st.progress(progress / 100, text=f"Прогресс: {progress}%")
        done_count = sum(task["status"] == "Done" for task in linked_tasks)
        st.caption(
            f"Выполнено задач: {done_count} из {len(linked_tasks)} · "
            f"Дедлайн: {format_due_date(goal['due_date'])}"
        )
        st.markdown("#### Связанные задачи")
        if linked_tasks:
            for task in linked_tasks:
                st.write(f"{'✓' if task['status'] == 'Done' else '○'} {task['title']}")
        else:
            st.info("К цели пока не привязаны задачи.")
        linkable = [task for task in tasks if not task.get("goal_id") or task.get("goal_id") == goal["id"]]
        if linkable:
            task_options = {task["id"]: task["title"] for task in linkable}
            selected_task_id = st.selectbox(
                "Выберите задачу для связи",
                list(task_options),
                format_func=lambda task_id: task_options[task_id],
                key=f"goal_task_{goal['id']}",
            )
            if st.button("Связать задачу", key=f"link_goal_{goal['id']}"):
                link_task_to_goal(selected_task_id, goal["id"])
                st.rerun()
        return

    st.markdown(
        "<div class='hero'><div><div class='eyebrow'>Большие ориентиры</div>"
        "<h1>Цели.</h1>"
        "<p>Связывайте ежедневные задачи с тем, к чему хотите прийти.</p></div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("Добавить цель", expanded=True):
        version = st.session_state.get("new_goal_form_version", 0)
        with st.form(f"new_goal_{version}"):
            title = st.text_input("Название", max_chars=120)
            description = st.text_area("Описание", max_chars=1000)
            due_date = st.date_input("Дедлайн", value=date.today())
            submitted = st.form_submit_button("Сохранить цель", type="primary")
        if submitted:
            if not title.strip():
                st.error("Укажите название цели.")
            else:
                try:
                    create_goal(title.strip(), description.strip(), due_date.isoformat())
                except DatabaseError as error:
                    st.error(str(error))
                else:
                    st.session_state.new_goal_form_version = version + 1
                    st.rerun()
    st.subheader("Активные цели")
    active_goals = [goal for goal in goals if goal["status"] == "Active"]
    if not active_goals:
        st.info("Активных целей пока нет.")
    for goal in active_goals:
        progress = calculate_goal_progress(goal["id"])
        linked_tasks = get_goal_tasks(goal["id"])
        st.markdown(f"### {goal['title']}")
        st.caption(f"{goal['description'] or 'Без описания'} · Дедлайн: {format_due_date(goal['due_date'])}")
        st.progress(progress / 100, text=f"{progress}% · выполнено {sum(task['status'] == 'Done' for task in linked_tasks)} из {len(linked_tasks)} задач")
        if st.button("Открыть цель", key=f"open_goal_{goal['id']}"):
            st.session_state.selected_goal_id = goal["id"]
            st.rerun()


def render_task_management(tasks: list[dict]) -> None:
    st.markdown(
        "<div class='hero'><div><div class='eyebrow'>Организация дня</div>"
        "<h1>Управление<br>задачами.</h1>"
        "<p>Добавляйте, уточняйте и доводите важное до готового.</p></div></div>",
        unsafe_allow_html=True,
    )
    filter_category, filter_priority = st.columns(2)
    with filter_category:
        selected_category_filter = st.selectbox(
            "Фильтр по категории",
            ["Все категории"] + list(CATEGORY_LABELS.values()),
            key="task_filter_category",
        )
    with filter_priority:
        selected_priority_filter = st.selectbox(
            "Фильтр по приоритету",
            ["Все приоритеты"] + list(PRIORITY_LABELS.values()),
            key="task_filter_priority",
        )
    category_filter = next(
        (code for code, label in CATEGORY_LABELS.items() if label == selected_category_filter),
        None,
    )
    priority_filter = next(
        (code for code, label in PRIORITY_LABELS.items() if label == selected_priority_filter),
        None,
    )
    filtered_tasks = [
        task for task in tasks
        if (category_filter is None or task.get("category", "Other") == category_filter)
        and (priority_filter is None or task.get("priority") == priority_filter)
    ]
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Все задачи")
        if filtered_tasks:
            for task in filtered_tasks:
                render_task(task)
        else:
            st.info("По выбранным фильтрам задач нет.")
    with right:
        st.subheader("Добавить задачу")
        task_form()


try:
    init_db()
    tasks = get_tasks()
    dashboard_stats = get_dashboard_stats()
    goals = get_goals()
    habits = get_habits()
    recent_notes = get_recent_notes()
except DatabaseError as error:
    st.error(str(error))
    st.stop()
page = render_navigation()
if page == "about":
    render_about_page()
    st.stop()
if page == "habits":
    render_habits_page(habits)
    st.stop()
if page == "notes":
    render_notes_page(recent_notes)
    st.stop()
if page == "goals":
    render_goals_page(goals, tasks)
    st.stop()
if page == "tasks":
    render_task_management(tasks)
    st.stop()
weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
today = f"{weekdays[date.today().weekday()]}, {format_due_date(date.today().isoformat())}"

st.markdown(
    f"<div class='hero'><div><div class='eyebrow'>Личный центр управления</div>"
    f"<h1>Освободите место<br>для жизни.</h1>"
    f"<p>Спокойный обзор того, что важно сегодня.</p></div>"
    f"<div class='date-mark'><strong>{date.today().strftime('%d')}</strong>"
    f"<span>{today}</span></div></div>",
    unsafe_allow_html=True,
)

filter_category, filter_priority = st.columns(2)
with filter_category:
    selected_category_filter = st.selectbox(
        "Фильтр по категории",
        ["Все категории"] + list(CATEGORY_LABELS.values()),
        key="dashboard_filter_category",
    )
with filter_priority:
    selected_priority_filter = st.selectbox(
        "Фильтр по приоритету",
        ["Все приоритеты"] + list(PRIORITY_LABELS.values()),
        key="dashboard_filter_priority",
    )
category_filter = next(
    (code for code, label in CATEGORY_LABELS.items() if label == selected_category_filter),
    None,
)
priority_filter = next(
    (code for code, label in PRIORITY_LABELS.items() if label == selected_priority_filter),
    None,
)
dashboard_filtered_tasks = [
    task for task in tasks
    if (category_filter is None or task.get("category", "Other") == category_filter)
    and (priority_filter is None or task.get("priority") == priority_filter)
]
today_iso = date.today().isoformat()
week_start = date.today() - timedelta(days=6)
filtered_tasks_today = sum(
    task.get("due_date") == today_iso for task in dashboard_filtered_tasks
)
filtered_completed_week = sum(
    task.get("status") == "Done"
    and task.get("updated_at", "")[:10] >= week_start.isoformat()
    for task in dashboard_filtered_tasks
)

st.subheader("Сегодня в фокусе")
stats_columns = st.columns(4)
stat_cards = [
    ("Задачи сегодня", filtered_tasks_today, "с дедлайном на сегодня"),
    ("Выполнено за неделю", filtered_completed_week, "за последние 7 дней"),
    ("Активные привычки", dashboard_stats["active_habits"], "в текущем списке"),
    ("Текущая серия", dashboard_stats["current_streak"], "дней подряд"),
]
for column, (label, value, hint) in zip(stats_columns, stat_cards):
    with column:
        st.markdown(
            f"<div class='stat-card'><small>{label}</small>"
            f"<span class='metric'>{value}</span><small>{hint}</small></div>",
            unsafe_allow_html=True,
        )

active_goals = [goal for goal in goals if goal["status"] == "Active"]
if active_goals:
    st.subheader("Активные цели")
    goal_columns = st.columns(min(3, len(active_goals)))
    for column, goal in zip(goal_columns, active_goals[:3]):
        with column:
            progress = calculate_goal_progress(goal["id"])
            st.markdown(f"**{goal['title']}**")
            st.progress(progress / 100, text=f"{progress}% · до {format_due_date(goal['due_date'])}")

st.divider()
st.subheader("Текущие задачи")
focus_tasks = [
    task for task in dashboard_filtered_tasks if task["status"] != "Done"
][:5]
if focus_tasks:
    for task in focus_tasks:
        priority_icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(
            task.get("priority"), "⚪"
        )
        st.markdown(
            f"<div class='list-item'><strong>{priority_icon} {task.get('title', 'Без названия')}</strong>"
            f"<span>{format_due_date(task.get('due_date'))} · "
            f"{CATEGORY_LABELS.get(task.get('category'), 'Другое')}</span></div>",
            unsafe_allow_html=True,
        )
else:
    st.info("Нет незавершённых задач.")

st.divider()
habits_column, notes_column = st.columns(2)
with habits_column:
    st.markdown("### Привычки")
    if habits:
        for habit in habits[:5]:
            st.markdown(
                f"<div class='list-item'><strong>{habit['name']}</strong>"
                f"<span>Серия: {habit['streak']} дн.</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Активных привычек пока нет.")
with notes_column:
    st.markdown("### Последние заметки")
    if recent_notes:
        for note in recent_notes[:5]:
            preview = note["content"].replace("\n", " ")[:90]
            st.markdown(
                f"<div class='list-item'><strong>{note['title']}</strong>"
                f"<span>{preview or 'Пустая заметка'}</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Заметок пока нет.")

