from datetime import date, timedelta

import requests
import streamlit as st


API_URL = st.secrets.get("API_URL", "http://localhost:8000")

DEFAULT_CATEGORIES = ["Assignments", "Revisions", "General"]


def fmt_date(iso_str: str) -> str:
    d = date.fromisoformat(iso_str)
    return d.strftime("%b %-d")


def days_left_str(due_iso: str) -> str:
    diff = (date.fromisoformat(due_iso) - date.today()).days

    if diff < 0:
        return f"Overdue by {abs(diff)}d"

    if diff == 0:
        return "Due today"

    if diff == 1:
        return "1 day left"

    return f"{diff} days left"


def duration_days(start_iso: str, due_iso: str) -> int:
    return (date.fromisoformat(due_iso) - date.fromisoformat(start_iso)).days + 1


def get_categories() -> list:
    try:
        r = requests.get(f"{API_URL}/categories", timeout=10)

        if r.status_code == 200:
            existing = r.json()
            merged = list(dict.fromkeys(DEFAULT_CATEGORIES + existing))
            return merged

    except requests.exceptions.RequestException:
        pass

    return DEFAULT_CATEGORIES


def bucket_for(due_iso: str) -> str:
    due = date.fromisoformat(due_iso)
    today = date.today()
    days_diff = (due - today).days

    if days_diff < 0:
        return "Overdue"

    if days_diff == 0:
        return "Today"

    this_week_end = today + timedelta(days=(6 - today.weekday()))
    next_week_end = this_week_end + timedelta(days=7)

    if due <= this_week_end:
        return "This Week"

    if due <= next_week_end:
        return "Next Week"

    return "Later"


BUCKET_ORDER = ["Overdue", "Today", "This Week", "Next Week", "Later"]


st.set_page_config(page_title="Student Task Scheduler", layout="wide")

st.title("📅 Student Task Scheduler")

st.caption(
    "Conflict-aware task & revision tracker — "
    "backend REST API + Supabase Postgres"
)


tab1, tab2, tab3 = st.tabs(
    ["📋 All Tasks", "➕ Add Task", "⚠️ Conflicts"]
)


with tab2:
    st.subheader("Add a new task")

    categories = get_categories()

    category_choice = st.selectbox(
        "Category",
        categories + ["+ Add new category"]
    )

    new_category = None

    if category_choice == "+ Add new category":
        new_category = st.text_input("New category name")

    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Title")

        description = st.text_area("Description", "")

        subject = st.text_input(
            "Subject (only relevant for revision tasks, e.g. 'DBMS')",
            ""
        )

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Scheduled date",
                date.today()
            )

        with col2:
            due_date = st.date_input(
                "Due date",
                date.today()
            )

        priority = st.selectbox(
            "Priority",
            ["low", "medium", "high"],
            format_func=str.title
        )

        submitted = st.form_submit_button("Add Task")

        if submitted:
            final_category = (
                (new_category or "").strip()
                if category_choice == "+ Add new category"
                else category_choice
            )

            if not title:
                st.error("Title is required")

            elif not final_category:
                st.error("Enter a name for the new category")

            elif due_date < start_date:
                st.error("Due date can't be before scheduled date")

            else:
                payload = {
                    "title": title,
                    "description": description or None,
                    "category": final_category,
                    "subject": subject or None,
                    "start_date": str(start_date),
                    "due_date": str(due_date),
                    "priority": priority,
                    "status": "pending",
                }

                try:
                    r = requests.post(
                        f"{API_URL}/tasks",
                        json=payload,
                        timeout=10
                    )

                    if r.status_code == 200:
                        st.success("Task added!")
                    else:
                        st.error(f"Failed: {r.text}")

                except requests.exceptions.RequestException as e:
                    st.error(
                        f"Could not reach the API at {API_URL}: {e}"
                    )


