#!/usr/bin/env python3

from prometheus_client import start_http_server, Gauge
from btlewrap.bluepy import BluepyBackend
from mitemp_bt.mitemp_bt_poller import MiTempBtPoller, MI_TEMPERATURE, MI_HUMIDITY, MI_BATTERY
from types import SimpleNamespace

import yaml
import time
import datetime
import sys
import os
import signal
import sched

def log(msg):
    print("[%s] : %s" % (str(datetime.datetime.now()), msg))

def get_config():

    env = os.environ
    c = {}

    c['port'] = int(env.get("PORT", 19667))
    c['metric_prefix'] = env.get("METRIC_PREFIX", "mijia")
    c['refresh_interval'] = int(env.get("REFRESH_INTERVAL", 60))
    c['macs'] = env.get("MIJIA_MACS_LIST", None).split(',')
    c['names'] = env.get("MIJIA_NAMES_LIST", None).split(',')

    return SimpleNamespace(**c)


def killer(_signo, _stack_frame):
    log("Stopping on signal %s" % _signo)
    sys.exit(0)


def main():

    signal.signal(signal.SIGINT, killer)
    signal.signal(signal.SIGTERM, killer)
    
    conf = get_config()

    m = {
        "last_refresh": Gauge( conf.metric_prefix + "_last_refresh_timestamp", "", ['name']),
        "temperature": Gauge( conf.metric_prefix + "_temperature_celsius", "", ['name']),
        "humidity": Gauge( conf.metric_prefix + "_humidity_percentage", "", ['name']),
        "battery": Gauge( conf.metric_prefix + "_battery_percentage", "", ['name'])
        }

    metrics = SimpleNamespace(**m)

    start_http_server(conf.port)

    pollers= []
    for m in conf.macs:
        pollers.append( MiTempBtPoller(m, BluepyBackend, conf.refresh_interval ) )

    while(1):
      
        i=0
        
        while(i<len(conf.macs)):
            
            try:
                pollers[i].fill_cache()
            except Exception as e:
                log("Error refreshing sensor: %s : %s" % (conf.names[i], e))
            else:
                log("Sensor %s refreshed" % (conf.names[i]))
                metrics.last_refresh.labels(conf.names[i]).set( time.time() )
                metrics.temperature.labels(conf.names[i]).set( pollers[i].parameter_value(MI_TEMPERATURE) )
                metrics.humidity.labels(conf.names[i]).set( pollers[i].parameter_value(MI_HUMIDITY) )
                metrics.battery.labels(conf.names[i]).set( pollers[i].parameter_value(MI_BATTERY) )
            finally:
                i=i+1
                time.sleep(conf.refresh_interval / len(conf.macs))
        


if __name__ == '__main__':
    main()
