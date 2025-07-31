from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cross_counting', '0003_optimize_timeseries_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY ts_alarm_time_brin_idx ON cross_counting_data_timeseries USING BRIN (alarm_time);",
            reverse_sql="DROP INDEX IF EXISTS ts_alarm_time_brin_idx;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY ts_created_at_brin_idx ON cross_counting_data_timeseries USING BRIN (created_at);",
            reverse_sql="DROP INDEX IF EXISTS ts_created_at_brin_idx;"
        ),
    ]
