from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('noticia/<int:id>/', views.detalhe, name='detalhe'),
    path('enviar-pei/', views.enviar_pei, name='enviar_pei'),
    path('pesquisar_noticias/', views.pesquisar_noticias, name='pesquisar_noticias'),
]