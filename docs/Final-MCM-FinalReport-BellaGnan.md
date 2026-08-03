

# **A BLE-Based Real-Time Location System with RESTful Integration for Healthcare Applications** 

Report of A Vocational Internship submitted as a partial requisition to obtain the degree of Master in Mobile Computing 

Supervisor: Professor Pedro Pinto Co-supervisor: Professor Carlos Carreto 

## **Bella Gnan** 

**July 2026** 

“When everything seems to be going against you, remember that the airplane takes off against the wind, not with it” 

Henry Ford 

Acknowledgments 

### **Acknowledgments** 

I would like to express my sincere gratitude to Professor José Fonseca for providing me with the opportunity to undertake my Erasmus internship project under his supervision, which made it possible for me to come to the IPG and begin my Master’s degree in Portugal. I would also like to thank Professors Pedro Pinto and Carlos Carreto for their guidance, availability, and unwavering support throughout the academic year and during this internship project, as their comments and encouragement were essential for completing this work. I also wish to thank the professors and staff at IPG, whose teaching, guidance, and support provided the foundation for this project and sustained me during the most demanding phases of my studies. 

I am grateful to Director Ricardo and Eng. Luis for the opportunity to carry out this internship at ULS da Guarda, as well as to everyone in the IT department for their collaboration, availability and practical assistance. Lastly, I owe special thanks to my family and friends for their constant encouragement and moral support during the most demanding phases of this dissertation project. 

Bella Gnan 

i 

Abstract 

### **Abstract** 

Hospital environments still lack continuous, real-time, and easily deployable solutions for tracking the location of patients and equipment, which limits operational efficiency and patient safety. This project addresses this gap by designing and implementing a modular real-time location system (RTLS) prototype that provides near real-time, room-level visibility of patients and equipment and can be incrementally deployed over existing infrastructure. The main contribution is a concrete, system-centric RTLS architecture that combines low-cost mobile computing with hospital interoperability standards and can be adapted to different hospital contexts. Methodologically, the work followed an iterative design, prototyping and validation process in collaboration with the IT team at Hospital Sousa Martins, ensuring alignment with real workflows and constraints. Functional testing showed that the prototype reliably detected registered devices at the room level, maintained consistent location histories and delivered movement events with acceptable latency. These results confirm the feasibility and effectiveness of a low-cost, incrementally deployable RTLS and provide a practical foundation for future extensions aimed at improving operational efficiency and patient safety in healthcare. 

**Keywords:** Health Information System, RTLS, RESTful APIs, BLE, ESP32, Flask, MongoDB, Mirth Connect 

ii 

Abstract 

### **Resumo** 

Os ambientes hospitalares continuam a carecer de soluções contínuas, em tempo real e de fácil implementação para rastrear a localização de doentes e equipamentos, o que limita a eficiência operacional e a segurança do doente. Este trabalho responde a essa lacuna através do desenho e implementação de um protótipo modular de sistema de localização em tempo real (RTLS) que fornece visibilidade quase em tempo real, ao nível da sala, da localização de doentes e equipamentos e que pode ser implementado de forma incremental sobre a infraestrutura existente. A principal contribuição é uma arquitetura RTLS concreta, centrada no sistema, que combina computação móvel de baixo custo com normas de interoperabilidade hospitalar e que pode ser adaptada a diferentes contextos hospitalares. Metodologicamente, o trabalho seguiu um processo iterativo de desenho, prototipagem e validação em colaboração com a equipa de informática do Hospital Sousa Martins, assegurando o alinhamento com fluxos de trabalho e constrangimentos reais. Os testes funcionais mostraram que o protótipo deteta de forma fiável os dispositivos registados ao nível da sala, mantém históricos de localização consistentes e entrega eventos de movimento com latência aceitável. Estes resultados confirmam a viabilidade e eficácia de um RTLS de baixo custo e implementação incremental, fornecendo uma base prática para futuras extensões orientadas à melhoria da eficiência operacional e da segurança do doente em contextos de saúde. 

**Palavras-chave:** Health Information System, RTLS, RESTful APIs, BLE, ESP32, Flask, MongoDB, Mirth Connect 

iii 

Index 

### **INDEX** 

|Index of Figures ............................................................................................................... vi|
|---|
|Index of Tables ............................................................................................................... vii|
|Acronyms and abbreviations ......................................................................................... viii|
|1.<br>Introduction .............................................................................................................. 1<br>|
|1.1.<br>Context and Motivation .................................................................................... 1|
|1.2.<br>Objectives and Proposed Solution .................................................................... 2|
|1.3.<br>Internship Framework ...................................................................................... 4|
|1.4.<br>Dissertation Overview ...................................................................................... 5|
|2.<br>Related Work ............................................................................................................ 6|
|2.1.<br>Identification Technologies in Healthcare ........................................................ 6|
|2.2.<br>RESTful APIs in Healthcare Systems .............................................................. 9|
|2.3.<br>Comparative Analysis .................................................................................... 10|
|<br>3.<br>System Development .............................................................................................. 13|
|3.1.<br>Requirements Analysis ................................................................................... 13|
|3.1.1.<br>Functional Requirements ........................................................................ 13|
|3.1.2.<br>Non-Functional Requirements ................................................................ 17|
|3.2.<br>Technology stack selection ............................................................................. 18|
|3.2.1.<br>ESP32 room nodes ................................................................................. 19|
|3.2.2.<br>Arduino IDE and ESP32 libraries .......................................................... 20|
|3.2.3.<br>BLE beacons ........................................................................................... 20|
|3.2.4.<br>Backend API (Flask,Python) .................................................................. 22|
|3.2.5.<br>Database (MongoDB) ............................................................................. 23|
|3.2.6.<br>Integration engine (Mirth Connect) ........................................................ 24|
|3.2.7.<br>Web dashboard (HTML/CSS/JavaScript, React) ................................... 24|
|3.2.8.<br>Technology stack summary .................................................................... 25|
|3.3.<br>System Architecture Overview ....................................................................... 26|
|3.4.<br>Implementation Details................................................................................... 30|
|3.4.1.<br>ESP32 room node ................................................................................... 30|
|3.4.2.<br>Live detection and commissioning ......................................................... 32|
|3.4.3.<br>Cloud and Integration Layer ................................................................... 32|
|3.4.4.<br>Web dashboard behaviour ...................................................................... 34|
|4.<br>Prototype Testing and Results ................................................................................ 35|
|4.1.<br>Functional Testing .......................................................................................... 35|
|4.1.1.<br>Functional test matrix ............................................................................. 36|
|4.1.2.<br>Components tests: ESP32 room nodes, backend and dashboard ........... 37|
|4.1.3.<br>Test 1 - End to end patient-transfer scenario .......................................... 45|
|4.1.4.<br>Test 2 - Security and access control ....................................................... 48|
|<br>4.1.5.<br>Test 3 – Data consistency ....................................................................... 49|
|<br>4.2.<br>Performance Testing ....................................................................................... 52|
|4.3.<br>Limitations ...................................................................................................... 53|
|5.<br>Conclusions ............................................................................................................ 56|
|5.1.<br>Summary of Contributions ............................................................................. 56|
|5.2.<br>Future Work .................................................................................................... 57|



iv 

Index 

Bibliography ................................................................................................................... 59 

v 

Index of  Figures 

### **INDEX OF FIGURES** 

|Figure 3.1. Use case diagram – patient transfer scenario ............................................... 16|
|---|
|Figure 3.2. FireBeetle ESP32 room node ....................................................................... 19|
|Figure 3.3. ESP32 firmware toolchain comparison ........................................................ 20|
|Figure 3.4. Seeed Studio E5 BLE tracking beacon ........................................................ 21|
|Figure 3.5.Comparison of backend framework ............................................................. 22|
|Figure 3.6. MongoDB data organization ........................................................................ 23|
|Figure 3.7. Mirth Connect integration engine ................................................................ 24|
|Figure 3.8. Hospital BLE tracking dashboard ................................................................ 25|
|Figure 3.9. System architecture ...................................................................................... 27|
|Figure 3.10. RTLS Data flow diagram ........................................................................... 29|
|Figure 3.11. ESP32 room node interactions ................................................................... 31|
|Figure 3.12. Cloud and integration workflow ................................................................ 33|
|Figure 4.1. ESP32 BLE scan output (Sensor1) .............................................................. 38|
|Figure 4.2. Flask console: ESP32 POSTs ...................................................................... 39|
|Figure 4.3. Whitelist collection (MongoDB) ................................................................. 40|
|Figure 4.4. History collection (MongoDB) .................................................................... 40|
|Figure 4.5. Administrator signup and login .................................................................... 41|
|Figure 4.6. Live BLE devices per ESP32 room node ..................................................... 42|
|Figure 4.7. ESP-room mapping configuration ............................................................... 42|
|Figure 4.8. Whitelist and movement history .................................................................. 43|
|Figure 4.9. Mirth management view .............................................................................. 44|
|Figure 4.10. Mirth channel movement event .................................................................. 45|
|Figure 4.11. Beacon in Radiology (live view)................................................................ 46|
|Figure 4.12. Beacon in Imaging (live view) ................................................................... 46|
|Figure 4.13. Mirth event: Radiology → Imaging ........................................................... 47|
|Figure 4.14. Mirth event: Imaging → Radiology ........................................................... 47|
|Figure 4.15. Unauthenticated GET request   (HTTP 401).............................................. 48|
|Figure 4.16. Authenticated GET request (HTTP 200) ................................................... 49|
|Figure 4.17. GET request for Whitelisted beacons ....................................................... 50|
|Figure 4.18. GET  request for movement  history for one beacon ................................. 51|



vi 

Index of Tables 

### **INDEX OF TABLES** 

|Table 2.1. Quantitative comparison of identification and localization technologies. ...... 8|
|---|
|Table 2.2. Representative systems vs. Proposed solution. ............................................. 11|
|Table 3.1.Technology stack and main responsibilities. .................................................. 26|
|Table 4.1. Functional test matrix. ................................................................................... 36|
|Table 4.2. Performance metric for the prototype configuration. .................................... 53|



vii 

Acronyms 

### **ACRONYMS AND ABBREVIATIONS** 

**API** – Application Programming Interface 

**BLE** – Bluetooth Low Energy **EHR** – Electronic Health Record 

**FHIR** – Fast Healthcare Interoperability Resources 

**FR** – Functional Requirement **HIS** – Hospital Information System **HL7** – Health Level Seven **HTTP** – Hypertext Transfer Protocol **IOT** – Internet of Things 

**JSON** – JavaScript Object Notation 

**MAC** – Media Access Control 

**NFR** – Non-Functional Requirement 

**ORM** – Object-Relational Mapping 

**PTAT** – Patient Turnaround Time 

**REST** – Representational State Transfer **RTLS** – Real-Time Location System 

**RSSI** – Received Signal Strength Indicator 

**UWB** – Ultra-Wideband 

viii 

Introduction 

### **1. INTRODUCTION** 

This chapter presents the context and motivation for the professional internship report, introduces the problem addressed at Hospital Sousa Martins, defines the objectives and proposed solution, and describes the internship framework in which the work was conducted. The chapter concludes with an overview of the structure of the remaining chapters. 

#### **1.1. Context and Motivation** 

Digital transformation in healthcare is prompting hospitals to adopt more intelligent, interconnected infrastructures where patients, staff, and equipment are continuously monitored and managed more efficiently. Many processes that support identification and tracking are still based on manual procedures, such as paper forms, visual checks, data entered at nursing stations, or phone calls between services. However, these mechanisms are slow and error-prone. They can lead to misidentification, loss of information, and delays in care. As the volume and complexity of hospital activities increase, these limitations become more evident and create pressure to adopt more automated solutions. Automatic identification technologies, such as barcodes and QR codes, are already being used in several areas. Examples include patient wristbands, medication administration, and laboratory samples [1]. They allow fast and low‑cost identification, but they depend on line-of-sight scanning and do not provide continuous information about the location of patients or equipment. 

