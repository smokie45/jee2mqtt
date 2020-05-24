# jee2mqtt

This small python tool can read data from [Jeelink RF sticks](https://www.digitalsmarties.net/products/jeelink) 
, decode and forward it to Mosquitto MQTT. The Jeelink must run the [FHEM LaCross Sketch](https://svn.fhem.de/trac/browser/trunk/fhem/contrib/arduino/).

I have created this tool when I switched from FHEM to Homeassistant and wouldn't loose my cheap [LaCross](https://www.lacrossetechnology.com/tx29u-it)/[Technoline](https://www.conrad.de/de/p/techno-line-tx-35-it-thermosensor-funk-868-672929.html) temperature sensors.

```
me@home:~> ./jee2mqtt.py --log=INFO --port=/dev/ttyUSB0
Started jee2mqtt using /dev/ttyUSB1
   INFO: connected to mqtt server
   INFO: ID=61 (/OG/Kueche), type=1, T=22.4, H=50
   INFO: ID=57 (/OG/Linus), type=1, T=19.6, H=None
   INFO: ID=27 (/Draussen), type=1, T=13.7, H=None
   INFO: ID=2 (2), type=1, T=20.5, H=54
   INFO: ID=61 (/OG/Kueche), type=1, T=22.4, H=50
   INFO: ID=57 (/OG/Linus), type=1, T=19.6, H=None
...
```
