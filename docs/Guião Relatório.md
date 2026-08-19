# **1. Introdução** 

#### **Texto introdutório sugerido** 

“Este capítulo apresenta o contexto do estágio, o problema abordado e a motivação para a continuação do sistema RTLS anteriormente desenvolvido na ULS da Guarda. São identificadas as limitações do protótipo existente, com particular destaque para a fiabilidade da localização ao nível da sala, e definidos os objetivos do novo trabalho. O capítulo apresenta ainda o enquadramento do estágio, a metodologia geral seguida e a organização do relatório.” 

### **1.1. Contexto e motivação** 

Apresentar de forma breve: 

- importância da localização de pessoas e equipamentos em ambiente hospitalar; 

- utilização de RTLS em contexto hospitalar; 

- opção por BLE e ESP32 como solução de baixo custo; 

- existência de um protótipo anteriormente desenvolvido; 

- necessidade de melhorar a estabilidade e a fiabilidade da localização. 

Aqui não é necessário voltar a fazer uma descrição detalhada de toda a arquitetura. 

### **1.2. Problema** 

Definir claramente o problema técnico do novo estágio. 

Por exemplo: 

“O protótipo existente determina a localização de um beacon essencialmente a partir das deteções realizadas pelos nós ESP32 e dos respetivos valores de RSSI. No entanto, a variabilidade do sinal BLE, a propagação através de paredes e portas e a sobreposição das áreas de cobertura podem provocar deteções simultâneas por vários nós e falsas mudanças de localização.” 

Esta formulação cria uma ligação direta com o trabalho experimental posterior. 

### **1.3. Objetivos** 

Separar em: 

#### **Objetivo geral** 

Melhorar e avaliar a fiabilidade da localização ao nível da sala do sistema RTLS existente. 

#### **Objetivos específicos** 

- analisar o funcionamento do sistema atual; 

- preparar uma infraestrutura que permita recolher e armazenar dados experimentais; 

- implementar diferentes estratégias de localização baseadas em RSSI; 

- implementar filtragem temporal; 

- estudar mecanismos de histerese; 

- estudar mecanismos de persistência da localização; 

- comparar experimentalmente as estratégias; 

- avaliar exatidão, falsas mudanças e latência; 

- identificar uma configuração adequada para o contexto de utilização hospitalar. 

### **1.4. Enquadramento do estágio** 

Apresentar: 

- ULS da Guarda / Hospital Sousa Martins; 

- curso de Licenciatura em Engenharia Informática; 

- continuidade do estágio anterior; 

- colaboração com a equipa de informática do Hospital; 

- papel do estudante no desenvolvimento. 

### **1.5. Metodologia geral** 

Descrever brevemente as fases: 

1. estudo e reprodução do sistema existente; 

2. instrumentação para recolha de dados; 

3. implementação das estratégias; 

4. definição dos ensaios; 

5. realização dos testes; 

6. análise e comparação dos resultados. 

### **1.6. Organização do relatório** 

Descrição breve dos restantes capítulos. 

# **2. Enquadramento Tecnológico e Trabalho Relacionado** 

#### **Texto introdutório sugerido** 

“Este capítulo apresenta os conceitos e tecnologias mais relevantes para o trabalho desenvolvido. É realizada uma breve caracterização dos sistemas RTLS e da utilização de Bluetooth Low Energy para localização em interiores, com especial atenção à utilização do RSSI como indicador de proximidade e às suas limitações. São também analisadas estratégias simples utilizadas para estabilizar a localização, como filtragem 

temporal, histerese e persistência. Por fim, é enquadrado o sistema desenvolvido no estágio anterior, que constitui a base do presente trabalho.” 

### **2.1. Sistemas RTLS** 

Abordar brevemente: 

- conceito de RTLS; 

- localização indoor; 

- localização ao nível de zona/sala; 

- principais tecnologias. 

### **2.2. Bluetooth Low Energy para localização indoor** 

Incluir: 

- advertising BLE; 

- beacons; 

- scanners; 

- RSSI; 

- relação entre RSSI e proximidade; 

- vantagens do BLE. 

### **2.3. Limitações do RSSI** 

Esta secção é importante para justificar o estágio. 

Abordar: 

- flutuação temporal; 

- orientação do beacon; 

- corpo humano; 

- paredes e portas; 

- reflexão e multipercurso; 

- interferência; 

- deteção simultânea por vários nós. 

### **2.4. Estratégias de decisão de localização** 

Aqui são apresentadas as abordagens que depois serão testadas. 

#### **2.4.1. Maior RSSI** 

Estratégia de referência. 

#### **2.4.2. Filtragem temporal** 

Por exemplo: 

- média; 

- mediana; 

- janela temporal. 

#### **2.4.3. Histerese** 

Evitar mudanças quando a diferença entre nós é pequena. 

#### **2.4.4. Persistência temporal** 

Confirmar uma mudança apenas depois de várias observações ou após determinado intervalo. 

#### **2.4.5. Combinação de estratégias** 

Introduzir o princípio de uma solução que combine filtragem, histerese e persistência. 

### **2.5. Avaliação de sistemas de localização** 

Introduzir as métricas que serão posteriormente utilizadas: 

- room-level accuracy; 

- falsas mudanças; 

- movimentos não detetados; 

- latência; 

- matriz de confusão; 

- repetibilidade. 

### **2.6. Sistema RTLS desenvolvido anteriormente** 

Esta secção deverá resumir apenas o que é necessário para compreender o novo trabalho. 

Explicar: 

- BLE beacons; 

- nós ESP32; 

- Flask; 

- MongoDB; 

- React; 

- Mirth Connect; 

- fluxo geral de dados. 

O estágio anterior já estabeleceu essa arquitetura e realizou testes funcionais e de desempenho limitados, com dois nós e poucos beacons. 

