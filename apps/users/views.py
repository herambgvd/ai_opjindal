from .adapter import user_has_valid_totp_device
from .forms import CustomUserChangeForm, UploadAvatarForm
from .helpers import require_email_confirmation, user_has_confirmed_email_address
from .models import CustomUser

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from allauth.account.models import EmailAddress


@login_required
def profile(request):
    """
    Display and handle profile update for the authenticated user.
    If email is changed and requires confirmation, sends a verification mail
    and preserves the original email until it's confirmed.
    """
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user_before_update = CustomUser.objects.get(pk=user.pk)

            new_email = user.email
            need_to_confirm_email = (
                user_before_update.email != new_email
                and require_email_confirmation()
                and not user_has_confirmed_email_address(user, new_email)
            )

            if need_to_confirm_email:
                # Send email confirmation and keep old email until confirmed
                email_address, created = EmailAddress.objects.get_or_create(
                    user=user,
                    email=new_email,
                    defaults={"primary": False, "verified": False},
                )
                email_address.send_confirmation(request)
                user.email = user_before_update.email  # rollback change

                # Recreate the form with the old email
                form = CustomUserChangeForm(instance=user)

            user.save()
            messages.success(request, _("Profile successfully saved."))
    else:
        form = CustomUserChangeForm(instance=request.user)

    return render(
        request,
        "account/profile.html",
        {
            "form": form,
            "active_tab": "profile",
            "page_title": _("Profile"),
            "user_has_valid_totp_device": user_has_valid_totp_device(request.user),
        },
    )


@login_required
@require_POST
def upload_profile_image(request):
    """
    Handle profile image (avatar) upload for authenticated users.
    Returns success message or validation errors.
    """
    user = request.user
    form = UploadAvatarForm(request.POST, request.FILES)

    if form.is_valid():
        user.avatar = request.FILES["avatar"]
        user.save()
        return HttpResponse(_("Success!"))
    else:
        readable_errors = ", ".join(
            str(error) for key, errors in form.errors.items() for error in errors
        )
        return JsonResponse(status=403, data={"errors": readable_errors})
