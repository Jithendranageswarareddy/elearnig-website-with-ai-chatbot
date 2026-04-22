"""
URL configuration for elearning_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.urls import path, include, re_path


admin.site.has_permission = lambda request: bool(
    request.user.is_active and request.user.is_superuser
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('courses.urls')),
    path('', include('progress.urls')),
    path('', include('chatbot.urls')),
    path('', include('contact.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", staticfiles_serve, {"insecure": True}),
    ]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
