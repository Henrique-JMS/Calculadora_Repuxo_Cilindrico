# Glossário Técnico — Repuxo Cilíndrico

Glossário de termos técnicos utilizados na Calculadora de Repuxo Cilíndrico, com
equivalentes em inglês, localização no código e descrição resumida.

---

## 1. Geometria da Peça

### Diâmetro interno (d ou d_i) / Internal diameter (d_i)
- **Onde aparece:** `app.py:152`, `blank_calculator.py:76`, `pass_sequence.py:238`, `validators.py:388`
- **Descrição:** Diâmetro interno do cilindro acabado, medido pela superfície interna da parede.

### Altura da parede (H) / Wall height (H)
- **Onde aparece:** `app.py:157`, `blank_calculator.py:124`, `pass_sequence.py:239`, `validators.py:389`
- **Descrição:** Altura da parede cilíndrica — do fundo interno até a base da aba.

### Diâmetro da aba (Da ou d_f) / Flange outer diameter (d_f)
- **Onde aparece:** `app.py:162`, `blank_calculator.py:139`, `pass_sequence.py:245`, `validators.py:390`
- **Descrição:** Diâmetro externo da aba plana. Deve ser maior que `d_i + 2t` para que exista uma aba mínima.

### Espessura da chapa ('e' ou 't') / Sheet thickness (t)
- **Onde aparece:** `app.py:168`, `blank_calculator.py:151`, `pass_sequence.py:240`, `validators.py:112`, todos os módulos
- **Descrição:** Espessura nominal da chapa metálica (blank). Intervalo suportado: 0,1–20,0 mm.

### Diâmetro neutro (d_target) / Neutral (mid-plane) diameter (d_target)
- **Onde aparece:** `pass_sequence.py:97,265`, `process_data.py:309`
- **Descrição:** Diâmetro da linha neutra (plano médio) da parede do copo acabado. `d_target = d_i + t`.

### Diâmetro externo da parede (d_e) / Outer wall diameter (d_e)
- **Onde aparece:** `blank_calculator.py:156`
- **Descrição:** Diâmetro externo da parede cilíndrica. `d_e = d_i + 2t`.

### Fundo plano / Flat bottom
- **Onde aparece:** `blank_calculator.py:76-95`, `app.py:302`
- **Descrição:** Região circular plana no fundo do copo, delimitada pelo início da concordância do punção. Área: `A = π/4 · (d_i − 2·r_p)²`.

### Concordância do punção (filete) / Punch fillet (quarter-toroid)
- **Onde aparece:** `blank_calculator.py:98-120`, `app.py:303`
- **Descrição:** Superfície toroidal de um quarto de círculo que conecta o fundo plano à parede cilíndrica. Área calculada por superfície de revolução do arco de concordância do punção.

### Parede cilíndrica / Cylindrical wall
- **Onde aparece:** `blank_calculator.py:123-136`, `app.py:304`
- **Descrição:** Superfície lateral cilíndrica reta entre a concordância do punção e o início da aba. Área: `A = π · d_i · H`.

### Aba plana / Annular flange
- **Onde aparece:** `blank_calculator.py:139-159`, `app.py:305`
- **Descrição:** Superfície anular plana que se estende da borda externa da parede (`d_e`) até o diâmetro externo da aba (`d_f`). Área: `A = π/4 · (d_f² − d_e²)`.

---

## 2. Blank (Disco Inicial)

### Blank (disco) / Blank
- **Onde aparece:** `blank_calculator.py:4-8`, `app.py:247`, `README.md:9`
- **Descrição:** Disco circular de chapa metálica a partir do qual a peça é conformada por repuxo. O diâmetro é calculado por conservação de área superficial.

### Diâmetro do blank teórico (d_blank_theoretical) / Theoretical blank diameter
- **Onde aparece:** `blank_calculator.py:43,234`, `app.py:292`
- **Descrição:** Diâmetro do blank calculado exclusivamente pela fórmula de conservação de área, sem margem de apara. `D_teórico = √(4 · A_total / π)`.

