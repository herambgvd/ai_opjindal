from django import forms
from .models import Tag, Camera

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'occupancy']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'occupancy': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Tag.objects.filter(name__iexact=name).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("A tag with this name already exists.")
        return name

    def clean_occupancy(self):
        occupancy = self.cleaned_data['occupancy']
        if occupancy < 0:
            raise forms.ValidationError("Occupancy cannot be negative.")
        return occupancy

class CameraForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ['name', 'rtsp_link', 'status', 'tag']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'rtsp_link': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tag': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Camera.objects.filter(name__iexact=name).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("A camera with this name already exists.")
        return name

    def clean_rtsp_link(self):
        rtsp_link = self.cleaned_data['rtsp_link']
        if not rtsp_link.startswith('rtsp://'):
            raise forms.ValidationError("RTSP link must start with 'rtsp://'.")
        return rtsp_link