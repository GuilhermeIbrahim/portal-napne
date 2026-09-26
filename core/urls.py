from django.urls import path

from . import views

urlpatterns = [
    path('', views.painel_home, name='painel_home'),
    path('criar_noticia/', views.criar_noticia, name='criar_noticia'),
    path('editar_noticia/<int:id>/', views.editar_noticia, name='editar_noticia'),
    path('excluir_noticia/<int:id>/', views.excluir_noticia, name='excluir_noticia'),
    path('detalhar_pei/<int:id>/', views.detalhar_pei, name='detalhar_pei'),
    path('listar_peis/', views.listar_peis, name='listar_peis'),
    path('excluir_pei/<int:id>/', views.excluir_pei, name='excluir_pei'),
    path('editar_pei/<int:id>/', views.editar_pei, name='editar_pei'),
    path('baixar_pei/<int:id>/', views.baixar_pei, name='baixar_pei'),
    path('solicitacoes-napne/', views.solicitacoes_napne, name='solicitacoes_napne'),
    path('solicitacoes-napne/<int:id>/aprovar/', views.aprovar_solicitacao_napne, name='aprovar_solicitacao_napne'),
    path('solicitacoes-napne/<int:id>/recusar/', views.recusar_solicitacao_napne, name='recusar_solicitacao_napne'),
    path('listar_feedbacks_privados/', views.listar_feedbacks_privados, name='listar_feedbacks_privados'),
]
