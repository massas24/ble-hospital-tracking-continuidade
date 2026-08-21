/*
  RTLS Node - ESP32 BLE Scanner + WiFi Uploader
  ------------------------------------------------
  Envia para POST /api/bledata um lote por scan, no formato:
    {
      "esp_id": "...", "node_seq": 42, "boot_id": 123456789,
      "node_time": "2026-08-04 10:15:32",   // omitido se o relogio nao estiver sincronizado
      "scan_duration_sec": 5, "upload_interval_ms": 10000,  // configuracao efetiva usada neste lote (guiao seccao 7)
      "readings": [ {"mac": "...", "rssi": -65}, ... ]
    }
  O backend (backend/app.py) tambem continua a aceitar o formato antigo
  (array simples sem estes metadados), por compatibilidade com dados/scripts
  anteriores - mas este ficheiro passa a usar sempre o formato novo.

  Sincronizacao temporal (NTP) e identificacao de lotes (guiao secção 3):
  - O no sincroniza o relogio via NTP no arranque e volta a sincronizar
    periodicamente (ver NTP_RESYNC_INTERVAL_MS).
  - node_seq (contador local, incrementa a cada tentativa de envio, mesmo
    que o POST falhe) permite ao backend detetar lotes em falta/duplicados.
  - boot_id (aleatorio, gerado uma vez por arranque) identifica uma sessao
    continua de funcionamento do no - node_seq reinicia a cada arranque, e
    sem boot_id dois arranques diferentes podiam parecer duplicados.

  Configuracao de aquisicao remota (guiao secção 7):
  - SCAN_DURATION_SEC/UPLOAD_INTERVAL_MS ja nao estao fixos no codigo - o no
    vai busca-los uma vez no arranque a NODE_CONFIG_URL (derivado de
    SERVER_URL, ver buildNodeConfigUrl()), com fallback aos valores de
    fabrica se o pedido falhar. So faz efeito apos reiniciar o no.

  Bibliotecas necessárias (Arduino IDE > Gerir Bibliotecas):
    - ArduinoJson (by Benoit Blanchon), v6.x
  BLEDevice/BLEScan/BLEAdvertisedDevice e time.h já vêm no core do ESP32.

  Placa: ESP32 Dev Module (ou equivalente)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <time.h>

// ---------- CONFIGURAÇÃO (edita estes valores) ----------
const char* WIFI_SSID     = "ULSG_UTENTES";
const char* WIFI_PASSWORD = "";

// IP do portátil onde o Flask corre, na mesma rede WiFi do ESP32, porta 5000.
// Descobre com "ipconfig" no PowerShell (adaptador Wi-Fi, endereço IPv4).
const char* SERVER_URL    = "http://172.29.128.226:5000/api/bledata";

// Identificador único deste nó - tem de coincidir, carácter a carácter, com
// o esp_id que registares no mapeamento de salas (dashboard ou
// POST /api/esp-mapping). Ex: "ESP-101".
const char* ESP_ID        = "ESP-01";

// Duração de cada scan BLE, em segundos - valor de fábrica, substituído no
// arranque pelo que vier de GET /api/node-config (ver fetchNodeConfig()).
int SCAN_DURATION_SEC = 5;

// Intervalo entre envios de dados ao servidor, em milissegundos - mesma
// nota acima.
unsigned long UPLOAD_INTERVAL_MS = 10000;

// Servidor NTP - pool público por default. Se a rede do hospital bloquear
// NTP externo (porta UDP 123 de saída), muda para um servidor NTP interno
// (ex: o IP do próprio servidor Flask, se tiver um serviço NTP local, ou o
// router) - ver README, secção de limitações conhecidas.
const char* NTP_SERVER = "pt.pool.ntp.org";

// Fuso horário de Lisboa (WET/WEST), com mudança de hora automática - a
// mesma referência que o backend usa (pytz "Europe/Lisbon"), para que
// node_time e a hora do servidor fiquem diretamente comparáveis. String
// POSIX TZ padrão para Europe/Lisbon - confirma isto ao compilar/testar,
// é o único detalhe deste ficheiro que não foi possível verificar sem
// executar código real no dispositivo.
const char* TZ_LISBON = "WET0WEST,M3.5.0/1,M10.5.0";

// Reforça a sincronização periodicamente (guião: "ressincronizar
// periodicamente"), para além da sincronização automática de fundo que o
// cliente SNTP do ESP32 já faz sozinho.
const unsigned long NTP_RESYNC_INTERVAL_MS = 3600000UL; // 1 hora
// ----------------------------------------------------------

BLEScan* pBLEScan;
unsigned long lastUpload = 0;
unsigned long lastNtpResync = 0;
uint32_t nodeSeq = 0;   // contador local de lotes - incrementa a cada tentativa de envio
uint32_t bootId = 0;    // identifica esta sessão de arranque - ver comentário no topo

String nodeConfigUrl;              // construído uma vez no arranque, ver buildNodeConfigUrl()
bool scanDurationFromBackend = false;
bool uploadIntervalFromBackend = false;

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

// Tenta sincronizar/ressincronizar via NTP. Não bloqueia indefinidamente -
// getLocalTime tem o seu próprio timeout.
void syncTime(uint32_t timeoutMs) {
  configTzTime(TZ_LISBON, NTP_SERVER);
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, timeoutMs)) {
    Serial.println("Relógio sincronizado via NTP.");
  } else {
    Serial.println("Aviso: falha a sincronizar via NTP (sem rede, ou servidor NTP inacessível?).");
  }
}

// Deriva-se de SERVER_URL em vez de ser uma constante própria - só um
// IP/porta a editar no ficheiro, nunca duas URLs a poderem dessincronizar.
String buildNodeConfigUrl() {
  String url = SERVER_URL;
  url.replace("/api/bledata", "/api/node-config");
  return url;
}

// Falha em qualquer passo (sem rede, HTTP != 200, JSON inválido) mantém os
// valores de fábrica - nunca impede o arranque.
void fetchNodeConfig() {
  String url = nodeConfigUrl + "?esp_id=" + ESP_ID;
  HTTPClient http;
  http.begin(url);
  http.setTimeout(5000);
  int httpCode = http.GET();

  if (httpCode != 200) {
    Serial.printf("Aviso: falha ao obter configuração do nó (HTTP %d) - a usar valores de fábrica.\n", httpCode);
    http.end();
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, http.getString());
  http.end();

  if (err) {
    Serial.printf("Aviso: resposta de configuração inválida (%s) - a usar valores de fábrica.\n", err.c_str());
    return;
  }

  if (doc["scan_duration_sec"].is<int>() && doc["scan_duration_sec"].as<int>() > 0) {
    SCAN_DURATION_SEC = doc["scan_duration_sec"].as<int>();
    scanDurationFromBackend = true;
  }
  if (doc["upload_interval_ms"].is<int>() && doc["upload_interval_ms"].as<int>() > 0) {
    UPLOAD_INTERVAL_MS = (unsigned long)doc["upload_interval_ms"].as<int>();
    uploadIntervalFromBackend = true;
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  connectWiFi();

  // esp_random() só devolve entropia verdadeira depois de o WiFi (ou
  // Bluetooth) estar ativo (documentação ESP-IDF, "Random Number
  // Generation": antes disso só há números pseudo-aleatórios, o que podia
  // repetir o mesmo bootId entre arranques e anular o seu propósito) - por
  // isso esta chamada fica DEPOIS de connectWiFi(), nunca antes.
  bootId = esp_random();
  Serial.printf("boot_id desta sessão: %u\n", bootId);

  syncTime(10000); // sincronização inicial, timeout generoso
  lastNtpResync = millis();

  nodeConfigUrl = buildNodeConfigUrl();
  fetchNodeConfig();
  Serial.printf("Configuração efetiva: scan_duration_sec=%d (%s), upload_interval_ms=%lu (%s)\n",
                SCAN_DURATION_SEC, scanDurationFromBackend ? "backend" : "fábrica",
                UPLOAD_INTERVAL_MS, uploadIntervalFromBackend ? "backend" : "fábrica");

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

  if (millis() - lastNtpResync >= NTP_RESYNC_INTERVAL_MS) {
    syncTime(5000);
    lastNtpResync = millis();
  }

  // 1. Faz o scan BLE (bloqueante durante SCAN_DURATION_SEC segundos)
  Serial.println("A escanear dispositivos BLE...");
  BLEScanResults* results = pBLEScan->start(SCAN_DURATION_SEC, false);
  int count = results->getCount();
  Serial.printf("Encontrados %d dispositivos.\n", count);

  // Instante de fim deste scan, se o relógio estiver sincronizado agora.
  // Timeout curto: só confirma frescura, a sincronização em si já
  // aconteceu no arranque/na última ressincronização periódica.
  struct tm timeinfo;
  bool haveTime = getLocalTime(&timeinfo, 100);
  char nodeTimeStr[20]; // "YYYY-MM-DD HH:MM:SS" + '\0' = 20 bytes exatos
  if (haveTime) {
    strftime(nodeTimeStr, sizeof(nodeTimeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);
  }

  // 2. Monta o objeto JSON do lote:
  //    {"esp_id","node_seq","boot_id","node_time"?,"scan_duration_sec","upload_interval_ms","readings":[{"mac","rssi"}, ...]}
  StaticJsonDocument<4096> doc;
  doc["esp_id"] = ESP_ID;
  JsonArray readings = doc.createNestedArray("readings");

  for (int i = 0; i < count; i++) {
    BLEAdvertisedDevice device = results->getDevice(i);
    JsonObject r = readings.createNestedObject();
    r["mac"] = device.getAddress().toString().c_str();
    r["rssi"] = device.getRSSI();
  }

  pBLEScan->clearResults();

  // 3. Envia para o backend a cada UPLOAD_INTERVAL_MS
  if (millis() - lastUpload >= UPLOAD_INTERVAL_MS) {
    lastUpload = millis();

    // Incrementa ANTES do envio, mesmo que o POST a seguir falhe - só
    // assim um lote perdido em trânsito consome mesmo o seu número,
    // permitindo ao backend detetar a falha como um buraco na sequência.
    nodeSeq++;
    doc["node_seq"] = nodeSeq;
    doc["boot_id"] = bootId;
    doc["scan_duration_sec"] = SCAN_DURATION_SEC;
    doc["upload_interval_ms"] = UPLOAD_INTERVAL_MS;
    if (haveTime) {
      doc["node_time"] = nodeTimeStr;
    }

    String payload;
    serializeJson(doc, payload);

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(payload);

    Serial.printf("POST enviado (node_seq=%u) -> código de resposta: %d\n", nodeSeq, httpCode);
    if (httpCode > 0) {
      Serial.println(http.getString());
    }
    http.end();
  }

  delay(1000);
}