### Diâmetro do blank final (d_blank_final) / Final blank diameter
- **Onde aparece:** `blank_calculator.py:44,238`, `app.py:247,293`, `pass_sequence.py:96`
- **Descrição:** Diâmetro do blank após adicionar a margem de apara (trim). `D_final = D_teórico · (1 + trim_fraction)`.

### Margem de apara (trim_allowance_mm) / Trim allowance
- **Onde aparece:** `blank_calculator.py:45,237`, `app.py:293`, `constants.py:81`
- **Descrição:** Acréscimo ao diâmetro teórico para compensar irregularidades de borda (earing) pós-repuxo. Padrão: 3% do diâmetro teórico.

### Fração de apara (trim_fraction) / Trim fraction
- **Onde aparece:** `blank_calculator.py:46,198,248`, `app.py:233`, `constants.py:81`
- **Descrição:** Fração decimal do diâmetro teórico usada como margem de apara. Intervalo: 0%–10%. Padrão: 0,03 (3%).

### Relação t/D / t/D ratio
- **Onde aparece:** `blank_calculator.py:53,241`, `app.py:255`, `process_data.py:98`
- **Descrição:** Relação espessura/diâmetro do blank (`t / d_blank_final × 100`). Indicador de risco de rugas: verde > 1,5%, amarelo 0,5–1,5%, vermelho < 0,5%.

---

## 3. Processo de Repuxo

### Passe (etapa) / Drawing pass (stage)
- **Onde aparece:** `pass_sequence.py:48-80`, `app.py:321-334`
- **Descrição:** Cada etapa de conformação na sequência de repuxo. Um passe reduz o diâmetro do semi-produto e aumenta sua altura.

### Sequência de passes / Pass sequence
- **Onde aparece:** `pass_sequence.py:1-25`, `app.py:452-458`, `README.md:11`
- **Descrição:** Conjunto ordenado de passes necessário para transformar o blank no produto final, respeitando os limites de conformação do material.

### Número de passes (n_passes) / Number of passes
- **Onde aparece:** `pass_sequence.py:89,95`, `app.py:250`, `process_data.py:328`
- **Descrição:** Quantidade mínima de etapas de conformação necessárias para atingir a geometria final sem violar os coeficientes limite de repuxo.

### Passe final (is_final) / Final pass
- **Onde aparece:** `pass_sequence.py:80,318`, `dxf_generator.py:301-302`
- **Descrição:** Último passe da sequência, onde a peça atinge as dimensões finais especificadas (altura H, diâmetro d_i, aba d_f).

### Passe intermediário / Intermediate pass
- **Onde aparece:** `dxf_generator.py:226-227`, `renderer.py:163-164`
- **Descrição:** Passe anterior ao final, onde o semi-produto ainda não possui a aba nas dimensões finais e pode ter altura menor que H.

### Diâmetro antes (d_before) / Diameter before (d_before)
- **Onde aparece:** `pass_sequence.py:55-56,316`
- **Descrição:** Diâmetro do blank ou semi-produto na entrada do passe. Para o passe 1, é igual ao diâmetro do blank final.

### Diâmetro depois (d_after) / Diameter after (d_after)
- **Onde aparece:** `pass_sequence.py:57,317`
- **Descrição:** Diâmetro do semi-produto após a conclusão do passe (linha neutra).

### Altura acumulada (height) / Accumulated cup height
- **Onde aparece:** `pass_sequence.py:59,348-351`
- **Descrição:** Altura do copo após cada passe. No passe final é igual a H; nos intermediários é calculada por conservação de área.

### Diâmetro da aba no passe (flange_diameter) / Flange diameter at pass
- **Onde aparece:** `pass_sequence.py:65,331-344`
- **Descrição:** Diâmetro externo da aba em cada passe. Interpola entre D_blank (passe 1) e d_f (passe final) conforme o progresso do repuxo.

