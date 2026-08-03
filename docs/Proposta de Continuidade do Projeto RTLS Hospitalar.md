# Proposta de continuidade do projeto “A BLE-Based Real-Time Location System with RESTful Integration for Healthcare Applications” 

## 1. Enquadramento e estado atual do projeto 

O projeto “A BLE-Based Real-Time Location System with RESTful Integration for Healthcare Applications“, realizado em contexto de estágio por Bella Gnan no Hospital Sousa Martins, da ULS da Guarda, teve como objetivo desenvolver um protótipo de sistema de localização em tempo real, ou RTLS, para apoiar a localização de doentes e equipamentos móveis no interior do hospital. 

A solução desenvolvida baseia-se nos seguintes componentes: 

- beacons Bluetooth Low Energy associados a doentes ou equipamentos; 

- nós ESP32 instalados nas salas, responsáveis por detetar os beacons; 

- comunicação dos nós ESP32 com um backend através da rede Wi-Fi; 

- backend desenvolvido em Python e Flask; 

- base de dados MongoDB para guardar a localização atual e o histórico de movimentos; 

- dashboard web desenvolvido em React; 

- integração com o Mirth Connect para encaminhamento dos eventos de localização para outros sistemas hospitalares. 

A arquitetura adotada é modular e separa adequadamente: 

1. a deteção dos dispositivos; 

2. o processamento e armazenamento dos dados; 

3. a visualização dos resultados; 

4. a integração com os sistemas hospitalares. 

O protótipo implementa as funcionalidades fundamentais: 

- deteção periódica de dispositivos BLE; 

- identificação dos beacons relevantes através de uma whitelist; 

- associação de cada nó ESP32 a uma sala; 

- determinação da localização atual de cada beacon; 

- armazenamento do histórico de movimentos; 

- geração de eventos quando é detetada uma mudança de sala; 

- apresentação dos dados num dashboard; 

- envio de eventos para o Mirth Connect. 

O trabalho permitiu demonstrar a viabilidade geral da solução e produzir um protótipo funcional. Contudo, a avaliação realizada teve uma escala muito reduzida. Foram utilizados apenas dois nós ESP32 e um número limitado de beacons, em condições controladas e durante períodos curtos. Assim, os resultados devem ser interpretados como uma demonstração de conceito e não como uma validação suficiente para utilização operacional num hospital. 

## 2. Principais limitações identificadas 

### 2.1. Escala reduzida da implementação 

A implementação foi testada apenas com dois nós ESP32 e três beacons. Esta configuração não permite avaliar adequadamente: 

- o comportamento do sistema com dezenas de salas; 

- a existência de vários beacons simultaneamente na mesma área; 

- a sobreposição da cobertura de vários nós; 

- o aumento da carga no backend e na base de dados; 

- a utilização simultânea do dashboard por vários utilizadores; 

- a capacidade de integração com diferentes serviços hospitalares. 

O número reduzido de componentes também torna difícil identificar problemas que apenas aparecem em sistemas distribuídos de maior dimensão. 

### 2.2. Localização baseada numa única deteção 

A localização é, essencialmente, determinada pelo nó ESP32 que comunica a deteção do beacon. Esta abordagem funciona em condições simples, mas pode produzir resultados incorretos quando o mesmo beacon é detetado simultaneamente em duas ou mais salas. 

Não existe ainda uma estratégia suficientemente robusta para decidir a sala mais provável com base em fatores como: 

- intensidade do sinal; 

- persistência da deteção; 

- histórico recente; 

- diferença de RSSI entre recetores; 

- número de deteções consecutivas; 

- posição física dos nós; 

- características das paredes e portas. 

Consequentemente, um beacon localizado próximo de uma porta ou de uma parede divisória pode parecer alternar repetidamente entre duas salas. 

### 2.3. Utilização direta e pouco tratada do RSSI 

O RSSI é uma medida instável e bastante sensível ao ambiente. Pode variar devido a: 

- orientação do beacon; 

- presença do corpo humano; 

- abertura ou fecho de portas; 

