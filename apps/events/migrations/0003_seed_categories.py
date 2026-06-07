# Generated manually to seed categories

from django.db import migrations

def seed_categories(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    from django.utils.text import slugify
    categories = [
        "Conférence",
        "Mariage & Cérémonie",
        "Matchs de Sport",
        "Concerts",
    ]
    for name in categories:
        slug = slugify(name)
        Category.objects.get_or_create(name=name, defaults={'slug': slug})

def rollback_categories(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    Category.objects.filter(name__in=["Conférence", "Mariage & Cérémonie", "Matchs de Sport", "Concerts"]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_event_price'),
    ]

    operations = [
        migrations.RunPython(seed_categories, rollback_categories),
    ]