### **2.7. Limitações identificadas e oportunidade de melhoria** 

Esta secção deverá estabelecer a ponte para o novo estágio. 

Por exemplo: 

- ausência de avaliação sistemática em zonas de fronteira; 

- utilização limitada do RSSI; 

- ausência de comparação de algoritmos; 

- reduzido número de nós; 

- testes curtos; 

- ausência de análise experimental rigorosa de falsas mudanças. 

# **3. Evolução do Sistema e Estratégias de Localização** 

#### **Texto introdutório sugerido** 

“Este capítulo descreve as alterações realizadas ao sistema RTLS existente para permitir uma localização ao nível da sala mais estável e uma avaliação experimental sistemática das diferentes estratégias. Inicialmente é apresentada a arquitetura utilizada como ponto de partida e as alterações necessárias para recolher e armazenar os dados de forma adequada. Em seguida são descritas as estratégias de localização implementadas, os respetivos parâmetros e as alterações efetuadas no backend para suportar a comparação entre métodos.” 

Este deverá ser o principal capítulo de desenvolvimento técnico do estágio. 

### **3.1. Sistema de base** 

Descrição resumida do sistema atual. 

Incluir um diagrama da arquitetura do relatório da Bella, com respetiva referencia bibliográfica. 

### **3.2. Requisitos para a evolução do sistema** 

Por exemplo: 

- suporte a pelo menos três nós ESP32; 

- deteções provenientes de vários nós; 

- timestamps; 

- RSSI; 

- armazenamento de dados brutos; 

- identificação dos ensaios; 

- configuração dos parâmetros. 

### **3.3. Configuração dos nós ESP32** 

Abordar: 

- firmware; 

- identificação única; 

- scan BLE; 

- parâmetros configuráveis; 

- sincronização temporal; 

- envio das deteções. 

### **3.4. Recolha e armazenamento das deteções** 

Esta secção é particularmente importante. 

Descrever: 

- estrutura dos dados; 

- RSSI bruto; 

- timestamp; 

- nó; 

- beacon; 

- scan; 

- localização estimada; 

- eventualmente ground truth experimental. 

### **3.5. Arquitetura da nova lógica de localização** 

Explicar que a decisão deixa de depender simplesmente de uma deteção isolada e passa a considerar várias observações. 

Pode existir um diagrama: 

```
ESP32 nodes
     ↓
Raw detections
     ↓
Temporal window
     ↓
RSSI processing
     ↓
Location decision
     ↓
Hysteresis / persistence
     ↓
Confirmed location
```

### **3.6. Estratégias implementadas** 

Explicar brevemente cada estratégia nas seguintes secções. 

#### **3.6.1. Estratégia de referência — maior RSSI** 

Deve existir porque permite medir objetivamente se os novos métodos melhoram o sistema. 

#### **3.6.2. Filtragem temporal do RSSI** 

Por exemplo, mediana numa janela de N segundos. 

#### **3.6.3. Filtragem temporal com histerese** 

#### **3.6.4. Filtragem, histerese e persistência** 

### **3.7. Gestão dos estados de localização** 

Por exemplo: 

- confirmed; 

- transition; 

- unknown/inactive. 

### **3.8. Configuração dos parâmetros** 

Apresentar: 

- tamanho da janela; 

- RSSI threshold; 

- margem de histerese; 

- número de confirmações; 

- timeout. 

### **3.9. Ferramentas de apoio à avaliação** 

Descrever ferramentas de apoio, caso sejam desenvolvidas. Por exemplo: 

- exportação CSV; 

- scripts Python; 

- cálculo automático de métricas; 

- geração de resultados. 

# **4. Avaliação Experimental e Resultados** 

#### **Texto introdutório sugerido** 

“Este capítulo apresenta a metodologia experimental utilizada para avaliar as estratégias de localização implementadas e os resultados obtidos. São descritos o ambiente de testes, a disposição dos nós ESP32 e dos beacons, os cenários considerados, os procedimentos de recolha de dados e as métricas utilizadas. Os resultados das diferentes 

estratégias são posteriormente comparados, analisando a exatidão da localização, a ocorrência de falsas mudanças de sala e a latência de confirmação das transições.” 

Este é o capítulo mais importante do relatório, juntamente com o capítulo 3. 

### **4.1. Objetivos da avaliação** 

Definir explicitamente as perguntas de investigação. 

Por exemplo: 

**RQ1:** A filtragem temporal do RSSI melhora a exatidão da localização? 

**RQ2:** A utilização de histerese e persistência reduz as falsas mudanças? 

**RQ3:** Qual é o impacto dessas estratégias na latência? 

**RQ4:** Qual das estratégias apresenta o melhor compromisso para o sistema hospitalar? 

### **4.2. Ambiente experimental** 

Descrever: 

- salas; 

- corredor; 

- portas; 

- paredes; 

- localização dos ESP32; 

- características dos beacons; 

- alimentação; 

- rede Wi-Fi. 

Apresentar um diagrama para ilustrar o ambiente experimental: 



<!-- Start of picture text -->
                         CORREDOR<br>        ┌───────────────────────────────────┐<br>        │             ESP32-C               │<br>        └───────┬───────────────────┬───────┘<br>                │                   │<br>              Porta               Porta<br>                │                   │<br>        ┌───────┴────────┐   ┌──────┴─────────┐<br>        │     SALA A     │   │     SALA B     │<br>        │     ESP32-A    │   │     ESP32-B    │<br>        └────────────────┘   └────────────────┘<br><!-- End of picture text -->

### **4.3. Cenários de teste** 

Sugiro que cada subsecção tenha um texto curto, técnico e já orientado para aquilo que será efetivamente avaliado. Adaptar o texto para descrever o que realmente foi considerado. 