Bluetooth Low Energy (BLE) beacons make it possible to add a localization layer to identification system. Small, low-power beacons can be attached to patients or assets and detected using fixed receivers or mobile devices. This enables room- or zonelevel localization without manual scanning. Previous studies have shown that BLE-based Real-Time Locating Systems (RTLS) can support concrete use cases, such as monitoring hand hygiene opportunities or measuring door-to-doctor times in emergency departments, improving the quality of the data collected and reducing the burden on professionals [2, 

1 

Introduction 

3]. However, many of these systems are limited to specific units or asset tracking. They often use proprietary platforms and do not offer an integrated approach that combines identification, localization, and interoperability with existing information systems. At the same time, hospitals already depend on several clinical and administrative systems, such as Electronic Health Records (EHR), imaging repositories, and scheduling platforms. Any new solution for identification and localization must be integrated with this ecosystem and respect strict requirements for security, privacy, and reliability. 

The problem addressed in this report is the absence of continuous, near realtime, and interoperable information about the location of patients and mobile medical assets inside Hospital Sousa Martins. Current hospital systems record administrative and clinical data but do not maintain up-to-date room-level locations or movement histories for patients, stretchers, or transport chairs. This lack of visibility affects porters, nurses, physicians, and support services, who depend on phone calls or manual checks to know whether a patient has arrived at a destination, where a stretcher is, or how long a transport has taken, which leads to delays, inefficient workflows, and lost time searching for patients and equipment. Existing technologies, such as barcodes, QR codes, and isolated RTLS deployments, help with identification or with specific localized use cases, but they either require manual scanning, lack continuous coverage, or are not integrated with the broader hospital information ecosystem. Consequently, they are insufficient to provide a unified, room-level, near real-time view of patient and asset location within the hospital. 

#### **1.2. Objectives and Proposed Solution** 

The main objective of this report is to design, implement, and evaluate a prototype RTLS capable of providing near real-time, room-level visibility of patients and mobile medical assets at Hospital Sousa Martins, while remaining compatible with the existing hospital information ecosystem. This work is guided by the following research question: To what extent is it feasible to develop a low-cost, BLE-based RTLS prototype that provides near real-time, room-level visibility while remaining simple to integrate with existing hospital systems? 

To address this question, the proposed solution uses BLE beacons attached to patients or equipment and ESP32-based room nodes deployed in selected areas of the 

2 

Introduction 

hospital. These room nodes continuously scan for nearby BLE devices and forward detection data to a central backend application. The backend filters detected devices using a configurable whitelist, maintains the current room-level location and movement history of each tracked entity in a MongoDB database, and exposes this information through a RESTful API. An integration layer based on Mirth Connect receives movement events and forwards them to hospital systems using established interoperability mechanisms. A web-based dashboard allows authorized users to visualize live detections, manage room mappings, and maintain the whitelist of tracked devices. 

The main objective can be decomposed into the following specific objectives, each corresponding to a key component or function of the proposed solution at the hospital: 

- Analyze the requirements for near real-time identification and localization in the hospital context, considering operational workflows, privacy, security, and integration constraints. 

- Design a modular system architecture for a BLE-based RTLS that separates sensing, processing, storage, visualization, and integration components. 

- Implement ESP32-based room nodes capable of continuously detecting nearby BLE devices and transmitting structured detection data to a central backend over the hospital network, enabling reliable room-level presence detection. 

- Develop a backend application exposing a RESTful API to ingest BLE detection data, apply whitelist-based filtering of tracking beacons, maintain current location states and movement histories and provide standardized access to this information. 

- Integrate the backend with the hospital integration engine to enable the generation and delivery of movement events and location updates to existing information systems, while keeping the prototype independent of clinical identifiers. 

- Implement a web-based dashboard that supports live visualization of detections, configuration of room mappings and tracking beacons, and basic administrative and monitoring functions. 

- Evaluate the prototype through functional testing and representative usage scenarios in the hospital environment. 

3 

Introduction 

This work presents a prototype-oriented solution to the problem identified at Hospital Sousa Martins, showing how low-cost BLE technology, embedded sensing devices, RESTful services, and integration engines can be combined to support room-level location visibility in a healthcare setting. The solution is intentionally scoped as a prototype, emphasizing feasibility, modularity, and interoperability, and establishing a foundation for future extensions related to scalability, security reinforcement, and more advanced localization techniques. 

#### **1.3. Internship Framework** 

The work described in this dissertation was carried out during a six‑month internship at the Local Health Unit of Guarda (ULS da Guarda), a public institution responsible for organizing and delivering healthcare services across the Guarda region. The ULS da Guarda provides primary and specialized care, as well as long‑term care, and manages hospitals such as Hospital Sousa Martins in Guarda and Hospital Nossa Senhora da Assunção in Seia. From a technological perspective, ULS da Guarda is integrated into the National Health IT Network and operates a dedicated data center that supports the digital tools required for clinical and administrative management. The institution is also recognized for its commitment to research, training, and teaching in the healthcare sector. 

The internship was conducted at Hospital Sousa Martins within the Information and Communication Systems Department. The project originated from requirements expressed by the local IT team, who identified the lack of near real-time visibility over the location of patients and mobile assets and the need for a low-cost solution that could be integrated with the existing infrastructure. The hospital environment imposed several constraints: the prototype had to use the internal Wi-Fi network, respect security and privacy policies, avoid storing clinical identifiers, and integrate with the current integration engine rather than introducing new middleware. 

Within this framework, the author’s role was to design and implement a prototype capable of making the collection and integration of identification and location information more flexible, better documented and cost-effective. The author was responsible for the main design decisions regarding the system architecture, choice of technologies, firmware for the ESP32 room nodes, backend API, MongoDB data model, 

4 

Introduction 

and web dashboard. The implementation of these components and the configuration of the integration flows with Mirth Connect were also carried out by the author, with feedback from the IT team. Supervision was organized through regular meetings used to review progress, discuss alternatives, and adjust the work plan when necessary, ensuring that the prototype remained aligned with both the academic objectives of the dissertation and the operational needs of ULS da Guarda. 

#### **1.4. Dissertation Overview** 

This report is organized into five chapters. Chapter 1 introduces the context and motivation of the work, formulates the problem addressed, defines the objectives and proposed solution, and describes the internship framework. Chapter 2 presents the related work, with emphasis on identification technologies in healthcare, the use of RESTful APIs and interoperability standards in hospital information systems, and a comparative analysis that frames the proposed approach. Chapter 3 describes the system development, covering the requirements analysis, selection of the technology stack, system architecture, and the main implementation details of the prototype. Chapter 4 presents the prototype testing and results, including functional and performance tests, and discusses the main limitations observed. Chapter 5 concludes the report, summarising the contributions and indicating possible directions for future work. 

5 

Related Work 

### **2. RELATED WORK** 

This chapter presents the main identification and localization technologies used in healthcare environments and discusses interoperability approaches based on RESTful Application Programming Interfaces (RESTful APIs). It also provides a comparative analysis that positions the proposed RTLS prototype relative to existing solutions. The chapter is organized into three sections: identification and localization technologies in healthcare, interoperability mechanisms for hospital systems, and a comparative analysis of the reviewed approaches. The chapter is organized into three sections. Section 2.1 reviews identification and localization technologies used in healthcare, including barcodes, QR codes, Radio Frequency Identification (RFID), UltraWideband (UWB), Wi-Fi, and BLE. Section 2.2 discusses RESTful APIs and interoperability mechanisms in healthcare systems, including Health Level Seven (HL7), Clinical Document Architecture (CDA), Fast Healthcare Interoperability Resources (FHIR), and integration engines. Section 2.3 provides a comparative analysis of the reviewed approaches and highlights the gaps that motivate the proposed solution. 

#### **2.1. Identification Technologies in Healthcare** 

Identification and localization technologies have been widely explored in healthcare to support asset tracking, patient flow monitoring, and workflow analysis. In a review of medical asset-tracking technologies, Kamal et al. [1] reported the use of barcodes, passive and active RFID, and UWB tags for equipment tracking and, in some cases, patient flow management. However, they also highlight cost, interference, and integration issues that may limit large-scale deployment and contribute to heterogeneous solutions across hospitals. These deployments often depend on proprietary middleware and vendor-specific readers, which can be expensive to acquire and maintain, especially when hospitals already operate Wi-Fi networks for clinical and administrative applications. Barcodes and QR codes remain common optical identification methods in healthcare. They can support fast and low-cost identification at the point of care, for 

6 

Related Work 

example through patient wristbands, medication labels, or laboratory samples. However, optical identification methods require line-of-sight scanning and manual interaction and therefore do not provide continuous information about the location of patients or mobile assets. RFID technologies extend identification by using radio-frequency tags that can be read without direct line of sight. Passive RFID tags are relatively inexpensive, while active RFID and UWB tags can provide longer range or higher accuracy at the cost of more complex and expensive infrastructure [1]. BLE has emerged as a practical option for indoor localization because it combines low-cost beacons with receivers that can run on embedded devices or smartphones. In a study on room-level localization, Hadian et al. [2] developed and evaluated a BLE-based system for healthcare workers in patient rooms, showing that BLE beacons combined with fingerprinting and machine-learning methods can support room-level localization for hand-hygiene performance estimation. However, this work focused mainly on localization accuracy and a specific workflow, rather than on integration, privacy management, or everyday operation within a broader hospital information system. Similarly, Iqbal et al. [4] proposed a BLE-based localization system in a clinical environment using deep learning and demonstrated accurate real-time tracking of people and equipment. This confirms the potential of BLE when combined with advanced localization algorithms. At the same time, such approaches may require more complex models, calibration, and data-processing resources, which can increase maintenance requirements in practical deployments. Frisby et al. [3] presented a Bluetooth-based contextual-computing system that tracked healthcare providers in emergency departments using beacons and fixed receivers. Their results showed that BLE-based systems can support workflow metrics such as encounter timing and door-todoctor time. However, the solution focused on staff movement in a specific emergency department context and provided limited discussion of hospital-wide scalability or standardized integration with other applications. Overmann et al. [5] conducted a systematic review of RTLS technologies used to improve healthcare delivery and found that RFID, Wi-Fi, UWB, and BLE have been applied in settings such as emergency departments, operating theatres, and other clinical areas. Their review shows that RTLS can support workflow analysis, patient safety, and operational efficiency, but also indicates that integration and effective use of location data remain challenging because many deployments are custom-built and strongly tied to local infrastructure. Muthu 

7 

Related Work 

Arumugam et al. [6]  reviewed IoT and BLE-based systems aimed at reducing patient waiting times in Malaysian public hospitals. They concluded that BLE and IoT platforms are promising for patient localization and Patient Turnaround Time (PTAT) reduction, but that complete implemented framework remains limited in that context. This supports the relevance of exploring BLE-based RTLS prototypes that combine detection, storage, and integration functions. 

Table 2.1 provides a quantitative comparison of the main identification and localization technologies discussed in this section. The values are approximate and should be interpreted as indicative ranges, since performance depends on hardware configuration, room layout, radio interference, and deployment conditions. 

**Table 2.1. Quantitative comparison of identification and localization technologies.** 

