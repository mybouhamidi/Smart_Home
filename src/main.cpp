#include <Arduino.h>
#include <WiFi.h>
#include <FirebaseESP32.h>
#include <time.h>
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>
#include "secrets.h"

String device_location = "Living Room";
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;
String databasePath = "";
String fuid = "";
unsigned long elapsedMillis = 0;
unsigned long update_interval = 10000;
bool isAuthenticated = false;

char timeStringBuff[20];

float hall = 0;
float touch = 0;
float touch_1 = 0;

const char *ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 3600;
const int daylightOffset_sec = 3600;

FirebaseJson hall_json;
FirebaseJson touch_json;
FirebaseJson touch_1_json;

void getLocalTime()
{
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo))
  {
    return;
  }

  strftime(timeStringBuff, sizeof(timeStringBuff), "%F %H:%M:%S", &timeinfo);
}

void Wifi_Init()
{
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(300);
  }
}

void firebase_init()
{                                     // configure firebase API Key
  config.api_key = API_KEY;           // configure firebase realtime database url
  config.database_url = DATABASE_URL; // Enable WiFi reconnection
  Firebase.reconnectWiFi(true);

  if (Firebase.signUp(&config, &auth, "", ""))
  {
    isAuthenticated = true; // Set the database path where updates will be loaded for this device
    databasePath = "/" + device_location;
    fuid = auth.token.uid.c_str();
  }
  else
  {
    isAuthenticated = false;
  }
  config.token_status_callback = tokenStatusCallback; // Initialise the firebase library
  Firebase.begin(&config, &auth);
}

void updateSensorReadings()
{
  hall = hallRead();
  touch = analogRead(32);
  touch_1 = analogRead(36);
  if (isnan(hall) || isnan(touch) || isnan(touch_1))
  {
    return;
  }
  hall_json.set("value", hall);
  touch_json.set("value", touch);
  touch_1_json.set("value", touch_1);
  getLocalTime();
  hall_json.set("time", timeStringBuff);
  touch_json.set("time", timeStringBuff);
  touch_1_json.set("time", timeStringBuff);
}

void setup()
{
  // put your setup code here, to run once:
  Serial.begin(115200);

  Wifi_Init();
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  getLocalTime();
  hall_json.add("name", "Hall sensor");
  hall_json.add("type", "Hall");
  hall_json.add("location", device_location);
  hall_json.add("value", hall); // Print out initial temperature values
  hall_json.add("time", timeStringBuff);
  String jsonStr;
  hall_json.toString(jsonStr, true);
  touch_json.add("name", "Touch sensor");
  touch_json.add("type", "Touch");
  touch_json.add("location", device_location);
  touch_json.add("value", touch); // Print out initial humidity values
  touch_json.add("time", timeStringBuff);
  String jsonStr2;
  touch_json.toString(jsonStr2, true);

  touch_1_json.add("name", "Touch sensor");
  touch_1_json.add("type", "Touch");
  touch_1_json.add("location", device_location);
  touch_1_json.add("value", touch_1); // Print out initial humidity values
  touch_1_json.add("time", timeStringBuff);
  String jsonStr1;
  touch_1_json.toString(jsonStr1, true);

  firebase_init();
}

void uploadSensorData()
{
  if (millis() - elapsedMillis > update_interval && isAuthenticated && Firebase.ready())
  {
    elapsedMillis = millis();
    updateSensorReadings();
    String hall_node = databasePath + "/Hall";
    String touch_node = databasePath + "/Touch";
    String touch_1_node = databasePath + "/Touch-1";
    if (Firebase.setJSON(fbdo, hall_node.c_str(), hall_json))
    {
      printResult(fbdo); //see addons/RTDBHelper.h
    }
    else
    {
      Serial.println("FAILED");
      Serial.println("REASON: " + fbdo.errorReason());
      Serial.println("------------------------------------");
      Serial.println();
    }
    if (Firebase.setJSON(fbdo, touch_node.c_str(), touch_json))
    {
      printResult(fbdo); //see addons/RTDBHelper.h
    }
    else
    {
      Serial.println("FAILED");
      Serial.println("REASON: " + fbdo.errorReason());
      Serial.println("------------------------------------");
      Serial.println();
    }
    if (Firebase.setJSON(fbdo, touch_1_node.c_str(), touch_1_json))
    {
      printResult(fbdo); //see addons/RTDBHelper.h
    }
    else
    {
      Serial.println("FAILED");
      Serial.println("REASON: " + fbdo.errorReason());
      Serial.println("------------------------------------");
      Serial.println();
    }
  }
}
void loop()
{
  uploadSensorData();
}