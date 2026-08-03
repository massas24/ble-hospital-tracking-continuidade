## **Comparação experimental de estratégias simples de localização BLE**

O estágio anterior já demonstrou a arquitetura completa — ESP32, BLE, Flask, MongoDB, React e Mirth Connect — mas a validação baseou-se apenas em dois nós, três beacons, períodos curtos e medições parcialmente manuais. Não foram estudadas adequadamente as zonas de fronteira nem técnicas como fusão de deteções, histerese ou tratamento temporal do RSSI.

**Foco científico** 

Para que o novo trabalho tenha relevância, dimensão e complexidade suficientes para um estágio de Eng. Informática, é definida a seguinte questão a responder pelo trabalho a realizar:

**Em que medida a combinação de filtragem temporal do RSSI, histerese e persistência das deteções melhora a fiabilidade da localização ao nível da sala num RTLS hospitalar de baixo custo baseado em BLE e ESP32?**

Esta questão permite aproveitar quase integralmente a arquitetura existente, introduzir um contributo técnico claro e realizar uma comparação experimental adequada. Pretende-se fazer uma **avaliação experimental de métodos simples e reproduzíveis para reduzir falsas mudanças de sala**.

**Melhorias técnicas mínimas**

**1\. Estabilização e reprodução do sistema atual**

Antes de acrescentar funcionalidades, é necessário conseguir instalar e executar autonomamente:

* firmware dos ESP32;  
* backend Flask;  
* MongoDB;  
* dashboard;  
* integração básica com o Mirth Connect.

Deverão também ser corrigidos erros que impeçam a execução repetível do sistema e documentar configurações, dependências e procedimentos de instalação, caso não existam. 

Esta fase é indispensável porque o estudante será novo no projeto e precisa de estabelecer uma versão de referência contra a qual serão comparados os melhoramentos.

**2\. Registo completo das deteções brutas**

Atualmente, o sistema está orientado sobretudo para guardar a localização inferida e o histórico de movimentos. Para uma avaliação científica, deverá passar a registar, para cada deteção:

* identificador do beacon;  
* identificador do ESP32;  
* sala associada ao ESP32;  
* RSSI;  
* timestamp;  
* número ou identificador do scan;  
* parâmetros usados no ensaio;  
* localização real do beacon, introduzida no protocolo experimental.

Sem guardar os dados brutos, será difícil comparar algoritmos ou repetir a análise posteriormente.

Idealmente, os algoritmos de localização deverão poder ser executados **offline** sobre o mesmo conjunto de dados. Assim, um único ensaio pode ser analisado com vários métodos, garantindo uma comparação justa.

**3\. Sincronização temporal e identificação dos scans**

Os ESP32 e o backend deverão usar uma referência temporal comum, preferencialmente através de NTP. Cada lote deverá incluir:

* timestamp da deteção ou do fim do scan;  
* identificador do nó;  
* número sequencial do lote;  
* identificador único do ensaio, quando aplicável.

Esta melhoria permite:

* agrupar deteções do mesmo intervalo temporal;  
* comparar os RSSI reportados por diferentes nós;  
* calcular latências;  
* detetar mensagens em falta ou duplicadas;  
* reconstruir corretamente a sequência dos acontecimentos.

**4\. Decisão centralizada da localização**

A localização não deverá ser imediatamente atualizada sempre que um nó deteta o beacon. O backend deverá manter, para cada beacon, uma janela recente com as deteções provenientes de todos os ESP32.

Essa estrutura deverá permitir comparar vários métodos sobre os mesmos dados.

**Método de referência**

O método atual, ou uma aproximação simples:

* escolher o nó com o maior RSSI na deteção ou janela mais recente.

Este método funciona como **baseline**.

**Método com filtragem temporal**

Calcular, para cada par beacon–nó, a mediana do RSSI numa janela temporal curta, por exemplo entre três e dez segundos.

A localização corresponde ao nó com maior mediana.

A mediana é simples de implementar e reduz o efeito de valores extremos.

**Método com histerese**

A mudança só é aceite quando o novo nó apresenta uma vantagem mínima sobre o nó atual:

RSSInovo​ \> RSSIatual​ \+ H

O parâmetro (H) deverá ser configurável e testado experimentalmente.

**Método com persistência**

A mudança só é confirmada quando o novo nó permanece dominante:

