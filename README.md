# Calculadora de Repuxo Cilíndrico

[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue)](LICENSE)

Aplicação web para dimensionamento completo de processos de repuxo cilíndrico com aba simples.

A partir das dimensões do produto final e dos dados do material, a calculadora determina automaticamente o blank, a sequência de passes, as forças de conformação e gera desenhos técnicos exportáveis.

Acesse o aplicativo em: https://repuxo.streamlit.app/

---

## Funcionalidades

### Cálculo de engenharia
- **Blank** — diâmetro teórico por conservação de área superficial, com margem de apara ajustável (0–10%)
- **Sequência de passes** — número mínimo de passes e dimensões (diâmetro, altura) de cada etapa intermediária, com distribuição geométrica proporcional
- **Forças de conformação** — força de repuxo, força e pressão do prensa-chapas, área de contato, força de extração, capacidade mínima da prensa, energia por ciclo
- **Indicadores de severidade** — razão t/D, razão de repuxo (DR), relação df/d, relação H/d, exibidos como barras coloridas (verde/amarelo/vermelho)

### Visualizações
- **Blank** — perfil do disco com cotas
- **Passe a passe** — perfil em corte de cada etapa (abas organizadas por passe)
- **Visão geral** — todos os perfis lado a lado em um único gráfico
- **Corte do copo final** — vista em espelho com cotas completas (d, Da, H, e, Rp, Rm)
- **GIF animado** — animação do processo do blank ao copo acabado

### Saída técnica
- **Arquivo DXF** (R2010) — desenho técnico exportável com camadas nomeadas (CONTORNO, EIXO, COTA, LEGENDA, HATCH), cotas dimensionais, legenda por passe e bloco de título. Compatível com AutoCAD, LibreCAD, FreeCAD.
- **Tabela de passes** — dados completos por etapa (coeficiente de repuxo, razão de repuxo, redução percentual), com coloração condicional por severidade
- **Detalhamento de forças** — força de repuxo, prensa-chapas, extração e capacidade da prensa em kN e tf, além de área de contato, pressão e energia

### Experiência do usuário
- **Glossário técnico pesquisável** — mais de 60 termos em português/inglês com localização no código
- **Material personalizado** — sliders para definir m₁_lim e mₙ_lim quando o material desejado não está na base
- **Validação em duas etapas** — validação de entrada pré-cálculo e validação geométrica pós-cálculo (altura mínima por passe)
- **Parâmetros avançados** — margem de apara e fator de segurança da prensa (colapsáveis por padrão)

---

## Como usar

1. **Insira as dimensões** do produto final: diâmetro interno (d), altura (H), diâmetro da aba (Da), espessura (e), raio do punção (Rp), raio da matriz (Rm)
2. **Selecione o material** na barra lateral (ou configure um personalizado)
3. **Ajuste parâmetros avançados** se necessário (margem de apara, fator de segurança)
4. **Clique em "Calcular"** — o processamento é acionado manualmente; os valores persistem entre execuções
5. **Explore os resultados**:
   - Animação GIF do processo
   - Tabela de passes (com coloração por severidade)
   - Detalhamento de forças por passe
   - Abas com desenho de cada etapa
   - Visão geral com todos os perfis
   - Download do arquivo DXF

---

## Deploy no Streamlit Cloud

Acesse a calculadora online:

