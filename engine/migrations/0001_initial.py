import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monthly_income', models.DecimalField(decimal_places=2, max_digits=12)),
                ('safety_buffer', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('due_day', models.PositiveSmallIntegerField(help_text='Day of month the bill is due (1-31)')),
                ('is_recurring', models.BooleanField(default=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bills', to='engine.profile')),
            ],
        ),
        migrations.CreateModel(
            name='CreditCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('balance', models.DecimalField(decimal_places=2, max_digits=12)),
                ('apr', models.DecimalField(decimal_places=2, help_text='Annual percentage rate, e.g. 24.99', max_digits=5)),
                ('min_payment', models.DecimalField(decimal_places=2, max_digits=12)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credit_cards', to='engine.profile')),
            ],
        ),
        migrations.CreateModel(
            name='SweepEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('checking_balance', models.DecimalField(decimal_places=2, max_digits=12)),
                ('amount_swept', models.DecimalField(decimal_places=2, max_digits=12)),
                ('allocations', models.JSONField(help_text='Map of credit_card_id -> amount allocated')),
                ('safety_breakdown', models.JSONField(help_text='Transparency breakdown of the safe-to-sweep math')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sweeps', to='engine.profile')),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