* durante (N) scans consecutivos; ou  
* durante um intervalo mínimo (T).

Também aqui, (N) ou (T) deverão ser configuráveis.

**5\. Combinação simples dos métodos**

Uma solução adequada seria:

1. agregar os RSSI numa janela temporal;  
2. usar a mediana por nó;  
3. escolher o nó com maior mediana;  
4. exigir uma margem de histerese;  
5. confirmar a mudança apenas após persistência temporal.

Esta abordagem é suficientemente acessível para um estudante de licenciatura e permite estudar um compromisso importante:

* janelas e persistências maiores aumentam a estabilidade;  
* mas também aumentam a latência da mudança.

Esse compromisso entre **precisão, falsos movimentos e latência** pode constituir o núcleo da contribuição do trabalho.

**6\. Estados de localização mínimos**

O sistema deverá distinguir, pelo menos:

* **localização confirmada**;  
* **localização em transição ou ainda não confirmada**;  
* **localização desconhecida ou beacon inativo**.

Estes três estados são suficientes para evitar que o sistema apresente imediatamente uma sala errada e para suportar os testes.

**7\. Configuração externa dos parâmetros experimentais**

Os parâmetros que influenciam a localização deverão poder ser alterados sem recompilar o firmware ou modificar diretamente o código:

* duração do scan;  
* intervalo entre scans;  
* limiar mínimo de RSSI;  
* tamanho da janela temporal;  
* margem de histerese;  
* número de confirmações consecutivas;  
* tempo após o qual um beacon é considerado inativo.

A configuração poderá ser feita através de um ficheiro no backend ou de uma página simples no dashboard. Não é necessário desenvolver uma plataforma avançada de gestão remota.

**8\. Exportação automática dos dados**

O sistema deverá permitir exportar os dados experimentais em CSV incluindo:

* ground truth;  
* sala estimada;  
* método utilizado;  
* RSSI por nó;  
* timestamp;  
* eventos de mudança;  
* parâmetros do ensaio.

Também deverá existir um script em Python que calcule automaticamente as métricas. Esta parte é essencial para reduzir erros manuais e facilitar a repetição dos testes.

**Configuração experimental mínima**

Para produzir resultados com interesse científico, considero adequado usar:

* **três nós ESP32**, correspondentes a duas salas adjacentes e a um corredor ou zona de transição;  
* **três a cinco beacons**, embora os testes de localização possam ser realizados inicialmente com um beacon de cada vez;  
* pelo menos uma porta ou fronteira real entre salas;  
* diferentes posições dentro de cada sala;  
* testes com o beacon transportado por uma pessoa e colocado num equipamento ou objeto.

**Comparação mínima a realizar**

Comparar quatro configurações:

1. **Baseline:** maior RSSI instantâneo ou da última deteção;  
2. **Filtragem:** maior mediana de RSSI numa janela temporal;  
3. **Filtragem \+ histerese**;  
4. **Filtragem \+ histerese \+ persistência**.

A comparação deverá responder a três perguntas principais:

* Qual o método que identifica corretamente a sala durante mais tempo?  
* Qual o método que produz menos falsas mudanças?  
* Qual o custo dessa estabilidade em termos de latência na deteção de uma mudança real?

Esta comparação já constitui um estudo coerente e suficiente para nível de licenciatura, desde que os testes tenham repetições suficientes e sejam apresentados com rigor.

**Métricas mínimas**

As métricas essenciais seriam:

* **exatidão da localização ao nível da sala**;  
* **número ou taxa de falsos movimentos**;  
* **movimentos reais não detetados**;  
* **latência de confirmação da mudança**;  
* **percentagem de tempo em estado desconhecido ou de transição**.

Para a latência deverão ser apresentados, pelo menos:

* mediana;  
* percentil 95;  
* intervalo interquartil ou desvio-padrão;  
* mínimo e máximo.

Também deverá ser apresentada uma matriz de confusão entre a sala real e a sala estimada.

**Distribuição aconselhada do estágio**

Para evitar o problema ocorrido no estágio anterior, sugiro aproximadamente:

* **20%**: instalação, compreensão e estabilização do protótipo;  
* **25%**: instrumentação, armazenamento dos dados e implementação dos algoritmos;  
* **15%**: testes preliminares e ajuste do protocolo;  
* **30%**: execução dos ensaios, repetições e análise dos resultados;  
* **10%**: relatório, documentação e preparação do artigo.

