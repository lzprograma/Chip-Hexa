# LUNZ HEX-16 — Especificação-base de arquitetura v0.3

**Estado:** proposta técnica inicial; aberta para revisão.  
**Propósito:** CPU de propósito geral, aberta, de 16 núcleos homogêneos, com foco em simplicidade, eficiência por watt, área moderada e comunicação local.  
**Importante:** esta é uma especificação de arquitetura, não um desenho RTL concluído nem uma alegação de desempenho de silício.

## 1. Princípios de projeto

1. Manter uma única microarquitetura de núcleo, replicada 16 vezes.
2. Preferir mecanismos simples e mensuráveis a recursos avançados que ainda não demonstraram retorno.
3. Não incluir GPU, NPU, unidade de IA, SIMD/vetores, SMT ou aceleradores dedicados na primeira versão.
4. Tornar a frequência configurável dentro de pontos de operação validados; **3,0 GHz é a meta nominal**, não uma garantia independente do processo físico.
5. Manter uma linha de base convencional de 16 KiB por cache L1 e avaliar 14 KiB como variante experimental.
6. Usar a malha hexagonal de vizinhança como hipótese arquitetural a ser comparada contra alternativas com os mesmos workloads.
7. Não declarar vantagem sobre x86, ARM ou outras CPUs sem comparações equivalentes reproduzíveis.

## 2. Parâmetros de linha de base

| Bloco | Linha de base v0.3 | Motivo |
|---|---|---|
| ISA | LUNZ-64, própria e aberta | Liberdade de projeto; exige toolchain próprio |
| Núcleos | 16 homogêneos | Paralelismo sem núcleos grandes e heterogêneos |
| Largura arquitetural | 64 bits | Inteiros, ponteiros e registradores de 64 bits |
| Emissão | Uma instrução por ciclo por núcleo | Reduz portas, bypass e complexidade de controle |
| Execução | In-order | Evita reorder buffer e execução fora de ordem |
| Pipeline | 5 estágios: IF, ID, EX, MEM, WB | Linha de base fácil de verificar; o fechamento de timing poderá exigir ajuste |
| Clock | Selecionável por software dentro da tabela validada | Controle de consumo sem permitir pontos elétricos inseguros |
| Clock nominal | 3,0 GHz | Meta de projeto a validar em síntese e implementação física |
| Faixa de exploração do simulador | 0,5–3,5 GHz | 3,5 GHz é apenas exploração matemática; não é meta de primeira implementação |
| ISA vetorial/SIMD | Não na primeira versão | Mantém datapath e controle menores |
| FPU dedicada | Não na primeira versão | Aritmética de ponto flutuante poderá começar por software; impacto em aplicações científicas deve ser medido |
| SMT | Não | Um fluxo de instruções por núcleo |
| Previsão de desvios | Não especulativa; inicialmente assume não tomado | Evita tabela de predição e recuperação especulativa no primeiro RTL |
| Especulação | Não | Facilita precisão de exceções e verificação |

## 3. Núcleo escalar

Cada núcleo contém:

- registrador de programa de 64 bits;
- 32 registradores inteiros de 64 bits, com `r0` permanentemente igual a zero;
- ALU de 64 bits para soma, subtração, lógica, deslocamentos e comparações;
- multiplicação e divisão inteiras iterativas, de múltiplos ciclos, para evitar multiplicadores/divisores grandes e de alta potência;
- unidade de load/store;
- controle de exceções e interrupções;
- TLB pequeno para tradução de endereços;
- L1 de instruções, L1 de dados e conexão local à NoC.

Não há execução fora de ordem nem register renaming na linha de base. Uma operação de múltiplos ciclos pode bloquear o núcleo; só devemos introduzir desacoplamento se benchmarks demonstrarem que vale a área adicional.

### 3.1 Pipeline inicial

- **IF:** busca instrução de 32 bits.
- **ID:** decodificação e leitura dos registradores.
- **EX:** ALU, endereço efetivo ou avaliação do desvio.
- **MEM:** acesso à hierarquia de memória.
- **WB:** gravação de resultado.

O objetivo é um ciclo por instrução para operações inteiras simples quando não houver stalls, misses ou desvios tomados. Isso é um objetivo de microarquitetura, não garantia para toda instrução.

## 4. ISA LUNZ-64 — base preliminar

### 4.1 Regras gerais