### **4.3.1. Localização estática no interior das salas** 

“Este cenário tem como objetivo avaliar a capacidade do sistema para identificar corretamente a sala onde se encontra um beacon quando este permanece imóvel em diferentes posições no interior da divisão. Serão definidos vários pontos de teste em cada sala, preferencialmente afastados das portas e das paredes comuns com outras áreas, de modo a representar condições favoráveis de localização. Em cada posição, o beacon permanecerá imóvel durante um intervalo de tempo previamente definido, sendo registadas as deteções efetuadas por todos os nós ESP32, os respetivos valores de RSSI e a localização estimada por cada estratégia. Este cenário permitirá estabelecer o desempenho de referência do sistema em condições estáveis e analisar a consistência das diferentes estratégias de localização.” 

### **4.3.2. Localização junto às paredes** 

“Este cenário pretende avaliar o comportamento do sistema quando o beacon se encontra próximo de paredes que separam duas áreas cobertas por diferentes nós ESP32. Nestas condições, o sinal BLE poderá ser detetado simultaneamente por vários recetores, com níveis de RSSI relativamente próximos, aumentando a possibilidade de atribuições incorretas da localização. Serão selecionados vários pontos junto às paredes, incluindo paredes comuns entre salas adjacentes, e o beacon permanecerá imóvel em cada posição durante um período definido. Os resultados serão utilizados para comparar a estabilidade das estratégias implementadas e determinar a sua capacidade para evitar falsas mudanças de sala provocadas pela propagação do sinal através das estruturas físicas.” 

### **4.3.3. Localização junto às portas** 

“As zonas próximas das portas constituem um dos cenários mais exigentes para a localização ao nível da sala, uma vez que existe normalmente uma forte sobreposição das áreas de cobertura dos nós instalados nas divisões adjacentes. Neste cenário, o beacon será colocado em posições previamente definidas junto às portas, incluindo pontos imediatamente antes, durante e após a passagem entre duas áreas. Serão analisadas as deteções realizadas pelos diferentes nós, a variação dos valores de RSSI e as decisões de localização produzidas por cada estratégia. O objetivo será avaliar em que medida os mecanismos de filtragem temporal, histerese e persistência reduzem as oscilações e as falsas transições de localização nestas zonas de maior ambiguidade.” 

### **4.3.4. Localização no corredor** 

“Este cenário será utilizado para avaliar a capacidade do sistema para distinguir uma zona de corredor das salas adjacentes, considerando a possibilidade de o beacon ser simultaneamente detetado pelo nó instalado no corredor e pelos nós localizados nas salas. Serão definidos vários pontos ao longo do corredor, incluindo posições próximas e afastadas das portas, e o beacon permanecerá imóvel em cada ponto durante um intervalo de tempo determinado. A análise permitirá verificar se o sistema identifica corretamente o corredor como localização dominante e avaliar o impacto da sobreposição dos sinais provenientes das diferentes áreas.” 

### **4.3.5. Movimento entre salas** 

“Este cenário pretende avaliar o comportamento dinâmico do sistema durante deslocações reais entre áreas. O beacon será transportado ao longo de percursos previamente definidos, por exemplo da Sala A para o corredor e posteriormente para a Sala B, bem como no sentido inverso. Para cada deslocação será registado o instante correspondente à mudança real de zona, permitindo comparar essa referência com o momento em que cada estratégia confirma a nova localização. Serão avaliadas a latência de confirmação, a ocorrência de falsas mudanças, eventuais oscilações entre salas e a existência de movimentos não detetados. Este cenário será particularmente importante para analisar o compromisso entre rapidez de resposta e estabilidade da localização.” 

### **4.3.6. Testes com vários beacons** 

“Este cenário permitirá avaliar o comportamento do sistema quando vários beacons estão ativos simultaneamente na infraestrutura de teste. Os dispositivos serão distribuídos pelas diferentes salas e corredor, podendo permanecer estáticos ou ser movimentados de forma independente ao longo dos percursos definidos. O objetivo será verificar se o aumento do número de beacons influencia a deteção, o processamento dos dados ou a qualidade da localização estimada. Serão analisadas eventuais perdas de deteções, alterações na latência e diferenças de desempenho relativamente aos ensaios realizados com um único beacon. Este cenário deverá ser considerado complementar e poderá ser realizado após a validação das estratégias em condições mais controladas.” 

### **4.4. Procedimento experimental** 

Definir claramente: 

- duração de cada ensaio; 

- número de repetições; 

- posição real conhecida; 

- movimentos realizados; 

- intervalos temporais; 

- parâmetros utilizados. 

Sugestão do texto (adaptar de acordo com o que realmente foi considerado): 

“Os ensaios foram realizados de forma controlada e repetível, utilizando a configuração experimental descrita anteriormente e os diferentes cenários definidos na Secção 4.3. 

Para cada ensaio serão registados previamente o cenário, a posição ou percurso do beacon, a estratégia de localização em avaliação e os respetivos parâmetros de configuração, incluindo o intervalo de varrimento BLE, o limiar mínimo de RSSI, o tamanho da janela temporal, a margem de histerese e o critério de persistência. 

Nos testes estáticos, o beacon foi colocado em pontos previamente definidos e permaneceu imóvel durante um período fixo, suficiente para recolher várias janelas de deteção. Durante esse intervalo foram registadas todas as deteções efetuadas pelos nós 

ESP32, incluindo o identificador do nó, o RSSI e o timestamp, bem como a localização estimada pelo sistema. 

Para esse ambiente experimental considerado com duas salas adjacentes e um corredor, foram definidas 11 posições estáticas: 

- **Sala A:** 3 posições — centro, junto à parede comum, junto à porta; 

