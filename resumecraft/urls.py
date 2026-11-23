"""
URL configuration for ResumeCraft AI project.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('builder.urls')),
]