with tab1:
    st.subheader("All Tasks")

    categories = get_categories()

    filter_category = st.selectbox(
        "Filter by category",
        ["All"] + categories
    )

    params = (
        {}
        if filter_category == "All"
        else {"category": filter_category}
    )

    try:
        r = requests.get(
            f"{API_URL}/tasks",
            params=params,
            timeout=10
        )

    except requests.exceptions.RequestException as e:
        r = None
        st.error(
            f"Could not reach the API at {API_URL}: {e}"
        )

    if r is not None and r.status_code == 200:
        tasks = r.json()

        if not tasks:
            st.info("No tasks yet — add one in the 'Add Task' tab.")

        grouped = {b: [] for b in BUCKET_ORDER}

        for task in tasks:
            grouped[bucket_for(task["due_date"])].append(task)

        priority_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }

        for bucket in BUCKET_ORDER:
            bucket_tasks = grouped[bucket]

            if not bucket_tasks:
                continue

            st.markdown(f"### {bucket}")

            for task in sorted(
                bucket_tasks,
                key=lambda t: t["due_date"]
            ):
                emoji = priority_emoji.get(
                    task["priority"],
                    "⚪"
                )

                label = (
                    f"{emoji} {task['title']} — "
                    f"due {fmt_date(task['due_date'])} "
                    f"· {days_left_str(task['due_date'])}"
                )

                with st.expander(label):
                    st.write(f"**Category:** {task['category']}")

                    if task.get("subject"):
                        st.write(f"**Subject:** {task['subject']}")

                    st.write(
                        f"**Description:** "
                        f"{task.get('description') or '—'}"
                    )

                    window_days = duration_days(
                        task["start_date"],
                        task["due_date"]
                    )

                    st.write(
                        f"**Window:** "
                        f"{fmt_date(task['start_date'])} → "
                        f"{fmt_date(task['due_date'])} "
                        f"({window_days} day"
                        f"{'s' if window_days != 1 else ''} "
                        f"to work on it)"
                    )

                    st.write(
                        f"**Priority:** "
                        f"{task['priority'].title()}"
                    )

                    st.write(
                        f"**Status:** "
                        f"{task['status'].title()}"
                    )

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if task["status"] == "pending":
                            if st.button(
                                "✅ Mark done",
                                key=f"done_{task['id']}"
                            ):
                                requests.put(
                                    f"{API_URL}/tasks/{task['id']}",
                                    json={"status": "done"},
                                    timeout=10
                                )

                                st.rerun()

                    with col2:
                        if st.button(
                            "✏️ Edit",
                            key=f"edit_{task['id']}"
                        ):
                            st.session_state["editing_task_id"] = task["id"]
                            st.rerun()

                    with col3:
                        if st.button(
                            "🗑️ Delete",
                            key=f"del_{task['id']}"
                        ):
                            requests.delete(
                                f"{API_URL}/tasks/{task['id']}",
                                timeout=10
                            )

                            st.rerun()

                    if st.session_state.get(
                        "editing_task_id"
                    ) == task["id"]:

                        st.markdown("---")
                        st.markdown("**Edit task**")

                        with st.form(
                            f"edit_form_{task['id']}"
                        ):
                            edit_title = st.text_input(
                                "Title",
                                value=task["title"]
                            )

                            edit_description = st.text_area(
                                "Description",
                                value=task.get("description") or ""
                            )

                            edit_categories = (
                                categories
                                if task["category"] in categories
                                else categories + [task["category"]]
                            )

                            edit_category = st.selectbox(
                                "Category",
                                edit_categories,
                                index=edit_categories.index(
                                    task["category"]
                                )
                            )

                            edit_subject = st.text_input(
                                "Subject",
                                value=task.get("subject") or ""
                            )

                            ecol1, ecol2 = st.columns(2)

                            with ecol1:
                                edit_start = st.date_input(
                                    "Scheduled date",
                                    value=date.fromisoformat(
                                        task["start_date"]
                                    )
                                )

                            with ecol2:
                                edit_due = st.date_input(
                                    "Due date",
                                    value=date.fromisoformat(
                                        task["due_date"]
                                    )
                                )

                            edit_priority = st.selectbox(
                                "Priority",
                                ["low", "medium", "high"],
                                index=[
                                    "low",
                                    "medium",
                                    "high"
                                ].index(task["priority"]),
                                format_func=str.title,
                            )

                            edit_status = st.selectbox(
                                "Status",
                                ["pending", "done"],
                                index=[
                                    "pending",
                                    "done"
                                ].index(task["status"]),
                                format_func=str.title,
                            )

                            fcol1, fcol2 = st.columns(2)

                            with fcol1:
                                save_clicked = st.form_submit_button(
                                    "💾 Save changes"
                                )

                            with fcol2:
                                cancel_clicked = st.form_submit_button(
                                    "Cancel"
                                )

                            if save_clicked:
                                if edit_due < edit_start:
                                    st.error(
                                        "Due date can't be before scheduled date"
                                    )

                                else:
                                    update_payload = {
                                        "title": edit_title,
                                        "description": edit_description or None,
                                        "category": edit_category,
                                        "subject": edit_subject or None,
                                        "start_date": str(edit_start),
                                        "due_date": str(edit_due),
                                        "priority": edit_priority,
                                        "status": edit_status,
                                    }

                                    resp = requests.put(
                                        f"{API_URL}/tasks/{task['id']}",
                                        json=update_payload,
                                        timeout=10
                                    )

                                    if resp.status_code == 200:
                                        st.session_state[
                                            "editing_task_id"
                                        ] = None

                                        st.success("Task updated!")
                                        st.rerun()

                                    else:
                                        st.error(
                                            f"Failed: {resp.text}"
                                        )

                            if cancel_clicked:
                                st.session_state[
                                    "editing_task_id"
                                ] = None

                                st.rerun()

    elif r is not None:
        st.error("Could not fetch tasks from the API.")


