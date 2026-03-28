import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0019_add_performance_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="annonce",
            name="prix",
            field=models.IntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
