from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^logout/?$', views.logout_user, name='logout'),
    url(r'^about/?$', views.about, name='about'),
    url(r'^create-fitbit/?$', views.create_fitbit, name='create-fitbit'),
    url(r'^create-lastfm/?$', views.create_lastfm, name='create-lastfm'),
    url(r'^delete-fitbit/?$', views.delete_fitbit, name='delete-fitbit'),
    url(r'^deauth_hook/?$', views.deauth_hook, name='deauth_hook'),
    url(r'^fitbit/authorized/?$', views.complete_fitbit, name='fb_complete'),
    url(r'^netatmo/authorized/?$', views.complete_netatmo, name='netatmo_complete'),
    path('data/<int:oh_id>/', views.deliver_data, name='deliver_data'),
    path('lametric_data/<int:oh_id>/', views.deliver_lametric, name='deliver_lametric'),
    url(r'^delete-netatmo/?$', views.delete_netatmo, name='delete-netatmo'),
    url(r'^ah_receiver/?$', views.ah_receiver, name='ah-receiver'),
]