- **Sala B:** 3 posições equivalentes; 

- **Corredor:** 3 posições — uma junto de cada porta e uma posição central; 

- **Zonas de fronteira:** 2 posições — uma exatamente na transição de cada porta. 

Em esquema: 



<!-- Start of picture text -->
                         CORREDOR<br>          C1 ------------ C2 ------------ C3<br>                 P1                 P2<br>                 │                  │<br>        ┌────────┴────────┐  ┌──────┴─────────┐<br>        │                 │  │                │<br>        │ A1          A3  │  │  B3         B1 │<br>        │                 │  │                │<br>        │       A2        │  │       B2       │<br>        │                 │  │                │<br>        └─────────────────┘  └────────────────┘<br><!-- End of picture text -->

Onde: 

- **A1 / B1** : zona mais interior da sala; 

- **A2 / B2** : posição central; 

- **A3 / B3** : junto à parede/porta, onde existe maior sobreposição; 

- **C1 / C3** : corredor junto a cada sala; 

- **C2** : centro do corredor; 

- **P1 / P2** : zona de passagem da porta. 

Cada posição foi testada várias vezes, preferencialmente em repetições independentes, de modo a reduzir a influência de variações ocasionais do sinal BLE. 

#### **<mark>Nota:</mark>** 

Se fizeres **5 repetições por posição** , tens: 

11 x 5 = 55 ensaios estáticos 

Com 60 s por ensaio: 

55 x 60 = 3300 s  aproximadamente 55 minutos de aquisição 

Na prática, com reposicionamento e preparação, será mais do que isso, mas continua perfeitamente gerível. 

As 11 posições são suficientes. Para este estudo, é mais importante ter boas repetições nas posições críticas do que muitas posições com poucos ensaios. As posições junto às portas, paredes comuns e corredor terão muito mais valor científico do que adicionar vários pontos semelhantes no centro das salas. 

Cada posição física de teste não deve ser medida uma única vez durante um período longo, mas sim através de vários ensaios separados. Isso permite perceber se o desempenho observado é consistente ou se resulta apenas de condições momentâneas do sinal BLE. 

Por exemplo, para uma posição A1 no interior da Sala A, o procedimento deveria ser o seguinte: 

1. Colocar o beacon exatamente na posição A1, com orientação definida. 

<mark>2. Iniciar um ensaio com duração fxa, por exemplo</mark> **<mark>60 s</mark>** <mark>.</mark> 

3. Durante esse período, registar continuamente todas as deteções dos três nós ESP32, incluindo RSSI e timestamp. 

<mark>4. Terminado o ensaio, interromper a recolha durante alguns segundos.</mark> 

<mark>5. Retrar o beacon da posição e voltar a colocá-lo em A1.</mark> 

<mark>6. Iniciar uma nova recolha de 60 s.</mark> 

<mark>7. Repetr este procedimento, por exemplo,</mark> **<mark>5 vezes</mark>** <mark>.</mark> 

Assim, para a posição A1 teríamos: 

|**Posiçã**<br>**o**|**Repetção**|**Duração**|
|---|---|---|
|A1|R1|60 s|
|A1|R2|60 s|
|A1|R3|60 s|
|A1|R4|60 s|
|A1|R5|60 s|



<mark>O mesmo procedimento seria repetido para A2, A3, A4, B1, B2, etc.</mark> 

A parte importante é que as cinco repetições devem ser tratadas como **ensaios independentes** , e não como uma única recolha de 300 s dividida posteriormente em cinco partes. Entre repetições, é conveniente retirar e voltar a colocar o beacon, porque pequenas diferenças de posição e orientação fazem parte da variabilidade real que se pretende captar. 

Dentro de um determinado conjunto de ensaios, deverão permanecer constantes: 

- posição nominal do beacon; 

- <mark>altura do beacon;</mark> 

- <mark>orientação defnida, se esta não estver a ser estudada;</mark> 

- <mark>posição dos ESP32;</mark> 

- <mark>potência de transmissão do beacon;</mark> 

- <mark>intervalo de advertsing;</mark> 

- <mark>duração e intervalo dos scans;</mark> 

- <mark>parâmetros dos algoritmos de localização.</mark> 

Isto permite atribuir as diferenças observadas essencialmente à variabilidade natural do canal BLE. 

Não é necessário tentar criar condições laboratoriais demasiado artificiais. Podem existir pequenas variações como: 

- pessoas a passar no corredor; 

- <mark>alterações normais do ambiente radioelétrico;</mark> 

- <mark>pequenas diferenças na colocação do beacon;</mark> 

- <mark>tráfego Wi-Fi normal.</mark> 

Estas variações são úteis porque aproximam os testes do ambiente real de utilização. 

Para analisar as repetições, o mais correto será primeiro calcular as métricas separadamente para cada repetição **.** 

Por exemplo: 

|**Repetção**|**Accurac**|**Falsas mudanças**|
|---|---|---|
||**y**||
|R1|96,2%|1|
|R2|94,8%|2|
|R3|97,1%|0|
|R4|95,5%|1|
|R5|96,7%|1|



<mark>Só depois deverão ser resumidos os cinco resultados, por exemplo:</mark> 

- accuracy média: **96,1%** ; 

- <mark>desvio-padrão:</mark> **<mark>0,9%</mark>** <mark>;</mark> 

- <mark>falsas mudanças:</mark> **<mark>1,0 ± 0,7 por ensaio</mark>** <mark>.</mark> 

Isto permite dizer não só que o algoritmo teve cerca de 96% de exatidão, mas também que esse resultado foi **reproduzível entre ensaios** . 

Para os testes dinâmicos o princípio deverá ser semelhante. 

Se o percurso for: 

```
Sala A → corredor → Sala B
```

