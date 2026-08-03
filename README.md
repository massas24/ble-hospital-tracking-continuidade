A real-time BLE tracking dashboard for hospitals using ESP32, Flask, React, and MongoDB.

System Architecture Data Flow Overview
<img width="892" height="629" alt="image" src="https://github.com/user-attachments/assets/52840c47-c4e2-4312-bb6f-5abfcf5db626" />

## Componentes

- **`backend/`** — API Flask + MongoDB. Recebe deteções BLE dos nós ESP32, decide a localização (histerese ao vivo), guarda histórico e deteções brutas, envia eventos ao Mirth Connect.
- **`frontend/`** — Dashboard React (login, gestão de whitelist/salas, histórico de beacons).
- **`esp32-firmware/`** — Firmware Arduino/C++ para os nós ESP32 (scanner BLE + upload HTTP).
- **`docs/`** — Guião experimental e proposta de continuidade do projeto.

---

## 1. Backend (Flask + MongoDB)

### Pré-requisitos
- Python 3.x instalado.
- MongoDB a correr localmente, à escuta em `mongodb://localhost:27017` (instala o MongoDB Community Server e garante que o serviço `mongod` está ativo — no Windows, verifica em `services.msc` ou corre `mongod` manualmente).

### Instalação
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para correr o script de análise offline (`analyze_room_decisions.py`), instala também as dependências extra (pandas/matplotlib, mantidas separadas do backend de produção):
```powershell
pip install -r requirements-analysis.txt
```

### Variáveis de ambiente
| Variável | Default | Para quê |
|---|---|---|
| `MIRTH_URL` | `http://192.168.1.117:6661` | Endpoint do Mirth Connect para onde os eventos de mudança de sala são enviados. Muda para o `mock_mirth.py` local durante testes (ver secção 4). |
| `HYSTERESIS_MARGIN` | `5` | Margem (dBm) que uma sala nova tem de superar sobre a sala atual para a mudança ser aceite pela histerese ao vivo (a que gera os eventos de Mirth). |
| `MEDIAN_WINDOW` | `5` | Nº de deteções recentes usadas na mediana de RSSI, para o cálculo do `location_status` ao vivo. Mesmo default do `--median-window` do `analyze_room_decisions.py`, para as duas visões (ao vivo/offline) refletirem a mesma configuração. |
| `PERSISTENCE_STREAK` | `3` | Nº de leituras seguidas iguais necessárias para a persistência confirmar uma sala, no cálculo do `location_status` ao vivo. Mesmo default do `--persistence-streak` offline. |
| `LOCATION_STATUS_HISTORY_SIZE` | `30` | Quantas `raw_detections` recentes por MAC são usadas para recalcular a cadeia mediana+histerese+persistência a cada deteção nova (ver `location_status` mais abaixo). |
| `INACTIVE_TIMEOUT_SEC` | `60` | Segundos sem deteção até um beacon whitelisted passar a `location_status: "desconhecida"`. Calculado em tempo de leitura (`/api/beacon-latest`, `/api/all-beacons`), não gravado. |
| `MIN_RSSI` | *(vazio = desativado)* | Limiar mínimo de RSSI (dBm) — leituras mais fracas são ignoradas pela camada de decisão do `location_status` (não pela histerese ao vivo nem pelo `raw_detections`, que ficam sempre completos). Desativado por default; ver nota metodológica abaixo. |

**Forma prática de definir isto sem repetir a cada terminal novo**: copia `backend/.env.example` para `backend/.env` e edita os valores que quiseres mudar — o `app.py` carrega-o automaticamente no arranque (`python-dotenv`). O `.env` real fica fora do git (`.gitignore`), cada máquina/pessoa tem o seu; sem esse ficheiro, tudo continua exatamente como na tabela acima.
```powershell
cd backend
cp .env.example .env
notepad .env   # edita o que precisares, ex: MIRTH_URL
python app.py
```

