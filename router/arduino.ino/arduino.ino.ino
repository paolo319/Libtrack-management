
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define SS_PIN 10
#define RST_PIN 9

// LCD address: 0x27, 16 columns, 2 rows
LiquidCrystal_I2C lcd(0x27, 16, 2);

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {

    Serial.begin(9600);

    // Initialize LCD
    lcd.init();
    lcd.backlight();

    lcd.setCursor(0, 0);
    lcd.print("LIBTRACK SYSTEM");

    lcd.setCursor(0, 1);
    lcd.print("Initializing...");

    // Initialize RFID
    SPI.begin();
    rfid.PCD_Init();

    delay(1500);

    showWaitingScreen();

    Serial.println("RFID SCANNER READY");
    Serial.println("TAP YOUR ID CARD");
}

void loop() {

    // Check for RFID card
    if (!rfid.PICC_IsNewCardPresent()) {
        return;
    }

    if (!rfid.PICC_ReadCardSerial()) {
        return;
    }

    // Display card detected
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("CARD DETECTED!");

    lcd.setCursor(0, 1);
    lcd.print("Reading ID...");

    // Read RFID UID
    String cardUID = "";

    for (byte i = 0; i < rfid.uid.size; i++) {

        if (rfid.uid.uidByte[i] < 0x10) {
            cardUID += "0";
        }

        if (i > 0) {
            // No separator between UID bytes
        }

        String hexValue = String(rfid.uid.uidByte[i], HEX);
        hexValue.toUpperCase();

        cardUID += hexValue;
    }

    // Display UID in Serial Monitor
    Serial.print("ID NUMBER: ");
    Serial.println(cardUID);

    // Display UID on LCD
    lcd.clear();

    lcd.setCursor(0, 0);
    lcd.print("ID NUMBER:");

    lcd.setCursor(0, 1);
    lcd.print(cardUID.substring(0, 16));

    // Stop RFID communication
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    // Wait 1.5 seconds
    delay(1500);

    // Return to waiting screen
    showWaitingScreen();
}

void showWaitingScreen() {

    lcd.clear();

    lcd.setCursor(0, 0);
    lcd.print("LIBTRACK SYSTEM");

    lcd.setCursor(0, 1);
    lcd.print("Tap Your ID Card");
}