|**Technology**|**Cost**|**Typical Range**|**Accuracy / Output**|**Main Limitation**|
|---|---|---|---|---|
|**Barcode /**<br>**QR code**|Very low|Line of sight|Exact identification|Requires manual<br>scanning|
|**Passive**<br>**RFID**|Low|Centimetres to a<br>few metres|Short-range<br>identification|Requires RFID<br>readers|
|**Active RFID**|Medium|Several metres to<br>tens of metres|Room / zone level|Higher<br>infrastructure cost|
|**Wi-Fi**|Medium|Building-wide<br>where coverage<br>exists|Room / zone level|Depends on<br>network coverage<br>and configuration|
|**UWB**|High|Tens of metres|High-precision<br>positioning|Requires dedicated<br>anchors|
|**BLE**|Low|Typically, 10-30m<br>indoors|Room / zone level|RSSI can be<br>unstable|



Overall, these studies show that barcodes, QR codes, RFID, Wi-Fi, UWB, and BLE can support different forms of identification or localization in healthcare environments. However, they differ significantly in cost, accuracy, infrastructure requirements, and integration complexity. For the prototype developed in this report, BLE offers a practical compromise between deployment cost, room-level visibility, and integration flexibility. This makes BLE beacons and ESP32-based room nodes suitable for a proof-of-concept RTLS focused on feasibility and interoperability rather than highprecision indoor positioning. 

8 

Related Work 

#### **2.2. RESTful APIs in Healthcare Systems** 

The interoperability of clinical data through FHIR has been widely discussed in the literature. Pimenta et al. [7] review how FHIR resources and RESTful APIs are used to integrate clinical systems, share data between institutions, and support new applications, emphasizing the role of resource-oriented design for modularity and reuse. Health-data interoperability standards such as Health Level Seven version 2 (HL7 v2), CDA, and FHIR have also been compared in a broader critical review, where Osamika et al. [8] argue that FHIR’s resource-oriented and REST-based design offers advantages for web integration, while still presenting challenges related to semantics, security, and regulation. These works concentrate on exchanging clinical documents and structured health records and therefore providing limited guidance on modelling high-frequency RTLS event streams or linking location events to patients and assets in practice. FHIR-based interoperability case studies report that FHIR APIs are now used to expose EHR data, support patient-facing applications and enable decision-support tools, reinforcing the idea that RESTful APIs are becoming the dominant integration layer in modern healthcare information systems. In the context of healthcare IoT, Sartaj et al. [9] studied REST API testing in an evolving application deployed by the city of Oslo, evaluating several automated testing tools on multiple APIs and releases. Their findings show that high test coverage does not always detect subtle regressions, especially when systems evolve quickly and several services interact. This supports the need to keep the RTLS API relatively small and to delegate complex transformations to an existing integration engine. 

In an RTLS-based system, location updates must be translated into a format that hospital systems can understand. FHIR provides resources such as Location, Device, and Encounter, which can represent hospital rooms, tracking devices, and patient-related care episodes. For example, when a beacon is detected in a new room, the event could theoretically be represented as an update to a FHIR Location resource or as part of an Encounter linked to a patient identifier. However, implementing full FHIR support in this room-level prototype would add significant complexity. It would require reliable clinical identifiers, strict validation rules, and careful alignment with existing hospital workflows. The prototype therefore follows a pragmatic approach. It does not implement FHIR 

9 

Related Work 

resources directly. Instead, it exposes identification and localization events through a lightweight RESTful API built with Flask and relies on Mirth Connect to transform these events into HL7 v2, CDA, or other formats already supported by hospital systems. This event-based integration keeps the RTLS component small and decoupled, while using the existing interoperability infrastructure of the hospital environment. Overall, RESTful APIs and healthcare interoperability standards provide a strong foundation for communication between systems, but the integration of continuous RTLS event streams remains a specific challenge. For this reason, an event-based integration approach using a REST API and Mirth Connect is appropriate for the prototype developed in this report. 

#### **2.3. Comparative Analysis** 

The articles reviewed in the previous sections show that barcodes, RFID, UWB, Wi-Fi, and BLE have all been used to support asset tracking, staff tracking, workflow monitoring, and, in some cases, patient flow management in healthcare environments. BLE-based systems have demonstrated potential for room-level localization and workflow metrics such as hand-hygiene events, emergency-department timings, and clinical-environment localization [2], [3], [4]. At the same time, broader RTLS reviews show that RFID, Wi-Fi, UWB, and BLE involve different trade-offs in terms of cost, accuracy, infrastructure requirements, and integration complexity [1], [5]. The interoperability reviews and the API-testing study indicate that HL7, CDA, FHIR, and RESTful APIs are becoming important mechanisms for healthcare data exchange, but that semantic modelling, security, system evolution, and testing remain important challenges [7], [8], [9]. Industry reports also show that hospitals are comparing RTLS and RFID options and increasingly considering BLE-based RTLS for operational improvement, although many described deployments rely on commercial platforms and provide limited technical detail [10], [11]. 

These contributions are, however, specialized in scope. Asset-tracking reviews mainly focus on equipment; room-level BLE localization studies often focus on specific workflows or controlled environments; BLE-IoT PTAT proposals remain partly conceptual; and FHIR and REST API studies mainly address clinical data exchange rather than continuous RTLS event streams. Many BLE-based studies emphasize advanced 

10 

Related Work 

localization algorithms and accuracy metrics, while others focus on workflow analysis, interoperability standards, or API testing. In contrast, this report adopts a system-centric approach that prioritizes a simple, reproducible architecture and integration with existing hospital systems over centimetre-level localization precision. 

Table 2.2 (Representative systems vs. proposed solution) summarizes these works and contrasts them with the prototype developed here, highlighting differences in identification technology, integration approach, clinical focus, main strengths and gaps relative to the proposed solution. 

**Table 2.2. Representative systems vs. Proposed solution.** 

|**Work /**<br>**System**|**Identification**<br>**Technology**|**Integration**<br>**Approach**|**Clinical**<br>**Focus**|**Main**<br>**Strengths**|**Gap relative to**<br>**proposed solutions**|
|---|---|---|---|---|---|
|**Medical**<br>**asset-trackin**<br>**g review [1]**|Barcodes,<br>passive/active<br>RFID, UWB<br>for assets and<br>sometimes<br>patients|Typically,<br>proprietary<br>middleware<br>, limited<br>standards‑b<br>ased APIs|Asset<br>management,<br>equipment<br>utilization,<br>some patient<br>flow|Mature,<br>well‑documented<br>technologies for<br>asset tracking|Limited<br>patient‑centric<br>journey tracking;<br>heterogeneous APIs;<br>no simple BLE +<br>REST prototype|
|**RTLS in**<br>**healthcare**<br>**review [5]**|RFID, Wi‑Fi,<br>UWB, BLE in<br>various RTLS<br>deployments|Diverse,<br>often<br>custom<br>integration<br>layers|Workflow<br>analysis,<br>safety,<br>throughput|Broad overview<br>of RTLS<br>technologies and<br>use cases|Highlights integration<br>and data‑use<br>challenges; no<br>specific BLE + API<br>reference design|
|**BLE–IoT**<br>**PTAT**<br>**review [6]**|Conceptual<br>BLE bracelets<br>and IoT<br>infrastructure<br>for patients|Envisioned<br>hospital‑sys<br>tem<br>integration|PTAT and<br>waiting‑time<br>reduction in<br>public<br>hospitals|Identifies PTAT<br>as key metric;<br>argues for<br>BLE‑IoT RTLS|No complete<br>implemented<br>framework: no simple<br>BLE + REST<br>prototype integrated<br>with existing HIS|
|**BLE**<br>**room‑level**<br>**localization**<br>**for hand**<br>**hygiene [2]**|BLE beacons<br>and smartphone<br>receiver in<br>single rooms|Local data<br>collection,<br>not<br>enterprise‑i<br>ntegrated|Hand‑hygiene<br>performance<br>estimation|Demonstrates<br>accurate,<br>low‑cost<br>room‑level BLE<br>localization|Limited to one room<br>type and workflow;<br>no hospital‑wide<br>tracking or API‑based<br>integration|
|**BLE**<br>**tracking of**<br>**providers in**<br>**ED [3]**|BLE beacons<br>carried by<br>clinicians; fixed<br>receivers per<br>room|Local<br>server logs<br>and<br>workflow<br>analysis|Emergency‑d<br>epartment<br>provider<br>movement<br>and timings|Shows feasibility<br>of automatic<br>encounter timing<br>(e.g.<br>door‑to‑doctor)|Tracks staff rather<br>than patients; focused<br>on one ED; lacks<br>integration with<br>broader hospital<br>informationsystems|
|**BLE**<br>**localization**<br>**with deep**<br>**learning [4]**|BLE tags and<br>receivers with<br>deep‑learning‑b<br>ased<br>localization|Local<br>processing<br>and<br>evaluation|Clinical‑envir<br>onment<br>localization<br>accuracy|Demonstrates<br>accurate real‑time<br>BLE localization<br>with advanced<br>algorithms|Focus on localization<br>algorithms; does not<br>address API design or<br>integration into<br>hospital workflows|



11 

Related Work 

|**Hospitals**<br>**adopting**<br>**RFID/RTLS/**<br>**AI [11]**|RFID and<br>RTLS<br>(including<br>BLE) in<br>hospital<br>operations|Various<br>vendor<br>platforms<br>and<br>integrations|Operational<br>improvement<br>and analytics|Shows growing<br>interest in RTLS<br>and related<br>technologies|Descriptive; does not<br>present a concrete<br>BLE + REST<br>prototype|
|---|---|---|---|---|---|
|**FHIR /**<br>**interoperabil**<br>**ity reviews**<br>**[8, 7]**|Not specific to<br>one RTLS;<br>focus on HL7,<br>FHIR and<br>related<br>standards|Standardize<br>d RESTful<br>APIs (FHIR<br>resources)<br>between<br>EHRs and<br>apps|General<br>interoperabilit<br>y, data<br>exchange,<br>decision<br>support|Provide models<br>and patterns for<br>REST‑based<br>exchange of<br>clinical data|Do not cover<br>real‑time location<br>streams; limited<br>guidance on<br>integrating RTLS<br>data with FHIR<br>resources|
|**REST‑API**<br>**testing in**<br>**healthcare**<br>**IoT [9]**|Multiple<br>medical devices<br>integrated via<br>REST APIs<br>(non‑RTLS‑spe<br>cific)|RESTful<br>APIs with<br>evolving<br>schemas;<br>automated<br>testing tools|Reliability of<br>healthcare<br>IoT backends|Empirical<br>evaluation of<br>REST‑API<br>testing tools on a<br>real healthcare<br>platform|Focuses on testing;<br>does not address<br>RTLS design or<br>BLE‑based<br>localization|
|**Proposed**<br>**solution (this**<br>**project)**|BLE beacons<br>detected by<br>ESP32 nodes;<br>optional<br>QR‑code ID|Simple<br>RESTful<br>API, JSON<br>over HTTP,<br>integration<br>via Mirth<br>Connect|Near<br>real‑time<br>view of<br>tagged<br>patients and<br>equipment|Unifies low‑cost<br>BLE detection<br>with a<br>lightweight,<br>documented<br>REST API and<br>hospital<br>integration<br>engine|Prototype scale only;<br>not a full RTLS or<br>PTAT platform, but a<br>modular component<br>that can be extended<br>in future|



Overall, the literature indicates that there is still limited evidence of lightweight, implemented BLE-based RTLS solutions that simultaneously support continuous room-level detection, whitelist-based filtering of BLE beacons, flexible storage of locations and histories, documented RESTful access, and concrete integration with a hospital-grade integration engine. In this context, this report contributes a modular BLE-based RTLS prototype designed to balance deployment cost, integration flexibility, and practical usability within a hospital environment. 

12 

System Development 

### **3. SYSTEM DEVELOPMENT** 

This chapter describes the development of the prototype. It begins with the analysis of functional and non‑functional requirements, then presents the chosen technologies and overall architecture, and finally details the implementation of the room nodes, backend, database, integration layer and dashboard. 

#### **3.1. Requirements Analysis** 

The requirements were elicited through meetings with the supervisor and the hospital IT team, as well as through constraints identified during the internship. Initial ideas from the project proposal were discussed and refined, leading to the functional and non‑functional requirements summarized below. 

##### **3.1.1. Functional Requirements** 

From discussions with the project supervisors and the hospital IT team, the following functional requirements were defined for the prototype. Each requirement describes what the system shall do and, where possible, the expected output. 

###### • **FR1 - Continuous detection per room** 

The system shall continuously detect BLE tracking devices (BLE beacons) in each covered area using room nodes installed in the corresponding rooms or corridors. Each room node shall periodically produce a list of detected devices containing at least a unique device identifier, a signal-strength value and a timestamp, so that the backend always has a recent view of which tracking devices are present in each room. 

###### • **FR2 - Whitelist‑based identification of tracking devices** 

The system shall support a configurable whitelist in which each tracking device is uniquely registered. For every detection received from a room node, the backend shall check the device identifier against this whitelist and classify the detection as either 

13 

System Development 

“whitelisted tracking device” or “other device”. Only devices in the whitelist shall be treated as valid tracking devices that participate in the location logic. 

###### • **FR3 - Storage of current location and movement history** 

For every whitelisted tracking device, the system shall maintain its latest known room and last detection timestamp, as well as a chronological history of movements between rooms. New detections from the same room shall update the current-location record, while room changes shall add a new entry to the movement history, so that later queries can reconstruct where and when a device has moved. 

###### • **FR4 - Generation and delivery of movement events** 

When the backend detects that a whitelisted tracking device has changed room compared to its previously stored location, it shall create a movement event containing at least the device identifier, previous room, new room, relevant signal-strength information and detection time. This event shall be sent to the hospital integration layer so that other systems can react, for example by updating a patient record or triggering an alert. 

###### • **FR5 - Live visualization of detections and device status** 

The system shall provide a web-based dashboard that allows authenticated users to see, in near real time, all devices currently detected by each room node and to distinguish whitelisted tracking devices from other devices. The dashboard shall also allow users to inspect basic information about each whitelisted device, such as its current room and last detection time. 

###### • **FR6 - API for querying locations and histories** 

The system shall expose a programmatic interface that allows authorized clients, such as the dashboard and external hospital applications, to query the current location and status of each whitelisted device and to retrieve its movement history. The interface shall provide operations to list active devices per room, obtain detailed information and history for a specific device and access the most recent detections reported by each sensing unit, so that other systems can integrate location data into their own workflows. 

14 

System Development 

To clarify the intended output, two typical usage scenarios were considered: 

###### • **Patient transfer scenario** 

A patient receives a tracking device that is registered in the whitelist and associated with the patient in an external hospital system. The patient is initially in an emergency‑room (ER) covered by room node **R1** , which periodically reports detections to the backend. When the patient is transported to the imaging department, the device stops being detected by **R1** and starts being detected by room node **R2** . When a new detection from **R2** arrives, the backend compares the previously stored room (ER **- R1** ) with the new room (Imaging 

**- R2** ), recognises a room change, updates the current‑location and history records and generates a movement event that is delivered to the integration engine, which can then notify the hospital information system so that the patient’s current location is updated automatically. Figure 3.1 summarizes this patient-transfer scenario as a use case diagram, showing the main actors involved: the ESP32 room node, backend, web dashboard, and HIS. 

15 



<!-- Start of picture text -->
RTLS Prototype<br>1. Detect BLE beacon<br>| | 2. Send detection batch<br>ESP32 Room Node<br>3. Filter whitelisted device<br>AS<br>a 5. Update current 6. Store movement 8. Displaycurrent<br>location history location<br>Web Dashboard<br>Backend<br>eo<br>9. Update patient location in HIS k<br>Hospital Information<br>System (HIS)<br><!-- End of picture text -->

System Development 

##### **3.1.2. Non-Functional Requirements** 

In addition to the functional behavior, the prototype shall satisfy a set of non-functional requirements related to configuration, performance, scalability, security and integration with the existing hospital infrastructure. 

###### • **NFR1 - Whitelist management and consistency** 

Each tracked device shall be uniquely registered in a central whitelist managed through the administrative views of the dashboard. Changes to this whitelist (addition, update or removal of entries) shall take effect for subsequent detections without requiring changes to the room nodes, ensuring consistent classification of devices and limiting maintenance overhead. 

###### • **NFR2 - Comprehensive scanning capability** 

Every room node shall continuously detect and report all nearby devices of the relevant technology, independently of whether they are registered in the whitelist. This guarantees that the system can be used during commissioning to discover new device identifiers, to verify that coverage is adequate in each room and to observe potential interference from other devices, while leaving the decision on storage and integration to the backend. 

###### • **NFR3 - Robust data filtering and storage discipline** 

The backend shall enforce strict filtering so that only detections from whitelisted devices are forwarded to the integration engine as RTSL data. Detections from non-whitelisted devices may be exposed in short-lived “live view” endpoints for diagnostic and commissioning purposes but shall not accumulate in long-term storage. This keeps the data model focused on clinically relevant devices, simplifies queries and prevents unnecessary growth of history collections. 

###### • **NFR4 - End-to-end latency** 

Under normal operating conditions, the end-to-end latency between a device being detected by a room node and the corresponding update becoming visible on the dashboard or being reflected in a movement event delivered to the integration engine shall typically 

17 

System Development 

be < 5s and shall not exceed 10s in the prototype deployment with two room nodes and up to three tracking devices. This requirement constrains parameters such as scan intervals, batch sizes and backend processing so that the system behaves as a near real-time location service rather than an offline reporting system. 

###### • **NFR5 - Scalability and robustness to load (prototype scope)** 

In the current prototype, the system shall reliably support two room nodes and at least three simultaneously active tracking devices without loss of detections and with dashboard response times below 2s for typical queries. The design shall, however, remain extensible so that additional room nodes and devices can be added in future work by scaling the backend and database if necessary. 

###### • **NFR6 - Security and privacy** 

The prototype shall minimize the handling of personal data by restricting stored identifiers to technical values such as device identifiers and internal keys, leaving the association with real patients or equipment to external hospital systems. Access to administrative functions and live views shall be restricted to authenticated users, and communication between room nodes, backend and dashboard shall comply with the hospital’s network security policies. This reduces privacy risks while still providing useful location information to integrated systems. 

#### **3.2. Technology stack selection** 

The prototype relies on a compact technology stack that combines low-cost sensing hardware with widely used software components. Each element in the stack was chosen to satisfy a specific subset of the functional requirements from Section 3.1 while keeping the overall solution easy to deploy, integrate and maintain in a hospital environment. The following subsections describe the main components and the rationale for each choice. 

18 



<!-- Start of picture text -->
° op lea Ae, eS yi =: =<br>Ja ne ee<br>c eanks2= 5282<br>O SSSe@eeoooooooooqo00n a<br>a ae eee eee eee SEE ae<br>= 2 3<br>=" : ‘@&eeFire eetleé<br>DFROBOCT FireBeetle Board—ESP32<br>s Beers 8 88 5 e2a88038<br>D, esagkegeSSeebstbes .<br>BGaeeeoeoo0000000008<br><!-- End of picture text -->



<!-- Start of picture text -->
¢ Simple setup ¢ More low-level control ¢ Rapid scripting<br>¢ Built-in Wi-Fi/BLE libraries ¢ FreeRTOS support e Easier syntax<br>e Serial monitor for debugging e Higher complexity e Higher runtime overhead<br>e Suitable for prototype e Steeper learning curve ¢ Less suitable for<br>development continuous BLE scanning<br><!-- End of picture text -->

System Development 

between hardware cost, power consumption, and deployment complexity for room-level tracking. In particular, the selected beacons support FR1 (being continuously detectable in covered areas) and contribute to easy, non-intrusive deployment (NFR3). 

The prototype uses Seeed Studio E5 BLE Location Beacons, built on an nRF52-series chip and implementing Bluetooth LE 5.0. Each beacon supports configurable transmission power between −30 and +4 dBm and advertising intervals from 100 ms to 10 s, enabling tuning of coverage and battery life for different environments. The devices are battery-powered, with a replaceable 2400 mAh lithium cell designed for multi-year operation in the default configuration, which aligns with the requirement for limited maintenance overhead. 

Wi-Fi RTT (Round-Trip Time) could provide sub-metre accuracy using existing hospital Wi-Fi infrastructure but requires 802.11mc-capable access points that were not available in the prototype environment. UWB offers centimetre-level precision but requires dedicated anchor hardware at significantly higher cost per room. Passive RFID requires line-of-sight scanning and is therefore unsuitable for continuous, automatic detection. Active RFID provides automatic detection but at higher infrastructure cost and with less flexible beacon form factors. BLE beacons therefore represent the most practical and cost-effective option for room-level, continuous, passive identification in the target environment. Figure 3.4 shows the physical BLE beacon used in the prototype. 



**Figure 3.4. Seeed Studio E5 BLE tracking beacon** 

21 



<!-- Start of picture text -->
& @ Flask + Python django. pjango © Fastari<br>. r ; — ‘ High-performance<br>Lightweight micro-framework Built-in ORM and admin tools asynchronous framework<br>Simple REST API development More feature-rich framework setaeworkloadsrte rntaaes<br>Flexible and easy to maintain Higher complexity for Additional concepts and<br>this use case setup overhead<br>Suitable for modest Less suitable for a Unnecessary for expected<br>prototype workload lightweight prototype prototype scale<br><!-- End of picture text -->



<!-- Start of picture text -->
ESP32 Room Nodes Flask Backend API<br>5) MongoDB<br>Se<br><!-- End of picture text -->



<!-- Start of picture text -->
G@ Mirth Connect 4.5.2-Lo.. 9 — x<br>Server:  /htkps://192<br>Mirth" Connect<br>by NextGen Healthcare<br><!-- End of picture text -->



<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard<br>Dashboard<br>Live. BLE Devices.<br>Components ESP ID ESP Name Room MAC RSSI Time<br>& Esp Mapping esp001 Sensor Emergency 3f:a8:Scef:1d:b1 32 2025-11-21 16:25:23<br>oO Whitelist— esp001 Sensor1 Emergency 4e:0d:9¢:d2:fc:95 48 2025-11-21 16:25:23<br>esp001 Sensor! Emergency §2:01:8a:90:95:12 55 2025-11-21 16:25:23<br>will Mirth esp001 Sensor1 Emergency §4:8b:b7:76:f5:c8-8b:b7:76:f5: 47 2025-11-21 16:25:2325:<br>esp001 Sensor1 Emergency €3:00:00:13:3b:b7 27 2025-11-21 16:25:23<br>esp001 Sensor1 Emergency €3:00:00:13:3b:f2 30 2025-11-21 16:25:23<br>esp001 Sensor! Emergency €3:00:00:13:3¢:1e 42 2025-11-21 16:25:23<br>esp001 Sensor! Emergency eb:23:ef:e4:f9:0d 47 2025-11-21 16:25:23<br><!-- End of picture text -->

System Development 

**Table 3.1.Technology stack and main responsibilities.** 

|**Component**|**Technology**|**Rationale (summary)**|
|---|---|---|
|**Room sensing**|FireBeetle ESP32 boards<br>(Wi-Fi+BLE)|Low-cost, dual-radio, low power, widely supported|
|**Identification**|BLE beacons|Battery-powered, room-level presence, easily<br>attached to patients or mobile equipment|
|**Node firmware**|Arduino IDE + ESP32<br>libraries|Simple C/C++ model, fast development, built-in<br>Wi-Fi/BLE support|
|**Backend API**|Python + Flask|Lightweight REST framework, easy JSON/HTTP<br>handling, small codebase|
|**Database**|MongoDB|Document model fits JSON events; flexible schema<br>for current/history|
|**Integration**|Mirth Connect|Reuses existing HL7/FHIR infrastructure;<br>centralizes transformations|
|**Web dashboard**|React +<br>HTML/CSS/JavaScript|Component-based UI, automatic updates|



The technology stack is deliberately minimal and built from widely used technologies, which reduces implementation risk and simplifies deployment, integration and maintenance in hospital environments. 

#### **3.3. System Architecture Overview** 

This project presents a prototype RTLS for hospital environments that relies on BLE-based beacons and ESP32 receiver nodes organized in a four-layer architecture, as shown in Figure 3.9. The main purpose of the prototype is to detect all BLE devices present in selected hospital areas and, within that set, identify which devices belong to a predefined whitelist of valid tracking beacons. These whitelisted beacons may later be physically attached to patients or to mobile assets such as wheelchairs, but the actual association between a beacon and a specific patient or item is performed by existing hospital systems and their users, not by the prototype itself. 

26 



<!-- Start of picture text -->
BLECollection beaconsof location-relatedand ESP32 roomsignalsnodes; from ESP32beacons roomand nodesend -detections scan for nearbyto backend BLE<br>1st Layer of) ( BLEequipment. beacons attached to patients or Bluetooth tags - for user identification.<br>r Sensor management; Backend - collects detection data from<br>ond L www Ll) Collection of location-related data; ESP32 nodes and filters by whitelist;<br>nd Layer =k Y— Connection with the Hospital application layer. Frontend - sensor management and lags.<br>a> Connector with the sensor and location Hospital connector- receives location events<br>3rd Layer = management layer. from whitelisted BLE beacons via backend;<br>= @ Database - storage of location data.<br>— Association of BLE beacons with patients or Frontend - Hospital applications and ;<br>4th Layer Bi YU~ equinment:quipment, ; dashboards;  for associatingaaaBLE beacons with<br>Tr ae Provision of current location to hospital staff. patients or assets and visualizing their<br>—— locations.<br><!-- End of picture text -->

System Development 

The fourth layer is formed by hospital applications and user interfaces that consume the location information produced by the prototype. Existing systems such as electronic medical records, asset-management tools or alerting platforms can associate BLE beacons with specific patients or equipment and update their own records and screens based on the movement events delivered through Mirth Connect. The web dashboard developed in this work also belongs to this layer, providing a browser-based view of live detections, current locations and recent histories, but leaving all clinical logic and patient identification to the existing hospital application. 

The localization model adopted in this prototype is intentionally simple. A beacon is assumed to be located in the room corresponding to the ESP32 node that reports its detection, which is a reasonable approach for a proof of concept but introduces technical limitations. In particular, RSSI values are inherently unstable and can be affected by distance, orientation, walls, interference, and human movement, while overlapping coverage areas between adjacent ESP32 nodes may lead to ambiguous or incorrect room assignments. As a result, the prototype should be understood as providing room-level proximity estimation rather than precise indoor positioning. Misclassification between neighboring rooms can occur, especially near doorways or in areas where signal propagation overlaps, and no advanced localization techniques such as multi-node RSSI fusion, fingerprinting, or trilateration were implemented in this work. These approaches could improve robustness and localization accuracy, but they would also increase calibration effort, algorithmic complexity, and deployment overhead, which were outside the scope of the internship. Therefore, the chosen design provides a functional and easily deployable architecture that is sufficient to validate the end-to-end flow of beacon detection, room-level location tracking, data storage, and system integration in a hospital-oriented prototype. 

Figure 3.10 illustrates the main data flow of the prototype, from BLE detections collected by the ESP32 room node to backend filtering, storage, dashboard access, movement-event generation, and integration with hospital information systems through Mirth Connect. 

28 



<!-- Start of picture text -->
F (BLERoom Scan Node+ WiFi) (JSON) (Receives Detection Data) (JSON) y:<br>aes<br>y (Check Whitelist Filter Web Dashboard(React)<br> whether device is registered) (Monitoring & Mat nt)<br>!<br>Y<br>Non-whitelisted Detection Whitelisted Detection | len See a ie<br>! Dashboard Functions 1<br>' (2) Live Device view '<br>Pa eh Ei | '<br>Distorted1 Live.  view only / ' @ (Latest__Lexation room per Store device) © (ChronologicalMovementHistoryrecords) | '|\ {E],Roompeo Mappings* 11<br>| (Not persisted in database) | | $= Whitelist Management |<br>Cees wees esc? ‘ {<br>: Q Movement History 1<br>S Sie Mick 4st as Epa cand?<br>‘ww = MongodB(Data Store) PeeeeRead Data<br>je Oe aaS<br>{ m= Data fiow —> Flask: Room Change Detection<br>| 777% API/ Data Access ' = (Compare new room with previous room)<br>| (7) Processing / Filtering :<br>He: } Data Storage / Update '<br>|i (7)(__] ProcessingDatabase  / Logic '; ral Movement(Create movement Event Generator event)<br>[7] Integration / External System |'<br>1aera Rejectedaici asec/ Not Stored ' > Mirth Connect > HIS<br><< (Send events to Hospital Information System)<br><!-- End of picture text -->

System Development 

#### **3.4. Implementation Details** 

##### **3.4.1. ESP32 room node** 

To collect information from BLE beacons, the system uses ESP32 microcontrollers installed in selected hospital rooms. Each ESP32 runs the same firmware but is configured with a unique identifier (ESP_ID) and name (ESP_NAME) that represent the physical room. The node periodically scans for nearby BLE devices and sends all detections to the backend over the hospital Wi-Fi network. 

In the prototype, two FireBeetle ESP32 room nodes were deployed, powered by 5 V USB adapters and installed high on the wall of an emergency room and an adjacent corridor to maximize BLE coverage and ensure stable Wi-Fi connectivity. The nodes behave as stateless sensors: they do not store any detection history locally and can be restarted without reconfiguration. 

In each cycle, the ESP32 performs a BLE scan for a fixed duration, discards detections below a configurable RSSI threshold and builds a JSON array where each entry contains esp_id, esp_name, mac and rssi for one detected device. If at least one device passes the filter, this JSON batch is sent via HTTP POST to the `/api/bledata` endpoint so that the backend always has a recent view of which BLE beacons are present in each covered area. In the prototype, the scan interval of each ESP32 room node was set to 2s and the RSSI cutoff to -60 dBm, values chosen to provide near real-time updates while ignoring weak signals that are unlikely to correspond to beacons inside the room. A status LED indicates whether at least one device above the threshold was seen in the last scan, which is useful during installation and troubleshooting but does not affect the backend logic. 

Figure 3.11 illustrates this flow: BLE beacons in the room broadcast advertising packets, the ESP32 room node scans and sends detections via HTTP over the hospital Wi-Fi network, and the backend forwards processed data to MongoDB and to the dashboard and integration engine. 

30 



<!-- Start of picture text -->
BLE devices in room<br>(BLE beacons / phones)<br>(BLE advertising)<br>ESP Room Node<br>-BLE scan<br>-\Wi-Fi client<br>Wi-Fi (HTTP PosT<br>fapl /bledata<br>Backend (Flask API)<br>WIFI Router<br>(locations & history) events to Mirth<br>S MongoDB React Dashboard / =<br><!-- End of picture text -->

System Development 

adequate at small scale but would need refinement or clock synchronization in larger multi-node deployments to ensure consistent event ordering across rooms. 

##### **3.4.2. Live detection and commissioning** 

During commissioning and testing, the same ESP32 room nodes were used not only for continuous tracking but also for discovering which BLE devices were present in each area. Even when the whitelist was empty or incomplete, the room nodes still scanned for all nearby BLE devices that passed the RSSI filter and sent their MAC addresses and RSSI values to the backend, which exposed this information through a live view in the web dashboard. 

This behavior allowed IT staff to observe, in real time, which BLE devices were active in each room and to identify the MAC addresses that should be registered as tracking beacons in the whitelist. Once a beacon’s MAC address was added to the whitelist via the administrative interface, subsequent detections of that beacon began were stored in MongoDB. If the backend detected that the beacon had moved from one room to another, a movement event was generated and sent to Mirth Connect. Detections from non-whitelisted devices remained visible only in the short-lived live view for diagnostic and commissioning purposes. In this way, commissioning and adjustment of the whitelist could be performed using only the deployed ESP32 room nodes, without requiring additional hardware. 

##### **3.4.3. Cloud and Integration Layer** 

The backend, database and integration engine together form the “cloud” part of the system. The Flask application exposes the `/api/bledata` endpoint, which receives HTTP POST requests from ESP32 room nodes, parses the JSON payload and processes each detection. For every MAC address, the backend determines the room using the ESP identifier and checks whether the device is present in the whitelist. Only detections whose MAC address is in the whitelist are persisted, updating the current-location record and appending entries to the movement history in MongoDB. When the backend detects that a whitelisted beacon is now assigned to a different room than in the previous record, it generates a movement event and forwards it to Mirth Connect, where it can be transformed and routed to external hospital systems. 

32 



<!-- Start of picture text -->
Receiveat /api/bledata POST (0)<br>-verify-useCheckESP32_ID whitelistMAC in whitelist andto determine map roomroom:=fO}~ -beacon_latest(current-beacon_history(movementUpdate MongoDB location)history)=<br>No yA . Yes |Create movement event JSON<br>oom changed since -MAC, old room, new room<br>last record ? -timestamp,: RSSI M<br>External(EMR, assethospital mgmt,systems alerts) SendConnectto Mirth Ps)<br><!-- End of picture text -->

System Development 

generated, the backend attempts to deliver it to Mirth Connect as a JSON message. If Mirth Connect or the relevant channel is unavailable, the event may not be delivered during that period because the current prototype does not implement a persistent event queue or automatic retry mechanism. This limitation affects integration reliability rather than BLE detection itself and motivates future work on queued event delivery, retry policies, and delivery-status monitoring. 

##### **3.4.4. Web dashboard behaviour** 

The web dashboard provides a browser-based interface for operational and administrative staff to monitor detections and manage basic configuration of the RTLS prototype. After authentication, the dashboard periodically calls read-only REST endpoints such as `/api/data` and `/api/beacon-history/<mac>` to obtain live detections, current locations and recent histories, which are rendered in the “Live BLE Devices” and per-beacon history views. Configuration tabs such as “ESP Mapping” and “Beacon Whitelist” use the same authenticated API to list and update mappings and whitelist entries, so changes are immediately reflected in subsequent ingestion and visualization. The dashboard therefore acts purely as a client of the backend, concentrating on presentation and interaction while all sensing, storage and integration logic remains on the server side and in Mirth Connect. 

34 

Prototype Testing and Results 

### **4. PROTOTYPE TESTING AND RESULTS** 

This chapter presents the tests carried out to evaluate the RTLS prototype and discusses the results obtained under the tested conditions. The evaluation was structured in three stages. First, component-level functional tests were performed to verify the main parts of the prototype, including ESP32 room-node scanning, backend ingestion, whitelist filtering, MongoDB persistence, dashboard visualization, administrator access, and movement-event delivery to Mirth Connect. Second, representative end-to-end scenarios were executed to verify that BLE detections could be transformed into current-location updates, movement histories, dashboard views, and integration events. Third, basic performance indicators were measured, including end-toend latency, detection reliability, and database query response time. 

The purpose of the evaluation was not to validate the prototype as a production-ready hospital RTLS, but to verify whether the implemented system satisfied the functional requirements defined for the internship prototype. The tests were conducted using a limited setup with two ESP32 room nodes, a small number of BLE beacons, a Flask backend, MongoDB, the React dashboard, and Mirth Connect. Therefore, the results should be interpreted as evidence of feasibility under controlled test conditions rather than proof of robustness at hospital-wide scale. 

#### **4.1. Functional Testing** 

Functional testing combined low‑level tests of individual components with end‑to‑end validation of the main use cases, using the Arduino IDE serial monitor, Postman and the React dashboard as primary tools. The aim was to confirm that the implemented prototype satisfies functional requirements FR1-FR6 and the related non-functional requirements on configuration, data handling and integration behavior. For each test, the evaluated component, test method, expected result, and observed status were recorded. A test was considered successful when the observed behavior matched the expected result without manual correction during the test execution. The tests were 

35 

Prototype Testing and Results 

performed using the Arduino IDE serial monitor, Postman, MongoDB Compass, backend logs, Mirth Connect, and the React dashboard. 

##### **4.1.1. Functional test matrix** 

Table 4.1 summarizes the main functional tests performed, indicating for each use case the component or endpoint under test, the method used, the expected behavior and the outcome. 

**Table 4.1. Functional test matrix.** 

|**Use Case**|**Component**<br>**/API endpoint**|**Test method**|**Expected result**|**Status**|
|---|---|---|---|---|
|**BLE device**<br>**detection per**<br>**room**|ESP32 room<br>nodes (esp001,<br>esp002)|Arduino IDE<br>Serial monitor|Multiple MAC/RSSI detections<br>per scan cycle for nearby BLE<br>devices in each room.|Pass|
|**Backend data**<br>**ingestion**|`/api/bledat`<br>`a`<br>(Flask backend)|Automatic<br>ESP32 POSTs;|HTTP 200, JSON list processed<br>without errors.|Pass|
|**Whitelist**<br>**filtering and**<br>**persistence**|Whitelist,<br>beacon-history,<br>beacon-latest<br>(MongoDB)|Postman +<br>MongoDB<br>Compass|Only whitelisted MACs stored<br>in`beacon_latest`and<br>`beacon_history`; non-<br>whitelisted devices ignored.|Pass|
|**Admin signup**<br>**and login**|`/api/signup`<br>,<br>`/api/login`,<br>dashboard auth|Postman +<br>dashboard UI|Accounts created and access<br>granted only with valid<br>credentials; invalid logins<br>rejected.|Pass|
|**Live device**<br>**visualization**|`/api/data`,<br>`/api/beacon`<br>`-`<br>`history/<ma`<br>`c>`, dashboard<br>views|Postman;<br>dashboard Live<br>Devices&<br>whitelist tabs|Live view shows all currently<br>detected BLE devices; only<br>whitelisted ones have stored<br>status and viewable history.|Pass|
|**Movement**<br>**events to Mirth**<br>**Connect**|`bledata,`<br>`/api/send-`<br>`active-`<br>`beacons-to-`<br>`mirth`|Backend logs +<br>Mirth channel|JSON movement events are<br>generated and delivered when a<br>whitelisted beacon changes<br>room.|Pass|