Âmbito mínimo obrigatório para garantir um estágio com dimensão e complexidade adequadas:

1. reproduzir e estabilizar o sistema existente;  
2. armazenar dados RSSI brutos e sincronizados de todos os nós;  
3. implementar um baseline e três variantes baseadas em janela temporal, histerese e persistência;  
4. suportar estados confirmado, transição e desconhecido;  
5. permitir configurar os parâmetros dos algoritmos;  
6. exportar automaticamente os dados;  
7. realizar testes repetidos em duas salas adjacentes e numa zona de transição;  
8. comparar exatidão, falsos movimentos e latência.

**Apresentação e análise dos resultados**

A apresentação dos resultados deverá permitir comparar, de forma clara, os diferentes métodos de decisão da localização e responder às três questões centrais do estudo:

1. **Qual é o método mais fiável na identificação da sala?**  
2. **Qual reduz mais as falsas mudanças de localização?**  
3. **Qual é o custo dessa melhoria em termos de latência?**

Os exemplos seguintes usam **valores hipotéticos**, apenas para ilustrar a organização, análise e interpretação dos resultados.

**1\. Tabela global de comparação dos métodos**

Uma primeira tabela deverá sintetizar os principais resultados de cada método.

| Método | Exatidão da localização | Falsos movimentos por hora | Movimentos não detetados | Latência mediana | Latência p95 | Tempo em estado incerto |
| ----- | ----: | ----: | ----: | ----: | ----: | ----: |
| Maior RSSI instantâneo | 82,4% | 14,2 | 0,0% | 1,2 s | 2,8 s | 0,0% |
| Mediana do RSSI — janela de 5 s | 91,8% | 5,1 | 1,0% | 3,4 s | 5,9 s | 2,1% |
| Mediana \+ histerese | 95,2% | 1,8 | 2,0% | 4,1 s | 7,0 s | 3,5% |
| Mediana \+ histerese \+ persistência | 97,1% | 0,6 | 3,0% | 6,2 s | 9,4 s | 5,8% |

**Exemplo de análise**

“O método baseado no maior RSSI instantâneo apresenta a menor latência, mas também a menor exatidão e um número muito elevado de falsas mudanças de sala. Isto confirma que uma decisão baseada numa única observação de RSSI é demasiado sensível às flutuações do sinal.

A utilização da mediana numa janela de cinco segundos melhora a exatidão de 82,4% para 91,8% e reduz substancialmente os falsos movimentos. A introdução de histerese melhora ainda mais a estabilidade, reduzindo os falsos movimentos para 1,8 por hora.

O método combinado apresenta o melhor resultado de localização, com 97,1% de exatidão e apenas 0,6 falsos movimentos por hora. Contudo, aumenta a latência mediana para 6,2 segundos e deixa o sistema em estado de transição ou incerteza durante uma proporção maior do tempo.”

**Exemplo de conclusão**

“Os resultados mostram que o tratamento temporal do RSSI melhora significativamente a fiabilidade da localização ao nível da sala. A combinação de mediana, histerese e persistência apresentou a maior exatidão e a menor taxa de falsos movimentos, embora com um aumento da latência de confirmação. Assim, a escolha do método deverá considerar o compromisso entre estabilidade e rapidez exigido pelo caso de utilização hospitalar.”

**2\. Gráfico de barras da exatidão**

Um gráfico de barras permite comparar imediatamente a percentagem de localização correta.

Este gráfico deverá ser acompanhado pelos intervalos de confiança ou pela variabilidade entre repetições. Caso contrário, diferenças pequenas, como 95,2% e 97,1%, podem parecer mais relevantes do que realmente são.

Uma tabela complementar poderá apresentar:

| Método | Exatidão média | Desvio-padrão | Intervalo de confiança de 95% |
| ----- | ----: | ----: | ----: |
| Maior RSSI instantâneo | 82,4% | 4,8% | 79,1%–85,7% |
| Mediana do RSSI | 91,8% | 3,1% | 89,7%–93,9% |
| Mediana \+ histerese | 95,2% | 2,4% | 93,6%–96,8% |
| Método combinado | 97,1% | 1,5% | 96,1%–98,1% |

**Interpretação**

