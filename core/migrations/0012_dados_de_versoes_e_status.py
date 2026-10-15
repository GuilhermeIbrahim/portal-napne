from django.db import migrations


def migrar_dados(apps, schema_editor):
    Pei = apps.get_model('core', 'Pei')
    VersaoPei = apps.get_model('core', 'VersaoPei')
    HistoricoPei = apps.get_model('core', 'HistoricoPei')

    # 1) Corrige o valor gravado com erro de digitação: "analizado" -> "analisado".
    Pei.objects.filter(status='analizado').update(status='analisado')
    HistoricoPei.objects.filter(status_anterior='analizado').update(status_anterior='analisado')
    HistoricoPei.objects.filter(status_novo='analizado').update(status_novo='analisado')

    # 2) Todo PEI existente passa a ter a versão 1 (o arquivo que já estava cadastrado).
    for pei in Pei.objects.all():
        if not pei.arquivo:
            continue
        VersaoPei.objects.get_or_create(
            pei=pei,
            numero=1,
            defaults={'arquivo': pei.arquivo.name, 'enviado_por': pei.professor},
        )

    # 3) O histórico que já existia se refere a essa única versão.
    for versao in VersaoPei.objects.filter(numero=1):
        HistoricoPei.objects.filter(pei=versao.pei, versao__isnull=True).update(versao=versao)


def desfazer(apps, schema_editor):
    Pei = apps.get_model('core', 'Pei')
    HistoricoPei = apps.get_model('core', 'HistoricoPei')

    Pei.objects.filter(status='analisado').update(status='analizado')
    HistoricoPei.objects.filter(status_anterior='analisado').update(status_anterior='analizado')
    HistoricoPei.objects.filter(status_novo='analisado').update(status_novo='analizado')
    # As versões criadas são removidas junto com a migração de esquema anterior.


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_versoes_de_pei_e_status_de_ajustes'),
    ]

    operations = [
        migrations.RunPython(migrar_dados, desfazer),
    ]
