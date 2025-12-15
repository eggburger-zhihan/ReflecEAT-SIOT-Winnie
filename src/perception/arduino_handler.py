"""
Arduino Handler - SmartSnack Monitor
------------------------------------
Serial communication with Arduino for:
- BH1750 light sensor reading
- LED warning control
- Servo control (shake head / nod)
"""

import serial
import serial.tools.list_ports
import time
import logging

logger = logging.getLogger(__name__)


class ArduinoHandler:
    """Manages Arduino serial communication."""
    
    def __init__(self, config=None, port=None, baudrate=9600):
        """
        Initialize Arduino handler.
        
        Args:
            config: ConfigLoader instance (optional)
            port: Serial port (auto-detect if None)
            baudrate: Serial baud rate
        """
        # Load from config if provided
        if config:
            port = config.get('arduino.serial.port')
            baudrate = config.get('arduino.serial.baudrate', 9600)
        
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.is_connected = False
        
        self._connect()
    
    def _connect(self) -> bool:
        """Establish serial connection."""
        # Auto-detect port if not specified
        if self.port is None:
            self.port = self._detect_port()
        
        if self.port is None:
            logger.error("No Arduino port found")
            return False
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2
            )
            time.sleep(2)  # Wait for Arduino reset
            self.serial.reset_input_buffer()
            self.is_connected = True
            logger.info(f"Arduino connected on {self.port}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Arduino connection failed: {e}")
            return False
    
    def _detect_port(self) -> str:
        """Auto-detect Arduino port."""
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            desc = port.description.lower()
            if any(k in desc for k in ['arduino', 'ch340', 'usb serial', 'usbmodem', 'iousbhostdevice']):
                logger.info(f"Found Arduino: {port.device}")
                return port.device
        
        # Fallback: list all ports
        logger.warning("No Arduino found. Available ports:")
        for port in ports:
            logger.warning(f"  {port.device}: {port.description}")
        return None
    
    def _send(self, command: str) -> str:
        """Send command and get response."""
        if not self.is_connected:
            return None
        
        try:
            self.serial.write(f"{command}\n".encode())
            self.serial.flush()
            response = self.serial.readline().decode().strip()
            return response
        except Exception as e:
            logger.error(f"Serial error: {e}")
            return None
    
    # ==================== Sensor ====================
    
    def read_light(self) -> float:
        """Read BH1750 light sensor (lux)."""
        response = self._send("READ_LIGHT")
        
        if response:
            try:
                lux = float(response)
                logger.debug(f"Light: {lux} lux")
                return lux
            except ValueError:
                logger.error(f"Invalid light response: {response}")
        return None
    
    # ==================== Actuators ====================
    
    def led_on(self) -> bool:
        """Turn LED on."""
        response = self._send("LED_ON")
        return response == "OK"
    
    def led_off(self) -> bool:
        """Turn LED off."""
        response = self._send("LED_OFF")
        return response == "OK"
    
    def servo_shake(self) -> bool:
        """Shake head (unhealthy warning)."""
        response = self._send("SERVO_SHAKE")
        return response == "OK"
    
    def servo_nod(self) -> bool:
        """Nod head (healthy encouragement)."""
        response = self._send("SERVO_NOD")
        return response == "OK"
    
    def servo_reset(self) -> bool:
        """Reset servos to neutral position."""
        response = self._send("SERVO_RESET")
        return response == "OK"
    
    # ==================== Combined Actions ====================
    
    def warn_unhealthy(self, led_duration=5) -> bool:
        """
        Trigger unhealthy food warning.
        LED on for duration + servo shake.
        """
        logger.info("Triggering unhealthy warning...")
        self.led_on()
        self.servo_shake()
        time.sleep(led_duration)
        self.led_off()
        self.servo_reset()
        return True
    
    def encourage_healthy(self) -> bool:
        """Trigger healthy food encouragement (nod)."""
        logger.info("Triggering healthy encouragement...")
        self.servo_nod()
        time.sleep(1)
        self.servo_reset()
        return True
    
    # ==================== Connection ====================
    
    def ping(self) -> bool:
        """Test connection."""
        response = self._send("PING")
        return response == "PONG"
    
    def close(self):
        """Close connection."""
        if self.serial:
            try:
                self.led_off()
                self.servo_reset()
                self.serial.close()
                logger.info("Arduino disconnected")
            except:
                pass
        self.is_connected = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# ==================== Test ====================

if __name__ == "__main__":
    print("\n=== Arduino Handler Test ===\n")
    
    arduino = ArduinoHandler()
    
    if not arduino.is_connected:
        print("❌ Failed to connect")
        exit(1)
    
    # Test ping
    print(f"Ping: {'✅' if arduino.ping() else '❌'}")
    
    # Test light sensor
    lux = arduino.read_light()
    print(f"Light: {lux} lux")
    
    # Test LED
    print("Testing LED (2 sec)...")
    arduino.led_on()
    time.sleep(2)
    arduino.led_off()
    
    # Test servo shake
    print("Testing servo shake...")
    arduino.servo_shake()
    time.sleep(2)
    arduino.servo_reset()
    
    # Test servo nod
    print("Testing servo nod...")
    arduino.servo_nod()
    time.sleep(2)
    arduino.servo_reset()
    
    arduino.close()
    print("Test completed!")