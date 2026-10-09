# LUNZ HEX-16 — registro de decisões v0.3

| Tópico | Decisão-base | Estado | Gatilho para alterar |
|---|---|---|---|
| Núcleos | 16 homogêneos | Proposta-base | Área/térmica inviável na tecnologia escolhida |
| Execução | In-order, emissão simples | Proposta-base | Benchmarks mostram ganho material com custo justificável |
| ISA | Própria LUNZ-64, instruções de 32 bits | Rascunho | Revisão de encoding antes do montador/RTL congelar |
| Clock | 3 GHz nominal, selecionável dentro da faixa validada | Meta, não garantia | Timing closure e caracterização da tecnologia |
| Frequência máxima | 3 GHz para alvo de primeira implementação | Provisório | Síntese/implementação física sustenta outra frequência |
| L1 | 16 KiB I + 16 KiB D por núcleo | Referência | Traces + energia de SRAM + síntese favorecem alternativa |
| L1 de 14 KiB | Variante de pesquisa, 7 vias × 32 conjuntos como candidata | Aberto | Resultado mensurável supera referência na função objetivo |
| L2 | 128 KiB por slice, 2 MiB total | Proposta-base | Área/miss rate justificam reduzir/aumentar |
| NoC | Grafo de vizinhança hexagonal, links de 64 bits | Hipótese central | Comparação justa não mostra benefício sobre alternativas |
| Coerência | Diretório MSI | Rascunho | Verificação revela custo/problema ou protocolo menor equivalente |
| DVFS | Um domínio comum no primeiro RTL | Escolha de simplicidade | Evidência mostra que DVFS por cluster paga sua complexidade |
| Energia | Clock gating individual; sem power-gating de cluster inicialmente | Proposta-base | L2/diretório podem ser preservados e economia validada |
| Aceleradores | Nenhum GPU/NPU/IA/SIMD/SMT na primeira versão | Decisão-base | Só reabrir com workload e análise custo/benefício claros |
| Ponto flutuante | FPU dedicada fora do primeiro chip | Decisão-base provisória | Benchmarks de software mostram penalidade impeditiva |
| Software | Emulador e montador antes do RTL multicore | Plano | Reavaliar sequência somente após ISA suficientemente estável |

## Regra de engenharia

Não registrar como “ganho de silício” nenhum número que venha apenas do modelo analítico. O simulador v0.2 usa uma lei simplificada para a taxa de misses, e sua NoC ainda não modela filas/contensão com detalhe de ciclo. A comparação física exige RTL, biblioteca de células declarada, síntese e timing/potência estimada.

| Licenças | CERN-OHL-S-2.0 para hardware, MIT para ferramentas, CC BY-SA 4.0 para documentação/ISA | Recomendação inicial | Revisão dos termos oficiais e dependências antes de publicar |
