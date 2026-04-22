from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ContactMessage
from accounts.decorators import principal_required

def contact_admin(request):
    if request.method == "POST":
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        body = (request.POST.get('message') or '').strip()
        if not name or not email or not body:
            messages.error(request, "Please complete all fields before submitting.")
            return render(request, 'contact.html')
        ContactMessage.objects.create(name=name, email=email, message=body)
        messages.success(request, "Message sent successfully. We'll get back to you soon.")
        return redirect('contact')
    return render(request, 'contact.html')


@login_required(login_url='user_login')
@principal_required
def view_messages(request):

    messages = ContactMessage.objects.all().order_by('-id')

    return render(request, 'view_messages.html', {'messages': messages})
