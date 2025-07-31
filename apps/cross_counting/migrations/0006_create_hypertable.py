from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cross_counting', '0005_add_timescaledb_hypertable_support'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",
                
                "SELECT create_hypertable('cross_counting_data_timeseries', 'time', if_not_exists => TRUE);",
                
                "SELECT add_compression_policy('cross_counting_data_timeseries', INTERVAL '7 days', if_not_exists => TRUE);",
                
                "SELECT add_retention_policy('cross_counting_data_timeseries', INTERVAL '90 days', if_not_exists => TRUE);",
                
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS cross_counting_hourly_agg
                WITH (timescaledb.continuous) AS
                SELECT 
                    time_bucket('1 hour', time) AS hour,
                    camera_id,
                    device_name,
                    channel,
                    MAX(cc_in_count) as max_in_count,
                    MAX(cc_out_count) as max_out_count,
                    MAX(cc_total_count) as max_total_count,
                    MIN(cc_in_count) as min_in_count,
                    MIN(cc_out_count) as min_out_count,
                    MIN(cc_total_count) as min_total_count,
                    AVG(cc_total_count) as avg_total_count,
                    COUNT(*) as data_points
                FROM cross_counting_data_timeseries
                GROUP BY hour, camera_id, device_name, channel;
                """,
                
                "SELECT add_continuous_aggregate_policy('cross_counting_hourly_agg', start_offset => INTERVAL '1 day', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE);",
                
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS cross_counting_daily_agg
                WITH (timescaledb.continuous) AS
                SELECT 
                    time_bucket('1 day', time) AS day,
                    camera_id,
                    device_name,
                    channel,
                    MAX(cc_in_count) as peak_in_count,
                    MAX(cc_out_count) as peak_out_count,
                    MAX(cc_total_count) as peak_total_count,
                    COUNT(*) as data_points
                FROM cross_counting_data_timeseries
                GROUP BY day, camera_id, device_name, channel;
                """,
                
                "SELECT add_continuous_aggregate_policy('cross_counting_daily_agg', start_offset => INTERVAL '7 days', end_offset => INTERVAL '1 day', schedule_interval => INTERVAL '1 day', if_not_exists => TRUE);",
            ],
            reverse_sql=[
                "DROP MATERIALIZED VIEW IF EXISTS cross_counting_daily_agg;",
                "DROP MATERIALIZED VIEW IF EXISTS cross_counting_hourly_agg;",
                
                "-- WARNING: Reversing hypertable conversion requires manual intervention",
            ]
        ),
    ]
