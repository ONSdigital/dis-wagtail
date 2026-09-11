from cms.core.forms import PageWithEquationsAdminForm, PageWithProtectedChartImagesAdminForm


class MethodologyPageAdminForm(PageWithProtectedChartImagesAdminForm, PageWithEquationsAdminForm):
    protected_chart_image_fields = ("content",)