### Distribuição de diâmetros / Diameter distribution
- **Onde aparece:** `pass_sequence.py:158-215`
- **Descrição:** Algoritmo que distribui os diâmetros intermediários ao longo dos passes usando interpolação logarítmica, garantindo que o último passe atinja exatamente d_target e que nenhum coeficiente limite seja violado.

### Conservação de área superficial / Surface area conservation
- **Onde aparece:** `blank_calculator.py:186-187`, `pass_sequence.py:122-155`
- **Descrição:** Princípio fundamental do cálculo: a área superficial do blank é igual à soma das áreas de todos os segmentos da peça conformada (fundo + filete + parede + aba).

---

## 4. Coeficientes e Razões de Repuxo

### Coeficiente de repuxo (m) / Drawing coefficient (m)
- **Onde aparece:** `pass_sequence.py:60,320`, `app.py:326`, `process_data.py:304`
- **Descrição:** Relação entre o diâmetro depois e antes do passe: `m = d_after / d_before`. Quanto menor m, mais severa é a redução.

### Razão de repuxo (DR) / Drawing ratio (DR)
- **Onde aparece:** `pass_sequence.py:61,321`, `app.py:252`, `process_data.py:303`, `renderer.py:404`
- **Descrição:** Inverso do coeficiente de repuxo: `DR = d_before / d_after = 1/m`. Indica a severidade da deformação em cada passe.

### Razão de repuxo total (DR_total) / Total drawing ratio (DR_total)
- **Onde aparece:** `pass_sequence.py:92,98,267,373`, `app.py:252`
- **Descrição:** Razão entre o diâmetro do blank e o diâmetro neutro final: `DR_total = d_blank / d_target`. Determina o número mínimo de passes.

### Coeficiente limite do 1º passe (m1_lim) / Limiting coefficient - 1st pass (m1_lim)
- **Onde aparece:** `materials.py:56`, `constants.py:51`, `pass_sequence.py:243`, `validators.py:396`
- **Descrição:** Menor valor de m permitido para o primeiro passe. Varia conforme o material (ex: 0,50 para aço DC01). Faixa típica: 0,40–0,70.

### Coeficiente limite de passes subsequentes (mn_lim) / Limiting coefficient - subsequent passes (mn_lim)
- **Onde aparece:** `materials.py:57`, `constants.py:52`, `pass_sequence.py:244`, `validators.py:397`
- **Descrição:** Menor valor de m permitido para passes após o primeiro. Sempre maior que m1_lim (passes menos severos). Faixa típica: 0,60–0,90.

### Razão de repuxo limite (LDR) / Limiting drawing ratio (LDR)
- **Onde aparece:** `materials.py:67-69`
- **Descrição:** Máxima razão de repuxo admissível no primeiro passe: `LDR = 1 / m1_lim`. Ex: para m1_lim = 0,50, LDR = 2,0.

### Redução percentual (reduction_pct) / Percentage reduction
- **Onde aparece:** `pass_sequence.py:62,361`, `app.py:327`
- **Descrição:** Percentual de redução diametral em cada passe: `Red = (1 − m) × 100%`.

---

## 5. Forças e Capacidade da Prensa

### Força de repuxo (punção) / Punch (drawing) force (F_punch)
- **Onde aparece:** `process_data.py:165-181`, `app.py:346`, `constants.py:63-64`
- **Descrição:** Força exercida pelo punção para deformar a chapa. Calculada pela fórmula de Siebel: `F_punch = π · d · t · UTS · (DR − 0,7)`.

### Constante de correção de Siebel / Siebel correction constant
- **Onde aparece:** `constants.py:64`
- **Descrição:** Constante empírica (0,7) que corrige a força de repuxo para considerar o atrito e a curvatura na borda da matriz.

### Força do prensa-chapas (F_bh) / Blank holder force (F_bh)
- **Onde aparece:** `process_data.py:62-63,283`, `app.py:329,347`
- **Descrição:** Força aplicada pelo prensa-chapas para evitar a formação de rugas no flange durante o repuxo. `F_bh = p_bh × A_bh`.

