from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^logout/?$', views.logout_user, name='logout'),
    url(r'^about/?$', views.about, name='about'),
    url(r'^create-fitbit/?$', views.create_fitbit, name='create-fitbit'),
    url(r'^delete-fitbit/?$', views.delete_fitbit, name='delete-fitbit'),
    url(r'^fitbit/authorized/?$', views.complete_fitbit, name='fb_complete'),
    path('data/<int:oh_id>/', views.deliver_data, name='deliver_data'),
]
