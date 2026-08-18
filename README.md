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
| `NODE_RATE_WINDOW_SEC` | `300` | Janela (segundos) usada pelo painel de estado dos nós (`/api/node-status`) para `detections_per_min` e `median_rssi_dbm` — ver secção 2, página "Estado dos Nós". |
| `DB_NAME` | `temp1_db` | Nome da base de dados MongoDB usada pelo backend. Muda para isolar uma instância de verificação (ex: `temp1_db_verify`) sem tocar nos dados reais de ensaios — mesmo `mongod` local, isolamento só pelo nome. |
| `PORT` | `5000` | Porta onde o backend fica à escuta. Combina com `DB_NAME` para correr uma instância de verificação em paralelo com a real, sem conflito. |

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

#### Nota metodológica: sincronização temporal (NTP) e identificação de lotes (guião secção 3)
`raw_detections` guarda, além do `time` já existente (hora de **receção no servidor**, sem alteração de significado, continua a comandar a ordenação em `analyze_room_decisions.py`), três campos novos, opcionais (`None`/ausentes em dados anteriores a esta funcionalidade, ou quando o firmware antigo/o formato antigo é usado):
- **`node_time`** — instante de fim do scan segundo o relógio do próprio ESP32, sincronizado por NTP no arranque e periodicamente depois. Fica ausente se o NTP não estiver sincronizado no momento do envio.
- **`node_seq`** — contador local do nó, incrementa a cada tentativa de envio (mesmo que o POST falhe). **Diferente do `batch_id`** já existente: esse é um UUID aleatório gerado pelo *servidor* só para agrupar as linhas de um POST; `node_seq` é do *nó*, e serve para detetar lotes em falta ou duplicados.
- **`boot_id`** — identifica uma sessão de arranque contínua do nó (gerado aleatoriamente uma vez por arranque). Necessário porque `node_seq` reinicia a cada arranque do firmware — sem `boot_id`, um reinício a meio de um ensaio pareceria gerar duplicados/gaps falsos.

`POST /api/bledata` aceita **dois formatos**, para trás sem quebrar nada: o antigo (array simples `[{"mac","esp_id","rssi"}, ...]`, como os scripts `simulate_hysteresis.py`/`simulate_metrics_trial.py` continuam a enviar) e o novo, em lote (`{"esp_id","node_seq","boot_id","node_time"?,"readings":[{"mac","rssi"}, ...]}`, como o firmware atual usa). Deteção de lotes em falta/duplicados corre em dois sítios: **ao vivo**, impressa na consola do backend a cada POST (aviso "lote(s) em falta"/"lote duplicado"/"reiniciou"); e **offline**, em `analyze_room_decisions.py` (`node_seq_gap_summary` no `run_metadata_<label>.json`, com números por `(esp_id, boot_id)` — contagens citáveis, não dependem de teres visto os prints em tempo real).

Na análise offline, `node_time` só é usado (`effective_time`, coluna `clock_source="node"`) quando **todas** as deteções de um `(mac, experiment_id)` o tiverem **e** vierem de um **único** `esp_id` — caso contrário recua sempre para a hora de receção (`clock_source="server"`). **Limitações a ter em conta, sérias, não apenas teóricas:**
- **Assim que existirem os 3 nós físicos planeados — precisamente nos ensaios de campo que vão para o relatório — `node_time` deixa de se aplicar** ao cálculo de latências (um grupo com mais de um `esp_id` recua sempre para o servidor). Suportar vários nós exigiria também mudar a ordem que alimenta os algoritmos de decisão (`decision_methods.py`), fora de âmbito por agora. O benefício real, hoje: cumprir a exigência do guião ao nível do firmware, e ficar com os dois instantes gravados lado a lado — o que já permite medir o próprio atraso de rede (`node_time` vs `time`) como diagnóstico, mesmo sem usar `node_time` nas métricas.
- **O relógio do servidor não é verificado nem garantido sincronizado por este código.** Hoje, deteção e ground truth vêm ambas do relógio do servidor — um desvio absoluto desse relógio cancela-se na subtração e a latência sai correta na mesma. Ao usar `node_time` (relógio do nó, corrigido por NTP) contra o ground truth (continua relógio do servidor), esse cancelamento deixa de acontecer: **se o relógio do servidor estiver desviado, esta funcionalidade piora a precisão da latência em vez de a melhorar.** Verificado nesta máquina de desenvolvimento que o serviço de hora do Windows (`w32tm`) está parado — não assumas que "o Windows já trata disso" sem confirmar.
- **Resolução de 1 segundo** em `node_time` e `time` (nenhum tem fração de segundo) — como as latências medidas andam tipicamente na ordem de poucos segundos, sincronizar o relógio por NTP não ajuda além do que esta quantização já limita.
- A rede do hospital pode bloquear NTP externo (porta UDP 123 de saída) — o firmware permite apontar `NTP_SERVER` para um servidor interno, se necessário.

