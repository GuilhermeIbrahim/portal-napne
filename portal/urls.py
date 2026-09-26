from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('noticia/<int:id>/', views.detalhe, name='detalhe'),
    path('enviar-pei/', views.enviar_pei, name='enviar_pei'),
    path('pesquisar_noticias/', views.pesquisar_noticias, name='pesquisar_noticias'),
    path('napne/cadastro/', views.cadastro_napne, name='cadastro_napne'),
    path('napne/login/', views.login_napne, name='login_napne'),
    path('sobre/', views.apresentacao_napne, name='apresentacao_napne'),
]