não se deve realizar o trajeto apenas uma vez. Por exemplo: 

- 10 percursos A → B; 

- <mark>10 percursos B → A.</mark> 

<mark>Cada percurso constitui uma repetição independente.</mark> 

Em cada repetição deverão ser registados: 

- instante real de saída da Sala A; 

- <mark>instante de entrada no corredor;</mark> 

- <mark>instante de entrada na Sala B;</mark> 

- <mark>instante em que cada algoritmo alterou a localização;</mark> 

- <mark>eventuais falsas transições intermédias.</mark> 

Depois, por exemplo, a latência poderá ser: 

|**Repetção**|**Latência**|
|---|---|
|R1|4,8 s|
|R2|5,3 s|
|R3|4,1 s|
|...|...|
|R10|5,0 s|



<mark>A partir destas dez observações calcula-se a</mark> **<mark>mediana, IQR, p95</mark>** <mark>, etc.</mark> 

Usar 5 repetições por posição nos testes estáticos e 10 repetições por percurso e por sentido nos testes dinâmicos. 

O ponto fundamental é que a **unidade experimental deve ser a repetição** , e não cada pacote BLE recebido. Se num ensaio de 60 s forem recolhidas centenas de amostras de RSSI, essas centenas de amostras não representam centenas de experiências independentes. Esta distinção é importante para evitar uma análise estatística artificialmente otimista. 

Nos testes dinâmicos, o beacon foi deslocado ao longo de percursos previamente definidos entre salas e corredor. O instante correspondente à entrada efetiva numa nova zona foi registado como referência ( _ground truth_ ) e comparado com o instante em que cada estratégia confirma a mudança de localização. 

Os percursos foram executados nos dois sentidos e repetidos várias vezes, mantendo condições semelhantes de velocidade de deslocação e transporte do beacon. 

Para garantir uma comparação justa, todas as estratégias de localização foram avaliadas sobre os mesmos dados experimentais. As deteções brutas de RSSI foram armazenadas e posteriormente processadas por cada estratégia, evitando que pequenas diferenças entre ensaios influenciem diretamente a comparação dos algoritmos. Esta abordagem 

permite também testar diferentes combinações de parâmetros sem necessidade de repetir toda a recolha experimental. 

Para cada ensaio foi mantido um registo contendo o identificador do teste, o cenário, a localização real, o beacon utilizado, os nós ESP32 ativos, os parâmetros de configuração, os timestamps das deteções e as localizações estimadas. Os resultados foram exportados para um formato CSV, e processados através de scripts que permitam calcular automaticamente as métricas definidas na secção seguinte. 

Antes da realização dos ensaios definitivos foram efetuados testes preliminares para verificar o correto funcionamento da infraestrutura, identificar problemas de cobertura e ajustar os parâmetros experimentais. Após esta fase, os valores selecionados foram mantidos constantes durante os ensaios comparativos, salvo nos testes especificamente destinados a estudar a influência de um determinado parâmetro. 

### **4.5. Métricas** 

A avaliação das estratégias de localização foram realizadas através de um conjunto de métricas destinadas a caracterizar não apenas a exatidão da localização, mas também a estabilidade das decisões e a rapidez com que o sistema reage a mudanças reais de zona. As métricas foram calculadas a partir da comparação entre a localização real do beacon, definida no protocolo experimental, e a localização estimada por cada estratégia. Os resultados serão analisados globalmente e por cenário de teste, permitindo identificar diferenças de comportamento entre situações estáticas, zonas de fronteira e movimentos entre salas. 

#### **4.5.1. Exatidão da localização** 

A exatidão da localização foi utilizada para avaliar a capacidade de cada estratégia em identificar corretamente a zona onde o beacon se encontra. Para cada instante ou janela de observação, a localização estimada pelo sistema foi comparada com a localização real definida no protocolo experimental. A métrica foi expressa como a percentagem de observações em que a zona estimada coincide com a zona real. A análise foi realizada globalmente e também separadamente por cenário de teste, permitindo identificar diferenças de desempenho entre o centro das salas, zonas próximas de paredes, portas, corredores e situações de movimento. 

#### **4.5.2. Falsas mudanças de localização** 

Esta métrica permitiu quantificar as situações em que o sistema indica uma mudança de zona que não corresponde a um movimento real do beacon. Uma falsa mudança foi considerada sempre que a localização estimada transite para outra sala ou zona enquanto o beacon permanece na mesma localização real. Os resultados foram apresentados através do número total de falsas mudanças, da média por ensaio ou da taxa de falsas mudanças por unidade de tempo. Esta métrica é particularmente relevante para avaliar o efeito da histerese e da persistência na redução de oscilações provocadas por variações do RSSI e pela sobreposição das áreas de cobertura dos nós ESP32. 

#### **4.5.3. Movimentos não detetados** 

Os movimentos não detetados correspondem às situações em que ocorre uma mudança real de zona, mas o sistema não confirma corretamente essa transição dentro de um intervalo de tempo considerado aceitável. Para cada percurso foi comparada a sequência real de zonas atravessadas com a sequência de localizações estimadas. A métrica foi expressa pelo número ou percentagem de transições reais que não foram identificadas. Esta análise permite verificar se estratégias mais conservadoras, apesar de reduzirem falsas mudanças, podem tornar o sistema demasiado resistente à atualização da localização. 

#### **4.5.4. Latência de confirmação da mudança** 

A latência de confirmação foi definida como o intervalo de tempo entre o instante em que o beacon entra efetivamente numa nova zona e o instante em que o sistema confirma essa nova localização. Esta métrica foi calculada para cada transição realizada nos testes dinâmicos. Os resultados são apresentados através da mediana, dos quartis e de percentis elevados, como o percentil 95, permitindo caracterizar não apenas o comportamento típico, mas também os casos menos favoráveis. A comparação desta métrica entre estratégias é importante para avaliar o compromisso entre estabilidade da localização e rapidez de resposta. 

