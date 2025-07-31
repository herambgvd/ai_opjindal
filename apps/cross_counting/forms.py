import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date

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


class DailyAnalysisForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a region"
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date:
            # Get current date in the application's timezone (Asia/Kolkata)
            current_date = timezone.localtime(timezone.now()).date()

            # Allow today's date and past dates
            if date > current_date:
                raise ValidationError(f"Date cannot be in the future. Today is {current_date}.")
        return date


class ComparativeAnalysisForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a region"
    )
    base_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    compare_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def clean_base_date(self):
        date = self.cleaned_data.get('base_date')
        if date:
            # Get current date in the application's timezone (Asia/Kolkata)
            current_date = timezone.localtime(timezone.now()).date()

            if date > current_date:
                raise ValidationError(f"Base date cannot be in the future. Today is {current_date}.")
        return date

    def clean_compare_date(self):
        date = self.cleaned_data.get('compare_date')
        if date:
            # Get current date in the application's timezone (Asia/Kolkata)
            current_date = timezone.localtime(timezone.now()).date()

            if date > current_date:
                raise ValidationError(f"Compare date cannot be in the future. Today is {current_date}.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        base_date = cleaned_data.get('base_date')
        compare_date = cleaned_data.get('compare_date')

        if base_date and compare_date:
            if base_date == compare_date:
                raise ValidationError("Base date and compare date must be different.")

        return cleaned_data


class ComprehensiveAnalysisForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a region"
    )
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def clean_from_date(self):
        date = self.cleaned_data.get('from_date')
        if date:
            # Get current date in the application's timezone (Asia/Kolkata)
            current_date = timezone.localtime(timezone.now()).date()

            if date > current_date:
                raise ValidationError(f"From date cannot be in the future. Today is {current_date}.")
        return date

    def clean_to_date(self):
        date = self.cleaned_data.get('to_date')
        if date:
            # Get current date in the application's timezone (Asia/Kolkata)
            current_date = timezone.localtime(timezone.now()).date()

            if date > current_date:
                raise ValidationError(f"To date cannot be in the future. Today is {current_date}.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date:
            if from_date > to_date:
                raise ValidationError("From date must be before to date.")

            if (to_date - from_date).days > 7:
                raise ValidationError("Date range cannot exceed 7 days.")

        return cleaned_data