The functional test matrix covers the main data path of the prototype, from BLE detection by the ESP32 room nodes to backend ingestion, whitelist filtering, MongoDB persistence, dashboard visualization, authentication, and movement-event delivery to Mirth Connect. Although the tests were performed on a limited prototype configuration, they provide evidence that the implemented components behaved according to the expected functional requirements under the tested conditions. 

36 

Prototype Testing and Results 

##### **4.1.2. Components tests: ESP32 room nodes, backend and dashboard** 

Before executing end-to-end scenarios, each major component of the prototype was tested in isolation to confirm its basic behavior: the ESP32 room nodes and BLE scanning logic, the backend ingestion and whitelist-based persistence in MongoDB, and the dashboard visualization and administration workflows. 

###### **4.1.2.1. ESP32 room nodes and BLE scanning** 

This component test validated the continuous detection of nearby BLE devices and the preparation of scan data for backend ingestion, addressing the continuous detection requirement FR1 and the comprehensive scanning capability NFR2. Two FireBeetle ESP32 development boards were configured as room nodes with identifiers esp001 (“Sensor1”) and esp002 (“Sensor2”), each connected to the hospital network and running identical firmware except for the ESP identifier and name. The firmware used the ESP32 BLE stack to perform active scans with a duration of 2s, applying an RSSI cutoff of -60 dBm so that only nearby devices were considered, and toggled an on-board LED to indicate whether any device above the cutoff had been detected during the latest scan window. 