- Instruções de comprimento fixo de **32 bits** na primeira versão. Não haverá mistura de instruções de 16/32 bits no v0.3.
- Endereçamento de memória por byte.
- Dados e instruções little-endian.
- Loads/stores alinhados são o caso rápido; acessos desalinhados geram exceção na primeira implementação.
- Operações inteiras são escalares e sobre registradores de 64 bits.
- Os formatos descritos abaixo são preliminares. Os números finais de opcode e as regras de exceção precisam ser congelados antes de se escrever um montador compatível.

### 4.2 Formatos candidatos

```text
R: [ opcode 6 | rd 5 | rs1 5 | rs2 5 | função 11 ]
I: [ opcode 6 | rd 5 | rs1 5 | imediato 16 ]
S: [ opcode 6 | base 5 | rs2 5 | deslocamento 16 ]
B: [ opcode 6 | rs1 5 | rs2 5 | deslocamento 16 ]
J: [ opcode 6 | rd 5 | deslocamento 21 ]
U: [ opcode 6 | rd 5 | imediato 21 ]
```

Imediatos I/S são assinados e expressos em bytes; deslocamentos B/J são assinados em unidades de instrução (4 bytes), somados ao PC da instrução. A semântica exata de `U` e das instruções de sistema será definida na tabela normativa de opcodes.

### 4.3 Operações necessárias à base

- Inteiros: `ADD`, `SUB`, `AND`, `OR`, `XOR`, `NOT`, shifts lógicos e aritméticos, comparações signed/unsigned.
- Imediatos: soma/lógica com imediato e construção de constantes/endereço em múltiplas instruções.
- Memória: `LB/LBU`, `LH/LHU`, `LW/LWU`, `LD`, `SB`, `SH`, `SW`, `SD`.
- Controle: `BEQ`, `BNE`, `BLT`, `BGE`, `BLTU`, `BGEU`, `JAL`, `JALR`.
- Sistema: trap/return de trap, leitura/escrita de registradores de controle, fence de memória e invalidação de instruções.
- Atomics: pelo menos `CAS`, `AMOADD` e `AMOSWAP` em palavras de 32 e 64 bits, com semântica definida antes do RTL.

### 4.4 Convenção inicial de registradores/ABI

| Registrador | Uso proposto |
|---|---|
| r0 | Zero constante |
| r1 | Endereço de retorno (RA) |
| r2 | Ponteiro de pilha (SP) |
| r3 | Ponteiro global (GP) |
| r4 | Ponteiro de thread (TP) |
| r5–r7 | Temporários voláteis |
| r8–r15 | Argumentos e retornos, voláteis conforme ABI |
| r16–r23 | Registradores preservados pela função |
| r24–r30 | Temporários/preservados conforme ABI final |
| r31 | Registrador reservado para uso de ABI; finalidade a congelar |

A convenção é uma proposta de trabalho; compilador, depurador e ABI só devem ser declarados estáveis depois de testes de conformidade.

## 5. Cache e memória

### 5.1 L1

**Configuração de referência:** cada núcleo tem L1I de 16 KiB e L1D de 16 KiB, linhas de 64 bytes, 4 vias e 64 conjuntos. Política inicial de substituição: pseudo-LRU em 4 vias. A capacidade total de L1 do chip é 512 KiB.

**Variante experimental HEX-14:** 14 KiB por L1I e L1D, total de 448 KiB. Com linhas de 64 bytes existem 224 linhas por cache. Para manter 32 conjuntos com índice de potência de dois, uma organização candidata é 7 vias; isso aumenta comparações de tags e seleção de via. Não se presume que esta variante seja mais barata até sintetizar ambas as opções e medir traces de acesso. A variante não substitui a referência de 16 KiB sem esses testes.

### 5.2 L2 distribuído

- 128 KiB de L2 por tile/núcleo, total lógico de 2 MiB.
- Cache unificado de instruções/dados por slice.
- Linha de 64 bytes, 8 vias, 256 conjuntos por slice.
- Slices distribuídas fisicamente; o endereço determina a slice-home.
- L2 e roteadores não podem ser desligados individualmente sem preservar os dados e o serviço de diretório de coerência.

Os parâmetros de L2 também são candidatos de síntese; não se assume que a capacidade escolhida seja ótima até avaliar misses e área.

