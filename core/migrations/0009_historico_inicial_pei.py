from django.db import migrations


def criar_historico_inicial(apps, schema_editor):
    Pei = apps.get_model('core', 'Pei')
    HistoricoPei = apps.get_model('core', 'HistoricoPei')

    for pei in Pei.objects.all():
        HistoricoPei.objects.get_or_create(
            pei=pei,
            status_anterior='em_analise',
            status_novo=pei.status,
            defaults={
                'alterado_por': pei.professor,
                'observacao': 'Status inicial atribuído automaticamente na migração do sistema de acompanhamento.',
            },
        )


def reverter_historico_inicial(apps, schema_editor):
    HistoricoPei = apps.get_model('core', 'HistoricoPei')
    HistoricoPei.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_pei_status_historicopei'),
    ]

    operations = [
        migrations.RunPython(criar_historico_inicial, reverter_historico_inicial),
    ]