### Pressão do prensa-chapas (p_bh) / Blank holder pressure (p_bh)
- **Onde aparece:** `materials.py:77-84`, `process_data.py:202-212`, `constants.py:39`
- **Descrição:** Pressão exercida pelo prensa-chapas sobre o flange. Fórmula empírica de Kawai: `p_bh = 0,015 × Ys`.

### Área de contato do prensa-chapas (A_bh) / Blank holder contact area (A_bh)
- **Onde aparece:** `process_data.py:184-199`, `app.py:351`
- **Descrição:** Área anular de contato entre o prensa-chapas e o flange. `A_bh = π/4 · [D_before² − (d_after + 2·r_die)²]`.

### Força de extração (F_ext) / Extraction force (F_ext)
- **Onde aparece:** `process_data.py:215-217,285`, `app.py:330,348`, `constants.py:67`
- **Descrição:** Força necessária para extrair o copo conformado do interior da matriz. Adotada como 8% da força de repuxo: `F_ext = 0,08 × F_punch`.

### Capacidade da prensa (F_press) / Press capacity (F_press)
- **Onde aparece:** `process_data.py:220-226`, `app.py:253-254,349`
- **Descrição:** Força mínima que a prensa deve ser capaz de fornecer. `F_press = (F_punch + F_bh) × safety_factor`. Inclui o fator de segurança.

### Fator de segurança (safety_factor) / Safety factor
- **Onde aparece:** `constants.py:70`, `app.py:220-223`, `process_data.py:255`
- **Descrição:** Multiplicador aplicado sobre a soma das forças de repuxo e prensa-chapas para dimensionar a prensa. Padrão: 1,25.

### Energia por ciclo (energy_J) / Energy per cycle
- **Onde aparece:** `process_data.py:229-240,301`, `app.py:353`, `constants.py:74`
- **Descrição:** Energia de entrada que a prensa deve fornecer por ciclo: `W_input = F_punch × H / (1000 × η)`. Inclui a eficiência mecânica (η = 0,65).

---

## 6. Ferramental

### Matriz (matriz de repuxo) / Drawing die
- **Onde aparece:** `app.py:178`, `validators.py:155,174`, `dxf_generator.py:195`
- **Descrição:** Ferramenta fêmea que contém o blank durante o repuxo. A borda da matriz possui um raio de concordância (r_die) para evitar fratura na chapa.

### Raio da matriz (r_die) / Die corner radius (r_die)
- **Onde aparece:** `app.py:177-181`, `pass_sequence.py:241`, `validators.py:160-182`, `constants.py:22,25`
- **Descrição:** Raio de concordância da borda da matriz. Mínimo absoluto: 2t. Recomendado: ≥ 4t. Raios menores aumentam risco de fratura.

### Punção / Drawing punch
- **Onde aparece:** `app.py:183`, `validators.py:212,237`, `dxf_generator.py:194`
- **Descrição:** Ferramenta macho que pressiona o blank contra a matriz, deformando-o plasticamente para formar o copo.

### Raio do punção (r_punch) / Punch corner radius (r_punch)
- **Onde aparece:** `app.py:182-186`, `blank_calculator.py:197,223`, `validators.py:218-257`, `constants.py:28,31`
- **Descrição:** Raio de concordância na base do punção (transição fundo-parede). Mínimo absoluto: 2t. Recomendado: ≥ 3t. Deve ser menor que d_i/2.

### Folga punção-matriz (clearance) / Punch-die clearance (c)
- **Onde aparece:** `materials.py:86-100`, `constants.py:89-94`
- **Descrição:** Folga lateral entre punção e matriz. `c = t + k · √(1000 · t)`, onde k depende do material (0,07 para aços, 0,06 para alumínio e cobre).

---

## 7. Materiais