### 5.3 RAM, endereçamento e MMU

- Espaço virtual: 48 bits canônicos.
- Endereço físico inicial: 40 bits (até 1 TiB de espaço físico endereçável).
- Página base: 4 KiB; page walk de quatro níveis com entradas de 64 bits.
- TLBs pequenos separados para instrução e dados, começando com 16 entradas cada por núcleo; tamanhos maiores só se o profiling justificar.
- O controlador de DRAM fica fora do núcleo e é descrito inicialmente como uma interface abstrata, para não amarrar a ISA a uma geração de memória específica.

## 6. Coerência e modelo de memória

- Coerência L1D/L2 por diretório distribuído com protocolo **MSI** (Modified, Shared, Invalid) como linha de base; sem MOESI nem protocolos especulativos avançados.
- Cada slice home mantém estado e informação de compartilhamento suficiente para invalidar cópias antes de conceder escrita exclusiva.
- Escritas em linhas compartilhadas podem sofrer latência extra; essa latência deve aparecer na simulação e nos testes de coerência.
- Buffer FIFO de escrita de dois entries por núcleo como candidato inicial, com forwarding para loads que coincidam com uma entrada. `FENCE` drena/ordena as operações anteriores.
- A semântica do modelo de memória deve especificar ordenação por endereço, atomics e fences antes do software concorrente ser considerado compatível.
- L1I precisa ter mecanismo de invalidação após modificações de código e sincronização explícita de instruções.

## 7. Interconexão HEX NoC

- 16 tiles, grafo com vizinhança hexagonal/triangular de até seis vizinhos por tile. O contorno físico atual é irregular, não um hexágono geométrico perfeito.
- Enlaces ponto a ponto full-duplex; largura de referência de 64 bits por direção.
- Latência inicial no simulador: 2 ciclos por salto a 3 GHz. É uma hipótese de modelo, não um resultado de RTL.
- Roteamento determinístico com seleção de caminho documentada e prevenção formal de deadlock antes do congelamento do RTL.
- Não usar um barramento global compartilhado como caminho normal entre os 16 núcleos.
- Os roteadores devem expor contadores de congestionamento, stalls e hops, para que a topologia seja comparada por evidência.

A malha é a hipótese central do projeto. Será comparada com uma rede mesh/torus simples, mantendo núcleos, caches, largura dos enlaces e workloads iguais. Se o hexagonal não ganhar em latência, energia ou área total, o nome não deve impedir uma mudança.

## 8. Energia, clock e estados de baixo consumo

- Um clock/frequency domain comum na primeira implementação RTL, para reduzir complexidade de CDC e distribuição de clock.
- Pontos de frequência configuráveis por software dentro dos limites validados pela implementação. Meta nominal: 3,0 GHz; faixa 0,5–3,0 GHz é alvo de exploração funcional, não garantia de viabilidade no processo escolhido.
- O software pode solicitar um perfil ou frequência; o controlador de energia/firmware aplica limites térmicos e elétricos e seleciona uma tensão validada. Usuário não pode forçar uma combinação V/f insegura.
- Clock gating individual por núcleo quando não há trabalho, mais estados `ACTIVE`, `IDLE`, `SLEEP` e `DEEP-SLEEP`.
- Power-gating de clusters fica fora da primeira versão porque as slices L2/diretório precisam continuar a servir dados ou mover o estado de forma correta.
- A estimativa dinâmica deve usar `P_dynamic ∝ C · V² · f`, mas a potência total também inclui fuga, memórias, clock tree e I/O. A fórmula isolada não prediz potência de silício.

## 9. Sistema e periféricos mínimos

Primeiro SoC/protótipo:

- ROM de boot;
- RAM de teste ou modelo de DRAM;
- temporizador e controlador de interrupções;
- UART para depuração;
- interface de debug;
- barramento simples de periféricos mapeados em memória.

Não incluir rádio 4G/5G, USB avançado, PCIe, áudio, GPU ou controlador de tela no primeiro chip. São componentes de plataforma, não requisitos da ISA; podem ser adicionados depois por IP aberto ou por um chip companheiro.

## 10. Segurança mínima

- Modos de privilégio User, Supervisor e Machine.
- Exceções precisas, interrupções por núcleo e registradores de controle explícitos.
- Permissões de páginas para leitura, escrita e execução.
- Acesso a periféricos restrito por privilégio.
- Secure boot completo, virtualização e recursos avançados de segurança ficam para uma fase posterior; o mecanismo de boot e a política de confiança terão de ser definidos antes de um produto comercial.

