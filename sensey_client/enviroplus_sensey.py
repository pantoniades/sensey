from smbus2 import SMBus
import asyncio
import logging
from sensey import EnvironmentSensor, SenseEvent, CSVLogger
from dataclasses import dataclass
#for moisture sensor
import signal
import sys
import time
from bme280 import BME280
from enviroplus import gas
#import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("sensey.log"), logging.StreamHandler()],
)

@dataclass(frozen=True) 
class LightEvent(SenseEvent):

    lux : float

    def reading(self):
        return { "lux" : self.lux }
    
@dataclass(frozen=True)
class TempHumidityPressureEvent(SenseEvent):

    temperature : float
    humidity: float 
    pressure: float

    def reading(self):
        read = { "temperature": self.temperature, "humidity": self.humidity, "pressure": self.pressure }

        return read 

@dataclass(frozen=True)
class AirQualityEvent(SenseEvent):

    oxidising : float
    reducing: float 
    nh3: float

    def reading(self):
        read = { "oxidising": self.oxidising, "reducing": self.reducing, "nh3": self.nh3 }

        return read

class BME280Sensor( EnvironmentSensor ):
    """ Polls a BME280 temperature & humidity sensor 
    """

    def __init__(self):
        self.bus = SMBus(1) 
        self.bm3280 = BME280(i2c_dev=self.bus)

    @property
    def sensor_names(self):
        return ["temperature", "humidity", "pressure"]
    
    def poll(self)->SenseEvent:
        temp = self.bm3280.get_temperature()
        humidity = self.bm3280.get_humidity()
        pres = self.bm3280.get_pressure()
        return TempHumidityPressureEvent( temp, humidity, pres )
    
class MICS6814GasSensor( EnvironmentSensor ):
    """ Polls the MICS6814 Analog gas sensor 
    """


    @property
    def sensor_names(self):
        return ["oxidising", "reducing", "nh3"]
    
    def poll(self)->SenseEvent:
        oxidising = gas.read_oxidising()
        reducing = gas.read_reducing()
        nh3 = gas.read_nh3()
        return AirQualityEvent( oxidising, reducing, nh3 )
    

async def main():
    
    sensors = []
    
    # Initialize sensors
    sensors.append( BME280Sensor() )
    sensors.append( MICS6814GasSensor() )

    # Initialize logger
    logger = CSVLogger(sensors)

    # Start logging
    await logger.log_data()


# Run the program
if __name__ == "__main__":
    asyncio.run(main())
