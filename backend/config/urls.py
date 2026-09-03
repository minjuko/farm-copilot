from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path

from common.views import capabilities


def index(request):
    return render(request, 'index.html')


urlpatterns = [
    path('', index),
    path('api/capabilities/', capabilities, name='capabilities'),
    path('admin/', admin.site.urls),
    path('login/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('community/', include('community.urls')),
    path('selfchatbot/', include('chatbot.urls', namespace='selfchatbot')),
    path('prediction/', include('prediction.urls')),
    path('detect/', include('detect.urls')),
    path('soil/', include('soil.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
