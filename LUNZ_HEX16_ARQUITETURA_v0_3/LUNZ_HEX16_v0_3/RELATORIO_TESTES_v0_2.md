# LUNZ HEX-16 v0.2 — Relatório de testes

**Status:** testes de software aprovados; decisão física de arquitetura ainda em aberto.

## 1. O que foi corrigido desde a v0.1

Na v0.1, o campo de tamanho de L1 estava presente, mas não influenciava as estimativas. A v0.2 agora faz a capacidade L1 alterar a taxa de acerto estimada, os misses de L1, a atividade estimada de DRAM, a latência e a energia calculada. A distribuição aleatória de carga entre núcleos também foi normalizada para manter exatamente a carga solicitada.

Isso significa que os números da v0.2 **não devem ser comparados diretamente** com os números da v0.1: o modelo inclui custos que antes estavam ausentes.

## 2. Resultado principal: L1 de 14 KiB vs 16 KiB

Configuração: clock nominal de 3 GHz, 16 núcleos, 160 milhões de instruções, fração de operações de memória de 25%, fração de comunicação de 5% e seed 7.

| Métrica | 14 KiB por L1I e L1D | 16 KiB por L1I e L1D |
|---|---:|---:|
| Throughput estimado | 15,829 GIPS | 16,334 GIPS |
| Tempo de parede estimado | 10.108,055 µs | 9.795,445 µs |
| Energia calculada | 117,489 mJ | 112,716 mJ |
| Potência média calculada | 11,623 W | 11,507 W |
| Energia por instrução | 0,7343 nJ | 0,7045 nJ |
| DRAM misses estimados | 1,02628 M | 0,96000 M |
| Capacidade total de L1 (16 núcleos, I+D) | 448 KiB | 512 KiB |

No modelo atual, 14 KiB reduz 64 KiB de capacidade L1 total (12,5%), mas tem throughput cerca de 3,1% menor e energia calculada cerca de 4,2% maior. O modelo **não inclui uma estimativa calibrada da economia de área, energia de acesso e leakage das células SRAM menores**; por isso, o resultado não escolhe sozinho o tamanho físico final.

## 3. Geometria de cache

Com linhas de 64 bytes e associatividade de quatro vias:

- **14 KiB:** 224 linhas, 56 conjuntos; o número de conjuntos não é potência de dois.
- **16 KiB:** 256 linhas, 64 conjuntos; o número de conjuntos é potência de dois.

A implementação de 14 KiB ainda pode ser viável, mas os custos de indexação, timing e seleção dos conjuntos devem ser sintetizados em RTL antes de afirmar que a economia de capacidade vira economia real de área/energia. Outra opção experimental seria 7 vias e 32 conjuntos, que tem outro custo de comparadores e seleção.

## 4. Sensibilidade a cargas sintéticas

| Carga | 14 KiB GIPS | 16 KiB GIPS | Energia 14 KiB | Energia 16 KiB |
|---|---:|---:|---:|---:|
| Computação intensiva | 20,084 | 20,574 | 84,965 mJ | 82,084 mJ |
| Equilibrada | 15,829 | 16,334 | 117,489 mJ | 112,716 mJ |
| Memória intensiva | 12,378 | 12,904 | 163,844 mJ | 155,761 mJ |
| Comunicação intensiva | 12,869 | 13,135 | 139,834 mJ | 136,007 mJ |

São workloads sintéticos, não traces de aplicações reais. A tendência é mais forte em cargas intensivas de memória, o que era esperado a partir da lei de taxa de misses utilizada.

## 5. Sensibilidade à lei de capacidade

Foi variado o expoente hipotético da estimativa de misses, mantendo os parâmetros-base de hit rate para 16 KiB:

| Expoente | L1I hit estimado (14 KiB) | L1D hit estimado (14 KiB) | Throughput 14 KiB | Energia 14 KiB |
|---:|---:|---:|---:|---:|
| 0,25 | 97,932% | 91,728% | 16,082 GIPS | 115,063 mJ |
| 0,50 | 97,862% | 91,448% | 15,829 GIPS | 117,489 mJ |
| 0,75 | 97,789% | 91,157% | 15,576 GIPS | 119,998 mJ |

A diferença entre 14 e 16 KiB depende diretamente dessa hipótese matemática. O próximo passo científico é substituir a lei de escala por traces de acesso e simulação LRU/set-associative.

## 6. Varredura de frequência

A varredura com L1 de 16 KiB e os parâmetros padrões mostrou a troca esperada no modelo entre tempo, potência e energia. Os resultados estão em `results/frequency_sweep.txt`. A tendência de energia por instrução neste modelo está fortemente influenciada pelo custo estático assumido e pela estratégia simplificada de “race to idle”; não deve ser interpretada como previsão de silício real.

## 7. Testes de software

**11 testes automatizados passaram**, incluindo:

- 16 nós, conectividade, grau máximo de seis vizinhos e simetria das distâncias;
- geometria de 14/16 KiB e efeito crescente da capacidade sobre a taxa de hit estimada;
- rejeição de parâmetros inválidos e frequências fora dos limites;
- conservação exata da carga total de instruções;
- reprodutibilidade para o mesmo seed;
- consistência interna de potência, energia e throughput;
- tendência comparativa 14 KiB vs 16 KiB para os parâmetros-base.

Logs: `results/unit_tests.txt`, `results/test_run.txt`, `results/sensitivity_report.txt`.

## 8. Conclusão de engenharia

A recomendação provisória é manter ambas as capacidades como candidatas. **16 KiB é a referência mais simples para 4 vias; 14 KiB economiza 12,5% de capacidade, mas exige demonstrar que o custo de indexação e os misses adicionais não anulam a economia de SRAM.** Não há, nesta versão, base para afirmar que HEX-16 supera x86, ARM ou RISC-V: falta comparar workloads e implementações equivalentes.

O próximo passo técnico recomendado é um modelo set-associative baseado em traces (I-cache e D-cache separados), seguido por RTL/SystemVerilog e síntese para obter área e timing, antes de tirar conclusões sobre custo físico.
