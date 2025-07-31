import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Region, Camera


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['name', 'occupancy']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter region name'
            }),
            'occupancy': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter maximum occupancy',
                'min': '1'
            })
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Region name cannot be empty.")
            qs = Region.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("A region with this name already exists.")
            if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
                raise ValidationError("Name can only contain letters, numbers, spaces, hyphens, and underscores.")
        return name

    def clean_occupancy(self):
        occupancy = self.cleaned_data.get('occupancy')
        if occupancy is None or occupancy <= 0:
            raise ValidationError("Occupancy must be a positive number.")
        if occupancy > 10000:
            raise ValidationError("Occupancy cannot exceed 10,000.")
        return occupancy


class CameraForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ['name', 'rtsp_link', 'region']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter camera name'
            }),
            'rtsp_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'rtsp://example.com:554/stream'
            }),
            'region': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].queryset = Region.objects.all().order_by('name')
        self.fields['region'].empty_label = "Select a region"

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Camera name cannot be empty.")
            qs = Camera.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("A camera with this name already exists.")
            if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
                raise ValidationError("Name can only contain letters, numbers, spaces, hyphens, and underscores.")
        return name

    def clean_rtsp_link(self):
        rtsp_link = self.cleaned_data.get('rtsp_link')
        if rtsp_link:
            if not rtsp_link.startswith('rtsp://'):
                raise ValidationError("RTSP link must start with 'rtsp://'")
        return rtsp_link
