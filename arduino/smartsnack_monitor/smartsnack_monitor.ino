/*
 * SmartSnack Monitor - Arduino Firmware
 * ======================================
 * Handles serial commands from Python:
 * - BH1750 light sensor reading
 * - LED warning control
 * - Servo control (shake/nod)
 * 
 * Serial Commands:
 *   PING        -> PONG
 *   READ_LIGHT  -> [lux value]
 *   LED_ON      -> OK
 *   LED_OFF     -> OK
 *   SERVO_SHAKE -> OK
 *   SERVO_NOD   -> OK
 *   SERVO_RESET -> OK
 */

#include <Wire.h>
#include <Servo.h>

// ==================== PIN CONFIGURATION ====================
const int LED_PIN = 12;         // Warning LED (D12)
const int SERVO1_PIN = 6;       // Servo 1 - Horizontal shake (D6)
const int SERVO2_PIN = 4;       // Servo 2 - Vertical nod (D4)

// ==================== BH1750 CONFIGURATION ====================
const int BH1750_ADDRESS = 0x23;  // Default I2C address (ADDR pin LOW)
// If ADDR pin is HIGH, use 0x5C

// ==================== SERVO CONFIGURATION ====================
Servo servo1;  // Horizontal (shake left-right)
Servo servo2;  // Vertical (nod up-down)

const int SERVO_CENTER1 = 100;   // Neutral position
const int SERVO_CENTER2 = 70;   // Neutral position
const int SHAKE_LEFT = 80;     // Shake left
const int SHAKE_RIGHT = 120;   // Shake right
const int NOD_UP = 70;         // Nod up
const int NOD_DOWN = 110;      // Nod down

// ==================== SETUP ====================
void setup() {
    Serial.begin(9600);
    Wire.begin();
    
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    // Initialize Servo
    servo1.attach(SERVO1_PIN);
    servo2.attach(SERVO2_PIN);
    servo1.write(SERVO_CENTER1);
    servo2.write(SERVO_CENTER2);
    
    // Initialize BH1750 (continuous high-res mode)
    Wire.beginTransmission(BH1750_ADDRESS);
    Wire.write(0x10);  // Continuous H-Resolution Mode
    Wire.endTransmission();
    
    delay(200);  // Wait for first measurement
    
    Serial.println("SmartSnack Arduino Ready");
}

// ==================== MAIN LOOP ====================
void loop() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command == "PING") {
            Serial.println("PONG");
        }
        else if (command == "READ_LIGHT") {
            float lux = readBH1750();
            Serial.println(lux, 2);
        }
        else if (command == "LED_ON") {
            digitalWrite(LED_PIN, HIGH);
            Serial.println("OK");
        }
        else if (command == "LED_OFF") {
            digitalWrite(LED_PIN, LOW);
            Serial.println("OK");
        }
        else if (command == "SERVO_SHAKE") {
            servoShake();
            Serial.println("OK");
        }
        else if (command == "SERVO_NOD") {
            servoNod();
            Serial.println("OK");
        }
        else if (command == "SERVO_RESET") {
            servo1.write(SERVO_CENTER1);
            servo2.write(SERVO_CENTER2);
            Serial.println("OK");
        }
        else {
            Serial.println("ERROR: Unknown command");
        }
    }
}

// ==================== BH1750 LIGHT SENSOR ====================
float readBH1750() {
    Wire.requestFrom(BH1750_ADDRESS, 2);
    
    if (Wire.available() == 2) {
        uint16_t raw = Wire.read() << 8;
        raw |= Wire.read();
        
        // Convert to lux (divide by 1.2 for accuracy)
        float lux = raw / 1.2;
        return lux;
    }
    
    return -1.0;  // Error
}

// ==================== SERVO ACTIONS ====================
void servoShake() {
    // Shake head left-right using Servo1 (disapproval)
    for (int i = 0; i < 3; i++) {
        servo1.write(SHAKE_LEFT);
        delay(400);
        servo1.write(SHAKE_RIGHT);
        delay(400);
    }
    servo1.write(SERVO_CENTER1);
}

void servoNod() {
    // Nod up-down using Servo2 (approval)
    for (int i = 0; i < 2; i++) {
        servo2.write(NOD_UP);
        delay(400);
        servo2.write(NOD_DOWN);
        delay(400);
    }
    servo2.write(SERVO_CENTER2);
}
