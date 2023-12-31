from django import forms
from django.forms.models import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from wagtail.admin.widgets import AdminPageChooser
from wagtail.contrib.search_promotions.models import Query, SearchPromotion


class QueryForm(forms.Form):
    query_string = forms.CharField(
        label=_("Search term(s)/phrase"),
        help_text=_(
            "Enter the full search string to match. An "
            "exact match is required for your Promoted Results to be "
            "displayed, wildcards are NOT allowed."
        ),
        required=True,
    )


class SearchPromotionForm(forms.ModelForm):
    sort_order = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["page"].widget = AdminPageChooser()

    class Meta:
        model = SearchPromotion
        fields = (
            "query",
            "page",
            "external_link_url",
            "external_link_text",
            "description",
        )

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


SearchPromotionsFormSetBase = inlineformset_factory(
    Query,
    SearchPromotion,
    form=SearchPromotionForm,
    can_order=True,
    can_delete=True,
    extra=0,
)


class SearchPromotionsFormSet(SearchPromotionsFormSetBase):
    minimum_forms = 1
    minimum_forms_message = _(
        "Please specify at least one recommendation for this search term."
    )

    def add_fields(self, form, *args, **kwargs):
        super().add_fields(form, *args, **kwargs)

        # Hide delete and order fields
        form.fields["DELETE"].widget = forms.HiddenInput()
        form.fields["ORDER"].widget = forms.HiddenInput()

        # Remove query field
        del form.fields["query"]

    def clean(self):
        # Search pick must have at least one recommended page to be valid
        # Check there is at least one non-deleted form.
        non_deleted_forms = self.total_form_count()
        non_empty_forms = 0
        for i in range(0, self.total_form_count()):
            form = self.forms[i]

            page = form.cleaned_data["page"]
            external_link_url = form.cleaned_data["external_link_url"]
            external_link_text = form.cleaned_data["external_link_text"]

            # only a page or external_link_url can be supplied
            if page is None:
                if external_link_url:
                    # if an external_link_url then external_link_text is also required
                    if not external_link_text:
                        raise forms.ValidationError(
                            _(
                                "You must enter an external link text if you enter an external link URL."
                            )
                        )
                else:
                    raise forms.ValidationError(
                        _("You must recommend a page OR an external link.")
                    )
            else:
                if external_link_url:
                    raise forms.ValidationError(
                        _("Please only select a page OR enter an external link.")
                    )

            if self.can_delete and self._should_delete_form(form):
                non_deleted_forms -= 1
            if not (form.instance.id is None and not form.has_changed()):
                non_empty_forms += 1
        if (
            non_deleted_forms < self.minimum_forms
            or non_empty_forms < self.minimum_forms
        ):
            raise forms.ValidationError(self.minimum_forms_message)