- mobiliário e equipamentos metálicos; 

- interferência de redes Wi-Fi; 

- movimento de pessoas; 

- reflexões e propagação por múltiplos caminhos; 

- posição e altura dos recetores. 

O protótipo utiliza sobretudo um limiar de RSSI. Esta abordagem é insuficiente para uma solução robusta. 

### 2.4. Ausência de avaliação de zonas de fronteira 

Os testes apresentados mostram a deslocação de um beacon entre duas salas, mas não caracterizam o comportamento do sistema nas zonas mais problemáticas: 

- portas; 

- corredores; 

- salas adjacentes; 

- salas separadas por divisórias leves; 

- áreas com cobertura sobreposta; 

- zonas com vários nós visíveis simultaneamente. 

Estas são precisamente as condições em que ocorrem mais falsos movimentos. 

### 2.5. Robustez e tolerância a falhas insuficientes 

Os nós ESP32 não mantêm uma fila persistente de mensagens. Se o backend ou a rede estiverem indisponíveis, as deteções desse período podem perder-se. 

O mesmo acontece no envio de eventos ao Mirth Connect. Caso o Mirth Connect esteja indisponível no momento da mudança de sala, não existe uma garantia de que o evento seja posteriormente reenviado. 

Também não foram suficientemente estudados: 

- reinício dos nós ESP32; 

- reinício do backend; 

- indisponibilidade temporária da base de dados; 

- perda de ligação Wi-Fi; 

- falhas do Mirth Connect; 

- duplicação de mensagens; 

- mensagens recebidas fora de ordem; 

- sincronização temporal entre dispositivos. 

### 2.6. Segurança adequada apenas a um protótipo 

O mecanismo de autenticação utilizado é demasiado simples para um ambiente hospitalar. A utilização de um cabeçalho com o nome do utilizador não corresponde a um sistema de autenticação seguro. 

Entre os aspetos que necessitam de melhoria encontram-se: 

- autenticação baseada em tokens ou em sessões seguras; 

- armazenamento seguro das palavras-passe; 

- controlo de acessos baseado em funções; 

- utilização de HTTPS; 

- autenticação dos próprios nós ESP32; 

- gestão segura das credenciais Wi-Fi; 

- proteção contra pedidos falsificados; 

- auditoria das operações administrativas; 

- registo de acessos; 

- integração com os mecanismos de identidade existentes no hospital. 

### 2.7. Monitorização operacional limitada 

O sistema não possui mecanismos suficientemente desenvolvidos para identificar: 

- nós ESP32 que deixaram de comunicar; 

- beacons que desapareceram; 

- beacons com bateria fraca; 

- atrasos anormais no envio de mensagens; 

- aumento da taxa de erros; 

- falhas no Mirth Connect; 

- crescimento excessivo da base de dados; 

- degradação do desempenho. 

Num sistema real, seria necessário um painel de estado técnico da infraestrutura e não apenas um painel de localização. 

### 2.8. Validação experimental pouco sistemática 

As medições de latência foram essencialmente manuais e realizadas durante períodos reduzidos. A afirmação de uma fiabilidade de 100% não é suficientemente sustentada por um protocolo experimental detalhado. 

Não são apresentados, de forma suficientemente clara: 

- número de ensaios; 

- duração dos ensaios; 

- número total de mensagens; 

- número de movimentos realizados; 

- distribuição das latências; 

- percentis de latência; 

- critérios usados para definir uma deteção correta; 

- taxa de falsos movimentos; 

- condições da rede; 

- carga do backend; 

- perdas e repetições de mensagens. 

## 3. Sugestão de melhoramentos técnicos 

Os melhoramentos técnicos apresentados nas secções seguintes resultam das limitações identificadas no protótipo atual e das possibilidades de evolução consideradas para uma nova fase do projeto. As propostas abrangem diferentes níveis de intervenção, desde melhorias essenciais na fiabilidade, estabilidade e robustez do sistema até extensões mais avançadas relacionadas com a escalabilidade, a segurança, a integração com outros sistemas e a monitorização da infraestrutura. 

