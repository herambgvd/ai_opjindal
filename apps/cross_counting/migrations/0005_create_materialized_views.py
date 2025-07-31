from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cross_counting', '0004_add_brin_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE MATERIALIZED VIEW cross_counting_hourly_aggregates AS
            SELECT 
                ROW_NUMBER() OVER (ORDER BY camera_id, hour) as id,
                camera_id,
                DATE_TRUNC('hour', alarm_time) as hour,
                MAX(cc_in_count) as max_in_count,
                MAX(cc_out_count) as max_out_count,
                MAX(cc_total_count) as max_total_count,
                MIN(cc_in_count) as min_in_count,
                MIN(cc_out_count) as min_out_count,
                MIN(cc_total_count) as min_total_count,
                AVG(cc_total_count::float) as avg_total_count,
                COUNT(*) as data_points
            FROM cross_counting_data_timeseries
            GROUP BY camera_id, DATE_TRUNC('hour', alarm_time);
            
            CREATE UNIQUE INDEX ON cross_counting_hourly_aggregates (camera_id, hour);
            """,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS cross_counting_hourly_aggregates;"
        ),
        migrations.RunSQL(
            """
            CREATE MATERIALIZED VIEW cross_counting_daily_peaks AS
            SELECT 
                ROW_NUMBER() OVER (ORDER BY camera_id, date) as id,
                camera_id,
                DATE(alarm_time) as date,
                MAX(cc_in_count) as peak_in_count,
                MAX(cc_out_count) as peak_out_count,
                MAX(cc_total_count) as peak_total_count
            FROM cross_counting_data_timeseries
            GROUP BY camera_id, DATE(alarm_time);
            
            CREATE UNIQUE INDEX ON cross_counting_daily_peaks (camera_id, date);
            """,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS cross_counting_daily_peaks;"
        ),
        migrations.RunSQL(
            """
            CREATE INDEX ts_active_alarms_partial_idx ON cross_counting_data_timeseries (alarm_time, camera_id) 
            WHERE alarm_status = true;
            """,
            reverse_sql="DROP INDEX IF EXISTS ts_active_alarms_partial_idx;"
        ),
    ]