O servidor fica à escuta em `http://0.0.0.0:5000` (todas as interfaces de rede).

### Verificar que está tudo a funcionar
```powershell
curl.exe http://localhost:5000/api/data -H "X-User: teste"
```
Deve devolver `[]` (lista vazia) ou os dispositivos atualmente detetados, sem erro. **Usa sempre `curl.exe`, não só `curl`** — no PowerShell, `curl` é um alias para `Invoke-WebRequest`, que não percebe `-H`/`-d` da mesma forma (dá erro `Cannot bind parameter 'Headers'`); `curl.exe` chama o curl a sério que já vem com o Windows.

**Testar isolado, sem tocar em `temp1_db`/porta 5000**: combina `DB_NAME` e `PORT` para correr uma segunda instância a apontar para uma base de dados de teste, em paralelo com a real:
```powershell
$env:DB_NAME = "temp1_db_verify"
$env:PORT = "5001"
python app.py
```
Mesmo `mongod` local — `temp1_db_verify` fica completamente isolada (coleções e índices próprios, criados automaticamente no arranque), sem partilhar nada com `temp1_db`.

### Ground truth e parâmetros do ensaio
Para a avaliação experimental (guião, pontos 2 e 8), há dois tipos de registo novos, além do `experiment_id` já existente.

**Fluxo principal: os botões "Iniciar ensaio"/"Terminar ensaio" na página `/ground-truth` (secção 2)** — pensados para nunca precisares do terminal a meio de um ensaio. "Iniciar" sugere um nome com data/hora (editável antes de confirmares); se já houver um ensaio ativo, pede confirmação antes de o substituir. "Terminar" (ou substituir um ativo por outro) mostra logo um resumo por MAC (deteções, eventos de ground truth, transições, duração) — para saberes se o ensaio foi válido antes de saíres do sítio. O indicador do ensaio ativo fica **verde** normalmente e **laranja** passadas 2h (`STALE_EXPERIMENT_THRESHOLD_MIN`) — um ensaio esquecido sobrevive a reinícios do backend e a dias inteiros (ver mais abaixo), por isso este limiar é preventivo, não só informativo.

Os comandos `curl.exe`/`Invoke-RestMethod` abaixo continuam a funcionar exatamente na mesma — ficam como alternativa via terminal, ou para scripting:

**Parâmetros de aquisição** — fixos durante a recolha (duração/intervalo de scan, filtragem no firmware), associados ao `experiment_id`. Regista-os ao mesmo tempo que marcas o ensaio:
```powershell
curl.exe -X POST http://localhost:5000/api/experiment -H "X-User: teste" -H "Content-Type: application/json" -d '{"experiment_id":"ensaio1","scan_duration_sec":5,"upload_interval_ms":10000,"firmware_rssi_cutoff":null}'
```
Um `POST` posterior que só reafirme o `experiment_id` (sem estes campos) **não apaga** os valores já registados. `GET /api/experiments` lista todos os ensaios registados (agora sempre com `created_at`, mesmo para ensaios iniciados sem nenhum parâmetro de aquisição). Isto fica guardado à parte (coleção `experiments`), nunca dentro do `raw_detections`.

