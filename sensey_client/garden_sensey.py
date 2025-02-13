import smbus
import asyncio
import logging
from sensey import EnvironmentSensor, SenseEvent, CSVLogger
from dataclasses import dataclass
#for moisture sensor
import signal
import sys
import time
import spidev
import RPi.GPIO as GPIO

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
class TempHumidityEvent(SenseEvent):

    temperature : float
    humidity: float 

    def reading(self):
        read = { "temperature": self.temperature, "humidity": self.humidity }

        return read 

@dataclass(frozen=True)
class SoilMoistureEvent(SenseEvent):

    soil_voltage : float
    soil_moisture : float

    def reading(self):
        read = { "soil_voltage": self.soil_voltage, "soil_moisture": self.soil_moisture }

        return read


class BH1750LightSensor( EnvironmentSensor ):
    """ Polls a BH1750 light sensor 
    """

    def __init__(self):
        self.bus = smbus.SMBus(1) 
        self.BH1750_ADDR = 0x23
        self.CMD_READ = 0x10

    @property
    def sensor_names(self):
        return ["lux"]
    
    def poll(self)->SenseEvent:
        result = None
        try:
            data = self.bus.read_i2c_block_data( self.BH1750_ADDR, self.CMD_READ)
            result = (data[1] + (256 * data[0])) / 1.2
        except Exception as ex:
            print( f"Unable to read sensor: {ex}" )
        return LightEvent( result ) 


class H2UT1DLightHumiditySensor( EnvironmentSensor ):
    """ Polls I2C light & humidity sensor """

    def __init__(self):
        self.HTU21D_ADDR = 0x40
        self.CMD_READ_TEMP = 0xE3
        self.CMD_READ_HUM = 0xE5
        self.CMD_RESET = 0xFE
        self.bus = smbus.SMBus(1)

    def reset(self):
       self.bus.write_byte( self.HTU21D_ADDR, self.CMD_RESET)

    @property
    def sensor_names(self):
        return["temperature", "humidity"]
    
    def poll(self)->SenseEvent:
        self.reset()
        msb, lsb, crc = self.bus.read_i2c_block_data(self.HTU21D_ADDR, self.CMD_READ_TEMP, 3)
        temperature = -46.85 + 175.72 * (msb * 256 + lsb) / 65536
        self.reset()
        msb, lsb, crc = self.bus.read_i2c_block_data(self.HTU21D_ADDR, self.CMD_READ_HUM, 3)
        humidity = -6 + 125 * (msb * 256 + lsb) / 65536.0
        return TempHumidityEvent( temperature, humidity )
        

class MoistureSensor( EnvironmentSensor):

    def __init__(self, channel:int = 0, dry_reading = 1023, wet_reading = 300 ):

        self.channel = channel
        self.dry_reading = dry_reading
        self.wet_reading = wet_reading

        logging.info( f"setting up new MoistureSensor for channel {self.channel}" )

        # Pin 15 corresponds to GPIO 22
        self.LED1 = 15
        # Pin 16 corresponds to GPIO 23
        self.LED2 = 16

        spi_ch = 0

        # Enable SPI
        self.spi = spidev.SpiDev(0, spi_ch)
        self.spi.max_speed_hz = 1200000


    @property
    def sensor_names(self):
        return [f"soil_voltage", f"soil_moisture"]    
    
    def light_up( self, seconds ):
        # to use board pin numbers
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        # set up GPIO output channel for lights
        GPIO.setup(self.LED1, GPIO.OUT)
        GPIO.setup(self.LED2, GPIO.OUT)
        
        # light up the LEDs
        GPIO.output( self.LED1, 1 )
        GPIO.output( self.LED2, 1 )
        #FIXME this needs to be someplace with asyncio
        time.sleep( 1 )
        GPIO.reset()

    
    def poll(self)->SenseEvent:
        
        # Construct SPI message
        #  First bit (Start): Logic high (1)
        #  Second bit (SGL/DIFF): 1 to select single mode
        #  Third bit (ODD/SIGN): Select channel (0 or 1)
        #  Fourth bit (MSFB): 0 for LSB first
        #  Next 12 bits: 0 (don't care)
        msg = 0b11
        msg = ((msg << 1) + self.channel) << 5
        msg = [msg, 0b00000000]
        reply = self.spi.xfer2(msg)

        # Construct single integer out of the reply (2 bytes)
        adc = 0
        for n in reply:
            adc = (adc << 8) + n

        # Last bit (0) is not part of ADC value, shift to remove it
        adc = adc >> 1
        logging.info( f"Current adc reading is {adc}" )
        
        # calculate moisture % from adc
        percentage = 100 * ((adc - self.dry_reading) / (self.wet_reading - self.dry_reading))

        return SoilMoistureEvent( adc, percentage )
    
async def main():
    
    sensors = []
    
    # Initialize sensors
    sensors.append( BH1750LightSensor() )
    sensors.append( H2UT1DLightHumiditySensor() )
    sensors.append( MoistureSensor(0) )

    # Initialize logger
    logger = CSVLogger(sensors)

    # Start logging
    await logger.log_data()


# Run the program
if __name__ == "__main__":
    asyncio.run(main())
