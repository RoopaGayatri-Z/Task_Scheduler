from datetime import date, timedelta

import requests
import streamlit as st

API_URL = st.secrets.get("API_URL", "http://localhost:8000")

DEFAULT_CATEGORIES = ["Assignments", "Revisions", "General"]


def fmt_date(iso_str: str) -> str:
    """'2026-09-05' -> 'Sep 5'"""
    d = date.fromisoformat(iso_str)
    return d.strftime("%b %-d")


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
st.caption("Conflict-aware task & revision tracker — backend REST API + Supabase Postgres")

tab1, tab2, tab3 = st.tabs(["📋 All Tasks", "➕ Add Task", "⚠️ Conflicts"])

with tab2:
    st.subheader("Add a new task")

    categories = get_categories()
    category_choice = st.selectbox("Category", categories + ["+ Add new category"])

    new_category = None
    if category_choice == "+ Add new category":
        new_category = st.text_input("New category name")

    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description", "")
        subject = st.text_input("Subject (only relevant for revision tasks, e.g. 'DBMS')", "")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Scheduled date", date.today())
        with col2:
            due_date = st.date_input("Due date", date.today())

        priority = st.selectbox("Priority", ["low", "medium", "high"], format_func=str.title)
        submitted = st.form_submit_button("Add Task")

        if submitted:
            final_category = (new_category or "").strip() if category_choice == "+ Add new category" else category_choice

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
                    r = requests.post(f"{API_URL}/tasks", json=payload, timeout=10)
                    if r.status_code == 200:
                        st.success("Task added!")
                    else:
                        st.error(f"Failed: {r.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach the API at {API_URL}: {e}")

with tab1:
    st.subheader("All Tasks")

    categories = get_categories()
    filter_category = st.selectbox("Filter by category", ["All"] + categories)
    params = {} if filter_category == "All" else {"category": filter_category}

    try:
        r = requests.get(f"{API_URL}/tasks", params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        r = None
        st.error(f"Could not reach the API at {API_URL}: {e}")

    if r is not None and r.status_code == 200:
        tasks = r.json()
        if not tasks:
            st.info("No tasks yet — add one in the 'Add Task' tab.")

        grouped = {b: [] for b in BUCKET_ORDER}
        for task in tasks:
            grouped[bucket_for(task["due_date"])].append(task)

        priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}

        for bucket in BUCKET_ORDER:
            bucket_tasks = grouped[bucket]
            if not bucket_tasks:
                continue

            st.markdown(f"### {bucket}")
            for task in sorted(bucket_tasks, key=lambda t: t["due_date"]):
                emoji = priority_emoji.get(task["priority"], "⚪")
                label = f"{emoji} {task['title']} — due {fmt_date(task['due_date'])}"
                with st.expander(label):
                    st.write(f"**Category:** {task['category']}")
                    if task.get("subject"):
                        st.write(f"**Subject:** {task['subject']}")
                    st.write(f"**Description:** {task.get('description') or '—'}")
                    st.write(f"**Window:** {fmt_date(task['start_date'])} → {fmt_date(task['due_date'])}")
                    st.write(f"**Priority:** {task['priority'].title()}")
                    st.write(f"**Status:** {task['status'].title()}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if task["status"] == "pending":
                            if st.button("✅ Mark done", key=f"done_{task['id']}"):
                                requests.put(f"{API_URL}/tasks/{task['id']}", json={"status": "done"}, timeout=10)
                                st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{task['id']}"):
                            requests.delete(f"{API_URL}/tasks/{task['id']}", timeout=10)
                            st.rerun()
    elif r is not None:
        st.error("Could not fetch tasks from the API.")

with tab3:
    st.subheader("Conflict Warnings")
    st.caption("High-priority, pending tasks whose date windows overlap")
    try:
        r = requests.get(f"{API_URL}/tasks/conflicts/check", timeout=10)
        if r.status_code == 200:
            conflicts = r.json()
            if not conflicts:
                st.success("No conflicts detected 🎉")
            for c in conflicts:
                st.warning(
                    f"**{c['task_1']}** overlaps with **{c['task_2']}** "
                    f"between {fmt_date(c['overlap_start'])} and {fmt_date(c['overlap_end'])}"
                )
        else:
            st.error("Could not fetch conflicts.")
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach the API at {API_URL}: {e}")