# routes
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name="home"),
    url(r'^about/?$', views.about, name="about"),
    url(r'^simulation/(?P<game_id>\d+)/end/?$', views.simulation_end, name="simulation_end"),
    url(r'^simulation/(?P<game_id>\d+)/(?P<sim_id>\d+)/?$', views.game_simulator, name="game_view"),
]

# url(r'^simulation/(?P<game_id>\d+)/(?P<sim_id>\d+)/(?P<x>\d+)/(?P<y>\d+)/?$', views.get_new_location, name="get_location"),
