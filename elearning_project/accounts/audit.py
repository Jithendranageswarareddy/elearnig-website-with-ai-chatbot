from .models import SystemLog


def log_system_event(user, action_type, object_type="", object_id=None, metadata=None):
    payload = metadata or {}
    safe_object_id = object_id if isinstance(object_id, int) and object_id > 0 else None
    try:
        SystemLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action_type=action_type,
            object_type=object_type or "",
            object_id=safe_object_id,
            metadata=payload,
        )
    except Exception as e:
        print("ERROR:", str(e))
        # Logging must never break user-facing actions.
        return
