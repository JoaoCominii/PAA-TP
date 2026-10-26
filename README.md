# Trabalho Prático: Metrô de Paris — PAA (PUC Minas)

Aplicação desenvolvida para a disciplina de **Projeto e Análise de Algoritmos (PAA)** do ICEI / PUC Minas (Prof. Alexei Machado).

O projeto implementa uma interface gráfica nativa em **Python com Tkinter** e resolve três problemas clássicos de teoria dos grafos através de três paradigmas algorítmicos:
1. **Força Bruta** (Busca Exaustiva)
2. **Branch-and-Bound** (Busca com podas por limitantes)
3. **Heurística Construtiva** (Algoritmo aproximado em tempo polinomial)

---

## 👥 Divisão das Responsabilidades

| Integrante | Foco Principal | Problema Teórico | Arquivos e Entregáveis |
|---|---|---|---|
| **Integrante 1** | **GUI (Tkinter) + Ciclos** | **Problema (a):** Maior Ciclo Simples | `main.py` (GUI e Algoritmos A), `PLANO_INTEGRANTE_1.md` |
| **Integrante 2** | **Dados & Modelagem** | **Problema (b):** Conjunto Dominante Mínimo | Parser dos dados das linhas sorteadas e Algoritmos B |
| **Integrante 3** | **Benchmarks & Relatório** | **Problema (c):** Coloração de Vértices | Scripts de teste de tempo/memória e Relatório SBC |

---

## 🚀 Como Executar o Projeto

Como o projeto utiliza estritamente bibliotecas padrão do Python (`tkinter`, `math`, `time`, `collections`), **não é necessário instalar pacotes adicionais via pip**.

### 1. Iniciar a Interface Gráfica
```bash
python main.py
```

### 2. Passo a Passo de Uso na Interface
1. Clique em **"1. Carregar Estações (.txt)"** e selecione o arquivo com as coordenadas (ex.: `dados/exemplo_estacoes.txt`).
- Integrante 2 irá extrair coordenadas das estações do mapa e gerar
os arquivos .txt reais segundo N(soma das matriculas) = soma % 5
2. Clique em **"2. Carregar Linhas (.txt)"** e selecione o arquivo de conexões e cores (ex.: `dados/exemplo_linhas.txt`).
3. O mapa do metrô será desenhado no Canvas central com ajuste dinâmico de escala.
4. Para o **Problema (a)**:
   - Escolha a estação de partida no menu suspenso ou **clique diretamente sobre uma estação no mapa**.
   - Escolha o método: *Força Bruta*, *Branch-and-Bound* ou *Heurística*.
   - Clique em **"▶ Executar Algoritmo"**.
5. O ciclo encontrado será destacado no mapa com linha dourada espessa e estações numeradas em ordem de visita (`#1`, `#2`, ...), acompanhado pelo tempo de execução em milissegundos e número de nós/podas.

---

## 🧩 Onde os Integrantes 2 e 3 Devem Plugar Suas Funções

No arquivo [`main.py`], localize a **Seção 5**:

* **Integrante 2:** Função `resolver_problema_b(grafo, metodo)`
* **Integrante 3:** Função `resolver_problema_c(grafo, metodo)`

Ambas já possuem pontos de chamada prontos na interface gráfica!