A resposta de `GET`/`POST /api/experiment` inclui também:
- `experiment_started_at` — quando o ensaio ativo começou.
- `experiment_elapsed_min` — minutos decorridos, **sempre calculado no servidor**, nunca no cliente (o relógio do telemóvel e o do servidor não são a mesma referência — ver limitação do relógio do servidor, mais abaixo — por isso o `/ground-truth` nunca faz essa conta sozinho).
- `ended_summary` (só quando um `POST` muda o `experiment_id` ativo para outra coisa — `null` ou outro nome) — o resumo por MAC do ensaio que acabou de ser abandonado.

**O ensaio ativo sobrevive a um reinício do backend.** Fica também guardado numa coleção pequena (`app_state`, um único documento, sempre substituído no lugar), recarregada no arranque do `app.py` — antes disto, reiniciar o backend a meio de um ensaio apagava-o silenciosamente da memória, e as deteções/marcações seguintes ficavam sem `experiment_id`, sem aviso nenhum.

**Ground truth** — onde o beacon esteve *realmente*, ao longo do tempo. Modelado como eventos discretos ("entrei na sala X agora"), não como intervalos diretos:
- `POST /api/ground-truth` `{mac, room, experiment_id?, time?, scenario?, note?}` — `experiment_id` usa por default o ensaio ativo no momento; `time` é opcional (`"YYYY-MM-DD HH:MM:SS"`) para entrada retroativa, senão usa a hora do servidor.
- `GET /api/ground-truth?experiment_id=&mac=` — lista para revisão.
- `DELETE /api/ground-truth/<id>` — desfaz uma marcação errada.

**`scenario`** (guião secção 9, "Comparação por cenário") — um de `centro_sala`, `junto_parede`, `junto_porta`, `movimento` (não validado no servidor, campo livre como o `note`). Corresponde a 4 dos 5 cenários do guião — falta "Vários beacons" de propósito: essa é uma condição do **ensaio inteiro** (quantos beacons ativos em simultâneo), não algo por marcação, já fica implícita em quantos beacons estão na whitelist durante o ensaio.

**Nota metodológica importante sobre `scenario`**: aplica-se a **todo o intervalo até à próxima marcação**, não a uma leitura isolada — exatamente como já acontece com a sala (`ground_truth_room`). Se tocares "Corredor / Centro da sala" e depois andares até à porta sem tocar de novo, todas as leituras nesse intervalo (mesmo já perto da porta) ficam etiquetadas "Centro da sala". **Para a comparação por cenário da secção 9 fazer sentido, tens de tocar sempre que mudas de cenário — mesmo que a sala não mude.**

Ver secção 2 para a página do dashboard que faz isto na prática (`/ground-truth`). Os intervalos de ground truth (`"esteve em X entre T1 e T2"`) são derivados só na análise offline (secção 4), emparelhando eventos consecutivos do mesmo ensaio — não ficam guardados como intervalos na BD.

### Estado dos nós, histórico pesquisável e exportação (guião secção 3.11)
Dashboard como ferramenta operacional, não só de demonstração — três endpoints novos, pensados para diagnosticar problemas de infraestrutura (nó mal posicionado, nó a não comunicar, falhas a chegar ao Mirth) *antes* de aparecerem na análise offline de um ensaio já terminado.

**`GET /api/node-status`** — por cada `esp_id` (configurado em `esp_mapping`, mesmo que nunca tenha enviado nada — aparece como offline, não como ausente):
```powershell
curl.exe http://localhost:5000/api/node-status -H "X-User: teste"
```
Devolve `{"nodes": [...], "rate_window_sec": 300, "mirth": {...}}`. Cada nó: `esp_id, room, boot_id, last_seen, seconds_since_last_seen, detections_per_min, median_rssi_dbm, gap_count, duplicate_count, reorder_count`. Não classifica online/offline no servidor — isso é feito na página "Estado dos Nós" (secção 2), contra um limiar ajustável ali mesmo, sem reiniciar o backend.

**`detections_per_min` vs `median_rssi_dbm` — não são a mesma coisa, e um sozinho não basta**: `detections_per_min` conta TODO o tráfego BLE de cada scan (qualquer dispositivo, não só beacons seguidos — 60+ por ciclo em dados reais, dominado por ruído ambiente), é só um sinal de que o nó está vivo e a escanear. Já aconteceu, num ensaio real, os 3 nós detetarem ao mesmo ritmo enquanto um deles via os beacons whitelisted a -80/-90 dBm contra -60/-77 dBm dos vizinhos no mesmo instante — `detections_per_min` sozinho não teria mostrado nada de errado. `median_rssi_dbm` (mediana do RSSI dos beacons whitelisted na mesma janela, `NODE_RATE_WINDOW_SEC`) é o que efetivamente distingue um nó mal posicionado/degradado de um saudável.