Alternativa pontual (sem `.env`, só para essa sessão do terminal):
```powershell
$env:MIRTH_URL = "http://127.0.0.1:6670"   # exemplo, para testar com o mock local
python app.py
```

#### Nota metodológica: filtragem de RSSI (diferença face ao protótipo original)
O firmware original da Bella Gnan tinha um **cutoff de -60 dBm aplicado no próprio ESP32** — deteções mais fracas eram descartadas antes de sequer serem enviadas ao backend (ver `docs/Final-MCM-FinalReport-BellaGnan.md`, secção 3.4.1). O firmware atual (`esp32-firmware/rtls_node.ino`) **não tem esse filtro** — envia todas as deteções, sem exceção. Em vez disso, a filtragem por RSSI mínimo (`MIN_RSSI`) foi movida para a **camada de decisão no backend**, propositadamente: assim o `raw_detections` fica sempre completo (importante para a avaliação experimental — ponto 2 do guião), e a filtragem é só aplicada quando e se quiseres, no cálculo de `location_status`, sem perder o dado bruto. Para replicar o comportamento original da Bella, define `MIN_RSSI=-60`.

O servidor fica à escuta em `http://0.0.0.0:5000` (todas as interfaces de rede).

### Verificar que está tudo a funcionar
```powershell
curl http://localhost:5000/api/data -H "X-User: teste"
```
Deve devolver `[]` (lista vazia) ou os dispositivos atualmente detetados, sem erro.

### Ground truth e parâmetros do ensaio
Para a avaliação experimental (guião, pontos 2 e 8), há dois tipos de registo novos, além do `experiment_id` já existente:

**Parâmetros de aquisição** — fixos durante a recolha (duração/intervalo de scan, filtragem no firmware), associados ao `experiment_id`. Regista-os ao mesmo tempo que marcas o ensaio:
```powershell
curl -X POST http://localhost:5000/api/experiment -H "X-User: teste" -H "Content-Type: application/json" -d '{"experiment_id":"ensaio1","scan_duration_sec":5,"upload_interval_ms":10000,"firmware_rssi_cutoff":null}'
```
Um `POST` posterior que só reafirme o `experiment_id` (sem estes campos) **não apaga** os valores já registados. `GET /api/experiments` lista todos os ensaios registados. Isto fica guardado à parte (coleção `experiments`), nunca dentro do `raw_detections`.

**Ground truth** — onde o beacon esteve *realmente*, ao longo do tempo. Modelado como eventos discretos ("entrei na sala X agora"), não como intervalos diretos:
- `POST /api/ground-truth` `{mac, room, experiment_id?, time?, note?}` — `experiment_id` usa por default o ensaio ativo no momento; `time` é opcional (`"YYYY-MM-DD HH:MM:SS"`) para entrada retroativa, senão usa a hora do servidor.
- `GET /api/ground-truth?experiment_id=&mac=` — lista para revisão.
- `DELETE /api/ground-truth/<id>` — desfaz uma marcação errada.

Ver secção 2 para a página do dashboard que faz isto na prática (`/ground-truth`). Os intervalos de ground truth (`"esteve em X entre T1 e T2"`) são derivados só na análise offline (secção 4), emparelhando eventos consecutivos do mesmo ensaio — não ficam guardados como intervalos na BD.

---

## 2. Frontend (React)

