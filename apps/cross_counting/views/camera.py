import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def camera_list(request):
    context = {}
    return render(request, 'cross_counting/camera/main.html', context)


@login_required(login_url="account_login")
def camera_create(request):
    context = {}
    return render(request, 'cross_counting/camera/camera_create.html', context)


@login_required(login_url="account_login")
def camera_update(request, camera_id):
    context = {}
    return render(request, 'cross_counting/camera/camera_update.html', context)


@login_required(login_url="account_login")
def camera_delete(request, camera_id):
    return render(request, 'cross_counting/camera/camera_delete_conf.html', context)
