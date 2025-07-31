import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Region


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['name', 'occupancy_limit']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            qs = Region.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("A region with this name already exists.")
            if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
                raise ValidationError("Name can only contain letters, numbers, spaces, hyphens, underscores.")
        return name

    def clean_occupancy_limit(self):
        limit = self.cleaned_data.get('occupancy_limit')
        if limit is None or limit <= 0:
            raise ValidationError("Occupancy limit must be positive.")
        return limit
