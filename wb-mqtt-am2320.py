#!/usr/bin/env python

import sys
import mosquitto
import json
import time

import am2320


class MQTTClient(mosquitto.Mosquitto):
    def publish_utf8(self, topic, payload, *args, **kwargs):
        if isinstance(topic, unicode):
            topic = topic.encode('utf8', 'ignore')
        if isinstance(payload, unicode):
            payload = payload.encode('utf8', 'ignore')

        self.publish(topic, payload, *args, **kwargs)


class TMQTTAM232xSensor(object):
    def init_config(self, fname):
        self.config = json.load(open(fname))

        self.config.setdefault('mqtt_id', 'am2320')
        self.config.setdefault('name', 'AM232x sensor')
        self.config.setdefault('debug', False)
        self.config.setdefault('i2c_bus', 0)
        self.config.setdefault('poll_interval', 10)
        if self.config['poll_interval'] < 2:
            raise RuntimeError("poll interval cannot be smaller than 2 seconds")

    def init_sensor(self):
        self.am2320 = am2320.AM2320(self.config['i2c_bus'])

    def init_mqtt(self):
        self.mqtt_client = MQTTClient()
        self.mqtt_client.connect('localhost')
        self.mqtt_client.loop_start()

        self.mqtt_client.publish_utf8("/devices/%s/meta/name" % self.config['mqtt_id'], self.config['name'], qos=1, retain=True)

        self.mqtt_client.publish_utf8("/devices/%s/controls/%s/meta/type" %
                                      (self.config['mqtt_id'], "temperature"), "temperature", qos=1, retain=True)

        self.mqtt_client.publish_utf8("/devices/%s/controls/%s/meta/type" %
                                      (self.config['mqtt_id'], "humidity"), "rel_humidity", qos=1, retain=True)

    def set_channel_error(self, control_id, error):
        if self.error_cache.get(control_id) != error:
            self.mqtt_client.publish("/devices/%s/controls/%s/meta/error" %
                                     (self.config['mqtt_id'], control_id), error, qos=1, retain=1)
        self.error_cache[control_id] = error

    def publish_channel(self, control_id, value, decimal_places=1):
        self.set_channel_error(control_id, "")
        format = "%%.%df" % decimal_places
        value_str = format % value
        self.mqtt_client.publish_utf8("/devices/%s/controls/%s" %
                                      (self.config['mqtt_id'], control_id), value_str, qos=1, retain=True)

    def __init__(self, fname):
        self.fname = fname
        self.error_cache = {}

    def start(self):
        self.init_config(self.fname)
        self.init_sensor()
        self.init_mqtt()

        while True:
            try:
                self.am2320.read()
            except am2320.CommunicationError:
                self.set_channel_error('temperature', "r")
                self.set_channel_error('humidity', "r")
            else:
                self.publish_channel('temperature', self.am2320.temperature)
                self.publish_channel('humidity', self.am2320.humidity)

            time.sleep(self.config['poll_interval'])

        return 0


def main():
    if len(sys.argv) != 2:
        print >>sys.stderr, "USAGE: %s <config file>"
        return 1

    sensor = TMQTTAM232xSensor(sys.argv[1])
    sensor.start()

    return 0


if __name__ == '__main__':
    main()
