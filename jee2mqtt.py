#!/bin/python
#
# Small program to read data received by JeeLink on 868MHz. JeeLink sends ASCII data.
#
import asyncio
import serial_asyncio
# python-pyserial
# python-setuptools
# python-pyserial-asyncio
import serial, time
#m import paho.mqtt.publish as pub
import paho.mqtt.client as mqtt
import logging
from logging.handlers import RotatingFileHandler
import sys
import argparse

PORT          = '/dev/ttyUSB1'
BAUDRATE      = 57600
MQTT_SERVER   = "192.168.0.90"
MQTT_PORT     = 1883
MQTT_ONCHANGE = False

Sensors = { 61 : "/OG/Kueche", 57 : "/OG/Linus", 50: "/OG/Bad", 22 : "/OG/Jonas", 27 : "/Draussen" }

# Unique is a metaclass which will only create a new instance of a class,
# if there was no other instance of this class created with same first
# argument to ctor. This is something like a singleton for classes with same
# first argument in ctor
class Unique( type ):
    def __call__( cls, *args, **kwargs):
        # This is called if class is instaciated ( a = Class())
        # check if cache contains already an instance
        if args[0] not in cls._cache:
            # new instance, init and add to cache
            self = cls.__new__(cls, *args, **kwargs)
            cls.__init__(self, *args, **kwargs)
            cls._cache[ args[0] ] = self
        return cls._cache[args[0]]

    def __init__(cls, name, bases, attributes):
        # This is called at startup to init metaclass
        super().__init__(name, bases, attributes)
        cls._cache = {}

from dataclasses import dataclass
@dataclass
class Updatable:
    value = 0
    isUpdated = True
    def set( self, new ):
        if self.value != new:
            self.value = new
            self.isUpdated = True

    def get( self):
        return self.value

    def reset(self):
        if MQTT_ONCHANGE == True:
            self.isUpdated = False

    def __str__(self):
        return str(self.value)

class Sensor(metaclass=Unique):
    # The Unique metaclass will ensure instances with different
    # "type" in ctor will be created at first time. At second call, no new
    # instance is created, but old one returned.
    id=0

    def __init__( self, id, mqttC ):
        self.id   = id
        self.name = Sensors.get( self.id )
        if not self.name:
            self.name = str(self.id)
        self.mqttC = mqttC
        self.temp = Updatable()
        self.hum  = Updatable()
        self.type = Updatable()

    def update( self, type, temp, hum, newBat, weakBat ):
        self.type.set( type )
        self.temp.set( temp )
        if hum == 106:
            self.hum.set( None )
        else:
            self.hum.set( hum )
        self.newBat  = newBat
        self.weakBat = weakBat
        self.mqttPub()

    def mqttPub( self ):
        # TODO: add recognition of server restart to update all values again-> retain=True
        try:
            # print("->mqtt")
            if self.temp.isUpdated:
                self.temp.reset()
                self.mqttC.publish( self.name+'/temp', str(self.temp), retain=True)
                log.debug( "mqttPub: temp" )
                # pub.single( self.name+'/temp', str(self.temp), hostname=MqttServer)
            if self.hum.isUpdated:
                self.hum.reset()
                self.mqttC.publish( self.name+'/hum', str(self.hum), retain=True)
                log.debug( "mqttPub: hum" )
            # print("<-- mqtt")
        except:
        #except Exception as e:
        #    print( e)
            log.error( "Error, failed to upload to mosquitto")
            # log.exception("Error, failed to upload to mosquitto")

    def __str__( self ):
        dbg  = 'ID='+str( self.id )
        dbg += " ("+str( self.name )+")"
        dbg += ", type="+str( self.type )
        dbg += ", T="+str( self.temp )
        dbg += ", H="+str( self.hum )
        return dbg

