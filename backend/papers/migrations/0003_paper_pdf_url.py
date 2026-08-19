from django.db import migrations, models


def backfill_pdf_url(apps, schema_editor):
    Paper = apps.get_model('papers', 'Paper')
    for paper in Paper.objects.all().iterator():
        url = (paper.pdf_url or '').strip()
        if not url:
            cover = (paper.cover_url or '').strip()
            if cover.startswith(('http://', 'https://')):
                url = cover
            elif paper.arxiv_id:
                url = f'https://arxiv.org/pdf/{paper.arxiv_id}.pdf'
        if url:
            updates = {}
            if paper.pdf_url != url:
                updates['pdf_url'] = url
            if not paper.cover_url:
                updates['cover_url'] = url
            if updates:
                Paper.objects.filter(pk=paper.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('papers', '0002_add_layout_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='pdf_url',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.RunPython(backfill_pdf_url, migrations.RunPython.noop),
    ]