Sugere-se que a prioridade do novo estágio não seja a simples introdução de novas funcionalidades visuais ou a integração de tecnologias adicionais. O principal objetivo deveria consistir em transformar a solução BLE já demonstrada num mecanismo de localização ao nível da sala que seja mensurável, estável e capaz de funcionar de forma fiável em condições reais. Assim, a questão central do estágio deverria incidir na fiabilidade da localização, e não apenas na expansão funcional do protótipo. 

A seleção dos melhoramentos a implementar deverá ser realizada em articulação com a equipa da ULS da Guarda, tendo em conta as necessidades e prioridades concretas do Hospital, os recursos técnicos e materiais que possam ser disponibilizados e a duração prevista para o estágio. Não se pressupõe, por isso, que todas as propostas apresentadas sejam incluídas no plano de trabalho. Sugere-se que seja estabelecida uma priorização clara entre objetivos essenciais, melhorias desejáveis e possíveis extensões, de modo a definir um âmbito de trabalho realista, coerente e exequível. 

### 3.1. Nós ESP32 e instalação física 

Os protótipos deveriam evoluir para unidades instaláveis em ambiente hospitalar. 

Cada nó deverá incluir caracteristicas como: 

- caixa de proteção; 

- alimentação elétrica segura; 

- fixação adequada à parede; 

- indicador visual de funcionamento; 

- possibilidade de reinício; 

- identificação física do nó; 

- proteção contra desconexão acidental; 

- gestão adequada da fonte de alimentação de 230 V para 5 V. 

Poderá ser considerada uma caixa do tipo adaptador de tomada, desde que sejam avaliados: 

- segurança elétrica; 

- dissipação térmica; 

- interferência causada pela proximidade da fonte; 

- facilidade de manutenção; 

Cada nó deveria possuir uma configuração centralizada, evitando a necessidade de recompilar o firmware para alterar parâmetros como: 

- identificador do nó; 

- nome da sala; 

- endereço do backend; 

- duração do scan; 

- intervalo entre scans; 

- limiar de RSSI; 

- credenciais de acesso; 

- potência e parâmetros de comunicação. 

Se possível, estas configurações deveriam ser obtidas a partir do backend ou de um ficheiro de configuração seguro. 

### 3.2. Algoritmo de decisão de localização 

Este é um dos melhoramentos mais importantes. 

O sistema não deverá decidir imediatamente que ocorreu uma mudança de sala com base numa única deteção. A localização deverá resultar de uma combinação de observações realizadas durante uma janela temporal. 

Sugere-se que sejam implementados e comparados vários métodos. 

#### Método A — Maior RSSI 

O beacon é associado ao nó que apresenta o maior RSSI. 

É simples, mas pode ser instável. 

#### Método B — Média ou mediana numa janela temporal 

Para cada beacon, são consideradas as deteções dos últimos segundos. A localização é atribuída ao nó que apresenta a maior mediana ou média filtrada do RSSI. 

A mediana poderá ser preferível por ser menos sensível a valores extremos. 

#### Método C — Histerese 

A mudança de sala só é aceite se o novo nó apresentar um RSSI superior ao nó atual por uma margem mínima, por exemplo: 

RSSInovo > RSSIatual + H 

em que (H) representa uma margem de histerese. 

#### Método D — Persistência temporal 

A mudança só é aceite depois de o novo nó ser dominante durante um número mínimo de scans consecutivos ou durante determinado período. 

Por exemplo: 

- novo nó dominante durante três scans consecutivos; ou 

- domínio mantido durante cinco segundos. 

#### Método E — Pontuação combinada 

Poderá ser calculada uma pontuação com base em: 

- RSSI médio; 

- número de deteções; 

- duração da deteção; 

- diferença relativamente ao segundo melhor nó; 

- localização anterior; 

- tempo desde a última mudança. 

Esta abordagem deverá reduzir falsas alternâncias entre salas. 

### 3.3. Estados explícitos de localização 

