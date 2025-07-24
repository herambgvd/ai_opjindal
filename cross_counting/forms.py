# cross_counting/forms.py

from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Tag, Camera


class TagForm(forms.ModelForm):
    """Form for creating and updating tags"""

    class Meta:
        model = Tag
        fields = ['name', 'occupancy']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'Enter location name'
            }),
            'occupancy': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'Enter maximum occupancy',
                'min': '1'
            })
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name.strip()) < 2:
            raise ValidationError("Location name must be at least 2 characters long.")
        return name.strip()

    def clean_occupancy(self):
        occupancy = self.cleaned_data['occupancy']
        if occupancy < 1:
            raise ValidationError("Occupancy must be at least 1.")
        if occupancy > 10000:
            raise ValidationError("Occupancy cannot exceed 10,000.")
        return occupancy


class CameraForm(forms.ModelForm):
    """Form for creating and updating cameras"""

    class Meta:
        model = Camera
        fields = ['name', 'tag', 'rtsp_link', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'Enter camera name'
            }),
            'tag': forms.Select(attrs={
                'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md'
            }),
            'rtsp_link': forms.URLInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': 'rtsp://username:password@ip:port/path'
            }),
            'status': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name.strip()) < 2:
            raise ValidationError("Camera name must be at least 2 characters long.")
        return name.strip()

    def clean_rtsp_link(self):
        rtsp_link = self.cleaned_data['rtsp_link']
        if not rtsp_link.startswith('rtsp://'):
            raise ValidationError("RTSP link must start with 'rtsp://'")
        return rtsp_link


# Analysis Forms
class DailyAnalysisForm(forms.Form):
    """Form for daily analysis configuration"""
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        empty_label="Select a location...",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md'
        })
    )
    analysis_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
        })
    )

    def clean_analysis_date(self):
        analysis_date = self.cleaned_data['analysis_date']
        if analysis_date > date.today():
            raise ValidationError("Analysis date cannot be in the future.")
        return analysis_date


class ComparativeAnalysisForm(forms.Form):
    """Form for comparative analysis configuration"""
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        empty_label="Select a location...",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm rounded-md'
        })
    )
    base_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm'
        })
    )
    compare_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-green-500 focus:border-green-500 sm:text-sm'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        base_date = cleaned_data.get('base_date')
        compare_date = cleaned_data.get('compare_date')

        if base_date and compare_date:
            if base_date > date.today() or compare_date > date.today():
                raise ValidationError("Dates cannot be in the future.")
            if base_date == compare_date:
                raise ValidationError("Base date and compare date must be different.")

        return cleaned_data


class ComprehensiveAnalysisForm(forms.Form):
    """Form for comprehensive analysis configuration"""
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        empty_label="Select a location...",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm rounded-md'
        })
    )
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm'
        })
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-purple-500 focus:border-purple-500 sm:text-sm'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date:
            if from_date > date.today() or to_date > date.today():
                raise ValidationError("Dates cannot be in the future.")
            if from_date > to_date:
                raise ValidationError("From date cannot be later than to date.")

            # Check if date range is more than 7 days
            date_diff = (to_date - from_date).days
            if date_diff > 7:
                raise ValidationError("Date range cannot exceed 7 days.")

        return cleaned_data