/*
  RTLS Node - ESP32 BLE Scanner + WiFi Uploader
  ------------------------------------------------
  Adaptado do projeto piloto anterior (rtls_node.ino) para o formato que o
  backend atual (backend/app.py) espera: um array JSON simples de deteções,
  uma por dispositivo BLE visto:
    [ {"mac": "...", "esp_id": "...", "rssi": -65}, ... ]
  enviado para POST /api/bledata (não /api/readings, e sem o wrapper
  "node_id"/"readings" do piloto).

  Bibliotecas necessárias (Arduino IDE > Gerir Bibliotecas):
    - ArduinoJson (by Benoit Blanchon), v6.x
  BLEDevice/BLEScan/BLEAdvertisedDevice já vêm no core do ESP32.

  Placa: ESP32 Dev Module (ou equivalente)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// ---------- CONFIGURAÇÃO (edita estes valores) ----------
const char* WIFI_SSID     = "TUA_REDE_WIFI";
const char* WIFI_PASSWORD = "TUA_PASSWORD";

// IP do portátil onde o Flask corre, na mesma rede WiFi do ESP32, porta 5000.
// Descobre com "ipconfig" no PowerShell (adaptador Wi-Fi, endereço IPv4).
const char* SERVER_URL    = "http://IP_DO_SERVIDOR:5000/api/bledata";

// Identificador único deste nó - tem de coincidir, carácter a carácter, com
// o esp_id que registares no mapeamento de salas (dashboard ou
// POST /api/esp-mapping). Ex: "ESP-101".
const char* ESP_ID        = "ESP-101";

// Duração de cada scan BLE, em segundos
const int SCAN_DURATION_SEC = 5;

// Intervalo entre envios de dados ao servidor, em milissegundos
const unsigned long UPLOAD_INTERVAL_MS = 10000;
// ----------------------------------------------------------

BLEScan* pBLEScan;
unsigned long lastUpload = 0;

void connectWiFi() {
  Serial.print("A ligar ao WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Ligado! IP do ESP32: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(500);

  connectWiFi();

  BLEDevice::init(ESP_ID);
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setActiveScan(true); // scan ativo dá RSSI mais fiável
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // 1. Faz o scan BLE (bloqueante durante SCAN_DURATION_SEC segundos)
  Serial.println("A escanear dispositivos BLE...");
  BLEScanResults* results = pBLEScan->start(SCAN_DURATION_SEC, false);
  int count = results->getCount();
  Serial.printf("Encontrados %d dispositivos.\n", count);

  // 2. Monta o array JSON no formato que /api/bledata espera:
  //    [ {"mac": "...", "esp_id": "...", "rssi": -65}, ... ]
  StaticJsonDocument<4096> doc;
  JsonArray root = doc.to<JsonArray>();

  for (int i = 0; i < count; i++) {
    BLEAdvertisedDevice device = results->getDevice(i);
    JsonObject r = root.createNestedObject();
    r["mac"] = device.getAddress().toString().c_str();
    r["esp_id"] = ESP_ID;
    r["rssi"] = device.getRSSI();
  }

  pBLEScan->clearResults();

  // 3. Envia para o backend a cada UPLOAD_INTERVAL_MS
  if (millis() - lastUpload >= UPLOAD_INTERVAL_MS) {
    lastUpload = millis();

    String payload;
    serializeJson(doc, payload);

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(payload);

    Serial.printf("POST enviado -> código de resposta: %d\n", httpCode);
    if (httpCode > 0) {
      Serial.println(http.getString());
    }
    http.end();
  }

  delay(1000);
}