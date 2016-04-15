"""
Forms for the project application
"""

from django import forms

from autocomplete_light import shortcuts as autocomplete_light
from autocomplete_light.contrib.taggit_field import TaggitField, TaggitWidget

from muckrock.project.models import Project

class ProjectBasicsForm(forms.ModelForm):
    """Form for the basic fields of a project."""

    tags = TaggitField(
        widget=TaggitWidget('TagAutocomplete', attrs={
            'placeholder': 'Search tags',
            'data-autocomplete-minimum-characters': 1
        }),
        help_text='Separate tags with commas.',
        required=False
    )

    class Meta:
        model = Project
        fields = ['title', 'summary', 'image', 'tags']
        help_texts = {
            'summary': 'A short description of the project and its goals.',
            'image': 'Image should be large and high-resolution.'
        }


class ProjectDescriptionForm(forms.ModelForm):
    """Allows for the editing of the project description"""
    class Meta:
        model = Project
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'prose-editor'})
        }


class ProjectUpdateForm(forms.ModelForm):
    """Form for updating a project instance"""

    tags = TaggitField(
        widget=TaggitWidget('TagAutocomplete', attrs={'placeholder': 'Search tags'}),
        help_text='Separate tags with commas.',
        required=False
    )

    class Meta:
        model = Project
        fields = [
            'summary',
            'image',
            'tags',
            'description',
            'contributors',
            'requests',
            'articles',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'class': 'prose-editor'})
        }


class ProjectManagerForm(forms.Form):
    """Form for managing a list of projects"""
    projects = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Project.objects.all(),
        widget=autocomplete_light.MultipleChoiceWidget(
            'ProjectManagerAutocomplete',
            attrs={'placeholder': 'Search for a project'}))
