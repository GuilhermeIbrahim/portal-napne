from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path ('noticia/<int:id>/', views.detalhe, name='detalhe'),
    path('criar_noticia/', views.criar_noticia, name='criar_noticia'),
    path('editar_noticia/<int:id>/', views.editar_noticia, name='editar_noticia'),
    path('excluir_noticia/<int:id>/', views.excluir_noticia, name='excluir_noticia'),
]