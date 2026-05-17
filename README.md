# Calculadora de Repuxo Cilíndrico

Aplicação web para dimensionamento completo de processos de repuxo cilíndrico com aba simples. Desenvolvida em Python com deploy via Streamlit.

## O que a calculadora faz

A partir das dimensões do produto final (diâmetro interno, altura, diâmetro da aba, espessura, raios de concordância) e dos dados do material, o sistema calcula automaticamente:

- **Diâmetro do blank** — por conservação de área superficial, com margem de apara
- **Número de passes** — sequência mínima para atingir a geometria final
- **Dimensões por etapa** — diâmetro e altura de cada semi-produto intermediário
- **Dados técnicos de produção** — força de repuxo, pressão e força do prensa-chapas, área de contato, força de extração, capacidade mínima da prensa
- **Indicadores de severidade** — t/D, razão de repuxo (DR), relação df/d, H/d — com semáforos visuais
- **Desenhos DXF** — perfil em corte de cada etapa, do blank ao produto final

## Estrutura do projeto

```
Calculadora_Repuxo_Cilindrico/
│
├── constants.py          # Constantes físicas e coeficientes empíricos
├── materials.py          # Banco de dados de materiais
├── validators.py         # Validação de inputs
├── blank_calculator.py   # Cálculo do blank
├── pass_sequence.py      # Sequência de passes
├── process_data.py       # Forças, pressões, capacidade da prensa
├── dxf_generator.py      # Geração de arquivos DXF  [Fase 2]
├── renderer.py           # Renderização matplotlib  [Fase 2]
├── app.py                # Interface Streamlit       [Fase 3]
│
├── tests/
│   ├── test_materials.py
│   ├── test_validators.py
│   ├── test_blank_calculator.py
│   ├── test_pass_sequence.py
│   └── test_process_data.py
│
├── requirements.txt
└── README.md
```

## Instalação

```bash
git clone https://github.com/seu-usuario/Calculadora_Repuxo_Cilindrico.git
cd Calculadora_Repuxo_Cilindrico
pip install -r requirements.txt
```

## Rodando os testes

```bash
# Todos os testes com relatório de cobertura
pytest tests/ -v --cov=. --cov-report=term-missing

# Módulo específico
pytest tests/test_blank_calculator.py -v
```

## Rodando a aplicação (após Fase 3)

```bash
streamlit run app.py
```

## Materiais pré-configurados

| Material | UTS (MPa) | Ys (MPa) | m₁_lim | mₙ_lim |
|---|---|---|---|---|
| DC01 / DC04 (Aço baixo carbono) | 310 | 175 | 0.50 | 0.75 |
| Aço inoxidável AISI 304 | 600 | 255 | 0.55 | 0.78 |
| Alumínio 1100-O | 100 | 38 | 0.53 | 0.76 |
| Alumínio 3003-H14 | 165 | 140 | 0.52 | 0.75 |
| Cobre ETP C11000 | 240 | 85 | 0.50 | 0.73 |
| Latão 70/30 | 350 | 140 | 0.52 | 0.75 |

## Referências

- Kalpakjian, S. & Schmid, S.R. — *Manufacturing Engineering and Technology*, 7ª ed.
- Marciniak, Z., Duncan, J.L., Hu, S.J. — *Mechanics of Sheet Metal Forming*, 2ª ed.
- Schuler GmbH — *Metal Forming Handbook*, Springer, 1998.

## Status do desenvolvimento

- [x] Fase 1 — Núcleo de Cálculo (`constants`, `materials`, `validators`, `blank_calculator`, `pass_sequence`, `process_data`)
- [ ] Fase 2 — Gerador DXF (`dxf_generator`, `renderer`)
- [ ] Fase 3 — Interface Streamlit (`app.py`)
- [ ] Fase 4 — Testes e validação final
- [ ] Fase 5 — Deploy Streamlit Cloud
