#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"
#include "DHT.h"

#define DHTPIN 4
#define CO2 32
#define DHTTYPE DHT22

const char *serverName = "http://127.0.0.1:8050";
unsigned long elapsedMillis = 0;
unsigned long update_interval = 1000;

float temperature = 0;
float humidity = 0;
float co2 = 0;
DHT dht(DHTPIN, DHTTYPE);

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
        co2 = analogRead(CO2);
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
}

void uploadSensorData()
{
    if (millis() - elapsedMillis > update_interval)
    {
        elapsedMillis = millis();
        updateSensorReadings();
        WiFiClient client;
        HTTPClient http;

        http.begin(client, serverName);
        String httpRequestData = "{\"Temperature\":\"" + String(temperature) + "\",\"Humidity\":\"" + String(humidity) + "\",\"CO2\":\"" + String(co2) + "\"}";
        int httpResponseCode = http.POST(httpRequestData);

        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);

        // Free resources
        http.end();
    }
}

void loop()
{
    uploadSensorData();
}