**`mirth`** (`last_success`, `last_failure`, `failure_count_session`) — hoje uma falha ao enviar para o Mirth só aparece impressa na consola do backend; estes contadores dão-lhe visibilidade no dashboard. Não é uma fila de reenvio (isso seria uma funcionalidade maior, fora de âmbito aqui) — só visibilidade de se os envios recentes estão a ter sucesso.

**`GET /api/detection-history`** — histórico pesquisável, filtros por sala, beacon (MAC) e intervalo temporal, todos opcionais:
```powershell
curl.exe "http://localhost:5000/api/detection-history?room=Sala1&start=2026-08-08%2010:00:00&end=2026-08-08%2011:00:00" -H "X-User: teste"
```
Devolve `{"results": [...], "truncated": bool}` — no máximo 500 linhas (`limit`, até 5000). `truncated: true` avisa que há mais dados do que os devolvidos — refina os filtros.

**`GET /api/detection-history/export`** — mesmos filtros, devolve CSV (`time, mac, room, esp_id, rssi, node_time, node_seq, boot_id, batch_id, experiment_id`), até 5000 linhas. **Isto é para consultas pontuais/filtradas a partir do dashboard, não para substituir o `analyze_room_decisions.py`** (secção 4) como exportação completa de um ensaio inteiro. Se o filtro corresponder a mais de 5000 linhas, o corte é sinalizado de duas formas — nunca dentro dos próprios dados do CSV, para não poluir uma análise posterior em pandas/Excel: o header HTTP `X-Export-Truncated`, e um sufixo `_truncated` no nome do ficheiro descarregado (visível mesmo fora da app).

**Caveat conhecido, não corrigível sem reprocessar dados antigos**: `raw_detections.room` reflete o nome da sala **no momento da deteção**, copiado do `esp_mapping` de então — se renomeares uma sala mais tarde, deteções antigas continuam com o nome antigo e não aparecem ao filtrares pelo nome novo.

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
1. **Indicador do ensaio ativo**, sempre visível: verde com o nome + "ativo há X min" (calculado no servidor, nunca no telemóvel), laranja passadas 2h (ensaio provavelmente esquecido), ou neutro se não houver nenhum — nunca bloqueia as marcações seguintes.
2. **"Iniciar ensaio"**: abre um formulário inline com um nome sugerido (data/hora), editável antes de confirmares. Se já houver um ensaio ativo, pede confirmação antes de o substituir (mostra o nome e há quanto tempo está ativo). Mostra também os últimos ensaios usados, para não repetires um nome sem querer.
3. **"Terminar ensaio"** (ou confirmar a substituição de um ativo): mostra logo um resumo por MAC — deteções, eventos de ground truth, transições, duração — antes de guardares o telemóvel.
4. Escolhe o beacon (MAC) num `<select>` — fica guardado no telemóvel para a próxima vez.
5. **Cenário** (guião secção 9): 4 botões (Centro da sala / Junto à parede / Junto à porta / Movimento entre salas), o escolhido fica guardado no telemóvel entre toques. Aplica-se a todo o intervalo até à próxima marcação — muda de cenário sem mudar de sala exige tocar na sala outra vez (ver nota na secção 1).
6. Toca no botão grande da sala onde estás **agora** — cada toque envia logo um evento com a hora do servidor e o cenário selecionado.
7. **"Hora manual"**: alternador que revela um campo de data/hora, para entrada retroativa (ex: sem rede no momento — anotas mentalmente as horas e introduzes tudo depois, já com rede).
8. Lista das últimas marcações desta sessão (com o cenário entre parêntesis, quando presente), cada uma com um botão **"Desfazer"** — para os toques errados, que vão acontecer.

Os eventos ficam guardados como pontos no tempo (não intervalos) — os intervalos ("esteve na sala X entre T1 e T2") só são calculados depois, no `analyze_room_decisions.py`.