Os intervalos mostram que o método combinado é mais estável entre repetições. No entanto, a diferença entre os dois últimos métodos é relativamente pequena. Para decidir se essa melhoria compensa o aumento da latência, é necessário analisar conjuntamente as restantes métricas.

**3\. Gráfico dos falsos movimentos**

Um segundo gráfico de barras poderá mostrar o número de mudanças de sala incorretamente geradas por hora.

| Método | Falsos movimentos por hora |
| ----- | ----: |
| Maior RSSI instantâneo | 14,2 |
| Mediana do RSSI | 5,1 |
| Mediana \+ histerese | 1,8 |
| Método combinado | 0,6 |

**Exemplo de análise**

“A principal melhoria não é apenas o aumento da exatidão global, mas a redução muito acentuada dos falsos movimentos. O método de referência gerou, em média, mais de catorze mudanças incorretas por hora, o que o tornaria inadequado para integração com um sistema hospitalar: cada falsa mudança poderia originar um evento indevido no Mirth Connect.

A filtragem por mediana reduz este valor em cerca de 64%. A introdução de histerese reduz-o em aproximadamente 87% relativamente ao método de referência. O método combinado consegue uma redução próxima de 96%.”

**Exemplo de conclusão**

“A histerese e a persistência tiveram um efeito particularmente relevante na redução das falsas transições. Este resultado é operacionalmente mais importante do que uma pequena melhoria na exatidão média, uma vez que reduz a geração de eventos incorretos para os sistemas hospitalares.”

**4\. Boxplot da latência de mudança**

Para a latência, não deverá ser apresentada apenas a média. Deve ser usadi um **boxplot** por método, baseado em todas as transições realizadas.

Exemplo de dados resumidos:

| Método | Mediana | Q1 | Q3 | p95 | Máximo |
| ----- | ----: | ----: | ----: | ----: | ----: |
| Maior RSSI instantâneo | 1,2 s | 0,9 s | 1,8 s | 2,8 s | 4,1 s |
| Mediana do RSSI | 3,4 s | 2,8 s | 4,2 s | 5,9 s | 7,3 s |
| Mediana \+ histerese | 4,1 s | 3,4 s | 5,0 s | 7,0 s | 8,8 s |
| Método combinado | 6,2 s | 5,1 s | 7,3 s | 9,4 s | 12,0 s |

O boxplot mostraria:

* a mediana da latência;  
* a dispersão entre ensaios;  
* valores extremos;  
* métodos mais previsíveis ou mais variáveis.

**Exemplo de análise**

“O método combinado introduz um atraso adicional porque exige que a nova sala permaneça dominante durante vários scans. Embora a mediana seja de 6,2 segundos, 95% das transições são confirmadas em menos de 9,4 segundos.

Caso o requisito do Hospital seja receber uma atualização em menos de dez segundos, o método combinado ainda poderá ser aceitável. Se for necessária uma resposta inferior a cinco segundos, o método com mediana e histerese poderá representar um compromisso mais adequado.”

**5\. Gráfico de compromisso entre fiabilidade e latência**

Um dos gráficos mais úteis seria um gráfico de dispersão:

* eixo horizontal: latência mediana;  
* eixo vertical: falsos movimentos por hora;  
* cada ponto: um algoritmo ou configuração.

Exemplo:

| Método | Latência mediana | Falsos movimentos/hora |
| ----- | ----: | ----: |
| Maior RSSI | 1,2 s | 14,2 |
| Mediana 5 s | 3,4 s | 5,1 |
| Mediana \+ histerese | 4,1 s | 1,8 |
| Método combinado | 6,2 s | 0,6 |

Neste gráfico, o ponto ideal estaria próximo do canto inferior esquerdo: baixa latência e poucos falsos movimentos.

**Exemplo de interpretação**

“O método de maior RSSI oferece rapidez, mas apresenta uma taxa de erro excessiva. O método combinado minimiza os falsos movimentos, mas apresenta a maior latência. O método com mediana e histerese encontra-se numa posição intermédia, podendo representar o melhor compromisso para utilização operacional.”

Isto permite uma conclusão mais equilibrada:

“Embora o método combinado tenha apresentado o melhor desempenho em termos de fiabilidade, o método baseado em mediana e histerese poderá ser mais adequado quando se pretende limitar a latência a aproximadamente cinco segundos. A configuração ótima depende, portanto, dos requisitos do processo hospitalar.”

