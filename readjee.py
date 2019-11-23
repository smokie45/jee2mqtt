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
import sys

JeeLinkPort     = '/dev/ttyUSB0'
JeeLinkBaudrate = 57600
Sensors = { 61 : "/OG/Kueche", 57 : "/OG/Linus", 50: "/OG/Bad", 45 : "/OG/Jonas", 8 : "/Draussen" }
MQTT_SERVER = "192.168.0.90"
MQTT_PORT   = 1883

logging.basicConfig(
    format='%(levelname)7s: %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger( __name__ )
log.setLevel( logging.INFO)

class Sensor:
    def __init__( self, id, type, temp, hum, newBat, weakBat, mqtt):
        self.id   = id
        self.name = Sensors.get( self.id )
        if not self.name:
            self.name = str(self.id)
        self.type = type
        self.temp = temp
        if hum == 106:
            # no humidity supported if "106%"
            self.hum = None
        else:
            self.hum  = hum
        self.newBat = newBat
        self.weakBat= weakBat
        self.mqtt = mqtt

    def __str__( self ):
        dbg  = 'ID='+str( self.id )
        dbg += " ("+str( self.name )+")"
        dbg += ", type="+str( self.type )
        dbg += ", T="+str( self.temp )
        dbg += ", H="+str( self.hum )
        return dbg

    def mqttPub( self ):
        try:
            # print("->mqtt")
            self.mqtt.publish( self.name+'/temp', str(self.temp))
            # pub.single( self.name+'/temp', str(self.temp), hostname=MqttServer)
            if self.hum:
                self.mqtt.publish( self.name+'/hum', str(self.hum))
            # print("<-- mqtt")
        except:
            log.error( "Error, failed to upload to mosquitto")
            # log.exception("Error, failed to upload to mosquitto")


async def main(loop):
    try:
        #reader, _ = await serial_asyncio.open_serial_connection(url='/dev/ttyUSB0', baudrate=57600)
        reader, writer = await serial_asyncio.open_serial_connection(url=JeeLinkPort, baudrate=JeeLinkBaudrate)
    except serial.SerialException:
        # log.error( "Can not open " + JeeLinkPort )
        exit("Cannot open "+JeeLinkPort)
    # _, writer = await serial_asyncio.open_serial_connection(url='/dev/ttyUSB0', baudrate=115200)
    # time.sleep(1)
    # messages = [b'v']
    # sent = send(writer, messages)
    received = recv(reader)
    print("Start receiving from "+JeeLinkPort )
    await asyncio.wait([ received])

async def send(w, msgs):
    for msg in msgs:
        w.write(msg)
        print(f'tx: {msg.decode().rstrip()}')
        await asyncio.sleep(0.5)
    print('Done sending')


async def recv(r):
    state = 'run'
    while True:
        msg = await r.readuntil(b'\n')
        if state != 'run':
            print('Done receiving')
            break
        args = msg.split()
        if args[0] == b'OK' and args[1] == b'9':
            id   = int( args[2] )
            type = int( args[3] )
            temp = int( args[4])*256+int(args[5] )
            temp = (float(temp)-1000) /10
            hum  = int( args[6] )
            # TODO: decode bat state
            newBat = 0
            weakBat= 0
            # TODO store Sensor objects in dict to avoid recreation
            a = Sensor(id, type, temp, hum, newBat, weakBat, mqtt)
            log.info( a )
            log.debug( f'raw= {msg.rstrip().decode()}')
            a.mqttPub()
state='stop'
# create mqtt client
mqtt = mqtt.Client()
mqtt.connect( MQTT_SERVER, MQTT_PORT, 10)
# create rx/tx thread in background
mqtt.loop_start()

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main(loop))
except KeyboardInterrupt:
    state='stop'
    time.sleep(2)
    loop.stop()
    mqtt.loop_stop()
    print("Terminated")
loop.close()


# class LaCross():
#     def __init__( self, dev ):
#         self.dev = dev
#
#     def read( self ):
#         while 1:
#             line = self.dev.readline()
#             self.decode( line )
#             time.sleep(1) # sleep 5 minutes
#
#     def decode( self, data ):
#         print( data )
#
# dev = serial.Serial('/dev/ttyUSB0', 57600)
# a = LaCross( dev )
# a.read()
# dev.close()
