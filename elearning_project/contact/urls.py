from django.urls import path
from .views import contact_admin, view_messages

urlpatterns = [
    path('contact/', contact_admin, name='contact'),
    path('admin-messages/', view_messages, name='view_messages'),
]