"""
Forms for FOIA application
"""

from django import forms
from django.template.defaultfilters import slugify
from django.forms.util import ErrorList

from foia.models import FOIARequest


class FOIARequestForm(forms.ModelForm):
    """A form for a FOIA Request"""

    def clean(self):
        """Check user and slug are unique together"""

        forms.ModelForm.clean(self)

        # if no title, just return, let field error be raised
        if 'title' not in self.cleaned_data:
            return self.cleaned_data

        user = self.instance.user
        slug = slugify(self.cleaned_data['title'])

        other_foias = FOIARequest.objects.filter(user=user, slug=slug)

        if len(other_foias) == 1 and other_foias[0] != self.instance:
            self._errors['title'] = \
                ErrorList(['You already have a FOIA request with a similar title'])

        if len(other_foias) > 1: # pragma: no cover
            # this should never happen
            self._errors['title'] = \
                ErrorList(['You already have a FOIA request with a similar title'])

        return self.cleaned_data

    class Meta:
        # pylint: disable-msg=R0903
        model = FOIARequest
        fields = ['title', 'jurisdiction', 'agency', 'request']

TEMPLATE_CHOICES = (
    ('Genealogy', (
            ('marriage', 'Marriage'),
            ('birth', 'Birth'),
            ('death', 'Death'),
        )
    ),
    ('Crime', (
            ('mug_shot', 'Mug Shots'),
            ('record', 'Criminal Record'),
            ('data', 'Data Regarding Crimes'),
        )
    ),
    ('Money', (
            ('property', 'Property Value'),
            ('record', 'Salaris'),
            ('data', 'Contracts'),
        )
    ),
    ('none', 'None'),
)

class FOIATemplateSelectForm(forms.Form):
    """A form to select which FOIA template you want"""

    template = forms.ChoiceField(choices=TEMPLATE_CHOICES)


class FOIAMugShotForm(forms.Form):
    """A form to fill in a mug shot template"""

    full_name = forms.CharField()
    date_begin = forms.DateField()
    date_end = forms.DateField()