**6\. Matriz de confusão entre sala real e sala estimada**

Considerar testes em três zonas:

* Sala A;  
* corredor;  
* Sala B.

Uma matriz de confusão poderá ser apresentada da seguinte forma:

| Localização real ↓ / Estimada → | Sala A | Corredor | Sala B | Desconhecida |
| ----- | ----: | ----: | ----: | ----: |
| Sala A | 95,6% | 2,1% | 0,8% | 1,5% |
| Corredor | 8,4% | 78,3% | 9,1% | 4,2% |
| Sala B | 0,7% | 2,8% | 95,1% | 1,4% |

**Exemplo de análise**

“O sistema apresenta elevada exatidão no interior das salas, mas o corredor é mais difícil de classificar. Parte das observações realizadas no corredor foi atribuída às salas adjacentes, o que é esperado devido à sobreposição da cobertura BLE.”

Esta matriz permite identificar onde ocorrem os erros. Uma exatidão global elevada pode ocultar um mau comportamento nas zonas de transição.

**Exemplo de conclusão**

“A maior parte dos erros ocorreu no corredor e nas proximidades das portas. No centro das salas, a exatidão foi superior a 95%. Estes resultados mostram que o principal desafio não é a deteção dentro das salas, mas a gestão das zonas de cobertura sobreposta.”

**7\. Gráfico temporal do RSSI durante uma transição**

Outro gráfico importante deverá mostrar, ao longo do tempo:

* RSSI registado pelo nó da Sala A;  
* RSSI registado pelo nó da Sala B;  
* localização real;  
* localização estimada;  
* instante em que o sistema confirma a mudança.

Exemplo simplificado:

| Tempo | RSSI Sala A | RSSI Sala B | Localização real | Localização estimada |
| ----: | ----: | ----: | ----- | ----- |
| 0 s | −48 | −72 | Sala A | Sala A |
| 2 s | −51 | −68 | Sala A | Sala A |
| 4 s | −57 | −61 | Porta | Sala A |
| 6 s | −64 | −56 | Sala B | Transição |
| 8 s | −69 | −50 | Sala B | Transição |
| 10 s | −73 | −47 | Sala B | Sala B |

**Análise**

“A partir dos seis segundos, o nó da Sala B passa a apresentar um RSSI superior. Contudo, o sistema não confirma imediatamente a mudança, devido à histerese e ao requisito de persistência. A localização é confirmada aos dez segundos.

Este gráfico permite explicar visualmente por que razão o algoritmo reduz falsas mudanças, mas introduz latência.”

**8\. Influência do tamanho da janela temporal**

É importante mostrar como os parâmetros afetam os resultados.

| Janela | Exatidão | Falsos movimentos/hora | Latência mediana |
| ----- | ----: | ----: | ----: |
| 1 s | 87,3% | 10,8 | 1,5 s |
| 3 s | 93,7% | 4,0 | 2,9 s |
| 5 s | 96,1% | 1,7 | 4,4 s |
| 8 s | 97,0% | 0,8 | 7,1 s |
| 10 s | 97,2% | 0,6 | 8,9 s |

Um gráfico de linhas poderá apresentar simultaneamente:

* aumento da exatidão com a janela;  
* aumento da latência;  
* redução dos falsos movimentos.

**Exemplo de análise**

“A exatidão melhora rapidamente entre um e cinco segundos. A partir dos cinco segundos, os ganhos são reduzidos: aumentar a janela de cinco para dez segundos melhora a exatidão apenas de 96,1% para 97,2%, mas duplica aproximadamente a latência.”

**Conclusão**

“A janela de cinco segundos apresentou o melhor compromisso. Janelas superiores produziram ganhos marginais de exatidão, acompanhados por um aumento considerável da latência.”

Esta é uma conclusão particularmente útil, pois permite justificar objetivamente a escolha dos parâmetros finais.

**9\. Comparação por cenário**

Os resultados não devem ser apresentados apenas de forma agregada.

| Cenário | Maior RSSI | Mediana | Mediana \+ histerese | Método combinado |
| ----- | ----: | ----: | ----: | ----: |
| Centro da sala | 96,8% | 98,2% | 98,7% | 98,9% |
| Junto à parede | 83,1% | 91,4% | 95,0% | 96,5% |
| Junto à porta | 65,2% | 80,6% | 90,1% | 94,2% |
| Movimento entre salas | 78,4% | 88,9% | 93,7% | 95,1% |
| Vários beacons | 80,5% | 90,7% | 94,4% | 96,0% |