### Página `/node-status` — "Estado dos Nós"
Um `esp_id` por linha: online/offline (badge, limiar ajustável num campo na própria página — sem precisar reiniciar o backend), última comunicação, deteções/min, RSSI mediano (dBm) dos beacons whitelisted, lotes perdidos/duplicados/reordenados na sessão atual do backend. Nota curta na própria página lembra que "deteções/min" e "RSSI mediano" respondem a perguntas diferentes (ver secção 1) — um nó pode escanear normalmente e ainda assim estar mal posicionado. Secção pequena à parte com o estado da integração Mirth (última confirmação/falha, nº de falhas). Atualiza a cada 5s.

### Página `/history` — "Histórico"
Filtros por sala, beacon (MAC) e intervalo temporal (todos opcionais), botão "Pesquisar" e botão "Exportar CSV" (usa os mesmos filtros). Um filtro sem resultados mostra uma mensagem em vez de uma tabela vazia; um filtro com mais de 500/5000 linhas (ecrã/CSV) mostra um aviso de truncagem — ver secção 1 para os detalhes e o porquê do limite.

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

### Sincronização NTP e identificação de lotes
O firmware sincroniza o relógio via NTP no arranque (`syncTime()`, timeout de 10s) e volta a sincronizar de hora a hora (`NTP_RESYNC_INTERVAL_MS`). `NTP_SERVER` é um pool público por default — muda para um servidor NTP interno se a rede do hospital bloquear NTP externo (porta UDP 123 de saída). `TZ_LISBON` é a string POSIX TZ para Europe/Lisbon (com mudança de hora automática, para bater certo com o relógio do servidor) — **confirma isto ao compilar/testar**, foi o único detalhe deste ficheiro que não foi possível verificar sem executar código real no dispositivo.

Cada lote enviado a `/api/bledata` leva `node_seq` (contador local, incrementa a cada envio, mesmo que falhe) e `boot_id` (identifica esta sessão de arranque — gerado com `esp_random()`, que só devolve entropia verdadeira depois do WiFi estar ativo, por isso é gerado depois de `connectWiFi()`, nunca antes). `node_time` (instante de fim do scan) só é incluído no lote se o relógio estiver sincronizado nesse momento — ver secção 1 para o que o backend faz com estes campos.

### Configuração remota do scan (guião secção 7)
`SCAN_DURATION_SEC`/`UPLOAD_INTERVAL_MS` já não estão fixos no `.ino` — cada nó vai buscar a sua configuração efetiva a `GET /api/node-config?esp_id=...` **uma vez, no arranque**, e cai nos valores de fábrica (5s / 10000ms) se o pedido falhar por qualquer razão (sem rede ainda, backend em baixo, resposta inválida) — o arranque nunca fica bloqueado à espera disto. O Monitor Série mostra sempre o valor efetivo e a origem (backend ou fallback); os mesmos valores vão em cada lote enviado (`scan_duration_sec`/`upload_interval_ms`), para ficarem também nos dados (`raw_detections`).