with tab3:
    st.subheader("Conflict Warnings")

    st.caption(
        "High-priority, pending tasks with the same due date"
    )

    try:
        r = requests.get(
            f"{API_URL}/tasks/conflicts/check",
            timeout=10
        )

        if r.status_code == 200:
            data = r.json()

            active = data.get("active", [])
            dismissed = data.get("dismissed", [])

            if not active:
                st.success("No active conflicts 🎉")

            else:
                for c in active:
                    t1_days = duration_days(
                        c["task_1_start"],
                        c["task_1_due"]
                    )

                    t2_days = duration_days(
                        c["task_2_start"],
                        c["task_2_due"]
                    )

                    st.warning(
                        f"**{c['task_1']}** and "
                        f"**{c['task_2']}** have the same due date: "
                        f"**{fmt_date(c['overlap_start'])}**\n\n"
                        f"Both tasks are high priority. Their scheduled "
                        f"working periods are different, so you can "
                        f"continue working on both if you are comfortable "
                        f"managing them.\n\n"
                        f"- **{c['task_1']}**: "
                        f"{fmt_date(c['task_1_start'])} → "
                        f"{fmt_date(c['task_1_due'])} "
                        f"({t1_days} day"
                        f"{'s' if t1_days != 1 else ''} available)\n"
                        f"- **{c['task_2']}**: "
                        f"{fmt_date(c['task_2_start'])} → "
                        f"{fmt_date(c['task_2_due'])} "
                        f"({t2_days} day"
                        f"{'s' if t2_days != 1 else ''} available)"
                    )

                    if st.button(
                        "👍 Proceed anyway",
                        key=f"dismiss_{c['conflict_id']}"
                    ):
                        response = requests.post(
                            f"{API_URL}/tasks/conflicts/"
                            f"{c['conflict_id']}/dismiss",
                            timeout=10
                        )

                        if response.status_code == 200:
                            st.success(
                                "Conflict acknowledged for 30 minutes."
                            )
                            st.rerun()

                        else:
                            st.error(
                                f"Failed to acknowledge conflict: "
                                f"{response.text}"
                            )

            if dismissed:
                st.markdown("### 🤝 Proceeding Anyway")

                st.caption(
                    "These tasks share a due date, but you chose to proceed. "
                    "This warning will disappear automatically after 30 minutes."
                )

                for c in dismissed:
                    st.info(
                        f"**{c['task_1']}** and "
                        f"**{c['task_2']}** — both due on "
                        f"{fmt_date(c['overlap_start'])}\n\n"
                        f"Their scheduled working periods are different. "
                        f"You chose to proceed anyway."
                    )

        else:
            st.error("Could not fetch conflicts.")

    except requests.exceptions.RequestException as e:
        st.error(
            f"Could not reach the API at {API_URL}: {e}"
        )