#### **4.5.5. Tempo em estado de transição ou desconhecido** 

Esta métrica permitiu avaliar a proporção do tempo em que o sistema não apresenta uma localização confirmada, permanecendo num estado de transição ou de localização desconhecida. Estes estados podem surgir quando as deteções recebidas de diferentes nós são demasiado semelhantes, quando ainda não foi cumprido o critério de persistência ou quando o beacon deixa temporariamente de ser detetado. O valor é expresso como percentagem do tempo total de observação. Esta métrica permite avaliar até que ponto o aumento da robustez da decisão é conseguido à custa de períodos mais longos sem uma localização confirmada. 

#### **4.5.6. Matriz de confusão por zona** 

Como complemento à exatidão global, foi construída uma matriz de confusão entre a localização real e a localização estimada. Esta representação permite identificar quais as zonas que são mais frequentemente confundidas entre si e perceber se os erros se concentram, por exemplo, entre salas adjacentes e corredores. A matriz de confusão é particularmente útil para analisar os cenários de fronteira, nos quais a exatidão global poderá esconder padrões específicos de erro. 

#### **4.5.7. Estabilidade da localização** 

A estabilidade permitiu avaliar a frequência com que a localização estimada varia durante períodos em que o beacon permanece parado. Para cada teste estático foi contabilizado o número de alterações da localização estimada ao longo do tempo. 

O resultado foi expresso como número de alterações por minuto ou por ensaio? 

Esta métrica complementa a análise das falsas mudanças e ajudará a perceber se uma determinada estratégia produz uma localização consistente ou apresenta oscilações frequentes entre zonas adjacentes. 

As secções seguintes apresentam um exemplo de texto-base com **dados fictícios** , pensado para demonstrar não só o tipo de conteúdo a incluir, mas também como interpretar os resultados. Os valores deverão naturalmente ser substituídos pelos obtidos nos ensaios reais e a interpretação dos resultados adaptada em conformidade. 

## **4.6. Comparação global das estratégias** 

Após a realização dos ensaios definidos anteriormente, foram comparadas quatro estratégias de localização: a estratégia de referência baseada no maior valor instantâneo de RSSI, a utilização da mediana do RSSI numa janela temporal de 5 s, a combinação da mediana com um mecanismo de histerese e, finalmente, uma estratégia que combina mediana, histerese e persistência temporal. A Tabela 4.X apresenta uma síntese dos principais resultados obtidos. 

