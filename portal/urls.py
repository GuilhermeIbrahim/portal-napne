from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('noticia/<int:id>/', views.detalhe, name='detalhe'),
    path('enviar-pei/', views.enviar_pei, name='enviar_pei'),
    path('pesquisar_noticias/', views.pesquisar_noticias, name='pesquisar_noticias'),
    path('napne/cadastro/', views.cadastro_napne, name='cadastro_napne'),
    path('napne/login/', views.login_napne, name='login_napne'),
<<<<<<< HEAD
    path('feedback-publico/<int:noticia_id>/', views.fazer_feedback_publico, name='fazer_feedback_publico'),
    path('feedback-privado/', views.fazer_feedback_privado, name='fazer_feedback_privado'),
    path('excluir-feedback-publico/<int:feedback_id>/', views.excluir_feedback_publico, name='excluir_feedback_publico'),
=======
>>>>>>> c21c7da6615de4faf12ec6f9a9e962b187ad9d58
]