### Resistência à tração (UTS / Rm) / Ultimate tensile strength (UTS)
- **Onde aparece:** `materials.py:8,54`, `app.py:199,205,210`, `validators.py:260-278`
- **Descrição:** Tensão máxima que o material suporta antes da ruptura (MPa). Empregada no cálculo da força de repuxo (Siebel).

### Limite de escoamento (Ys / Re) / Yield strength (Ys)
- **Onde aparece:** `materials.py:9,55`, `app.py:200,205,210`, `validators.py:270-273`
- **Descrição:** Tensão a partir da qual o material deforma plasticamente (MPa). Usado no cálculo da pressão do prensa-chapas.

### Coeficiente de atrito (µ) / Friction coefficient (mu)
- **Onde aparece:** `materials.py:58`, `app.py:211`
- **Descrição:** Coeficiente de atrito de Coulomb entre a chapa e as ferramentas (punção, matriz, prensa-chapas) em condição lubrificada. Varia de 0,10 a 0,15.

### Aço DC01/DC04 (baixo carbono) / Low-carbon steel DC01/DC04
- **Onde aparece:** `materials.py:112-125`, `README.md:70`
- **Descrição:** Aço para embutimento profundo (EN 10130). UTS = 310 MPa, Ys = 175 MPa, m1_lim = 0,50. DC04 possui melhor conformabilidade.

### Aço inoxidável AISI 304 / Stainless steel AISI 304
- **Onde aparece:** `materials.py:127-140`, `README.md:71`
- **Descrição:** Aço inoxidável austenítico com alto encruamento. UTS = 600 MPa, Ys = 255 MPa, m1_lim = 0,55. Requer raios de matriz generosos e boa lubrificação.

### Alumínio 1100-O (recozido) / Aluminium 1100-O (annealed)
- **Onde aparece:** `materials.py:142-155`, `README.md:72`
- **Descrição:** Alumínio comercialmente puro, estado recozido. UTS = 100 MPa, Ys = 38 MPa, m1_lim = 0,53. Excelente conformabilidade, sensível a rugas.

### Alumínio 3003-H14 / Aluminium 3003-H14
- **Onde aparece:** `materials.py:157-170`, `README.md:73`
- **Descrição:** Liga Al-Mn, estado H14 (semi-encruado). UTS = 165 MPa, Ys = 140 MPa, m1_lim = 0,52.

### Cobre ETP C11000 (recozido) / Copper ETP C11000 (annealed)
- **Onde aparece:** `materials.py:172-185`, `README.md:74`
- **Descrição:** Cobre eletrolítico de alta pureza, recozido. UTS = 240 MPa, Ys = 85 MPa, m1_lim = 0,50. Alta ductilidade; pode requerer recozimento intermediário.

### Latão 70/30 CuZn30 (recozido) / Brass 70/30 CuZn30 (annealed)
- **Onde aparece:** `materials.py:187-200`, `README.md:75`
- **Descrição:** Liga Cu-Zn 70/30, recozido. UTS = 350 MPa, Ys = 140 MPa, m1_lim = 0,52. Clássico material de embutimento.

### Material personalizado / Custom material
- **Onde aparece:** `materials.py:202-211,46`, `app.py:197-202`
- **Descrição:** Opção para o usuário inserir manualmente UTS, Ys, m1_lim e mn_lim sem usar os valores pré-configurados.

---

## 8. Indicadores de Severidade (Sistema RAG)

### Severidade / Severity
- **Onde aparece:** `blank_calculator.py:54,162-168`, `pass_sequence.py:64,114-119`, `process_data.py:93-116`
- **Descrição:** Classificação semafórica (verde/amarelo/vermelho) que indica o risco de cada indicador do processo. Verde = seguro, amarelo = atenção, vermelho = crítico.

### Relação t/D (espessura/diâmetro) / t/D ratio
- **Onde aparece:** `blank_calculator.py:68,241`, `app.py:255,271`, `process_data.py:98,310`, `constants.py:42-43`
- **Descrição:** Indicador de risco de rugas. Verde (≥ 1,5%), amarelo (0,5%–1,5%), vermelho (< 0,5%). Quanto menor, maior a tendência a rugas.

