from django.shortcuts import render, redirect


def home(request):
    if request.user.is_authenticated:
        return redirect('cross_counting:enhanced_dashboard')
    else:
        return render(request, "web/landing_page.html")


def simulate_error(request):
    raise Exception("This is a simulated error.")
