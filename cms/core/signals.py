from django.dispatch import Signal

# Sent when a page's title changes without its slug changing.
page_title_changed = Signal()
