import json
from dateutil.parser import parse
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cross_counting.models import CrossCountingData, Camera


class Command(BaseCommand):
    help = "Listen to MQTT topic and save Cross Counting data into the database"

    def handle(self, *args, **kwargs):
        MQTT_BROKER = "0.0.0.0"
        MQTT_PORT = 1883
        MQTT_TOPIC = "alert"

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(f"Connected to MQTT Broker: {MQTT_BROKER}")
                client.subscribe(MQTT_TOPIC)
                self.stdout.write(f"Subscribed to topic: {MQTT_TOPIC}")
            else:
                self.stderr.write(f"Failed to connect, return code {rc}")

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
                self.stdout.write(f"Received MQTT payload: {json.dumps(payload, indent=2)}")
                
                data = payload.get("data", {})
                dev_net_info = data.get("dev_net_info", [{}])[0]
                alarm_list = data.get("alarm_list", [])
                subscribe_id = data.get("subscribe_id")
                data_pos = data.get("data_pos")

                channel_name = dev_net_info.get("ChannelName")
                if not channel_name:
                    self.stderr.write("Missing ChannelName in dev_net_info. Discarding alert.")
                    return

                try:
                    camera = Camera.objects.get(name=channel_name)
                    camera.last_data_received = timezone.now()
                    camera.save(update_fields=['last_data_received'])
                except Camera.DoesNotExist:
                    self.stdout.write(f"Camera object not found for ChannelName: {channel_name}. Discarding alert.")
                    return

                device_name = dev_net_info.get("device_name", "Unknown Device")
                device_ip = dev_net_info.get("ip", "0.0.0.0")
                device_mac = dev_net_info.get("mac", "00:00:00:00:00:00")
                device_phy = dev_net_info.get("phy", "")

                for alarm in alarm_list:
                    alarm_time_str = alarm.get("time")
                    if not alarm_time_str:
                        self.stderr.write("Missing alarm time. Skipping alarm.")
                        continue
                    
                    try:
                        alarm_time = parse(alarm_time_str)
                    except Exception as e:
                        self.stderr.write(f"Failed to parse alarm time '{alarm_time_str}': {e}")
                        alarm_time = timezone.now()

                    channel_alarms = alarm.get("channel_alarm", [])

                    for channel_alarm in channel_alarms:
                        channel = channel_name
                        int_alarm = channel_alarm.get("int_alarm", {})
                        
                        if int_alarm.get("int_subtype") == "cc":
                            try:
                                cc_alarm_num = channel_alarm.get("cc_alarm_num", {})
                                cc_in_count = cc_alarm_num.get("cc_in_num", 0)
                                cc_out_count = cc_alarm_num.get("cc_out_num", 0)
                                cc_total_count = cc_alarm_num.get("cc_total_num", 0)
                                
                                alarm_snapshot = bool(int_alarm.get("take_alarm_snap", 0))
                                alarm_status = bool(int_alarm.get("alarm_val", False))
                                alarm_subtype = int_alarm.get("int_subtype", "cc")
                                
                                record_flag = channel_alarm.get("record_flag", {})
                                record_flag_str = record_flag.get("s", "") if isinstance(record_flag, dict) else str(record_flag)
                                now = timezone.now()
                                CrossCountingData.objects.create(
                                    device_name=device_name,
                                    device_ip=device_ip,
                                    device_mac=device_mac,
                                    device_phy=device_phy,
                                    channel=channel,  # Now uses ChannelName from dev_net_info
                                    channel_alias=channel_alarm.get("chn_alias", ""),
                                    cc_in_count=cc_in_count,
                                    cc_out_count=cc_out_count,
                                    cc_total_count=cc_total_count,
                                    alarm_snapshot=alarm_snapshot,
                                    alarm_subtype=alarm_subtype,
                                    alarm_status=alarm_status,
                                    record_flag=record_flag_str,
                                    subscribe_id=subscribe_id,
                                    data_pos=data_pos,
                                    alarm_time=alarm_time,
                                    time=now,  # Let save method set this to created_at for timezone consistency
                                    created_at=now,
                                    camera=camera
                                )
                                self.stdout.write(f"Saved Cross Counting data for device: {device_name}, channel: {channel} (ChannelName: {channel_name}), counts: in={cc_in_count}, out={cc_out_count}, total={cc_total_count}")
                            except Exception as e:
                                self.stderr.write(f"Failed to process or save alarm for channel: {channel} (ChannelName: {channel_name}), Error: {e}")

            except json.JSONDecodeError as e:
                self.stderr.write(f"Failed to decode message payload: {e}")
            except Exception as e:
                self.stderr.write(f"Error processing message: {e}")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT)
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write("Shutting down MQTT listener.")
        except Exception as e:
            self.stderr.write(f"Error: {e}")