### DR do 1º passe / First pass DR
- **Onde aparece:** `process_data.py:100,311`, `app.py:266,272`, `constants.py:55-56`
- **Descrição:** Razão de repuxo do primeiro passe. Verde (≤ 1,8), amarelo (1,8–2,0), vermelho (> 2,0). Quanto maior, mais severa a deformação inicial.

### Relação df/d (aba/diâmetro) / df/d ratio
- **Onde aparece:** `process_data.py:102-103,312`, `app.py:267,273`, `constants.py:99-100`
- **Descrição:** `d_f / d_neutral`. Indica a largura relativa da aba. Verde (≤ 1,5), amarelo (1,5–2,0), vermelho (> 2,0).

### Relação H/d (altura/diâmetro) / H/d ratio
- **Onde aparece:** `process_data.py:104-105,313`, `app.py:268,274`, `constants.py:105-106`
- **Descrição:** `H / d_neutral`. Indica a profundidade do repuxo. Verde (≤ 0,5), amarelo (0,5–1,0), vermelho (> 1,0 — repuxo severo).

---

## 9. Validação

### ValidationResult
- **Onde aparece:** `validators.py:57-96`
- **Descrição:** Classe que encapsula o resultado da validação, contendo listas de erros (bloqueantes) e avisos (não bloqueantes). Permite que a interface decida como exibir as mensagens sem tratamento de exceções.

### Erro bloqueante (ERROR) / Blocking error
- **Onde aparece:** `validators.py:12-13`
- **Descrição:** Impede o cálculo. Corresponde a entradas fisicamente impossíveis ou matematicamente indefinidas (ex: `d_f ≤ d_i + 2t`, `t ≤ 0`).

### Aviso não bloqueante (WARNING) / Non-blocking warning
- **Onde aparece:** `validators.py:14-15`
- **Descrição:** Não impede o cálculo, mas alerta o usuário sobre riscos (ex: `r_die < 4t` aumenta risco de fratura).

### Altura geométrica mínima / Minimum geometric height
- **Onde aparece:** `validators.py:207,482`
- **Descrição:** Altura mínima que um passe deve ter para acomodar os raios do punção e da matriz: `H_min = r_punch + r_die + t`. Abaixo disso, a geometria renderizada fica degenerada (paredes invertidas).

---

## 10. Arquivos DXF

### Camada CONTORNO / Layer CONTOUR
- **Onde aparece:** `dxf_generator.py:21,48`
- **Descrição:** Linhas do perfil do contorno da peça. Cor: branca (código 7).

### Camada EIXO / Layer EIXO
- **Onde aparece:** `dxf_generator.py:22,49`
- **Descrição:** Linha de eixo de simetria (centro). Cor: vermelha (código 1).

### Camada COTA / Layer COTA
- **Onde aparece:** `dxf_generator.py:23,50`
- **Descrição:** Anotações dimensionais (cota). Cor: amarela (código 2).

### Camada LEGENDA / Layer LEGENDA
- **Onde aparece:** `dxf_generator.py:24,51`
- **Descrição:** Textos e rótulos informativos. Cor: ciano (código 4).

### Perfil em corte / Cross-section profile
- **Onde aparece:** `dxf_generator.py:7-8`, `renderer.py:7-8`
- **Descrição:** Representação em corte do semi-perfil direito (simetria axial) de cada etapa, com contorno interno e externo, eixos e cotas.

---

## 11. Renderização

### Renderização por etapa / Per-stage rendering
- **Onde aparece:** `renderer.py:420-452`, `app.py:358-378`
- **Descrição:** Geração de figuras matplotlib independentes para cada etapa (blank + cada passe), exibidas em abas na interface Streamlit.

### Visão geral (overview) / Stage overview
- **Onde aparece:** `renderer.py:455-532`, `app.py:376`
- **Descrição:** Figura compacta com todas as etapas dispostas lado a lado em uma única linha, útil como resumo visual rápido.