**Análise**

“Todos os métodos apresentam bons resultados no centro das salas. As diferenças tornam-se evidentes junto às portas e durante movimentos entre salas. Isto mostra que os testes em condições simples não são suficientes para distinguir os algoritmos.”

**Conclusão**

“O método combinado apresentou vantagens sobretudo nas situações de maior ambiguidade, como portas, paredes comuns e deslocações. Em posições estáveis no centro das salas, os métodos produziram resultados semelhantes.”

**10\. Análise estatística recomendada**

Para um projeto de licenciatura, não é necessário recorrer a métodos estatísticos excessivamente complexos, mas usar pelo menos:

* mediana e intervalo interquartil para latência;  
* média, desvio-padrão e intervalo de confiança para a exatidão;  
* resultados separados por repetição;  
* comparação emparelhada dos algoritmos, uma vez que todos devem ser avaliados sobre os mesmos ensaios;  
* teste de Wilcoxon para comparar dois métodos, quando os dados não apresentarem distribuição normal;  
* teste de Friedman, caso sejam comparados mais de dois métodos;  
* dimensão do efeito, para avaliar se a diferença tem relevância prática.

Exemplo de apresentação:

“O método combinado apresentou uma exatidão superior à do método de maior RSSI em todas as dez repetições. A diferença foi estatisticamente significativa no teste de Wilcoxon ((p \< 0{,}01)) e apresentou uma dimensão de efeito elevada. A latência também aumentou significativamente, passando de uma mediana de 1,2 para 6,2 segundos.”

Não deverá ser afirmado apenas que um método é “melhor” porque obteve um valor ligeiramente superior. É necessário considerar:

* variabilidade;  
* significância;  
* dimensão da diferença;  
* relevância operacional.

**11\. Exemplo de síntese final dos resultados**

Um texto final para a secção de discussão poderia seguir esta lógica:

“Os resultados demonstram que a utilização direta do maior RSSI não é suficientemente robusta para a localização ao nível da sala, sobretudo em zonas de cobertura sobreposta. A aplicação de uma janela temporal reduziu a influência de flutuações pontuais, enquanto a histerese e a persistência diminuíram substancialmente a ocorrência de falsas mudanças.

O método combinado obteve a maior exatidão e a menor taxa de falsos movimentos. No entanto, esta melhoria foi acompanhada por um aumento da latência. A análise dos diferentes tamanhos de janela mostrou que uma janela de cinco segundos proporciona um compromisso favorável: janelas maiores introduzem atrasos adicionais sem ganhos proporcionais de exatidão.

Os erros concentraram-se nas portas e no corredor, enquanto a localização no centro das salas se manteve estável. Isto sugere que futuras melhorias devem incidir prioritariamente no tratamento das zonas de transição e não no aumento indiscriminado da complexidade do algoritmo.

Para o caso de utilização estudado, o método baseado em mediana, histerese e persistência mostrou-se adequado quando se privilegia a estabilidade da localização. Em aplicações que exijam atualizações mais rápidas, a variante sem persistência poderá representar um compromisso mais apropriado.”

**Estrutura recomendada para a secção de testes e resultados do relatório.**

Uma organização adequada seria:

**5.1. Configuração experimental**  
Espaços, nós, beacons, parâmetros e repetições.

**5.2. Comparação global dos métodos**  
Tabela principal com todas as métricas.

**5.3. Exatidão da localização**  
Gráfico de barras e matriz de confusão.

**5.4. Falsas mudanças de sala**  
Gráfico e análise por cenário.

**5.5. Latência de confirmação**  
Boxplots, mediana e percentis.

**5.6. Influência dos parâmetros**  
Janelas temporais, histerese e persistência.

**5.7. Análise por cenário**  
Centro da sala, portas, corredor e movimento.

**5.8. Discussão**  
Compromissos, limitações e escolha da configuração recomendada.

O mais importante é que cada tabela ou gráfico esteja associado a uma pergunta concreta. Os resultados não deverão limitar-se a mostrar que o sistema “funciona”; deverão permitir perceber **quanto funciona, em que condições falha e qual a configuração que oferece o melhor compromisso para o Hospital**.