## 11. Plano de validação

A comparação entre variantes deve usar os mesmos workloads e registrar throughput, IPC, ciclos bloqueados, misses de L1/L2, tráfego DRAM, hops, congestionamento, latência, energia estimada, área sintetizada e frequência máxima atingida.

1. **Emulador funcional:** referência para semântica da ISA e exceções.
2. **Montador e testes de instrução:** um teste por opcode e por caso de borda.
3. **Modelo de cache baseado em traces:** substitui a lei de misses aproximada usada no simulador v0.2.
4. **Verificação multicore:** atomics, fences, invalidações e litmus tests de memória.
5. **NoC:** testes de conectividade, deadlock, saturação e tráfego concorrente.
6. **RTL/SystemVerilog:** começar com um núcleo e memória de teste; depois replicar 16 núcleos e NoC.
7. **Simulação/lint:** Verilator ou ferramenta equivalente de código aberto; assertions e regressão automatizada.
8. **Síntese e implementação física:** medir área/timing/potência estimada com biblioteca de células e processo tecnológico declarados. O fluxo OpenROAD pode servir como caminho aberto de exploração, conforme suporte da biblioteca escolhida.
9. **Benchmark público:** publicar configurações, código, seeds, traces e limites do modelo. Comparar x86/ARM/outros apenas com software, processos e limites energéticos documentados.

## 12. Itens deliberadamente fora do escopo inicial

- GPU, NPU, IA dedicada ou outros aceleradores.
- SIMD/vetores e matriz.
- FPU dedicada; a ausência afeta workloads de ponto flutuante e será avaliada com benchmarks.
- SMT, execução fora de ordem, reorder buffer e especulação.
- L3 global.
- DVFS independente por núcleo e power-gating de grupos.
- Compatibilidade binária x86/ARM.
- Rádio, tela, armazenamento e interfaces de plataforma avançadas.

## 13. Critérios para considerar uma decisão congelada

Uma decisão só passa de “proposta” a “congelada” quando:

- está descrita sem ambiguidade;
- tem testes positivos e negativos;
- passa pela regressão funcional;
- foi sintetizada para a biblioteca alvo;
- a área e o timing são reportados;
- a relação desempenho/energia foi medida em workloads definidos;
- a alternativa mais simples foi comparada, não apenas ignorada.

## 14. Política de abertura e licenças propostas

Para não confundir “código publicado” com “hardware aberto”, a distribuição deve separar as licenças por tipo de artefato:

- **RTL, netlists de referência e arquivos de hardware:** CERN-OHL-S-2.0 como proposta de reciprocidade forte, para que modificações distribuídas do hardware permaneçam compartilhadas sob os termos da licença.
- **Simulador, montador, emulador e ferramentas de software:** MIT como proposta simples e permissiva.
- **Especificação da ISA e documentação:** CC BY-SA 4.0 como proposta de atribuição e compartilhamento pela mesma licença.

Essas licenças são uma recomendação inicial, não uma decisão jurídica irrevogável. Antes de publicar, verificar os textos oficiais e a compatibilidade de componentes de terceiros. A orientação do Open Hardware Repository do CERN ressalta que hardware, firmware, software e documentação podem precisar de licenças diferentes. Referência: https://ohwr.org/licences/ .

## 15. Conclusão provisória

O equilíbrio inicial é: 16 núcleos homogêneos, núcleo escalar in-order de emissão simples, ISA fixa de 32 bits, caches de 16 KiB como referência, L2 distribuído modesto, NoC hexagonal com enlaces de 64 bits, clock configurável com meta nominal de 3 GHz e sem aceleradores dedicados. A variante de 14 KiB fica em pesquisa.

Esta configuração não é ainda comprovadamente mais barata, mais eficiente ou mais rápida que x86/ARM/RISC-V. Ela é uma linha de base compacta e verificável para gerar essa evidência.

## Referências de ferramentas

- Verilator (simulação/lint SystemVerilog): https://github.com/verilator/verilator
- OpenROAD Flow Scripts (síntese/implementação física e exploração PPA): https://openroad-flow-scripts.readthedocs.io/en/latest/tutorials/FlowTutorial.html