---

## 12. Constantes do Sistema

### DEFAULT_TRIM_ALLOWANCE
- **Onde aparece:** `constants.py:81`
- **Descrição:** Margem de apara padrão: 3% (0,03) do diâmetro teórico do blank.

### DEFAULT_SAFETY_FACTOR
- **Onde aparece:** `constants.py:70`
- **Descrição:** Fator de segurança padrão para capacidade da prensa: 1,25.

### SIEBEL_CORRECTION
- **Onde aparece:** `constants.py:64`
- **Descrição:** Constante empírica de Siebel: 0,7.

### EXTRACTION_FORCE_FACTOR
- **Onde aparece:** `constants.py:67`
- **Descrição:** Fração da força de repuxo usada como força de extração: 0,08 (8%).

### PRESS_EFFICIENCY (η)
- **Onde aparecer:** `constants.py:74`
- **Descrição:** Eficiência mecânica da prensa: 0,65 (65%). Usada para calcular energia de entrada a partir do trabalho útil.

### BH_PRESSURE_COEFF
- **Onde aparece:** `constants.py:39`
- **Descrição:** Coeficiente empírico de Kawai para pressão do prensa-chapas: 0,015 × Ys.

---

## 13. Classes (Dataclasses)

### BlankResult
- **Onde aparece:** `blank_calculator.py:37-69`
- **Descrição:** Resultado do cálculo do blank. Contém diâmetros (teórico e final), margem de apara, áreas de cada segmento, relação t/D e severidade.

### PassData
- **Onde aparece:** `pass_sequence.py:48-80`
- **Descrição:** Dados dimensionais e parâmetros de repuxo de um único passe: diâmetros, altura, coeficientes m e DR, redução, raios, severidade.

### PassSequenceResult
- **Onde aparece:** `pass_sequence.py:83-99`
- **Descrição:** Resultado completo da sequência de passes: número de passes, blank, diâmetro alvo, DR total e lista de PassData.

### PassForces
- **Onde aparece:** `process_data.py:51-89`
- **Descrição:** Dados técnicos de produção para um passe: forças (repuxo, prensa-chapas, extração, prensa), pressão, área de contato e energia.

### SeverityIndicators
- **Onde aparece:** `process_data.py:92-116`
- **Descrição:** Indicadores globais de severidade do processo: t/D, DR, df/d, H/d com classificação RAG.

### ProcessDataResult
- **Onde aparece:** `process_data.py:119-133`
- **Descrição:** Resultado completo do módulo de dados de processo: forças por passe, severidade global e pico de capacidade da prensa.

### Material
- **Onde aparece:** `materials.py:49-103`
- **Descrição:** Container imutável com propriedades do material: UTS, Ys, m1_lim, mn_lim, µ, clearance_k. Inclui propriedades calculadas (LDR, pressão BH) e método clearance(t).

---

## 14. Referências Bibliográficas

### Kalpakjian & Schmid — Manufacturing Engineering and Technology, 7ª ed.
- **Onde aparece:** `blank_calculator.py:19`, `constants.py:10`, `materials.py:28`, `pass_sequence.py:21`, `process_data.py:18`, `README.md:79`
- **Descrição:** Referência principal para fórmulas de blank, forças (Siebel) e coeficientes de repuxo.

### Marciniak, Duncan & Hu — Mechanics of Sheet Metal Forming, 2ª ed.
- **Onde aparece:** `blank_calculator.py:21`, `constants.py:11`, `pass_sequence.py:23`, `README.md:80`
- **Descrição:** Referência para mecânica da conformação de chapas, sequência de passes e conservação de área.

### Schuler GmbH — Metal Forming Handbook, Springer, 1998
- **Onde aparece:** `blank_calculator.py:22`, `constants.py:12`, `materials.py:29`, `pass_sequence.py:24`, `process_data.py:20`, `README.md:81`
- **Descrição:** Referência para dados práticos de materiais, folgas, pressões de prensa-chapas e capacidade de prensas.
