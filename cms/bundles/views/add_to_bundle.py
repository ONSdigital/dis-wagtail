from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import get_text_list
from django.views.generic import FormView
from wagtail.admin import messages
from wagtail.models import Page

from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.mixins import BundledPageMixin
from cms.bundles.models import Bundle, BundlePage
from cms.bundles.permissions import user_can_manage_bundles

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseBase, HttpResponseRedirect


class AddToBundleView(FormView):
    form_class = AddToBundleForm
    template_name = "bundles/wagtailadmin/add_to_bundle.html"

    page_to_add: Page = None
    goto_next: str | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.page_to_add = get_object_or_404(
            Page.objects.specific().defer_streamfields(), id=self.kwargs["page_to_add_id"]
        )

        if not isinstance(self.page_to_add, BundledPageMixin):
            raise Http404("Cannot add this page type to a bundle")

        page_perms = self.page_to_add.permissions_for_user(request.user)  # type: ignore[attr-defined]
        if not (page_perms.can_edit() or page_perms.can_publish()):
            raise PermissionDenied

        if not user_can_manage_bundles(request.user):
            raise PermissionDenied

        self.goto_next = None
        redirect_to = request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts={self.request.get_host()}):
            self.goto_next = redirect_to

        if self.page_to_add.in_active_bundle:
            text_list = get_text_list(
                list(self.page_to_add.active_bundles.values_list("name", flat=True)),
                last_word="and",
            )
            admin_display_title = self.page_to_add.get_admin_display_title()  # type: ignore[attr-defined]

            messages.warning(request, f"Page '{admin_display_title}' is already in a bundle ('{text_list}')")

            if self.goto_next:
                return redirect(self.goto_next)

            return redirect("wagtailadmin_home")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs.update({"page_to_add": self.page_to_add})
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data.update(
            {
                "page_to_add": self.page_to_add,
                "next": self.goto_next,
            }
        )
        return context_data

    def form_valid(self, form: AddToBundleForm) -> HttpResponseRedirect:
        bundle: Bundle = form.cleaned_data["bundle"]  # the 'bundle' field is required in the form.
        bundle.bundled_pages.add(BundlePage(page=self.page_to_add))
        bundle.save()

        messages.success(
            self.request,
            f"Page '{self.page_to_add.get_admin_display_title()}' added to bundle '{bundle}'",
            buttons=[
                messages.button(
                    reverse("wagtailadmin_pages:edit", args=(self.page_to_add.id,)),
                    "Edit",
                )
            ],
        )
        redirect_to = self.request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts={self.request.get_host()}):
            return redirect(redirect_to)

        return redirect("wagtailadmin_explore", self.page_to_add.get_parent().id)
