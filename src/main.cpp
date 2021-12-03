#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <time.h>
#include <ArduinoJson.h>
#include <Redis.h>
#include "secrets.h"
#include "DHT.h"

#define DHTPIN 4
#define CO2 32
#define DHTTYPE DHT22

WiFiClient redisConn;
Redis *gRedis = nullptr;

unsigned long elapsedMillis = 0;
unsigned long update_interval = 1000;

float temperature = 0;
float humidity = 0;
float co2 = 0;
DHT dht(DHTPIN, DHTTYPE);

StaticJsonDocument<2048> doc;

const char *ntpServer = "pool.ntp.org";

unsigned long getTime()
{
    time_t now;
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo))
    {
        return (0);
    }
    time(&now);
    return now;
}

void Wifi_Init()
{
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(300);
    }
}

void updateSensorReadings()
{
    if (isnan(dht.readHumidity()) || isnan(dht.readTemperature()) || isnan(analogRead(CO2)))
    {
        return;
    }
    else
    {
        humidity = dht.readHumidity();
        co2 = analogRead(CO2) / 4095.0;
        temperature = dht.readTemperature();
    }
}

void setup()
{
    Serial.begin(115200);
    Serial.println("Beginning heating");
    delay(120000);
    dht.begin();
    Wifi_Init();
    redisConn.connect(REDIS_ADDR, REDIS_PORT);
    gRedis = new Redis(redisConn);
    auto connRet = gRedis->authenticate(REDIS_PASSWORD);
    configTime(-18000, 0, ntpServer);
}

void uploadSensorData()
{
    if (millis() - elapsedMillis > update_interval)
    {

        updateSensorReadings();

        doc["Time"] = getTime();
        doc["Temperature"] = temperature;
        doc["Humidity"] = humidity;
        doc["CO2"] = co2;
        String key;
        key += getTime();
        char char_key[key.length() + 1];
        key.toCharArray(char_key, key.length());
        String jsonStr;
        serializeJson(doc, jsonStr);
        auto sender = gRedis->append("data", jsonStr.c_str());
        auto separator = gRedis->append("data", ";");
        Serial.println(jsonStr.c_str());
        doc.clear();
        elapsedMillis = millis();
    }
}

void loop()
{
    uploadSensorData();
}