[Abrir no Streamlit](https://repuxo.streamlit.app/)

**https://repuxo.streamlit.app**

---

## Estrutura do projeto

```
Calculadora_Repuxo_Cilindrico/
│
├── app.py                   # Interface Streamlit
├── blank_calculator.py      # Cálculo do blank (conservação de área)
├── constants.py             # Constantes físicas e coeficientes empíricos
├── materials.py             # Banco de dados de materiais (6 pré-configurados)
├── validators.py            # Validação de entrada e geométrica pós-cálculo
├── pass_sequence.py         # Sequência de passes (distribuição geométrica)
├── process_data.py          # Forças, pressões, capacidade da prensa, energia
├── dxf_generator.py         # Geração de arquivos DXF (R2010, camadas, cotas)
├── renderer.py              # Renderização matplotlib (blank, passes, overview, corte)
├── gif_renderer.py          # Geração de GIF animado do processo
├── precache.py              # Pré-cache para inicialização instantânea
│
├── glossario.md             # Glossário técnico (420 linhas, pesquisável)
├── requirements.txt         # Dependências
├── LICENSE                  # PolyForm Noncommercial 1.0.0
├── .gitignore               # Regras de exclusão
├── default_cache.pkl        # Cache pré-computado (21 KB)
│
├── .streamlit/
│   └── config.toml          # Configuração de tema (dark) e servidor
│
├── img/
│   └── Dimensions.JPG       # Imagem de referência das dimensões de entrada
│
└── tests/
    ├── test_materials.py        # 31 testes
    ├── test_validators.py       # 59 testes
    ├── test_blank_calculator.py # 34 testes
    ├── test_pass_sequence.py    # 48 testes
    ├── test_process_data.py     # 24 testes
    ├── test_renderer.py         # 24 testes
    ├── test_dxf_generator.py    # 28 testes
    └── test_precache.py         # 4 testes
```

---

## Instalação

```bash
git clone https://github.com/Henrique-JMS/Calculadora_Repuxo_Cilindrico.git
cd Calculadora_Repuxo_Cilindrico
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux / macOS
pip install -r requirements.txt
```

## Execução local

```bash
streamlit run app.py
```

A aplicação abrirá em `http://localhost:8501`.

---

## Testes

O projeto possui **8 suites de teste** com **264 testes**, cobrindo todos os módulos de cálculo, validação, renderização e geração de arquivos.

```bash
# Todos os testes com relatório de cobertura
pytest tests/ -v --cov=. --cov-report=term-missing

# Módulo específico
pytest tests/test_blank_calculator.py -v
```

---

## Materiais pré-configurados

| Material | UTS (MPa) | Ys (MPa) | µ | m₁_lim | mₙ_lim |
|---|---|---|---|---|---|
| DC01 / DC04 (Aço baixo carbono) | 310 | 175 | 0,12 | 0,50 | 0,75 |
| Aço inoxidável AISI 304 | 600 | 255 | 0,15 | 0,55 | 0,78 |
| Alumínio 1100-O (puro, recozido) | 100 | 38 | 0,10 | 0,53 | 0,76 |
| Alumínio 3003-H14 | 165 | 140 | 0,10 | 0,52 | 0,75 |
| Cobre ETP C11000 (recozido) | 240 | 85 | 0,10 | 0,50 | 0,73 |
| Latão 70/30 (CuZn30, recozido) | 350 | 140 | 0,12 | 0,52 | 0,75 |

> Também é possível definir um **material personalizado** manualmente, ajustando UTS, Ys, m₁_lim e mₙ_lim via sliders na interface.

---

## Tecnologias

- [Python](https://www.python.org/) ≥ 3.10
- [Streamlit](https://streamlit.io/) — interface web
- [Matplotlib](https://matplotlib.org/) — renderização de perfis
- [ezdxf](https://ezdxf.mozman.at/) — geração de arquivos DXF
- [NumPy](https://numpy.org/) — suporte numérico
- [pytest](https://docs.pytest.org/) — testes automatizados

---

## Referências

- Kalpakjian, S. & Schmid, S.R. — Manufacturing Engineering and Technology, 7th ed.
- Marciniak, Z., Duncan, J.L., Hu, S.J. — Mechanics of Sheet Metal Forming, 2nd ed.
- Schuler GmbH — Metal Forming Handbook, Springer, 1998.

---

## Licença

**PolyForm Noncommercial License 1.0.0** — Uso pessoal, educacional e de pesquisa permitido. Uso comercial vedado sem consentimento expresso do autor. O software é fornecido "como está", sem garantias de qualquer natureza.

Veja o arquivo [LICENSE](LICENSE) para os termos completos.