- **Cadência só-arranque, não periódica**: uma alteração só faz efeito depois de reiniciar fisicamente o nó — não há verificação a meio do funcionamento. Isto é deliberado: os nós já são reiniciados fisicamente entre ensaios como parte da rotina de campo, e uma verificação periódica introduziria interrupções a meio de um scan/envio por um benefício que não é necessário hoje.
- **Âmbito por `esp_id`**: cada nó pode ter a sua própria configuração (`POST /api/esp-mapping`, campos `scan_duration_sec`/`upload_interval_ms`, opcionais e independentes de `room`) — útil dado o hardware misto (FireBeetle vs. WROOM-32). Sem override, cai nos defaults globais (`DEFAULT_SCAN_DURATION_SEC`/`DEFAULT_UPLOAD_INTERVAL_MS`, ver `.env.example`).
- **Integridade dos ensaios**: `POST /api/esp-mapping` (alterar configuração) e `DELETE /api/delete-room/<esp_id>` (remover o mapeamento inteiro) ficam bloqueados (409) enquanto houver um ensaio ativo (`current_experiment_id`) — mudar a configuração de aquisição, ou perder o mapeamento de sala de um nó, a meio da recolha de dados corromperia o ensaio em curso. O valor efetivo usado em cada lote fica sempre gravado em `raw_detections` (independentemente disto correr como esperado), e `analyze_room_decisions.py` compara-o offline com o que ficou registado em `experiments` (`acquisition_config_divergence` em `run_metadata_<label>.json`) — avisa sempre que o MESMO `esp_id` usou mais do que um valor dentro do mesmo ensaio, e compara o valor registado com o efetivo da frota só quando todos os nós desse ensaio concordam entre si (evita falsos positivos quando a configuração por `esp_id` está mesmo a ser usada para dar valores diferentes a nós diferentes).

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
- `analysis_output/raw_with_decisions_<experiment_id>.csv` — uma linha por deteção, com a decisão de cada método, as colunas `ground_truth_room`/`ground_truth_scenario` (sala real e cenário, derivados dos eventos marcados em `/ground-truth` — em branco antes da 1ª marcação de um ensaio; `ground_truth_scenario` só expõe o dado, não há ainda nenhuma análise que o agregue), e as colunas `node_time`/`node_seq`/`boot_id`/`effective_time`/`clock_source` (ver secção 1 — `clock_source` diz se essa linha usou o relógio do nó ou do servidor).
- `analysis_output/decision_summary_<experiment_id>.csv` — métricas por MAC/método (nº de transições, concordância com o método final).
- `analysis_output/run_metadata_<experiment_id>.json` — metadados desta execução específica: os parâmetros de **análise** usados (`--hysteresis-margin`, `--median-window`, `--persistence-streak`, `--min-rssi`), os parâmetros de **aquisição** de cada `experiment_id` presente nos dados (lidos da coleção `experiments`), um resumo de quantos eventos de ground truth foram carregados por MAC, um resumo de cobertura de `node_time`/`node_seq` por MAC (`node_time_summary`), a deteção offline de lotes em falta/duplicados por `(esp_id, boot_id)` (`node_seq_gap_summary` — ver secção 1), e um aviso citável (`node_time_clock_warning`, `null` se não se aplicar) sempre que algum grupo tenha usado o relógio do nó em vez do servidor. É este ficheiro que te permite reanalisar o mesmo ensaio com parâmetros diferentes sem repetir a recolha — cada execução sobrescreve o seu próprio `run_metadata_<label>.json`, nunca os dados brutos.
- `plots/<mac>_<experiment_id>_room_timeline.png` — gráfico com o RSSI bruto e a decisão de cada método ao longo do tempo.

```powershell
pip install -r requirements-analysis.txt   # se ainda não tiveres feito
python analyze_room_decisions.py --experiment-id <id> --mac aa:bb:cc:dd:ee:01
python analyze_room_decisions.py                       # todos os ensaios, todos os MACs
python analyze_room_decisions.py --experiment-id <id> --min-rssi -70   # ignora leituras mais fracas que -70 dBm
```
Principais opções: `--hysteresis-margin`, `--median-window`, `--persistence-streak`, `--min-rssi` (default: sem filtro — ver nota metodológica acima sobre o cutoff de -60 dBm da Bella), `--no-plots`, `--mongo-uri`, `--db-name` (default `temp1_db` — aponta a análise a outra base de dados, ex: uma de teste, sem editar o script).

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
Confirma primeiro que só tens **um** processo do backend a correr (ver acima) — é a causa mais comum de "a consola que estou a ver não é a que está a responder". Depois testa o endpoint diretamente com `curl.exe` (não só `curl` — ver nota na secção 1) para veres o traceback completo.

**Mirth Connect inacessível (timeout ao mudar de sala)**
Usa o `mock_mirth.py` + `MIRTH_URL` (secção 4) para testar sem depender da rede do hospital.

**ESP32 não regista deteções novas / valores presos no dashboard**
Confirma com dois `curl.exe` seguidos a `/api/all-beacons` se o `time` de cada beacon está mesmo a mudar — se estiver idêntico, o problema é o ESP32 não estar a enviar (`POST /api/bledata`), não o frontend. Verifica o Serial Monitor do ESP32.
