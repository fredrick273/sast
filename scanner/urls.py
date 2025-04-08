from django.urls import path
from . import views

urlpatterns = [
    path('',views.home,name='home'),
    path('add/<int:id>/',views.add_to_scanlist,name='add_to_scanlist'),
    path('webhook/',views.github_webhook,name='github_endpoint')
]