During each scan cycle, the firmware collected the MAC address and RSSI value of every BLE device whose signal strength exceeded the cutoff and aggregated these detections into a JSON array, including the fields ESP_ID, ESP_NAME, MAC, and RSSI for each device. At the same time, the MAC/RSSI pairs were printed between explicit “scan start” and “scan end” markers on the Arduino IDE serial monitor, allowing manual inspection of the number of detections obtained in each 2s window. Figure 4.1 illustrates a representative scan for Sensor1, showing multiple MAC/RSSI lines per scan and confirming that the room node can discover several nearby BLE devices simultaneously 

37 



<!-- Start of picture text -->
-’ ESP32 Dev Module ~ Vv 2<br>latest.ino —<br>#include WiFi.h<br>#include <HTTPClient.h><br>#include <BLEDevice.h<br>#include <BLEScan.h<br>i#tinclude <BLEAdvertisedDevice.h<br>* WIFI_SSID = “UlNPRe TTEFTES"S<br>* WIFI_PASSWORD = ""; ~~<br>+ SERVER_URL “http 172.29.°7%,%%n 5000/api/bledata";<br>* ESP_ID = “espeei";<br>* ESP_NAME = “Sensor1";<br>SCAN_TIME_SECONDS = 2;<br>CUTOFF_RSSI = -60;<br>LED_PIN = 2;<br>BLEScan* bleScanner;<br>Of<br>22 : ("Connecting to Wi-Fi: %s\n", WIFI_SSID);<br>- (WIFI_STA);<br>5 (WIFI_SSID, WIFI_PASSWORD);<br>attempts = 0;<br>hile ¢ . () l= WL_CONNECTED && attempts < 30) {<br>(500):<br>utpu Serial Monitor x < oOo =<br>New Li ~|| 5200 bau ~<br>LE AN STAI<br>MAC:MAC:b 2 A47:ee:13:c8:f1:22ztec:8f:9a:55:e1:47:e0:44:a5 ||| RSSI:RSF I:I: 5342 ¢dBm4 ava<br>MAC: 5£:66:ab:cf:6arca | RSST: aBm<br>MAC: c:12: seS: 3 | F Is 6a an<br>MAC:MAC:M 2 3:00:00:13:©3:00:00:13:3b:b7:00:00:13:3b:£23c: le ||| RSST:RS RSSI:I: 2 0 dBmdBm« a<br>MAC: ed:88:b3:£4:4a:0b | RSST: > dBm<br>LE SCAN ENE<br><!-- End of picture text -->



