from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from .models import Tag, Camera, CrossCountingData
from .forms import TagForm, CameraForm

class DashboardView(LoginRequiredMixin, ListView):
    model = Tag
    context_object_name = 'tags'
    template_name = 'cross_counting/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tags = Tag.objects.all()
        tag_data = []

        for tag in tags:
            cameras = tag.cameras.all()
            camera_data = []

            for camera in cameras:
                latest_data = CrossCountingData.objects.filter(camera=camera).order_by('-created_at').first()
                camera_info = {
                    'camera': camera,
                    'latest_in_count': latest_data.cc_in_count if latest_data else 0,
                    'latest_out_count': latest_data.cc_out_count if latest_data else 0,
                    'latest_total_count': latest_data.cc_total_count if latest_data else 0,
                }
                camera_data.append(camera_info)

            tag_info = {
                'tag': tag,
                'cameras': camera_data,
                'current_occupancy': tag.get_current_occupancy(),
                'is_over_occupancy': tag.is_over_occupancy(),
            }
            tag_data.append(tag_info)

        context['tag_data'] = tag_data
        return context

class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    context_object_name = 'tags'
    template_name = 'cross_counting/tag_list.html'
    paginate_by = 10

class TagCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = 'cross_counting/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' created successfully."

class TagUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = 'cross_counting/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' updated successfully."

class TagDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tag
    template_name = 'cross_counting/tag_confirm_delete.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag deleted successfully."

    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class CameraListView(LoginRequiredMixin, ListView):
    model = Camera
    context_object_name = 'cameras'
    template_name = 'cross_counting/camera_list.html'
    paginate_by = 10

class CameraCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cross_counting/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' created successfully."

class CameraUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cross_counting/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' updated successfully."

class CameraDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Camera
    template_name = 'cross_counting/camera_confirm_delete.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera deleted successfully."

    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)