|**Estratégia**|**Exatidã**<br>**o global**|**Falsas**<br>**mudanças/**<br>**h**|**Movimento**<br>**s não**<br>**detetados**|**Latênci**<br>**a**<br>**mediana**|**Latênci**<br>**a p95**|**Temp**<br>**o em**<br>**estado**<br>**incert**<br>**o**|
|---|---|---|---|---|---|---|
|Maior<br>RSSI<br>instantâneo|82,6%|13,8|0,0%|1,3 s|2,9 s|0,0%|
|Mediana<br>do RSSI (5<br>s)|91,7%|5,2|1,1%|3,3 s|5,7 s|2,0%|
|Mediana +<br>histerese|95,1%|1,9|2,0%|4,2 s|6,8 s|3,4%|
|Mediana +<br>histerese +<br>persistênci<br>a|97,0%|0,7|2,9%|6,1 s|9,2 s|5,6%|



Os resultados mostram uma melhoria progressiva da exatidão à medida que são introduzidos mecanismos de estabilização da localização. A estratégia baseada apenas no maior RSSI apresentou a menor exatidão, 82,6%, e o maior número de falsas mudanças, com uma média de 13,8 transições incorretas por hora. Este comportamento confirma a elevada sensibilidade da decisão baseada numa única observação às flutuações do sinal BLE. 

A utilização da mediana numa janela temporal de 5 s aumentou a exatidão para 91,7% e reduziu o número de falsas mudanças para 5,2 por hora. A introdução de histerese permitiu uma melhoria adicional, atingindo 95,1% de exatidão e apenas 1,9 falsas mudanças por hora. O melhor desempenho em termos de estabilidade foi obtido com a 

combinação de mediana, histerese e persistência, que apresentou 97,0% de exatidão e apenas 0,7 falsas mudanças por hora. 

Esta melhoria apresenta, contudo, um custo em termos de rapidez de resposta. A latência mediana aumentou de 1,3 s na estratégia de referência para 6,1 s na estratégia combinada. Verifica-se, assim, um compromisso entre estabilidade e rapidez: estratégias mais conservadoras reduzem falsas mudanças, mas necessitam de mais tempo para confirmar uma alteração real da localização. 

De forma global, os resultados indicam que a utilização direta do maior RSSI não oferece estabilidade suficiente para o contexto estudado. A estratégia combinada apresentou o melhor desempenho global em termos de exatidão e redução de falsas transições, enquanto a combinação de mediana e histerese apresentou um compromisso mais equilibrado quando a latência de atualização é um requisito importante. 

## **4.7. Resultados por cenário** 

A análise global foi complementada com uma avaliação separada dos diferentes cenários experimentais, uma vez que o desempenho do sistema pode variar significativamente em função da posição do beacon e da proximidade de áreas adjacentes. A Tabela 4.X apresenta a exatidão obtida em cada cenário. 

|**Cenário**|**Maior**<br>**RSSI**|**Mediana**|**Mediana +**<br>**histerese**|**Mediana + histerese +**<br>**persistência**|
|---|---|---|---|---|
|Centro das salas|96,5%|98,0%|98,6%|98,8%|
|Junto às paredes|84,0%|91,5%|95,0%|96,4%|
|Junto às portas|66,1%|81,0%|90,2%|94,5%|
|Corredor|76,8%|87,9%|92,8%|95,0%|
|Movimento entre<br>salas|78,1%|88,7%|93,5%|95,3%|



Os resultados mostram que as diferenças entre estratégias são reduzidas quando o beacon se encontra no centro das salas. Neste cenário, todos os métodos apresentaram uma exatidão superior a 96%, indicando que a localização é relativamente simples quando existe uma clara diferença entre o sinal recebido pelo nó da sala correta e os restantes nós. 

A situação altera-se significativamente nas zonas próximas das paredes e, sobretudo, junto às portas. Para a estratégia baseada no maior RSSI, a exatidão junto às portas diminuiu para 66,1%. A análise dos dados de RSSI mostrou que, nestas posições, o beacon era frequentemente detetado pelos nós das duas zonas adjacentes com valores semelhantes, originando alterações sucessivas da localização estimada. 

A utilização da mediana reduziu este efeito, aumentando a exatidão junto às portas para 81,0%. A introdução de histerese revelou-se particularmente eficaz neste cenário, permitindo alcançar 90,2%. Com a estratégia completa, a exatidão aumentou para 94,5%. 

No corredor foi observado um comportamento semelhante. Embora o ESP32 instalado nessa zona fosse normalmente o nó dominante, a proximidade das portas permitia que os nós instalados nas salas recebessem sinais com intensidade comparável. A utilização dos mecanismos de estabilização reduziu substancialmente estas classificações incorretas. 

A matriz de confusão apresentada na Tabela 4.X permite analisar em maior detalhe os erros observados para a estratégia combinada. 

|**Localização real / estimada**|**Sala A**|**Corredor**|**Sala B**|**Desconhecida**|
|---|---|---|---|---|
|Sala A|96,8%|1,9%|0,4%|0,9%|
|Corredor|3,8%|92,7%|2,7%|0,8%|
|Sala B|0,5%|2,1%|96,6%|0,8%|



Verifica-se que os erros ocorrem predominantemente entre zonas fisicamente adjacentes. Não foram observadas classificações significativas diretamente entre a Sala A e a Sala B, enquanto a maior parte dos erros correspondeu a confusões entre uma sala e o corredor. 

Estes resultados indicam que o principal desafio do sistema não se encontra na localização no interior das salas, mas nas zonas de transição e de sobreposição da cobertura BLE. Assim, as melhorias introduzidas são particularmente relevantes precisamente nas condições em que a estratégia original apresenta maior instabilidade. 

## **4.8. Influência dos parâmetros** 

Para avaliar a influência dos principais parâmetros da estratégia de localização, foram realizados ensaios adicionais variando o tamanho da janela temporal, a margem de histerese e o critério de persistência. O objetivo foi identificar valores que proporcionassem um compromisso adequado entre exatidão, estabilidade e latência. 

### **Influência do tamanho da janela temporal** 

A Tabela 4.X apresenta os resultados obtidos para diferentes tamanhos de janela utilizados no cálculo da mediana do RSSI. 

|**Janel**|**Exatidão**|**Falsas mudanças/h**|**Latência mediana**|
|---|---|---|---|
|**a**||||
|1 s|87,1%|10,5|1,5 s|
|3 s|93,6%|4,1|2,8 s|
|5 s|96,0%|1,8|4,3 s|
|8 s|96,9%|0,9|7,0 s|
|10 s|97,1%|0,7|8,8 s|



O aumento da janela temporal produziu uma melhoria clara entre 1 s e 5 s. A exatidão aumentou de 87,1% para 96,0%, enquanto o número de falsas mudanças diminuiu de 10,5 para 1,8 por hora. Para janelas superiores a 5 s, os ganhos foram bastante menores. 

Entre 5 s e 10 s, a exatidão aumentou apenas 1,1 pontos percentuais, enquanto a latência mediana passou de 4,3 s para 8,8 s. 

Estes resultados sugerem que uma janela de aproximadamente 5 s constitui um compromisso adequado para o ambiente estudado, uma vez que janelas maiores introduzem atrasos significativos sem uma melhoria proporcional da exatidão. 

### **Influência da histerese** 

Foram também testadas diferentes margens de histerese, definidas como a diferença mínima de RSSI exigida para que um novo nó possa substituir o nó associado à localização atual. 

|**Histeres**<br>**e**|**Exatidão**|**Falsas mudanças/h**|**Latência mediana**|
|---|---|---|---|
|0 dB|91,7%|5,2|3,3 s|
|3 dB|94,1%|2,9|3,7 s|
|5 dB|95,1%|1,9|4,2 s|
|8 dB|95,4%|1,2|5,6 s|
|10 dB|94,8%|0,9|7,1 s|



A introdução de uma pequena margem de histerese reduziu significativamente as falsas mudanças. O valor de 5 dB apresentou um bom compromisso, com 95,1% de exatidão e uma latência mediana de 4,2 s. Valores superiores reduziram ligeiramente as falsas mudanças, mas aumentaram a latência e começaram a dificultar a confirmação de algumas transições reais. 

### **Influência da persistência** 

Por último, foi estudado o número de observações consecutivas necessário para confirmar uma nova localização. 

|**Confirmações**<br>**consecutivas**|**Exatidão**|**Falsas**<br>**mudanças/h**|**Movimentos não**<br>**detetados**|**Latência**<br>**mediana**|
|---|---|---|---|---|
|1|95,1%|1,9|2,0%|4,2 s|
|2|96,3%|1,1|2,3%|5,1 s|
|3|97,0%|0,7|2,9%|6,1 s|
|5|97,2%|0,4|5,8%|9,0 s|



Os resultados mostram que exigir três confirmações consecutivas reduz de forma significativa as falsas mudanças sem aumentar excessivamente a latência. O aumento para cinco confirmações apresentou ganhos reduzidos na exatidão e na estabilidade, mas quase duplicou a percentagem de movimentos não detetados e aumentou a latência para 9,0 s. 

Com base nestes ensaios, a configuração selecionada para o sistema foi uma janela temporal de 5 s, uma margem de histerese de 5 dB e três confirmações consecutivas. Esta configuração apresentou o melhor compromisso global entre exatidão, estabilidade e rapidez de resposta nas condições experimentais consideradas. 

## **4.9. Análise estatística** 

Para avaliar se as diferenças observadas entre as estratégias eram consistentes entre as várias repetições e não resultavam apenas da variabilidade natural do sinal BLE, foi realizada uma análise estatística dos principais indicadores de desempenho. Cada cenário foi repetido dez vezes, sendo todas as estratégias aplicadas aos mesmos conjuntos de dados de RSSI, o que permitiu realizar uma comparação emparelhada entre os métodos. 

A Tabela 4.X apresenta a média e o desvio-padrão da exatidão obtida nas dez repetições. 

|**Estratégia**|**Exatidão média**|**Desvio-padrão**|
|---|---|---|
|Maior RSSI|82,6%|4,7%|
|Mediana|91,7%|3,2%|
|Mediana+histerese|95,1%|2,3%|
|Estratégia combinada|97,0%|1,6%|



Além de apresentar a maior exatidão média, a estratégia combinada apresentou também o menor desvio-padrão, indicando um comportamento mais consistente entre repetições. 

Uma vez que os resultados não apresentaram uma distribuição aproximadamente normal em todos os métodos, foi utilizado o teste de Friedman para comparar simultaneamente as quatro estratégias. O teste revelou diferenças estatisticamente significativas entre os métodos para a exatidão da localização ((p < 0,001)) e para o número de falsas mudanças ((p < 0,001)). 

Posteriormente, foram realizadas comparações emparelhadas entre estratégias utilizando o teste de Wilcoxon. A comparação entre o maior RSSI e a estratégia combinada revelou uma melhoria estatisticamente significativa da exatidão ((p = 0,002)). Também foi observada uma redução significativa do número de falsas mudanças ((p = 0,002)). 

A comparação entre a estratégia baseada em mediana e histerese e a estratégia combinada revelou uma diferença menor na exatidão, de 95,1% para 97,0%, mas ainda consistente entre as repetições. Por outro lado, a introdução de persistência provocou um aumento significativo da latência de confirmação, de uma mediana de 4,2 s para 6,1 s. 

Estes resultados mostram que a maior estabilidade da estratégia combinada não resulta apenas de alguns ensaios isolados. Contudo, a análise estatística deve ser interpretada em conjunto com a relevância prática das diferenças observadas. Embora o aumento de aproximadamente dois pontos percentuais na exatidão entre as duas estratégias mais avançadas seja relativamente reduzido, a diminuição das falsas mudanças pode ser operacionalmente relevante num RTLS hospitalar, uma vez que cada falsa transição poderá originar uma atualização incorreta da localização num sistema externo. 

Assim, a análise estatística confirma a existência de diferenças consistentes entre as estratégias, mas a seleção da configuração mais adequada deverá considerar simultaneamente a significância estatística, a magnitude das diferenças e os requisitos operacionais do sistema. 

### **4.10. Discussão dos resultados** 

Esta secção deverá responder diretamente às RQ. 

Não deverá simplesmente repetir os números. 

Deverá explicar: 

- porque determinado método funcionou melhor; 

- em que situações falhou; 

- relação entre estabilidade e latência; 

- configuração recomendada; 

- significado dos resultados para o Hospital. 

# **5. Conclusões e Trabalho Futuro** 

#### **Texto introdutório sugerido** 

“Este capítulo apresenta as principais conclusões do estágio, avaliando o cumprimento dos objetivos inicialmente definidos e sintetizando os resultados obtidos na comparação das estratégias de localização. São identificadas as principais contribuições para a evolução do sistema RTLS existente, discutidas as limitações do estudo e apresentadas possíveis linhas de trabalho futuro que poderão permitir melhorar a fiabilidade, a robustez e a escalabilidade da solução.2 

### **5.1. Síntese do trabalho realizado** 

Resumo breve: 

- sistema anterior estudado; 

- sistema adaptado; 

- algoritmos implementados; 

- testes realizados. 

### **5.2. Principais resultados** 

Apresentar apenas as conclusões mais relevantes. 

Por exemplo: 

- filtragem temporal melhora a estabilidade; 

- histerese reduz falsas transições; 

- persistência aumenta robustez mas também latência; 

- método X oferece melhor compromisso. 

### **5.3. Contributos do estágio** 

Destacar três níveis: 

#### **Contributo técnico** 

- melhoria do algoritmo de localização. 

#### **Contributo experimental** 

- metodologia de avaliação reproduzível. 

#### **Contributo para a ULS** 

- identificação de uma estratégia recomendada para evolução do protótipo. 

### **5.4. Limitações** 

Por exemplo: 

- número limitado de salas; 

- número de nós; 

- ambiente específico; 

- número de beacons; 

- influência do corpo humano; 

- diversidade limitada dos cenários; 

- duração dos testes. 

### **5.5. Trabalho futuro** 

Aqui poderão reaparecer algumas melhorias que deliberadamente ficaram fora do estágio: 

- mais nós; 

- mais áreas do Hospital; 

- calibração automática; 

- fingerprinting; 

- machine learning; 

- MQTT; 

- tolerância a falhas; 

- buffering; 

- segurança; 

- monitorização da infraestrutura; 

- integração hospitalar mais avançada. 

