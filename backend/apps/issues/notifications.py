"""Support-issue notifications (in-app + email via notifications.notify)."""
from apps.notifications.models import NotificationCategory
from apps.notifications.services.dispatcher import notify, notify_admins

# Where each role reads its support threads in the web app.
SUPPORT_PATH_BY_ROLE = {
    "customer": "/support",
    "farmer": "/farmer/support",
    "driver": "/driver/support",
    "admin": "/admin/support",
}


def _reporter_link(issue):
    return f"{SUPPORT_PATH_BY_ROLE.get(issue.reported_by.role, '/support')}/{issue.id}"


def notify_issue_created(issue):
    notify_admins(
        "issue_created",
        f"New support issue #{issue.id} ({issue.get_category_display()}) from {issue.reported_by.email}.",
        NotificationCategory.ISSUE_UPDATES, link=f"/admin/support/{issue.id}",
    )


def notify_issue_message(issue, message):
    if message.sender.role == "admin":
        if issue.reported_by_id != message.sender_id:
            notify(
                issue.reported_by, "issue_reply",
                f"Vuna Fresh support replied to issue #{issue.id}.",
                NotificationCategory.ISSUE_UPDATES, link=_reporter_link(issue),
            )
    else:
        notify_admins(
            "issue_reply",
            f"New reply on support issue #{issue.id} from {message.sender.email}.",
            NotificationCategory.ISSUE_UPDATES, link=f"/admin/support/{issue.id}",
        )


def notify_issue_status(issue):
    notify(
        issue.reported_by, "issue_status_changed",
        f"Your support issue #{issue.id} is now {issue.get_status_display().lower()}.",
        NotificationCategory.ISSUE_UPDATES, link=_reporter_link(issue),
    )