def decode( msg ):
        args = msg.split()
        if len(args) == 0:
            log.debug( "rx unknown message. Ignoring! '" + str(msg)+"'" )
            return
        if args[0].startswith( b'[LaCrosseITPlusReader'):
            log.debug("rx::versionreply:" +str(args) )
            return
        if args[0] != b'OK' or args[1] != b'9':
            log.debug( "rx unknown message. Ignoring! '" + str(msg)+"'" )
            return
        # we're sure it's an LaCross message. Decode it..
        id   = int( args[2] )
        type = int( args[3] )
        temp = int( args[4])*256+int(args[5] )
        temp = (float(temp)-1000) /10

        hum  = int( args[6] )
        # TODO: decode bat state
        newBat = 0
        weakBat= 0
        a = Sensor( id, mqttC)
        a.update( type, temp, hum, newBat, weakBat)
        # print( a )
        log.info( a )

async def main(loop):
    try:
        reader, writer = await serial_asyncio.open_serial_connection(url=PORT, baudrate=BAUDRATE)
    except serial.SerialException:
        log.error( "Can not open " + PORT )
        exit("Cannot open " + PORT)
    # time.sleep(1)
    received = recv(reader)
    #messages = [ b'1r', b'0t', b'0a', b'v' ]
    messages = [ b'1r0t0a', b'v' ]
    sent = send(writer, messages)
    log.debug("Start receiving ..." )
    await asyncio.wait([ sent, received])

async def send(w, msgs):
    for msg in msgs:
        w.write(msg)
        log.debug(f'tx: {msg.decode().rstrip()}')
        await asyncio.sleep(0.5)
    log.debug('Done sending')


async def recv(r):
    state = 'run'
    while True:
        msg = await r.readuntil(b'\n')
        if state != 'run':
            # state != run given from outside ... lets die
            log.debug('State switch to != run. Terminate')
            break
        # log.debug( f'raw= {msg.rstrip().decode()}')
        log.debug( 'rx::raw: ' +str(msg) )
        decode( msg )

def on_mqtt( client, userdata, msg ):
    log.debug("on_mqtt: '"+msg.topic+"' -> '" + str(msg.payload) +"'")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("connected to mqtt server")
        client.isConnected = True
    else:
        log.error("on_connect: failed to connect to mqtt server")

def on_subscribe( client, userdata, mid, granted_qos):
    log.debug("on_subscribe:")

def on_log( client, userdata, level, buf):
    if "PING" not in buf:
        log.debug("on_log: " + buf)

#def onMqttConnect( client, userdata, flags, rc):
#    log.info( "Connected to mqtt server")


my_parser = argparse.ArgumentParser(description='Read jeelink data from ttyUSB and publish to MQTT server')

my_parser.add_argument('--port',
                       required=False,
                       type=str,
                       default="/dev/ttyUSB1",
                       help='Path to serial port device')
my_parser.add_argument('--log',
                       required=False,
                       type=str,
                       default="ERROR",
                       help='Set loglevel to [DEBUG, INFO, ..]')
args = my_parser.parse_args()
PORT = args.port

# get name of program. Remove prefixed path and postfixed fileytpe
myName = sys.argv[0]
myName = myName[ myName.rfind('/')+1: ]
myName = myName[ : myName.find('.')]
print("Started " + myName + " using " + PORT)

logging.basicConfig(
    format='%(levelname)7s: %(message)s',
    # level=logging.INFO,
    level = getattr(logging, args.log.upper()),
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.handlers.RotatingFileHandler('/tmp/'+myName+'.log',
                                             # maxBytes=2000,
                                             # backupCount=1)
    ]
)
log = logging.getLogger( __name__ )

state='stop'

# create mqtt client
mqttC = mqtt.Client(client_id="jee2mqtt")
mqttC.isConnected = False
mqttC.on_connect = on_connect
mqttC.on_message = on_mqtt
mqttC.on_subscribe = on_subscribe
mqttC.on_log = on_log
mqttC.loop_start()        # create rx/tx thread in background
try:
    mqttC.connect( MQTT_SERVER, MQTT_PORT, 10)
except:
    log.error("Failed to connect to mqtt server. Retry in 2 secs ....")
while not mqttC.isConnected:
    time.sleep(1)           # wait till mqtt server arrives.

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete( main( loop) )
except KeyboardInterrupt:
    state='stop'
    time.sleep(2)
    loop.stop()
    mqttC.loop_stop()
    print("Terminated")
loop.close()