<!-- Start of picture text -->
°<br>sonity( history<br>’<br>TERMINAL python - backend<br>» Pre [ t uit<br>. l le [@2 2026 1 | bay. pi l T )<br><!-- End of picture text -->



<!-- Start of picture text -->
°<br>Compass @ Welcome & beocon_whitelist = +<br>) My Queries localhost:27017 >» templ_db > beacon_whitelist > Open MongoDB shell +<br># Data Modeling Documents 3 Aggregations Schema Indexes 1 Validation<br>Ee<br>CONNECTIONS (2) ><br>Or Type a query: field: 'value’ } or | Explain Reset Options><br>Search connections<br>—— GE ajc -j\e 100 ¥}1-30f3O -|@Gois<br>> & cluster0.ceirusj.mongodb.net<br>v & locolhost:2701732701 _id: ObjectId('68d27¢358a789bb90a863504')<br>> & codmin mac: ''c3:00:00:13:3b:f2"<br>added_at: 2025-09-23711:02:13.984+00:00<br>> & config<br>> & local<br>id: ObjectId( '68d27e628a789bb90a86350b' )<br>y & tempi_db mac: ''c3:00:00:13:3b:b7"<br>Bs cdmin_users . addedidded_at :at: 2025-09-2372025-09- 11:02:58.173+60:0002:5 73+60:00<br>Bi beccon_history<br>Bw beccon_latest: id: ObjectId('68d2851e8a789bb90a863512' )<br>mac: ''¢3:60:00:13:3c:le"<br>Be beacon_whitelist ove added_at : 2025-09-237T11:31:42.086+00:00<br>Be esp_mapping<br><!-- End of picture text -->



<!-- Start of picture text -->
( My Queries localhost:27017 > templ_db > beacon_history >_ Open MongoDB shell +<br>«& Data Modeling Documents 9.4K Aggregations Schema Indexes 2 Validation<br>CONNECTIONS (2) X tom Qo Type a query: field: ‘value’ } or Explain Reset Options><br>Search connections ys<br>L> $ clusterO.ceirusj.mongodb.net GB) ((e -j\(+)a.- 93019378 - 9378 of 2 < US. =@=5<br>¥ & locothost:27017 So: =<br>>» 40": (Qh,<br>> & admin "esp_id": "espee2",<br>% "“esp_name”: "Sensor2",<br>> & config "room": "Imaging",<br>> & local "ssi":"mac": "c3:66:66:13:3c:1le",-39,<br>» & templ_db "time": "2626-64-02 15:31:54"<br>}<br>Be ccmin_users<br>Be beacon_history: oes wed» 90": 163},<br>Bm beacon_totest "esp_id":“esp_name”:"espeo1""Sensor.",<br>Be beocon_whitelist "room": "Radiology",<br>"mac": "c3:60:00:13:3b:b7",<br>Be esp_mopping "rssi": -1T,<br>"time": "2026-64-02 15:31:57"<br>}<br>oj) vt= mgams iESe ? fe) |e<br>"esp_id": "espee2",<br>"esp_name”: "Sensor2",<br>"room": "Imaging",<br>“mac”: "c3:@6:60:13:3b:f2",<br>Spast“: ~—42,<br>"time": "2026-04-02 15:31:58"<br><!-- End of picture text -->



<!-- Start of picture text -->
ADMIN SIGNUP ADMIN LOGIN<br>niane@gmail.com niane@gmail.com<br>Sp clea Login<br><!-- End of picture text -->



<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard<br>Dashboard<br>Live° BLE Devices°<br>Cent PETE ESP ID ESP Name Room MAC RSSI Time<br>3 ESP Mapping esp002 Sensor2 Imaging 3:00:00:13:3b:f2 -40 2026-04-02 17:25:12<br>oO Whitelist— esp001 Sensor1 Radiology €3:00:00:13:3b:b7 -20 2026-04-02 17:25:12<br>esp002 Sensor2 Imaging €3:00:00:13:3c:1e -36 2026-04-02 17:25:12<br>will Mirth esp001 Sensorl Radiology 52:b9:13:34:84:08 42 2026-04-02 17:25:12<br>esp001 Sensor Radiology de:20:6¢:51:9f:38 -44 2026-04-02 17:25:12<br><!-- End of picture text -->



<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard<br>Dashboard<br>@® Live Devices ESP Ma ppings<br>Components ESP ID<br>Room<br>© Whitelist (EINE spl)<br>alll Mirth ESP ID Room Action<br>esp001 Radiology | Delete |<br>esp002 Imaging Delete |<br><!-- End of picture text -->

##### Beacon Whitelist 



<!-- Start of picture text -->
MAC Address Action History<br>€3:00:00:13:3b:f2<br>€3:00:00:13:3b:b7<br>€3:00:00:13:3c:1e<br><!-- End of picture text -->

History for beacon: c3:00:00:13:3b:f2 

|ESP ID|ESP Name|Room|MAC|RSSI|Time|
|---|---|---|---|---|---|
|esp002|Sensor2|Imaging|€3:00:00:13:3b:f2|-38|2026-04-02 17:28:19|
|esp002|Sensor2|Imaging|€3:00:00:13:3b:f2|-40|2026-04-02 17:28:16|
|esp002|Sensor2|Imaging|€3:00:00:13:3b:f2|-37|2026-04-02 17:28:13|
|esp002|Sensor2|Imaging|€3:00:00:13:3b:f2|-38|2026-04-02 17:28:10|
|esp002|Sensor2|Imaging|€3:00:00:13:3b:f2|-41|2026-04-02 17:28:07|
|esp002|Sensor2|Imaging|¢3:00:00:13:3b:f2|-36|2026-04-0217:28:04|





<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard<br>Dashboard<br>@ Live Devices Beacon Management<br>3 ESP Mapping Active Beacons (3)<br>© Whitelist MAC Address Room RSSI Last Seen Status<br>¢3:00:00:13:3 b:f2 Imaging -38 2026-04-02 17:28:19 ¥ Sent<br>€3:00:00:13:3c:le Imaging Se 2026-04-02 17:28:19 ¥ Sent<br>¢3:00:00:13:3b:b7 Radiology -22 2026-04-02 17:28:10 ¥ Sent<br>Inactive Beacons (0)<br>No inactive beacons<br><!-- End of picture text -->



<!-- Start of picture text -->
@ Message ><br><RemoteAddress>192.168.1.253</RemoteAddress> a<br><RequestUrl>http: //192.168.1.117:6661/</RequestUrl><br><Method>POST</Method><br><RequestPath/><br><RequestContextPath>/</RequestContextPath><br><Header><br><Accept>*/*</Accept><br><User-Agent>python-requests/2.32.5</User-Agent><br><Connection>keep-alive</Connection><br><Host>192.168.1.117:6661</Host><br><Accept-Encoding>gzip, deflate, zstd</Accept-Encoding> g<br><Content-Length>479< /Content-Length> q<br><Content-Type>application/json</Content-Type> |<br></Header><br><Content multipart="no">{"beacons™:<br>[{"esp_id": “esp002", “esp_name": "Sensor2", "room": "Imaging", "mac": "c3:00:00:13:3b:f£2", “rssi": -34, “time: "2026-04-02 22:48:15"},<br>{"esp_id™: “esp002", “esp_name": “Sensor2", "room": “Imaging”, "mac™: "c3:00:00:13:3c:le", “rssi": -35, “time™: "2026-04-02 22:48:15"},<br>{"esp_id™: “espOO01", “esp_name™: “Sensorl", "room": "Radiology", "mac™: "c3:00:00:13:3b:b7", “rssi™: -32, “time: "2026-04-02 23:14:57"}],<br>"summary": "Successfully sent active beacons to Mirth"}</Content><br></HttpRequest><br>.<br>Open Binary File...<br><!-- End of picture text -->



<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard<br>Dashboard<br>Live BLE Devices<br>(SIE PETMETALE ESPID ESPName Room MAC RSSI_ Time<br>3 ESP Mapping esp001 Sensor Radiology 6e:48:16:e6:6c:b8 -26 2026-04-02 22:49:33<br>Oo Whitelist—— esp001 Sensor Radiology | ¢3:00:00:13:3b:b7 -22 2026-04-02 22:49:33<br>esp001 Sensor Radiology d0:95:cc:80:92:d7 -24 2026-04-02 22:49:33<br>alll Mirth<br><!-- End of picture text -->



<!-- Start of picture text -->
MENU Hospital BLE Tracking Dashboard | Logout<br>Dashboard<br>Live BLE Devices<br>Components ESP ID ESP Name Reom MAC RSS| Time<br>EB ESPMapping esp002 Sensor? Imaging 40 2026-04-02 23:08:18<br>© Whitelist es p eool Sensor Radioload Tet sacaTral 26 2026-04-02 23:08:18<br>epool Sengori Radiclogy ae69:0d7:f6:55:b9 -24 2026-04-02 2308518<br>alll Mirth<br><!-- End of picture text -->



<!-- Start of picture text -->
@ Message x<br><HttpRequest> -<br><RemoteAddress>192.168. ‘RemoteAddress><br><RequestUrl>http: //192.16¢ 1/</RequestUr1><br><Method>POST</Method><br><RequestPath/><br><RequestContextPath> /</RequestContextPath><br><Header><br><Accept>*/*</Accept><br><User-Agent>python-requests/2.32.5</User-Agent><br><Connection>keep-alive</Connection><br><Host>192.168.1 -</Host><br><Accept-Encoding>gzip, deflate, zstd</Accept-Encoding><br><Content-Length>252</Content-Length><br><Content-Type>application/json< /Content-Type><br></Header><br><Content multipart="no">{"event™: “beacon_location_change", “summary”:<br>"Beacon [c3:00:00:13:3b:b7<br>| (vesp_ia™: “esp002", “esp_name™:joved from{Radiology|to“Sensor2", "room": (Imaging|,“Imaging”,"beacon":"mac": "yssi": -30, "time": 2026-04-02 22:58:56"}}</Content><br></HttpRequest><br>a] ><br><!-- End of picture text -->



<!-- Start of picture text -->
@ Message x<br><HttpRequest> «|<br><RemoteAddress>192.11 ‘RemoteAddress><br><RequestUrl>http: //192.168 /</RequestUrl><br><Method>POST< /Method><br><RequestPath/><br><RequestContextPath>/</RequestContextPath><br><Header><br><Accept>*/*</Accept><br><User-Agent>python-requests/2.32.5</User-Agent><br><Connection>keep-alive</Connection><br><Host>192.168.1. i/Host><br><Accept-Encoding>gzip, deflate, zstd</Accept-Encoding><br><Content-Length>254</Content-Length><br><Content-Type>application/json< /Content-Type><br></Header><br>"Beacon (5:00:00:13:3n:b7]{"esp_id™:<Content“esp001",multipart="no">{"event™:“esp_name":uovea trou{naging]to[Reaiology|“Sensorl",“beacon“room”:location_change","Radiology",“beacon:"summary":"mac":[c3: 00:00:13: 3b:b7"} "resi": -34, “time™: "2026-04-02 23:12:43"}}</Content><br></HttpRequest><br>i)<br>i] “|<br><!-- End of picture text -->



<!-- Start of picture text -->
GET v http://192.168 Yapi/data | send<br>= Docs Pararns Auth Headers (10} Body e Scripts Tests Settings Cookie<br>sody v ©) 401 UNAUTHORIZED 17ms  234B @ Save Response ¢<br>{} JSON Y  — Preview §% Pass the correct auth credentials Vv => =Q Ge<br>41vi<br>2 | "error": "Unauthorized"<br>3}<br><!-- End of picture text -->



<!-- Start of picture text -->
= Docs Params Auth Headers (10) Body e Scripts Tests Settings Cookies<br>Body ~ 200 OK 7ms 5768 ® fs) Save Response «<-<br>{} JSON~ Db Preview G9 Visuslize ~ > =a 0862<br>2 sc<br>2i<br>3 "“esp_id*: “espoo2*,<br>4 “esp_name*: “Sensor2*,<br>5 *mac*: *c3:00:00:13:3b:22°, =<br>6 *xoom*: “Imaging”,<br>7 “xssi*: -44,<br>8 “time*: “2026-04-02 16:04:41°<br>9 ¥.<br>10 i<br>11 *esp_id*: “espoo1*,<br>a2 “esp_mame*: “Sensori*,<br>a3 “mac”: “¢3:00:00:13:3b:b7",<br>a4 *xoom": “Radiology”,<br>a5 “xssi": -15,<br>16 *“time*: “2026-06-62 16:04:43°<br>a7 I.<br>a9 “esp_id": “espoo2*,<br>29 *esp_name*: “Sensor2*,<br>21 "mac": “c3:06:00:13:3c:41¢",<br>22 *xoom*: “Imaging*,<br>23 “xssi*: -42,<br>24 “time”: “2026-64-62 16:04:19"<br>25 I<br>oud View QQ Gi Console ©) Terminal HiRuner & G& Avan BF CG<br><!-- End of picture text -->

|GET|“<br>ntp7//1982<br>40<br>COOs/api/asta||
|---|---|---|
|=Docs|Params<br>Auth<br>Headers (10)<br>Body<br>©<br>Scripts<br>Tests<br>Settings|Cookies|
|Body<br>~|£&<br>200 OK<br>7 ms<br>5768<br>&<br>8 SaveResp|onse +|
|{} JS|ON v<br>> Preview<br>G9 Visusiize<br>~<br>=><br>Q|OD 2|
|2|c||
|2|i||
|J|“esp_id*:<br>“espoo2*,||
|a|“esp_name*:<br>“Sensor2*,||
|5|*“mac*:<br>“c3:00:00:13:3b:f£2"°,|=|
|6|*xoom*:<br>“Imaging*,||
|7|“xssi*:<br>-44,||
|6|“time*:<br>"2026-06-02<br>16:04:41°||
|°|i.||
|2|i||
|21|“esp_id*:<br>*espoo1*,||
|a2|“esp_name*:<br>“Sensori*,||
|a3|“mac*><br>*¢€3:00:00:13:3b:b7".||
|14|*xoom":<br>“Radioclogy’.||
|a6|“xesi*:<br>-15,||
|16|*“time*:<br>°2026-04-02<br>16:04:43°||
|17|}.||
|as|{||
|a°|“esp_id*:<br>“espoo2*,||
|2|“esp_name*:<br>“Sensor2*,||
|21|“mac*:<br>“¢3:00:00:13:3c:1¢",||
|22|*xoom*:<br>“Imaging”*,||
|23|“xesi*:<br>42,||
|24<br>25|“time:<br>°2026-04-02<br>16:06:19"<br>}||





<!-- Start of picture text -->
GET ~ httpy/ 192.4 . api/beacon-historyfcs:0000:12:3bf2<br>=DPocs Params Auth Headers (10) Body® Scripts Tests Settings Cookies<br>Body ~ <7) 200 OK 86éms - 363.96KeB - GD Ee] Save Response os<br>{} JSON ~ [ Preview [FJ] Visualize ~ = =a Bh &<br>roe fa<br>2d<br>3 "asp_id": “espoo2",<br>4 "asp_name": “Sensor2",<br>5 "mac": “e3:0@:@@0413:3b:22°,<br>6 "room": "Imaging",<br>T “rssi": -44,<br>3 "time": "2026-94-02 16:05:45"<br>9 ie<br>190 £<br>41 "asp_id": “espod2",<br>42 "@Sp_name": “Sensor2",<br>413 "mac": “c3:00200°13:3b:f2",<br>44 "room": "Imaging",<br>15 “rssi": -43,<br>16 "time": "2026-04-02 16:05:24"<br>17 be<br>16 {<br>a9 "esp_id": “espoo2",<br>20 "“asp_name": "Sensor",<br>21 “mac"s “c3:00700213:3b:f2",<br>22 "room": "Imaging",<br>23 “rssi": -aa,<br>24 "time": "2026-04-02 16:05:11"<br>25 te<br>dView © (Console E) Terminal ElRunner  & AvVeun HE<br><!-- End of picture text -->

Prototype Testing and Results 

#### **4.2. Performance Testing** 

This test evaluates whether the prototype can process detections from multiple ESP32 room nodes and deliver updates to the dashboard and integration engine with acceptable latency and reliability at the scale of the pilot deployment, addressing the near real-time requirement NFR4 and supporting FR3-FR4. 

Two FireBeetle ESP32 nodes (esp001 “Sensor1” in Radiology and esp002 “Sensor2” in Imaging) were configured as described in Section 4.1.2.1, performing active BLE scans with a duration of 2s and an RSSI cutoff of -60 dBm and sending JSON batches to the `/api/bledata` endpoint. Three whitelisted beacons were distributed between the two rooms and moved periodically to generate a continuous stream of detections. The backend (Flask application and MongoDB) and Mirth Connect ran on a single hospital virtual machine accessed over the hospital Wi-Fi network, and the React dashboard was used to observe live updates. 

Performance was assessed along three dimensions: End-to-end latency, detection reliability, and API/database query response time. End-to-end latency was defined as the time between the physical movement of a beacon into another room, noted manually, and the moment when the corresponding location update appeared in the Live BLE Devices table and as a movement event in the Mirth Connect channel. This measurement includes the BLE scan delay, HTTP transmission from the ESP32 node to the backend, backend processing, MongoDB persistence, dashboard refresh, and delivery of the movement event to Mirth Connect. Detection reliability was assessed during continuous operation by checking whether the expected detections for the present whitelisted beacons were received across repeated scan cycles. In the firmware used for the prototype, each ESP32 scan lasted 2 seconds and was followed by a short delay before the next cycle. API/database query performance was evaluated by issuing repeated REST API read requests and monitoring response times for current-location and movementhistory queries, particularly `/api/data` and `/api/beacon-history/<mac>` . 

Across several minutes of continuous operation with three whitelisted beacons and two room nodes, the end-to-end latency from beacon detection through backend processing, MongoDB persistence, dashboard update, and Mirth Connect event delivery was observed to remain below five seconds under stable network conditions. In 

52 

Prototype Testing and Results 

this configuration, detection reliability was observed to be 100% during the monitored test period, with ESP32 nodes batching and transmitting scan results over the hospital Wi-Fi network without missing expected detections in the observed scan cycles. Backend processing handled the received detections without visible queuing delays. REST API response times for current-location and movement-history queries through `/api/data` and `/api/beacon-history/<mac>` remained below 20 ms, indicating that the database layer did not constitute a performance bottleneck at the tested scale. 

**Table 4.2. Performance metric for the prototype configuration.** 

|**Metric**|**Measured value**|**Comment**|
|---|---|---|
|**End-to-end latency**|<5s|From room entry to dashboard update and<br>movement event|
|**Detection reliability**|100%|Three whitelisted beacons, 30s scan interval, no<br>lost detections|
|**MongoDB query time**|<20ms|api/data and /api/beacon-history/<mac> current-<br>location lookups|



These measurements are limited to a small deployment with two ESP32 nodes, three whitelisted beacons, and a single backend server under stable network conditions. They also relied on manual timing rather than automated benchmarking tools, because the prototype did not include synchronized timestamps or automated logging at each stage of the pipeline. Larger numbers of nodes and devices, shorter scan cycles, concurrent external API clients, and adverse network scenarios were not exercised. Therefore, additional load and stress testing would be required to characterize throughput limits, tail latencies, and fault tolerance before considering deployment in a production hospital environment. 

#### **4.3. Limitations** 

Despite meeting the functional requirements in the controlled test environment, the prototype has several limitations that need to be addressed before deployment in a production hospital setting. The evaluation was performed with a small-scale setup and simplified conditions, so the results should be interpreted as evidence of feasibility rather than proof of robustness at hospital scale. 

First, reliability and scalability were evaluated with only two ESP32 room nodes and a small number of whitelisted beacons, using relatively long scan intervals and 

53 

Prototype Testing and Results 

a single backend instance. Performance under higher densities of devices, shorter scan intervals, overlapping coverage areas and more complex network conditions remains untested, and no systematic load or stress testing was performed to identify throughput limits or tail latencies. Additional experiments with more nodes and synthetic traffic would be required to characterize behavior under peak usage, including the impact on end-to-end latency and movement event generation. 

Second, robustness and fault tolerance were not evaluated in depth. The tests assumed stable Wi-Fi connectivity, continuous backend availability and a responsive Mirth Connect channel. Scenarios such as temporary network failures, backend restarts, Mirth unavailability or ESP32 reboots were not systematically exercised, so it is unknown how many detection batches or movement events might be lost in these situations or how quickly the system recovers. The current implementation does not include explicit retry strategies, buffering mechanisms or redundancy, which would be essential in a clinical environment where missed events could have operational consequences. 

Third, the current security model is minimal and suitable only for a prototype. Authentication relies on a simple username header without session management or token-based mechanisms, and communication between ESP32 nodes, backend, dashboard and Mirth Connect is not encrypted. There is no role-based access control, audit logging or protection against common web security threats. For deployment in a real hospital, the system would require hardened authentication and authorization, transport-level encryption (for example HTTPS and secure Wi-Fi), and integration with existing identity management and logging processes. 

Fourth, the prototype relies on simplifying assumptions in device identification and timing. BLE MAC addresses are used as the main identifiers for detected devices, which is suitable for the dedicated beacons used in the prototype but may not apply to all BLE devices because some devices use address randomization for privacy. In addition, the ESP32 room nodes do not generate synchronized timestamps. Instead, each detection batch is timestamped by the Flask backend when it is received and processed. This is acceptable for the small-scale prototype but may affect event ordering and comparability in larger multi-node deployments. 

Finally, the localization approach and user interface also have inherent limitations. The system provides room-level rather than bed-level location based on 

54 

Prototype Testing and Results 

RSSI-based proximity, which is sensitive to interference, obstacles and multipath effects and was not evaluated in boundary scenarios between adjacent rooms. More advanced techniques such as multi-node RSSI fusion, hysteresis rules or time-window averaging were not implemented. The administrative interfaces offer basic monitoring and configuration but lack advanced features such as alerts, analytics, reporting, or fine-grained access control. Together, these constraints frame the prototype as a proof-of-concept suitable for exploring integration patterns and workflows rather than as a fully engineered clinical product. 

55 

Conclusion 

### **5. CONCLUSIONS** 

This chapter summarizes the main outcomes of the professional internship and reflects on the contributions of the developed RTLS prototype. It also outlines future work, distinguishing between short‑term improvements that can be built directly on the current implementation and longer-term developments that would require more extensive redesign, infrastructure, and validation. 

#### **5.1. Summary of Contributions** 

This project demonstrated the feasibility of a prototype RTLS for hospital environments based on BLE beacons and ESP32 receiver nodes. The work progressed through defined phases, including requirements analysis, technology selection, system architecture design, implementation of hardware and software components, frontend development, integration configuration, and functional testing. Within the scope of the prototype, the system demonstrated continuous BLE scanning across covered areas, whitelist-based filtering of tracking beacons, persistent storage of current locations and movement histories in MongoDB, and delivery of movement events to the Mirth Connect integration engine under the tested conditions. In the evaluated setup, the end-to-end latency was observed to remain below five seconds, indicating that the prototype can support near real-time room-level visibility in small-scale controlled scenarios. The prototype enables near real-time visualization of tagged devices through a web-based dashboard and exposes RESTful API endpoints that support interaction between the sensing, storage, visualization, and integration components. Developed in collaboration with the hospital IT team, the solution was designed to respect operational constraints related to network security, data privacy, and interoperability, while avoiding the storage of clinical identifiers within the RTLS component itself. The main contributions of this work include the design of a low-cost and modular BLE-based tracking architecture, the implementation of ESP32-based room nodes, the development of a Flask backend with whitelist-based filtering and movement-history storage, the integration of movement- 

56 

Conclusion 

event delivery through Mirth Connect, and the creation of a web-based dashboard for visualization and basic configuration. Although the prototype was evaluated only under limited test conditions, it provides a practical foundation for future work on scalability, security hardening, improved localization accuracy, and broader integration with hospital information systems. 

#### **5.2. Future Work** 

Future work can be organized into short-term improvements that build directly on the current prototype and longer-term developments that would require more extensive redesign, infrastructure, and validation. In the short term, one priority is to add buffering and retry mechanisms in the ESP32 room nodes or backend, so that detection batches and movement events are not lost during temporary network failures or backend unavailability. The RSSI-based filtering strategy should also be refined through calibration in different hospital rooms, since signal strength varies with walls, furniture, interference, and beacon orientation. Simple techniques such as time-window averaging, hysteresis rules, or configurable per-room thresholds could reduce unstable room assignments without significantly increasing system complexity. The web dashboard could be extended with more practical monitoring functions, including clearer device status indicators, beacon last-seen timestamps, basic alerts for prolonged inactivity, and improved administration of room mappings and beacon registration. On the backend, stronger authentication, role-based access control, audit logging, and HTTPS communication would be necessary before considering any use beyond a controlled prototype environment. Further short-term work should include more systematic testing. The current evaluation was performed with a limited number of ESP32 nodes and beacons under controlled conditions, so additional experiments should measure latency, detection reliability, and data consistency over longer periods and under different network and room configurations. Automated logging and metric collection would make evaluations more reproducible and allow basic statistical analysis of performance. 

In the longer term, the system could be extended toward larger-scale deployment across additional hospital areas, which would require planning of ESP32 node placement, coverage overlap, network capacity, and maintenance procedures. More 

57 

Conclusion 

advanced localization techniques, such as multi-node RSSI fusion, trilateration, fingerprinting, or machine-learning-based approaches, could be investigated if higher accuracy is required, though these would increase complexity and demand more extensive calibration and validation. A further longer-term direction is deeper integration with hospital information systems. While the current prototype delivers movement events through Mirth Connect under tested conditions, future versions could explore more formal mappings to interoperability standards such as HL7 or FHIR, in collaboration with hospital IT and clinical teams, to define how location events should be associated with patients, assets, encounters, and clinical workflows. Overall, the prototype provides a practical foundation for further development, but additional work is required before it can be considered suitable for production deployment. The next steps should therefore focus first on reliability, security, evaluation, and maintainability, before progressing toward larger-scale deployment or more advanced localization and interoperability features. 

58 

Bibliography 

### **BIBLIOGRAPHY** 

- [1]  U. M. A. Kamal, N. A. Nayan, R. Jaafar and S.-N. A. Ismail, "Medical Asset Tracking Technologies in Healthcare: A Review," _Journal of Information Science and Engineering,_ vol. 41, no. 4, pp. 1009-1029, Jul. 2025. 

- [2]  K. Hadian, G. Fernie and A. Roshan Fekr, "Development and Evaluation of BLE-Based Room-Level Localization to Improve Hand Hygiene Performance Estimation," _Journal of Healthcare Engineering,_ vol. 2023, p. Article ID 4258362, Jan. 2023. 

- [3]  J. Frisby, V. Smith, S. Traub and V. L. Patel, "Contextual Computing: A Bluetooth based approach for tracking healthcare providers in the emergency room," _Journal of Biomedical Informatics,_ vol. 65, pp. 97-104, Nov. 2016. 

- [4]  Z. Iqbal, D. Luo, P. Henry, S. Kazemifar, T. Rozario, Y. Yan, K. Westover, W. Lu, D. Nguyen, T. Long, J. Wang, H. Choy and S. Jiang, "Accurate real time localization tracking in a clinical environment using Bluetooth Low Energy and deep learning," _PLOS ONE,_ vol. 13, no. 10, p. e0205392, oct. 2018. 

- [5]  K. M. Overmann, D. T. Y. Wu, C. T. Xu, S. S. Bindhu and L. Barrick, "Real-time locating systems to improve healthcare delivery: A systematic review," _Journal of the American Medical Informatics Association,_ vol. 28, no. 6, p. 1308–1317, Mar. 2021. 

- [6]  G. R. Muthu Arumugam, K. S. Muthu Anbananthen and S. Muthaiyah, "An IoT BLE based system literature review of real time location monitoring and tracking to shorten patient wait times in Malaysian public hospitals," _F1000Research,_ vol. 14, p. 14:568, Jun. 2025. 

- [7]  N. Pimenta, A. Chaves, R. Sousa, A. Abelha and H. Peixoto, "Interoperability of clinical data through FHIR: A review," _Procedia Computer Science,_ vol. 220, pp. 856-861, 2023. 

- [8]  D. Osamika, B. S. Adelusi, M. T. C. Kelvin-Agwu, A. Y. Mustapha, A. Y. Forkuo and N. Ikhalea, "A Critical Review of Health Data Interoperability Standards: FHIR, HL7, and Beyond," _World Scientific News,_ vol. 203, pp. 195-233, May 2025. 

- [9]  H. Sartaj, S. Ali and J. M. Gjøby, "REST API Testing in DevOps: A Study on an Evolving Healthcare IoT Application," _CoRR,_ Jul. 2025 . 

- [10] Kontakt.io, “RTLS vs. RFID: The Pros and Cons of Both for Asset Tracking and Management,” 2024. [Online]. Available: https://kontakt.io/blog/rtls-vs-rfid-the-prosand-cons-of-both-for-asset-tracking-and-management/. [Accessed 15 November 2025]. 

- [11] M. Hickey, "Hospitals look to RFID, RTLS, AI to improve operations: Study," RFID JOURNAL, 2024. [Online]. Available: https://www.rfidjournal.com/news/hospitalslook-to-rfid-rtls-ai-to-improve-operations-study/215652/. [Accessed 15 November 2025]. 

- [12] ESPBoards, "ESP32 Development Boards," 2025. [Online]. Available: https://www.espboards.dev/esp32/microcontroller/esp32/. [Accessed 20 November 2025]. 

59 

Bibliography 

- [13] DFROBOT, "FireBeetle ESP32 IOT Microcontroller(V3.0) - DFRobot Wiki," 2025. [Online]. Available: 

   - https://wiki.dfrobot.com/FireBeetle_ESP32_IOT_Microcontroller(V3.0)__Supports_WiFi_%26_Bluetooth__SKU__DFR0478. [Accessed 18 november 2025]. 

- [14] Arduino, "Arduino IDE," 2024. [Online]. Available: https://docs.arduino.cc/software/ide/. [Accessed 17 october 2025]. 

- [15] Python, "The Python Tutorial," 2001. [Online]. Available: https://docs.python.org/3/tutorial/. [Accessed 10 September 2025]. 

- [16] Pallets, "Tutorial," 2010. [Online]. Available: https://flask.palletsprojects.com/en/stable/tutorial/. [Accessed 17 August 2025]. 

- [17] GeeksforGeeks, "Create Database using MongoDB Compass," 2025. [Online]. Available: https://www.geeksforgeeks.org/mongodb/create-database-using-mongodbcompass/. [Accessed 10 August 2025]. 

- [18] N. Healthcare, "Experience the power of Mirth Connect," 2025. [Online]. Available: https://www.nextgen.com/solutions/interoperability/mirth-integration-engine. [Accessed 3 November 2025]. 

- [19] J. Erolin, "React Single Page Application," 2025. [Online]. Available: https://www.bairesdev.com/blog/react-spa-single-page-application/. [Accessed 25 October 2025]. 

- [20] B. Vaillants, "Building Modern Web Apps: A Complete Guide to React Single Page Applications," 2025. [Online]. Available: https://bix-tech.com/building-modern-webapps-react-spa-guide/. [Accessed 27 November 2025]. 

- [21] B. Gnan, "ble_hosptal_react: A real-time BLE tracking dashboard for hospitals using ESP32, Flask, React, and MongoDB," 2025. [Online]. Available: https://github.com/bella-cd/ble_hosptal_react. [Accessed 2025]. 

- [22] M. Ayaz, M. F. Pasha, M. Y. Alzahrani, R. Budiarto and D. Stiawan, "The Fast Health Interoperability Resources (FHIR) Standard: Systematic Literature Review of Implementations, Applications, Challenges and Opportunities," _JMIR Medical Informatics,_ vol. 9, no. 7, p. e21929, Aug. 2021. 

60 