Além das salas, o sistema deveria suportar estados como: 

- localização desconhecida; 

- beacon inativo; 

- zona de transição; 

- deteção ambígua; 

- comunicação perdida; 

- beacon detetado por vários nós; 

- localização ainda não confirmada. 

É preferível indicar que a localização é incerta do que apresentar uma sala errada. 

### 3.4. Sincronização temporal 

Os nós ESP32 e o backend deveriam usar uma referência temporal consistente, preferencialmente através de NTP. 

Cada mensagem deverá incluir: 

- instante da deteção; 

- instante do envio; 

- instante da receção no backend; 

- número de sequência; 

- identificador do lote. 

Isto permitirá: 

- medir corretamente a latência; 

- detetar mensagens atrasadas; 

- identificar mensagens duplicadas; 

- ordenar eventos; 

- analisar falhas de comunicação. 

### 3.5. Armazenamento temporário nos nós 

Os nós deveriam guardar temporariamente as mensagens quando a rede ou o backend estiverem indisponíveis. 

Uma solução simples poderá usar: 

- uma fila circular em memória; 

- armazenamento em flash para interrupções mais prolongadas; 

- números de sequência; 

- confirmação de receção pelo backend; 

- reenvio com limite de tentativas. 

Deverá evitar-se que o sistema envie indefinidamente mensagens antigas. Poderá ser definida uma idade máxima para os dados armazenados. 

### 3.6. Comunicação mais robusta 

A comunicação HTTP poderá ser mantida, mas deveria ser melhorada com: 

- autenticação do nó; 

- HTTPS; 

- timeouts; 

- confirmação explícita; 

- reenvio; 

- backoff exponencial; 

- identificação de mensagens duplicadas; 

- códigos de erro claros. 

Como alternativa, poderá ser comparada com MQTT, que possui funcionalidades úteis para sistemas IoT, como: 

- qualidade de serviço; 

- persistência de sessão; 

- mensagens retidas; 

- identificação de clientes; 

- last will; 

- desacoplamento entre produtores e consumidores. 

A substituição por MQTT não deverá, contudo, ser assumida sem avaliação. Poderá constituir uma questão técnica do novo estágio: comparar a robustez de HTTP e MQTT para este caso de utilização. 

### 3.7. Backend e base de dados 

O backend deveria deixar de utilizar o servidor de desenvolvimento do Flask e passar a ser executado através de uma configuração mais próxima de produção, por exemplo: 

- Gunicorn ou outro servidor WSGI; 

- proxy inverso; 

- Docker; 

- configuração separada para desenvolvimento e produção; 

- variáveis de ambiente; 

- logging estruturado. 

Na base de dados deverão ser definidos índices adequados, nomeadamente para: 

- identificador do beacon; 

- timestamp; 

- nó ESP32; 

- sala; 

- estado ativo; 

- combinação beacon–timestamp. 

Deveria também ser definida uma política de retenção para os dados de diagnóstico e para as deteções não relevantes. 

### 3.8. Fila de eventos para o Mirth Connect 

O envio ao Mirth Connect não deveria depender exclusivamente de uma chamada HTTP imediata. 

Sugere-se a criação de uma fila persistente de eventos com estados como: 

- criado; 

- por enviar; 

- enviado; 

- confirmado; 

- falhou; 

- em nova tentativa. 

Cada evento deverá ter um identificador único para permitir processamento idempotente. 

Se o Mirth Connect estiver indisponível, o backend deverá manter os eventos e tentar reenviá-los posteriormente. 

### 3.9. Integração hospitalar 

A continuação do projeto deverá clarificar o modelo de integração com os sistemas da ULS da Guarda. 

Importa definir: 

- que sistema associa o beacon ao doente ou equipamento; 

- que sistema é responsável pela localização oficial; 

- que informação deve constar do evento; 

- como é efetuada a associação entre identificadores; 

- qual o formato esperado pelo Mirth Connect; 

- que eventos devem originar atualizações; 

- como são corrigidas localizações erradas; 

- como é tratado o desaparecimento de um beacon; 

