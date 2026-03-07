#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include "RTClib.h" 

#define SS_PIN    10
#define RST_PIN   9
#define LED_PIN   7
#define BUZZ_PIN  6
MFRC522 mfrc522(SS_PIN, RST_PIN);
RTC_DS3231 rtc;

int readsuccess;
byte readcard[4];
char str[32] = "";
String StrUID;

// --- NEW VARIABLE ---
int lateCount = 0; 
// --------------------

void setup() {
  Serial.begin(9600);
  Wire.begin();        
  SPI.begin();         
  mfrc522.PCD_Init();
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZ_PIN, OUTPUT);

  if (!rtc.begin()) {
    Serial.println("MSG, RTC Module Not Found!");
  }

  // Set the headers for PLX-DAQ Excel
  Serial.println("CLEARDATA");
  // Added "Late Total" as the 5th column (Column E)
  Serial.println("LABEL,Date,Time,RFID UID,Status,Late Total"); 
  delay(1000);
}

void loop() {
  readsuccess = getid();

  if(readsuccess){
    DateTime now = rtc.now();
    String status = "";

    // Check if current time is 7:31 AM or later
    if (now.hour() > 7 || (now.hour() == 7 && now.minute() >= 31)) {
      status = "Late";
      lateCount++; // Increment the counter when someone is late
    } else {
      status = "On Time";
    }

    // Send data to Excel columns A, B, C, D, and E
    Serial.print("DATA,DATE,TIME,");
    Serial.print(StrUID);
    Serial.print(",");
    Serial.print(status);
    Serial.print(",");
    Serial.println(lateCount); // Send the running total to Column E

    if (status == "On Time") {
      // One short blink + high beep
      digitalWrite(LED_PIN, HIGH);
      tone(BUZZ_PIN, 1000, 200);
      delay(200);
      digitalWrite(LED_PIN, LOW);
    } else {
      // Two quick blinks + low beep
      for (int i = 0; i < 2; i++) {
        digitalWrite(LED_PIN, HIGH);
        tone(BUZZ_PIN, 400, 150);
        delay(150);
        digitalWrite(LED_PIN, LOW);
        delay(100);
      }
    }

    delay(2000); // Prevents duplicate scans
  }
}

int getid(){  
  if(!mfrc522.PICC_IsNewCardPresent()) return 0;
  if(!mfrc522.PICC_ReadCardSerial()) return 0;
  
  for(int i=0;i<4;i++){
    readcard[i]=mfrc522.uid.uidByte[i];
    array_to_string(readcard, 4, str);
    StrUID = str;
  }
  mfrc522.PICC_HaltA();
  return 1;
}

void array_to_string(byte array[], unsigned int len, char buffer[]) {
    for (unsigned int i = 0; i < len; i++) {
        byte nib1 = (array[i] >> 4) & 0x0F;
        byte nib2 = (array[i] >> 0) & 0x0F;
        buffer[i*2+0] = nib1  < 0xA ? '0' + nib1  : 'A' + nib1  - 0xA;
        buffer[i*2+1] = nib2  < 0xA ? '0' + nib2  : 'A' + nib2  - 0xA;
    }
    buffer[len*2] = '\0';
}