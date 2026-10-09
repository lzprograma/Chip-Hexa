# LUNZ HEX-16 v0.3 — arquitetura-base

Esta pasta contém a especificação preliminar da arquitetura, um arquivo JSON de parâmetros, o registro de decisões, o simulador analítico v0.2 e seu relatório anterior.

## Arquivos

- `ESPECIFICACAO_LUNZ_HEX16_v0_3.md` — definição técnica da linha de base.
- `LUNZ_HEX16_BASELINE.json` — parâmetros estruturados para integração futura com ferramentas.
- `REGISTRO_DE_DECISOES.md` — o que está decidido, provisório ou experimental.
- `lunz_hex16.py` — simulador arquitetural analítico v0.2 (não é RTL).
- `RELATORIO_TESTES_v0_2.md` — relatório da versão anterior do simulador.

## Executar simulador v0.2

Requer Python 3.9+ e não usa dependências externas:

```bash
python lunz_hex16.py
python lunz_hex16.py --freq 3.0 --l1-kib 14
python lunz_hex16.py --cache-sweep
python lunz_hex16.py --sweep
python lunz_hex16.py --topology
```

O JSON v0.3 é uma especificação de parâmetros para referência; o simulador v0.2 ainda não lê esse JSON automaticamente.

## Estado honesto do projeto

A especificação é uma proposta arquitetural. Ainda não existe RTL funcional do LUNZ-64, não há síntese de área/timing e as métricas de potência/desempenho são estimativas de simulação. A arquitetura não foi demonstrada superior a processadores comerciais nem a outras ISAs abertas.