- como é registada a devolução ou desassociação de um beacon. 

A adoção direta de FHIR não deve ser obrigatória sem que exista um caso de utilização concreto. O Mirth Connect poderá continuar a receber eventos JSON e efetuar as transformações necessárias para HL7 ou FHIR. 

### 3.10. Segurança 

O novo estágio deverá implementar, pelo menos: 

- autenticação segura dos utilizadores; 

- palavras-passe armazenadas com hashing adequado; 

- tokens de acesso com validade limitada; 

- separação entre administradores e utilizadores de consulta; 

- HTTPS; 

- autenticação dos nós ESP32; 

- registo das alterações à whitelist e às salas; 

- proteção de endpoints administrativos; 

- validação rigorosa dos dados recebidos; 

- limitação da taxa de pedidos; 

- gestão de segredos através de variáveis de ambiente; 

- registo de eventos de segurança. 

A associação entre beacon e pessoa deverá permanecer fora do protótipo ou ser efetuada apenas através de identificadores pseudonimizados. 

### 3.11. Dashboard 

O dashboard deverá evoluir de uma interface de demonstração para uma ferramenta operacional. 

Funcionalidades recomendadas: 

- estado online ou offline de cada nó; 

- hora da última comunicação; 

- taxa de deteções por nó; 

- número de beacons ativos; 

- indicação de localizações ambíguas; 

- alarmes de ausência prolongada; 

- histórico pesquisável; 

- filtros por sala, beacon e intervalo temporal; 

- representação gráfica dos movimentos; 

- exportação de dados; 

- gestão de utilizadores e perfis; 

- auditoria das alterações; 

- estado da integração com o Mirth Connect; 

- sinalização de eventos por enviar ou com erro. 

## 4. Melhoramentos na validação experimental 

### 4.1. Objetivo da nova avaliação 

A nova avaliação não deverá limitar-se a confirmar que o sistema funciona. Deverá responder a perguntas como: 

- Com que fiabilidade o sistema determina a sala correta? 

- Quantas falsas mudanças de sala são geradas? 

- Quanto tempo demora a confirmar uma mudança? 

- Como varia o desempenho junto de portas e paredes? 

- Qual é o impacto do número de nós e beacons? 

- Como reage o sistema a falhas de rede e serviços? 

- Que algoritmo de localização apresenta o melhor compromisso entre precisão e latência? 

### 4.2. Configuração mínima sugerida 

Para uma avaliação credível, recomenda-se, sempre que possível: 

- cinco nós ESP32; 

- entre cinco e dez beacons; 

- pelo menos três salas e um corredor; 

- duas salas adjacentes; 

- uma zona de porta; 

- vários posicionamentos dos nós; 

- execução durante vários dias. 

Caso o hospital não permita instalar cinco nós, poderá ser construída uma configuração experimental equivalente no laboratório, seguida de uma validação mais pequena no hospital. 

### 4.3. Avaliação experimental 

Sugere-se que os cenários de teste, as métricas a recolher, os critérios de sucesso e a forma de apresentação dos resultados sejam definidos após a definição da lista de melhoramentos e extensões a realizar e dos objetivos da nova avaliação referidos em 4.1 

Sugere-se que a componente de testes e análise de resultados assuma um peso significativo no novo estágio. No estágio anterior, esta parte ficou aquém do esperado, sobretudo devido ao tempo limitado disponível após a conclusão do desenvolvimento. 

Para evitar que a avaliação volte a ser realizada apenas na fase final, recomenda-se que a preparação dos testes seja iniciada em paralelo com o desenvolvimento, em coordenação com a supervisão e orientação do estágio, e que sejam reservados, exclusivamente para a execução dos ensaios, tratamento dos dados, análise e discussão dos resultados, cerca de 25% da duração total do estágio. 

## 5. Proposta de novo estágio 

Segue-se a sugestão da proposta do plano de trabalho do novo estágio, no formato dos formulários. Editar e validar a mesma com base na lista dos melhoramentos técnicos pretendidos que for definida. 

