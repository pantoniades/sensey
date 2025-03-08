import logging
import asyncio
from sensey import EnvironmentSensor, SenseEvent, CSVLogger
from dataclasses import dataclass
from sense_hat import SenseHat 

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
    
class SenseHatReader( EnvironmentSensor):
    def __init__(self, sense_hat:SenseHat):
        super().__init__()
        self.sense_hat = sense_hat
        
    @property
    def sensor_names(self):
        return ["temperature", "humidity"]
        
    def poll(self):
        return TempHumidityEvent( self.sense_hat.get_temperature(), self.sense_hat.get_humidity() )
    
class SenseHatLightReader( EnvironmentSensor ):
    def __init__(self, sense_hat:SenseHat ):
        super().__init__()
        self.sense_hat = sense_hat

    @property
    def sensor_names(self):
        return["brightness"]
    
    def poll(self):
        return LightEvent( self.sense_hat.color.clear_raw )
        

async def main():
    
    sensors = []
    sense_hat = SenseHat()
    
    # Initialize sensors
    sensors.append( SenseHatReader( sense_hat ) )
    sensors.append( SenseHatLightReader( sense_hat ) )

    # Initialize logger
    logger = CSVLogger(sensors)

    # Start logging
    await logger.log_data()


# Run the program
if __name__ == "__main__":
    asyncio.run(main())