### Pré-requisitos
- **Node.js 18.x** (ex: 18.20.8) — o projeto usa `react-scripts` 5.0.1, que é uma versão mais antiga do Create React App; versões de Node muito recentes (20+) podem funcionar mas 18.x é a testada. Recomenda-se usar o [nvm-windows](https://github.com/coreybutler/nvm-windows) para gerir versões:
```powershell
nvm install 18.20.8
nvm use 18.20.8
```

### Instalação
```powershell
cd frontend
npm install
npm start
```
Abre em `http://localhost:3000`.

### Nota importante: proxy `127.0.0.1` em vez de `localhost`
O `frontend/package.json` tem:
```json
"proxy": "http://127.0.0.1:5000",
```
**Não muda isto para `"http://localhost:5000"`** — no Windows, o Node.js resolve `localhost` preferencialmente para IPv6 (`::1`), mas o Flask só está à escuta em IPv4 (`0.0.0.0`). Isto causa o erro:
```
Proxy error: Could not proxy request /api/... from localhost:3000 to http://localhost:5000/ (ECONNREFUSED)
```
que aparece no browser disfarçado de "500 Internal Server Error". Usar o IP `127.0.0.1` explicitamente evita a ambiguidade de resolução de DNS. Se mudares este valor, **reinicia o `npm start`** — o CRA só lê o `proxy` do `package.json` no arranque do dev server, não em quente.

### Página `/ground-truth` — marcar a localização real durante um ensaio
Página pensada para usar no **telemóvel**, a andar fisicamente com o beacon, longe do portátil. Acessível pela ligação "Ground Truth" na sidebar, ou diretamente pelo URL `http://<IP-do-portátil>:3000/ground-truth` — vale a pena **adicionar aos favoritos/ecrã principal do telemóvel** para acesso rápido a meio de um ensaio. Fica fora do layout de desktop (sem sidebar fixa), só precisa de autenticação normal (mesmo login que já usas — o telemóvel também guarda a sessão em `localStorage` depois de entrares uma vez).

Como usar:
1. Mostra o `experiment_id` ativo em destaque (aviso vermelho se não houver nenhum).
2. Escolhe o beacon (MAC) num `<select>` — fica guardado no telemóvel para a próxima vez.
3. Toca no botão grande da sala onde estás **agora** — cada toque envia logo um evento com a hora do servidor.
4. **"Hora manual"**: alternador que revela um campo de data/hora, para entrada retroativa (ex: sem rede no momento — anotas mentalmente as horas e introduzes tudo depois, já com rede).
5. Lista das últimas marcações desta sessão, cada uma com um botão **"Desfazer"** — para os toques errados, que vão acontecer.

Os eventos ficam guardados como pontos no tempo (não intervalos) — os intervalos ("esteve na sala X entre T1 e T2") só são calculados depois, no `analyze_room_decisions.py`.

---

## 3. Firmware ESP32 (`esp32-firmware/rtls_node.ino`)

### Pré-requisitos (Arduino IDE)
1. Instala o suporte para placas ESP32 (`Ficheiro > Preferências > URLs adicionais de gestor de placas`, adiciona o índice do `esp32` da Espressif, depois `Ferramentas > Placa > Gestor de Placas` e instala "esp32").
2. Biblioteca **ArduinoJson** (by Benoit Blanchon), **v6.x** — instala via `Ferramentas > Gerir Bibliotecas`. `BLEDevice`/`BLEScan`/`BLEAdvertisedDevice` já vêm incluídas no core do ESP32.
3. Placa: **ESP32 Dev Module** (ou equivalente).
4. **Esquema de partição**: `Ferramentas > Partition Scheme > "No OTA (2MB APP/2MB SPIFFS)"` ou **"Huge APP (3MB No OTA/1MB SPIFFS)"**. O sketch (WiFi + BLE + HTTPClient + ArduinoJson) pode não caber no esquema de partição default em algumas placas — se o compilador der erro de "sketch too big"/espaço insuficiente, muda para um destes esquemas.

### Variáveis a editar antes de carregar
O ficheiro em `esp32-firmware/rtls_node.ino` traz **placeholders genéricos** de propósito (não credenciais reais, para poder ficar no repositório). Antes de carregar para o ESP32, edita localmente estas 3 variáveis no topo do ficheiro — **não commites os valores reais de volta**:
```cpp
const char* WIFI_SSID     = "TUA_REDE_WIFI";              // <- muda para a tua rede WiFi
const char* WIFI_PASSWORD = "TUA_PASSWORD";               // <- muda para a password dessa rede
const char* SERVER_URL    = "http://IP_DO_SERVIDOR:5000/api/bledata";  // <- muda para o IP real do portátil, nunca "localhost"
const char* ESP_ID        = "ESP-101";  // tem de coincidir com o mapeamento em /api/esp-mapping
```
Descobre o IP do portátil com `ipconfig` (adaptador Wi-Fi, endereço IPv4) — **muda sempre que a rede mudar** (DHCP pode atribuir um IP diferente).

### Limitação conhecida: configuração do scan não é remota
`SCAN_DURATION_SEC` e `UPLOAD_INTERVAL_MS` continuam fixos como `const` no `.ino` — só se mudam recompilando e recarregando o firmware em cada ESP32. O guião (secção 7) pede que isto seja configurável sem recompilar; para isso seria preciso o ESP32 ir buscar a sua configuração ao backend no arranque (ex: um endpoint novo tipo `/api/node-config`), o que ainda não foi implementado. Fica registado como trabalho futuro, não como algo já resolvido.

### Antes de ligar
- Regista o(s) MAC(s) dos beacons na whitelist (`POST /api/whitelist` ou dashboard) — só MACs whitelisted ficam guardados em `beacon_history`/`beacon_latest`/`raw_detections`.
- Regista o mapeamento `esp_id → sala` (`POST /api/esp-mapping` ou dashboard), senão a sala fica `"unknown"`.
- Serial Monitor a **115200 baud** (tem de bater certo com `Serial.begin(115200)` no código, senão aparecem caracteres ilegíveis).
- Portátil e ESP32 na mesma rede WiFi; a firewall do Windows tem de permitir ligações de entrada na porta 5000 vindas da rede local (perfil de rede "Privado" ajuda; em "Público" o Firewall bloqueia por defeito).

---

## 4. Scripts de teste e análise (`backend/`)

### `mock_mirth.py` — substituto local do Mirth Connect
Serve para testar sem aceder à rede real do hospital. Escuta HTTP numa porta à escolha, imprime qualquer JSON recebido, responde 200.
```powershell
python mock_mirth.py --port 6670
```
Usa com `$env:MIRTH_URL = "http://127.0.0.1:6670"` antes de arrancar o `app.py`.

### `simulate_hysteresis.py` — gerador de tráfego de teste
Simula um beacon a mover-se entre duas salas, com 3 cenários (mudança clara aceite, oscilação rejeitada, mudança forte finalmente aceite), enviando diretamente para `/api/bledata`. Whitelista o MAC e mapeia as salas automaticamente.
```powershell
python simulate_hysteresis.py --base-url http://localhost:5000 --delay 1.0
```
No fim, imprime um resumo de quantas leituras foram aceites/rejeitadas — compara com o que aparece na consola do backend (linhas "Histerese rejeitou...").

### `analyze_room_decisions.py` — comparação offline dos métodos de decisão
Lê `raw_detections` da MongoDB e aplica 4 configurações em cadeia (baseline → mediana → mediana+histerese → mediana+histerese+persistência), gerando:
- `analysis_output/raw_with_decisions_<experiment_id>.csv` — uma linha por deteção, com a decisão de cada método **e a coluna `ground_truth_room`** (sala real, derivada dos eventos marcados em `/ground-truth` — em branco antes da 1ª marcação de um ensaio).
- `analysis_output/decision_summary_<experiment_id>.csv` — métricas por MAC/método (nº de transições, concordância com o método final).
- `analysis_output/run_metadata_<experiment_id>.json` — metadados desta execução específica: os parâmetros de **análise** usados (`--hysteresis-margin`, `--median-window`, `--persistence-streak`, `--min-rssi`), os parâmetros de **aquisição** de cada `experiment_id` presente nos dados (lidos da coleção `experiments`), e um resumo de quantos eventos de ground truth foram carregados por MAC. É este ficheiro que te permite reanalisar o mesmo ensaio com parâmetros diferentes sem repetir a recolha — cada execução sobrescreve o seu próprio `run_metadata_<label>.json`, nunca os dados brutos.
- `plots/<mac>_<experiment_id>_room_timeline.png` — gráfico com o RSSI bruto e a decisão de cada método ao longo do tempo.

```powershell
pip install -r requirements-analysis.txt   # se ainda não tiveres feito
python analyze_room_decisions.py --experiment-id <id> --mac aa:bb:cc:dd:ee:01
python analyze_room_decisions.py                       # todos os ensaios, todos os MACs
python analyze_room_decisions.py --experiment-id <id> --min-rssi -70   # ignora leituras mais fracas que -70 dBm
```
Principais opções: `--hysteresis-margin`, `--median-window`, `--persistence-streak`, `--min-rssi` (default: sem filtro — ver nota metodológica acima sobre o cutoff de -60 dBm da Bella), `--no-plots`, `--mongo-uri`.

Usa `POST /api/experiment {"experiment_id": "..."}` antes de um ensaio real para conseguires filtrar os dados desse ensaio especificamente.

---

## 5. Problemas comuns e soluções

**"não é possível carregar... porque a execução de scripts foi desativada neste sistema" (PowerShell, ao correr `npm`/`npx`)**
Política de execução do PowerShell bloqueia scripts `.ps1` por default. Corrige com (PowerShell como utilizador normal chega):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Alternativa: usa o `cmd.exe` ou o Git Bash para correr `npm`/`npx`.

**Vejo dois processos `python.exe` a correr `app.py` — é normal?**
Depende. Se um é **pai** do outro (`Get-CimInstance Win32_Process | Select ProcessId,ParentProcessId,CommandLine` no PowerShell mostra a relação), é normal — em Python 3.13+/Windows, `venv\Scripts\python.exe` é um pequeno *launcher stub* que arranca o interpretador real como processo filho. Se forem **dois processos independentes** (sem relação pai-filho, de invocações separadas — ex: esqueceste-te de fechar um terminal antigo antes de abrir outro), só um está realmente a ocupar a porta 5000 (confirma com `Get-NetTCPConnection -LocalPort 5000`), e o outro é um duplicado a mais que deves fechar — normalmente é a causa de "o dashboard não atualiza mesmo o backend a responder" (estás a testar/ver um processo, mas o outro é que está ligado à porta).

**Erro `options.allowedHosts[0] should be a non-empty string"` ao correr `npm start`**
Ver secção 2 acima — normalmente resolve-se com `DANGEROUSLY_DISABLE_HOST_CHECK=true` (só se o fix do proxy `127.0.0.1` não for suficiente) num ficheiro `.env.development.local` dentro de `frontend/` (fica fora do git). Reinicia o `npm start` depois de qualquer alteração a variáveis de ambiente ou ao `proxy`.

**500 Internal Server Error em `/api/login` ou `/api/signup`, sem traceback na consola**
Confirma primeiro que só tens **um** processo do backend a correr (ver acima) — é a causa mais comum de "a consola que estou a ver não é a que está a responder". Depois testa o endpoint diretamente com `curl` para veres o traceback completo.

**Mirth Connect inacessível (timeout ao mudar de sala)**
Usa o `mock_mirth.py` + `MIRTH_URL` (secção 4) para testar sem depender da rede do hospital.

**ESP32 não regista deteções novas / valores presos no dashboard**
Confirma com dois `curl` seguidos a `/api/all-beacons` se o `time` de cada beacon está mesmo a mudar — se estiver idêntico, o problema é o ESP32 não estar a enviar (`POST /api/bledata`), não o frontend. Verifica o Serial Monitor do ESP32.