Designação do Projeto 

##### **Evolução e Validação de um Sistema RTLS Hospitalar Baseado em BLE e ESP32** 

Objetivos Previstos 

O projeto tem como objetivo dar continuidade a um protótipo de um sistema de localização em tempo real para aplicações hospitalares desenvolvido no âmbito de um estágio anterior, melhorando a fiabilidade da localização ao nível da sala, a robustez da comunicação, a segurança e a capacidade de monitorização do sistema. 

Pretende-se desenvolver e comparar métodos de tratamento das deteções BLE que reduzam falsas mudanças de sala e melhorem a estabilidade da localização, nomeadamente através da utilização de filtragem do RSSI, janelas temporais, histerese e confirmação da localização com base em várias deteções consecutivas. O projeto 

deverá ainda reforçar a tolerância a falhas e realizar uma avaliação experimental mais sistemática da solução. 

##### Resumo do Trabalho a Desenvolver 

O trabalho começará pela instalação, análise e reprodução do protótipo atualmente existente, constituído por beacons BLE, nós ESP32, backend Flask, base de dados MongoDB, dashboard React e integração com o Mirth Connect. 

Posteriormente, serão implementados melhoramentos nos mecanismos de decisão da localização, no tratamento de deteções simultâneas e na gestão de falhas de comunicação. Poderão também ser introduzidos mecanismos de armazenamento temporário e reenvio de mensagens, monitorização do estado dos nós e reforço da autenticação e do controlo de acessos. 

O projeto culminará com a realização de experiências que permitam avaliar a fiabilidade da localização, a latência, a ocorrência de falsos movimentos e o comportamento do sistema em diferentes condições de funcionamento. Os cenários de teste e as métricas serão definidos com base nas perguntas técnicas e científicas que se pretenda que a avaliação responda. 

Metodologia a Utilizar 

O projeto seguirá uma metodologia de desenvolvimento iterativa, combinando investigação aplicada, integração de sistemas e validação experimental. 

Numa fase inicial será analisado o sistema existente e definida a questão científica do projeto. Seguidamente, serão implementados e comparados diferentes métodos de decisão da localização. Após a integração das melhorias selecionadas, será realizada uma avaliação experimental estruturada, com recolha e análise de dados quantitativos. 

A componente de testes e análise de resultados deverá ser planeada desde o início e representar aproximadamente 25% a 30% da duração total do estágio **,** uma vez que esta componente ficou aquém do esperado no estágio anterior, nomeadamente devido ao tempo limitado disponível após a conclusão do desenvolvimento. 

Cronograma de Atividades 

##### **1.ª Etapa — Estudo e reprodução do sistema existente** 

Análise da arquitetura, instalação dos componentes, reprodução dos testes anteriores e definição da questão científica. 

##### **2.ª Etapa — Melhoria da localização** 

Implementação e comparação de algoritmos baseados em filtragem do RSSI, janelas temporais, histerese e persistência das deteções. 

##### **3.ª Etapa — Robustez e integração** 

Melhoria dos mecanismos de comunicação, tratamento de falhas, monitorização dos nós, segurança e integração com o Mirth Connect. 

##### **4.ª Etapa — Avaliação experimental e relatório** 

Realização dos testes, tratamento e análise dos resultados, discussão das limitações e redação do relatório final. 

Conclusões e Resultados Esperados 

Espera-se obter uma versão mais fiável e robusta do sistema de localização, capaz de determinar a localização ao nível da sala com maior estabilidade e menor ocorrência de falsos movimentos. 

Pretende-se também obter resultados quantitativos que permitam avaliar o desempenho da solução em termos de exatidão da localização, latência, fiabilidade da comunicação e recuperação após falhas. O trabalho deverá ainda produzir documentação técnica atualizada, scripts de teste e recomendações para uma eventual implantação do sistema em maior escala na ULS da Guarda. 

Os resultados poderão servir de base para futuras extensões do sistema e para a preparação de uma publicação científica sobre localização hospitalar de baixo custo baseada em BLE e ESP32. 

