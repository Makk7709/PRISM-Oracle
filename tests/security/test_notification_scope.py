from python.helpers.notification import NotificationManager, NotificationPriority, NotificationType


def test_notification_visibility_is_scoped():
    manager = NotificationManager()
    manager.add_notification(
        NotificationType.SUCCESS,
        NotificationPriority.HIGH,
        "Task done",
        title="Done",
        target_username="jeremie",
        target_organization="dica",
        task_uuid="task-1",
        source="scheduler",
    )

    jeremie = manager.output(
        start=0,
        target_username="jeremie",
        target_organization="dica",
    )
    amine = manager.output(
        start=0,
        target_username="amine",
        target_organization="korev-ai",
    )

    assert len(jeremie) == 1
    assert jeremie[0]["task_uuid"] == "task-1"
    assert amine == []


def test_mark_read_refuses_cross_scope():
    manager = NotificationManager()
    manager.add_notification(
        NotificationType.INFO,
        NotificationPriority.NORMAL,
        "Hello",
        target_username="jeremie",
        target_organization="dica",
        task_uuid="task-2",
        source="scheduler",
    )
    nid = manager.notifications[0].id

    denied = manager.mark_read_ids(
        [nid],
        target_username="amine",
        target_organization="korev-ai",
    )
    allowed = manager.mark_read_ids(
        [nid],
        target_username="jeremie",
        target_organization="dica",
    )

    assert denied == 0
    assert allowed == 1


def test_unscoped_notification_is_rejected():
    manager = NotificationManager()
    try:
        manager.add_notification(
            NotificationType.WARNING,
            NotificationPriority.HIGH,
            "no scope",
        )
        assert False, "Expected scoped notification rejection"
    except ValueError as exc:
        assert "target_username" in str(exc)


def test_unscoped_helpers_return_nothing():
    manager = NotificationManager()
    manager.add_notification(
        NotificationType.INFO,
        NotificationPriority.NORMAL,
        "scoped",
        target_username="jeremie",
        target_organization="dica",
        task_uuid="task-3",
        source="scheduler",
    )
    by_type = manager.get_notifications_by_type(
        NotificationType.INFO,
        target_username=None,
        target_organization=None,
    )
    recent = manager.get_recent_notifications(
        120,
        target_username=None,
        target_organization=None,
    )
    assert by_type == []
    assert recent == []
