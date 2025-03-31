from django.contrib.auth import get_permission_codename


def get_permission_name(model, action: str) -> str:
    """Get the full app-label-qualified permission name (as required by
    user.has_perm(...) ) for the given action on this model.
    """
    return f"{model._meta.app_label}.{get_permission_codename(action, model._meta)}"
