from django.db import migrations

NOMES_DOS_GRUPOS = ["NAPNE", "Estudante", "Servidor"]

def criar_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in NOMES_DOS_GRUPOS:
        Group.objects.get_or_create(name=nome)

def remover_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=NOMES_DOS_GRUPOS).delete()
    
class Migration(migrations.Migration):
    
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    
    operations = [
        migrations.RunPython(criar_grupos, remover_grupos),
    ]