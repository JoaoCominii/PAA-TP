"""
========================================================================================
PUC MINAS - ICEI - CIÊNCIA DA COMPUTAÇÃO
DISCIPLINA: PROJETO E ANÁLISE DE ALGORITMOS (PAA)
PROFESSOR: ALEXEI MACHADO
TRABALHO PRÁTICO: O METRÔ DE PARIS
========================================================================================
ESTRUTURA DE RESPONSABILIDADES:
- Integrante 1: Interface Gráfica (Tkinter) & Problema (a) [Maior Ciclo Simples]
- Integrante 2: Modelagem de Dados, Parser & Problema (b) [Conjunto Dominante Mínimo]
- Integrante 3: Automação de Testes/Benchmarks & Problema (c) [Coloração de Vértices]
========================================================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
import math
from collections import deque
from itertools import permutations


# ======================================================================================
# 1. MAPEAMENTO DE CORES DAS LINHAS
# ======================================================================================
# Converte os nomes de cores informados em português nos arquivos do metrô para cores
# válidas que o Tkinter consegue desenhar no Canvas.
MAPA_CORES = {
    "azul": "#0055A5",
    "vermelha": "#C60B1E",
    "amarela": "#FFCC00",
    "verde": "#009944",
    "roxa": "#7D3C98",
    "magenta": "#D9007E",
    "laranja": "#E67E22",
    "marrom": "#8D6E63",
    "rosa": "#F48FB1",
    "cinza": "#7F8C8D",
    "turquesa": "#1ABC9C",
    "oliva": "#827717",
    "preto": "#2C3E50"
}

def obter_cor_hex(nome_cor):
    """
    Retorna o código hexadecimal correspondente ao nome da cor.
    Se a cor não estiver no dicionário ou já for hexadecimal (#...), retorna ela mesma
    ou um valor padrão seguro.
    """
    cor_limpa = nome_cor.strip().lower()
    if cor_limpa in MAPA_CORES:
        return MAPA_CORES[cor_limpa]
    if cor_limpa.startswith("#"):
        return cor_limpa
    # Fallback seguro para cores não mapeadas
    return "#555555"


# ======================================================================================
# 2. ESTRUTURA DE DADOS DO GRAFO
# ======================================================================================
class GrafoMetro:
    """
    Representa o sistema de linhas e estações do Metrô de Paris.
    
    A estrutura utiliza listas/dicionários de adjacência:
    - estacoes: dicionário { 'NomeEstacao': (coord_x, coord_y) }
    - adjacencias: dicionário { 'EstacaoOrigem': { 'EstacaoDestino': ['Linha1', ...] } }
    - trechos: lista de tuplas (estacao1, estacao2, linha, cor) para desenho no mapa
    """

    def __init__(self):
        self.estacoes = {}          # { nome: (x, y) }
        self.adjacencias = {}       # { u: { v: [linhas] } }
        self.trechos = []           # [ (u, v, linha, cor) ]

    def limpar(self):
        """Limpa todos os dados carregados do grafo."""
        self.estacoes.clear()
        self.adjacencias.clear()
        self.trechos.clear()

    def adicionar_estacao(self, nome, x, y):
        """Adiciona ou atualiza as coordenadas de uma estação no grafo."""
        self.estacoes[nome] = (float(x), float(y))
        if nome not in self.adjacencias:
            self.adjacencias[nome] = {}

    def adicionar_trecho(self, u, v, nome_linha, cor):
        """
        Adiciona uma ligação bidirecional (não-direcionada) entre as estações u e v,
        associando o identificador da linha de metrô e a sua cor.
        """
        # Garante que os nós existam no dicionário de adjacências
        if u not in self.adjacencias:
            self.adjacencias[u] = {}
        if v not in self.adjacencias:
            self.adjacencias[v] = {}

        # Registra a conexão de u para v
        if v not in self.adjacencias[u]:
            self.adjacencias[u][v] = []
        if nome_linha not in self.adjacencias[u][v]:
            self.adjacencias[u][v].append(nome_linha)

        # Como o metrô é não-direcionado, registra de v para u
        if u not in self.adjacencias[v]:
            self.adjacencias[v][u] = []
        if nome_linha not in self.adjacencias[v][u]:
            self.adjacencias[v][u].append(nome_linha)

        # Guarda o trecho para facilitar a renderização gráfica
        self.trechos.append((u, v, nome_linha, cor))

    def vizinhos(self, u):
        """Retorna uma lista com os nomes das estações diretamente conectadas a u."""
        return list(self.adjacencias.get(u, {}).keys())

    def grau(self, u):
        """Retorna o grau (número de conexões) de uma estação."""
        return len(self.adjacencias.get(u, {}))

    def obter_todos_os_vertices(self):
        """Retorna a lista de todas as estações cadastradas."""
        return list(self.estacoes.keys())


# ======================================================================================
# 3. PARSERS DE ARQUIVOS (CONFORME ESPECIFICAÇÃO DO EDITAL)
# ======================================================================================
def carregar_arquivo_estacoes(caminho_arquivo, grafo):
    """
    Lê o arquivo de estações no formato:
        NomeEstacao x y
    Exemplos aceitos:
        Nation 100 150
        Republique 50 100
        Gare du Nord 510 150 (suporta nomes compostos com espaços ou underlines)
    """
    total_lidas = 0
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            # Ignora linhas em branco ou comentários
            if not linha or linha.startswith("#"):
                continue
            
            # rsplit com maxsplit=2 garante que os dois últimos itens sejam as coordenadas x e y,
            # e todo o restante inicial seja tratado como o nome da estação (mesmo com espaços).
            partes = linha.rsplit(None, 2)
            if len(partes) == 3:
                nome = partes[0].strip()
                try:
                    x = float(partes[1])
                    y = float(partes[2])
                    grafo.adicionar_estacao(nome, x, y)
                    total_lidas += 1
                except ValueError:
                    continue
    return total_lidas


def carregar_arquivo_linhas(caminho_arquivo, grafo):
    """
    Lê o arquivo de linhas do metrô no formato dividido em seções:
        LinhaX cor N
        Estacao1 Estacao2
        ...
    Exemplo:
        Linha1 azul 2
        Nation Republique
        Republique Chatelet
        
    Robustez:
    - Suporta nomes compostos separados por espaço, tabulação ou casando com estações cadastradas.
    """
    total_trechos = 0
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    estacoes_conhecidas = sorted(grafo.estacoes.keys(), key=lambda s: len(s), reverse=True)

    i = 0
    while i < len(linhas):
        cabecalho = linhas[i].split()
        if len(cabecalho) >= 3:
            nome_linha = cabecalho[0]
            cor = cabecalho[1]
            try:
                qtd_trechos = int(cabecalho[2])
            except ValueError:
                qtd_trechos = 0

            i += 1
            lidos = 0
            while i < len(linhas) and lidos < qtd_trechos:
                texto_trecho = linhas[i].strip()
                u, v = None, None

                # 1. Tentativa via delimitadores comuns (tabulação, ponto-e-vírgula ou hífen com espaços)
                for delim in ["\t", ";", " - "]:
                    if delim in texto_trecho:
                        pedacos = texto_trecho.split(delim, 1)
                        if len(pedacos) == 2:
                            u, v = pedacos[0].strip(), pedacos[1].strip()
                            break

                # 2. Se não achou delimitador especial, tenta casar com as estações cadastradas
                if not u and estacoes_conhecidas:
                    for est in estacoes_conhecidas:
                        if texto_trecho.startswith(est):
                            resto = texto_trecho[len(est):].strip()
                            if resto in grafo.estacoes:
                                u, v = est, resto
                                break

                # 3. Fallback: split simples por espaços se forem duas palavras
                if not u:
                    par = texto_trecho.split()
                    if len(par) >= 2:
                        u, v = par[0], par[1]

                if u and v:
                    grafo.adicionar_trecho(u, v, nome_linha, cor)
                    total_trechos += 1
                    lidos += 1
                i += 1
        else:
            i += 1

    return total_trechos


# ======================================================================================
# 4. ALGORITMOS DO PROBLEMA (A) — MAIOR CICLO SIMPLES (INTEGRANTE 1)
# ======================================================================================
"""
O PROBLEMA:
Determinar o maior ciclo simples que sai e retorna a uma estação 's' sem repetir estações.
Critérios de validade:
1. Deve ser um ciclo: começa em 's' e termina em 's'.
2. Deve ser simples: todos os nós intermediários devem ser visitados no máximo 1 vez.
3. Comprimento mínimo: no mínimo 3 nós distintos mais o retorno (ex: s -> a -> b -> s),
   pois ir e voltar pelo mesmo trilho (s -> a -> s) não é um ciclo simples em grafos não-direcionados.
"""

def forca_bruta_maior_ciclo(grafo, inicio):
    """
    ABORDAGEM 1: FORÇA BRUTA PURA (GENERATE-AND-TEST / PERMUTAÇÕES - SEM BACKTRACKING)
    
    Explicação detalhada para a banca examinadora:
    - Esta é a abordagem legítima e estrita de Força Bruta: NÃO utiliza recursão,
      NÃO navega por árvore de busca no grafo e NÃO realiza backtracking.
    - O algoritmo gera cegamente todas as permutações possíveis de estações intermediárias
      usando itertools.permutations no vácuo, sem consultar arestas durante a geração.
    - Para cada permutação candidata gerada, o algoritmo executa um teste direto (Generate-and-Test):
      valida se todas as arestas consecutivas existem no grafo (inicio -> p[0] -> p[1] ... -> inicio).
    - Para maximizar a eficiência sem perder a pureza da Força Bruta, testa os tamanhos
      em ordem decrescente (do maior número possível de intermediários até 2).
      O primeiro ciclo válido encontrado no maior tamanho já é garantidamente ótimo!
    - Complexidade: Fatorial O(|V|!) no espaço de permutações avaliadas.
    """
    inicio_tempo = time.perf_counter()
    
    # Dicionário de adjacências como conjuntos para consulta instantânea O(1)
    adj_set = {u: set(grafo.vizinhos(u)) for u in grafo.obter_todos_os_vertices()}
    
    # Nós candidatos a intermediários: estações com grau >= 2 (grau <= 1 nunca forma ciclo)
    candidatos = [v for v in grafo.obter_todos_os_vertices() if v != inicio and grafo.grau(v) >= 2]
    
    melhor_ciclo = []
    permutacoes_avaliadas = 0
    
    # Um ciclo simples requer no mínimo 2 intermediários (inicio -> v1 -> v2 -> inicio)
    # Testamos os tamanhos m de intermediários do maior para o menor
    for m in range(len(candidatos), 1, -1):
        achou_neste_tamanho = False
        
        for perm in permutations(candidatos, m):
            permutacoes_avaliadas += 1
            
            # Validação cega das conexões nos trilhos:
            # 1. Checa a aresta de partida (inicio -> perm[0]) e de volta (perm[-1] -> inicio)
            if perm[0] not in adj_set.get(inicio, set()) or perm[-1] not in adj_set.get(inicio, set()):
                continue
            
            # 2. Checa todas as arestas intermediárias consecutivas
            valido = True
            for i in range(len(perm) - 1):
                if perm[i + 1] not in adj_set.get(perm[i], set()):
                    valido = False
                    break
            
            # Se todas as arestas consecutivas existem, temos um ciclo simples válido!
            if valido:
                melhor_ciclo = [inicio] + list(perm) + [inicio]
                achou_neste_tamanho = True
                break  # Como m é decrescente, este ciclo já é de comprimento máximo!
        
        if achou_neste_tamanho:
            break
            
    tempo_total = (time.perf_counter() - inicio_tempo) * 1000.0  # milissegundos
    return melhor_ciclo, tempo_total, permutacoes_avaliadas


def branch_and_bound_maior_ciclo(grafo, inicio):
    """
    ABORDAGEM 2: BRANCH-AND-BOUND (PODA POR LIMITANTE SUPERIOR + RETORNO)
    
    Explicações:
    - Produz a mesma solução ótima da força bruta, mas de maneira muito mais rápida.
    - ESTRATÉGIAS DE PODA (BOUND):
      1. Poda por Upper Bound:
         Em qualquer estado da busca, calculamos os nós ainda não visitados que conseguem
         alcançar 'inicio'. Se (tamanho_caminho_atual + nós_alcançáveis) <= tamanho_melhor_ciclo,
         não há como esse ramo superar o melhor já encontrado. PODA IMEDIATA!
      2. Poda por Falta de Retorno:
         Se a partir do vértice atual for impossível alcançar a estação de partida 'inicio'
         usando apenas vértices livres (não visitados), o ramo é um beco sem saída. PODA!
      3. Ordenação Gulosa de Ramificação (Branching Order):
         Testa primeiro os vizinhos com maior grau residual. Isso faz com que ciclos grandes
         sejam descobertos rapidamente no começo da busca, elevando o corte e podando
         milhares de ramos prematuramente.
    """
    inicio_tempo = time.perf_counter()
    
    melhor_ciclo = []
    nos_expandidos = 0
    podas_realizadas = 0

    def calcular_alcance_retorno(atual, visitados):
        """
        Executa um BFS rápido a partir de 'atual' pelos nós não visitados para checar:
        1. Se 'inicio' ainda é alcançável (se não for, o ciclo não pode fechar).
        2. Quantos vértices livres no total estão na mesma componente conexa (Limitante Superior).
        """
        fila = deque([atual])
        alcancaveis = set([atual])
        alcanca_inicio = False

        while fila:
            u = fila.popleft()
            for v in grafo.vizinhos(u):
                if v == inicio:
                    alcanca_inicio = True
                elif v not in visitados and v not in alcancaveis:
                    alcancaveis.add(v)
                    fila.append(v)

        return alcanca_inicio, len(alcancaveis)

    def bnb_dfs(vertice_atual, caminho, visitados):
        nonlocal melhor_ciclo, nos_expandidos, podas_realizadas
        nos_expandidos += 1

        vizinhos = grafo.vizinhos(vertice_atual)

        # Checa se fecha ciclo com 'inicio'
        if inicio in vizinhos and len(caminho) >= 3:
            ciclo_candidato = caminho + [inicio]
            if len(ciclo_candidato) > len(melhor_ciclo):
                melhor_ciclo = list(ciclo_candidato)

        # Ordena vizinhos não visitados por grau residual decrescente (Heurística de Ramificação)
        candidatos = [v for v in vizinhos if v not in visitados]
        candidatos.sort(key=lambda v: grafo.grau(v), reverse=True)

        for vizinho in candidatos:
            # PODA: Testa se avançando para 'vizinho' ainda é possível retornar a 'inicio'
            # e calcula o limite superior teórico de nós que ainda podem ser adicionados
            visitados.add(vizinho)
            caminho.append(vizinho)

            pode_retornar, max_restantes = calcular_alcance_retorno(vizinho, visitados)

            # Condição de Poda 1: Impossível retornar à origem
            # Condição de Poda 2: Mesmo usando todos os alcançáveis, não supera o melhor ciclo já achado
            tamanho_maximo_possivel = len(caminho) + (max_restantes - 1) + 1  # +1 pelo nó 'inicio'
            if not pode_retornar or tamanho_maximo_possivel <= len(melhor_ciclo):
                podas_realizadas += 1
            else:
                bnb_dfs(vizinho, caminho, visitados)

            # Backtracking
            caminho.pop()
            visitados.remove(vizinho)

    # Inicia busca
    bnb_dfs(inicio, [inicio], {inicio})

    tempo_total = (time.perf_counter() - inicio_tempo) * 1000.0
    return melhor_ciclo, tempo_total, nos_expandidos, podas_realizadas


def heuristica_maior_ciclo(grafo, inicio):
    """
    ABORDAGEM 3: HEURÍSTICA POLINOMIAL (DFS GULOSO COM GARANTIA DE RETORNO)
    
    Explicações:
    - O problema de encontrar o maior ciclo simples é NP-Difícil. Para grafos grandes
      ou muitas linhas, os métodos exatos podem demorar muito.
    - Esta heurística executa em tempo estritamente polinomial O(|V| * (|V| + |E|)).
    - LÓGICA DO ALGORITMO:
      A cada passo, selecionamos gulozamente o vizinho não visitado com maior conectividade/grau,
      MAS apenas entre aqueles que comprovadamente ainda possuem caminho de volta até 'inicio'
      através dos nós restantes (checagem rápida por BFS).
      Assim, o caminho se estende o máximo possível sem jamais ficar preso em um beco sem saída.
    """
    inicio_tempo = time.perf_counter()
    
    caminho = [inicio]
    visitados = {inicio}
    atual = inicio

    def existe_caminho_de_retorno(origem, visitados_set):
        """Verifica por BFS se 'origem' consegue alcançar 'inicio' pelos nós livres."""
        fila = deque([origem])
        vistos = {origem}
        while fila:
            u = fila.popleft()
            for v in grafo.vizinhos(u):
                if v == inicio:
                    return True
                if v not in visitados_set and v not in vistos:
                    vistos.add(v)
                    fila.append(v)
        return False

    passos = 0
    while True:
        passos += 1
        vizinhos = grafo.vizinhos(atual)
        candidatos = [v for v in vizinhos if v not in visitados]

        # Filtra apenas vizinhos a partir dos quais ainda é viável voltar para o início
        candidatos_viaveis = []
        for cand in candidatos:
            visitados.add(cand)
            if existe_caminho_de_retorno(cand, visitados):
                candidatos_viaveis.append(cand)
            visitados.remove(cand)

        # Se não há como continuar por nós novos mantendo o retorno, verificamos se podemos fechar agora
        if not candidatos_viaveis:
            if inicio in vizinhos and len(caminho) >= 3:
                caminho.append(inicio)
            break

        # Escolha gulosa: seleciona o vizinho viável com maior número de conexões (maior grau)
        candidatos_viaveis.sort(key=lambda v: grafo.grau(v), reverse=True)
        proximo = candidatos_viaveis[0]

        visitados.add(proximo)
        caminho.append(proximo)
        atual = proximo

    # Se terminou fechando em 'inicio', temos um ciclo simples válido
    ciclo_encontrado = caminho if (len(caminho) >= 4 and caminho[0] == caminho[-1]) else []

    tempo_total = (time.perf_counter() - inicio_tempo) * 1000.0
    return ciclo_encontrado, tempo_total, passos


# ======================================================================================
# 5. PLACEHOLDERS PARA OS COLEGAS (INTEGRANTES 2 E 3)
# ======================================================================================
def resolver_problema_b(grafo, metodo):
    """
    PROBLEMA (B) - CONJUNTO DOMINANTE MÍNIMO (GUICHÊS DE VENDAS)
    Responsável: Integrante 2
    Métodos: 'forca_bruta', 'branch_and_bound', 'heuristica'
    """
    inicio_tempo = time.perf_counter()
    # Placeholder demonstrativo:
    tempo_total = (time.perf_counter() - inicio_tempo) * 1000.0
    return [], tempo_total, "A ser integrado pelo Integrante 2"


def resolver_problema_c(grafo, metodo):
    """
    PROBLEMA (C) - COLORAÇÃO DE VÉRTICES (PERÍODOS DE MANUTENÇÃO)
    Responsável: Integrante 3
    Métodos: 'forca_bruta', 'branch_and_bound', 'heuristica'
    """
    inicio_tempo = time.perf_counter()
    # Placeholder demonstrativo:
    tempo_total = (time.perf_counter() - inicio_tempo) * 1000.0
    return {}, tempo_total, "A ser integrado pelo Integrante 3"


# ======================================================================================
# 6. INTERFACE GRÁFICA (TKINTER) - INTEGRANTE 1
# ======================================================================================
class InterfaceMetro(tk.Tk):
    """
    Janela Principal da Interface Gráfica do Metrô de Paris.
    
    Responsabilidades:
    - Carregar e exibir arquivos de dados do metrô.
    - Desenhar o mapa no Canvas com auto-ajuste de escala e centralização.
    - Interagir com o usuário (seleção de problema, algoritmo, estação inicial).
    - Exibir visualmente o resultado (ciclo em destaque dourado com numeração).
    - Mostrar métricas precisas de tempo de execução e complexidade.
    """

    def __init__(self):
        super().__init__()
        self.title("Metrô de Paris - PAA (PUC Minas) - Integrante 1")
        self.geometry("1200x750")
        self.minsize(900, 600)

        # Dados do sistema
        self.grafo = GrafoMetro()
        self.ciclo_destacado = []
        self.estacao_selecionada = None

        # Configuração de Layout
        self._criar_componentes()

    def _criar_componentes(self):
        """Cria e organiza todos os painéis, menus, botões e canvas da interface."""
        
        # -------------------------------------------------------------
        # BARRA SUPERIOR: CONTROLES E SELETORES
        # -------------------------------------------------------------
        frame_topo = ttk.LabelFrame(self, text=" Painel de Controle e Parâmetros ", padding=10)
        frame_topo.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Botões de Carregar Arquivo
        btn_carregar_estacoes = ttk.Button(
            frame_topo, text="1. Carregar Estações (.txt)", command=self._acao_carregar_estacoes
        )
        btn_carregar_estacoes.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        btn_carregar_linhas = ttk.Button(
            frame_topo, text="2. Carregar Linhas (.txt)", command=self._acao_carregar_linhas
        )
        btn_carregar_linhas.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # Seletor do Problema
        ttk.Label(frame_topo, text="Problema:").grid(row=0, column=2, padx=(15, 2), pady=2, sticky="e")
        self.combo_problema = ttk.Combobox(
            frame_topo, state="readonly", width=32,
            values=[
                "Problema (a) - Maior Ciclo Simples",
                "Problema (b) - Conjunto Dominante",
                "Problema (c) - Coloração de Vértices"
            ]
        )
        self.combo_problema.current(0)
        self.combo_problema.grid(row=0, column=3, padx=5, pady=2)
        self.combo_problema.bind("<<ComboboxSelected>>", self._ao_mudar_problema)

        # Seletor do Algoritmo / Abordagem
        ttk.Label(frame_topo, text="Método:").grid(row=0, column=4, padx=(15, 2), pady=2, sticky="e")
        self.combo_metodo = ttk.Combobox(
            frame_topo, state="readonly", width=22,
            values=["Força Bruta", "Branch-and-Bound", "Heurística"]
        )
        self.combo_metodo.current(0)
        self.combo_metodo.grid(row=0, column=5, padx=5, pady=2)

        # Seletor da Estação Inicial (Específico do Problema a)
        self.label_origem = ttk.Label(frame_topo, text="Estação Origem:")
        self.label_origem.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.combo_origem = ttk.Combobox(frame_topo, state="readonly", width=24)
        self.combo_origem.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.combo_origem.bind("<<ComboboxSelected>>", self._ao_selecionar_origem_combo)

        # Botões de Ação
        btn_executar = ttk.Button(
            frame_topo, text="▶ Executar Algoritmo", command=self._acao_executar
        )
        btn_executar.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        btn_limpar = ttk.Button(
            frame_topo, text="Limpar Destaques", command=self._acao_limpar_destaques
        )
        btn_limpar.grid(row=1, column=4, padx=5, pady=5, sticky="w")

        # -------------------------------------------------------------
        # ÁREA PRINCIPAL: MAPA (CANVAS) + PAINEL LATERAL DE RESULTADOS
        # -------------------------------------------------------------
        frame_corpo = ttk.Frame(self)
        frame_corpo.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Canvas para desenho do mapa do Metrô
        self.canvas = tk.Canvas(frame_corpo, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda event: self.redesenhar_mapa())
        self.canvas.bind("<Button-1>", self._ao_clicar_no_canvas)

        # Painel Lateral de Métricas e Logs
        frame_lateral = ttk.LabelFrame(frame_corpo, text=" Métricas & Resultados ", width=320, padding=10)
        frame_lateral.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_lateral.pack_propagate(False)

        # Labels informativas
        self.lbl_status = ttk.Label(frame_lateral, text="Status: Aguardando carregamento", wraplength=290)
        self.lbl_status.pack(anchor="w", pady=2)

        self.lbl_tempo = ttk.Label(frame_lateral, text="Tempo: -- ms", font=("Segoe UI", 9, "bold"))
        self.lbl_tempo.pack(anchor="w", pady=2)

        self.lbl_metrica = ttk.Label(frame_lateral, text="Métrica: --", font=("Segoe UI", 9, "bold"))
        self.lbl_metrica.pack(anchor="w", pady=2)

        self.lbl_detalhes_busca = ttk.Label(frame_lateral, text="Nós / Podas: --", wraplength=290)
        self.lbl_detalhes_busca.pack(anchor="w", pady=2)

        ttk.Separator(frame_lateral, orient="horizontal").pack(fill=tk.X, pady=8)

        ttk.Label(frame_lateral, text="Sequência / Rota Encontrada:").pack(anchor="w")
        self.txt_resultado = tk.Text(frame_lateral, height=18, width=35, bg="#F4F6F7", font=("Consolas", 9))
        self.txt_resultado.pack(fill=tk.BOTH, expand=True, pady=5)

        # -------------------------------------------------------------
        # BARRA DE STATUS INFERIOR
        # -------------------------------------------------------------
        self.barra_status = ttk.Label(
            self, text="Dica: Clique em uma estação no mapa para defini-la como ponto de partida.",
            relief=tk.SUNKEN, anchor=tk.W, padding=3
        )
        self.barra_status.pack(side=tk.BOTTOM, fill=tk.X)

    # =================================================================
    # CONTROLE DE CARREGAMENTO DE ARQUIVOS
    # =================================================================
    def _acao_carregar_estacoes(self):
        """Abre o seletor de arquivos para carregar as coordenadas das estações."""
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo de estações",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if not caminho:
            return

        try:
            total = carregar_arquivo_estacoes(caminho, self.grafo)
            self._atualizar_dropdown_estacoes()
            self.redesenhar_mapa()
            self.lbl_status.config(text=f"{total} estações carregadas com sucesso.")
            messagebox.showinfo("Sucesso", f"{total} estações carregadas!")
        except Exception as e:
            messagebox.showerror("Erro ao Carregar", f"Falha ao ler arquivo de estações:\n{e}")

    def _acao_carregar_linhas(self):
        """Abre o seletor de arquivos para carregar os trechos e cores das linhas."""
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo de linhas do metrô",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if not caminho:
            return

        try:
            total = carregar_arquivo_linhas(caminho, self.grafo)
            self.redesenhar_mapa()
            self.lbl_status.config(text=f"{total} trechos de linha carregados.")
            messagebox.showinfo("Sucesso", f"{total} trechos carregados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro ao Carregar", f"Falha ao ler arquivo de linhas:\n{e}")

    def _atualizar_dropdown_estacoes(self):
        """Atualiza a lista de opções do Combobox de estações."""
        nomes = sorted(self.grafo.obter_todos_os_vertices())
        self.combo_origem["values"] = nomes
        if nomes:
            self.combo_origem.current(0)
            self.estacao_selecionada = nomes[0]

    def _ao_selecionar_origem_combo(self, event):
        """Chamado quando o usuário escolhe a estação pelo dropdown."""
        self.estacao_selecionada = self.combo_origem.get()
        self.redesenhar_mapa()

    def _ao_mudar_problema(self, event):
        """Controla a visibilidade dos controles de acordo com o problema escolhido."""
        prob = self.combo_problema.get()
        if "Problema (a)" in prob:
            self.label_origem.grid()
            self.combo_origem.grid()
        else:
            # Nos problemas b e c a estação de partida não é necessária
            self.label_origem.grid_remove()
            self.combo_origem.grid_remove()

    # =================================================================
    # RENDERIZAÇÃO GRÁFICA NO CANVAS (AUTO-ESCALA E DESTAQUES)
    # =================================================================
    def redesenhar_mapa(self):
        """
        Desenha todo o sistema de metrô no Canvas com cálculo dinâmico de escala
        para que qualquer conjunto de coordenadas caiba na janela visível.
        """
        self.canvas.delete("all")

        estacoes = self.grafo.estacoes
        if not estacoes:
            self.canvas.create_text(
                self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2,
                text="Carregue os arquivos de estações e linhas para visualizar o mapa.",
                fill="#888888", font=("Segoe UI", 12)
            )
            return

        # 1. Determina os limites mínimo e máximo das coordenadas
        xs = [coord[0] for coord in estacoes.values()]
        ys = [coord[1] for coord in estacoes.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        largura_canvas = max(self.canvas.winfo_width(), 400)
        altura_canvas = max(self.canvas.winfo_height(), 400)
        margem = 60

        dx = max(max_x - min_x, 1.0)
        dy = max(max_y - min_y, 1.0)

        escala_x = (largura_canvas - 2 * margem) / dx
        escala_y = (altura_canvas - 2 * margem) / dy
        # Mantém proporção visual uniforme (aspect ratio 1:1)
        escala = min(escala_x, escala_y)

        # Função interna de conversão das coordenadas do arquivo para o Canvas
        def para_canvas(x, y):
            cx = margem + (x - min_x) * escala
            cy = margem + (y - min_y) * escala
            return cx, cy

        # 2. Desenha todos os trechos normais (arestas)
        for u, v, linha, cor_nome in self.grafo.trechos:
            if u in estacoes and v in estacoes:
                x1, y1 = para_canvas(*estacoes[u])
                x2, y2 = para_canvas(*estacoes[v])
                cor_hex = obter_cor_hex(cor_nome)
                self.canvas.create_line(x1, y1, x2, y2, fill=cor_hex, width=3, capstyle=tk.ROUND)

        # 3. Desenha o destaque do ciclo (se houver um ciclo calculado)
        if self.ciclo_destacado and len(self.ciclo_destacado) > 1:
            for i in range(len(self.ciclo_destacado) - 1):
                u = self.ciclo_destacado[i]
                v = self.ciclo_destacado[i + 1]
                if u in estacoes and v in estacoes:
                    x1, y1 = para_canvas(*estacoes[u])
                    x2, y2 = para_canvas(*estacoes[v])
                    # Linha externa dourada espessa
                    self.canvas.create_line(x1, y1, x2, y2, fill="#FFD700", width=7, capstyle=tk.ROUND)
                    # Linha interna de contraste
                    self.canvas.create_line(x1, y1, x2, y2, fill="#FFFFFF", width=2, capstyle=tk.ROUND)

        # 4. Desenha as estações (vértices)
        raio = 7
        for nome, (x, y) in estacoes.items():
            cx, cy = para_canvas(x, y)

            # Define cor de preenchimento do vértice
            if nome == self.estacao_selecionada:
                cor_fundo = "#00FFFF"  # Ciano para estação de partida
                borda = "#FFFFFF"
                r = raio + 3
            elif nome in self.ciclo_destacado:
                cor_fundo = "#FFD700"  # Ouro para estações do ciclo
                borda = "#000000"
                r = raio + 2
            else:
                cor_fundo = "#FFFFFF"  # Branco padrão
                borda = "#333333"
                r = raio

            # Círculo da estação
            tag_estacao = f"estacao_{nome}"
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=cor_fundo, outline=borda, width=2, tags=(tag_estacao, "vertice")
            )

            # Rótulo com o nome da estação
            self.canvas.create_text(
                cx + r + 4, cy, text=nome, fill="#EEEEEE",
                anchor=tk.W, font=("Segoe UI", 8, "bold"), tags=("texto_vertice",)
            )

        # 5. Desenha a numeração de visita no ciclo (Problema a)
        if self.ciclo_destacado and len(self.ciclo_destacado) > 1:
            for idx, nome in enumerate(self.ciclo_destacado[:-1], start=1):
                if nome in estacoes:
                    cx, cy = para_canvas(*estacoes[nome])
                    self.canvas.create_text(
                        cx, cy - 14, text=f"#{idx}", fill="#FFD700",
                        font=("Segoe UI", 9, "bold")
                    )

    def _ao_clicar_no_canvas(self, event):
        """
        Permite ao usuário clicar diretamente em uma estação no mapa para
        defini-la como estação de partida.
        """
        estacoes = self.grafo.estacoes
        if not estacoes:
            return

        # Recalcula a escala para saber qual estação está próxima do clique
        xs = [coord[0] for coord in estacoes.values()]
        ys = [coord[1] for coord in estacoes.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        largura = max(self.canvas.winfo_width(), 400)
        altura = max(self.canvas.winfo_height(), 400)
        margem = 60
        escala = min((largura - 2 * margem) / max(max_x - min_x, 1.0),
                     (altura - 2 * margem) / max(max_y - min_y, 1.0))

        # Encontra a estação mais próxima dentro de um raio de 15 pixels
        clique_x, clique_y = event.x, event.y
        estacao_mais_proxima = None
        menor_distancia = 15.0

        for nome, (x, y) in estacoes.items():
            cx = margem + (x - min_x) * escala
            cy = margem + (y - min_y) * escala
            dist = math.hypot(clique_x - cx, clique_y - cy)
            if dist < menor_distancia:
                menor_distancia = dist
                estacao_mais_proxima = nome

        if estacao_mais_proxima:
            self.estacao_selecionada = estacao_mais_proxima
            self.combo_origem.set(estacao_mais_proxima)
            self.redesenhar_mapa()
            self.barra_status.config(text=f"Estação selecionada: {estacao_mais_proxima}")

    # =================================================================
    # DISPARO DOS ALGORITMOS
    # =================================================================
    def _acao_executar(self):
        """Dispara a execução do problema e abordagem selecionados."""
        if not self.grafo.estacoes:
            messagebox.showwarning("Atenção", "Por favor, carregue os arquivos de estações e linhas primeiro.")
            return

        problema = self.combo_problema.get()
        metodo = self.combo_metodo.get()

        # -------------------------------------------------------------
        # CASO 1: PROBLEMA (A) - MAIOR CICLO SIMPLES (INTEGRANTE 1)
        # -------------------------------------------------------------
        if "Problema (a)" in problema:
            origem = self.combo_origem.get()
            if not origem or origem not in self.grafo.estacoes:
                messagebox.showwarning("Atenção", "Selecione uma estação de origem válida.")
                return

            self.lbl_status.config(text=f"Executando {metodo} para o Problema (a)...")
            self.update_idletasks()

            ciclo = []
            tempo_ms = 0.0

            if metodo == "Força Bruta":
                candidatos_qtd = sum(1 for v in self.grafo.obter_todos_os_vertices() if v != origem and self.grafo.grau(v) >= 2)
                if candidatos_qtd > 10:
                    aviso = messagebox.askyesno(
                        "Força Bruta Pura (Sem Backtracking)",
                        f"Atenção: A Força Bruta Pura irá testar permutações cegas de {candidatos_qtd} estações (dezenas de milhões de permutações).\n\n"
                        "Isso pode levar de alguns segundos a vários minutos.\n\n"
                        "Deseja continuar mesmo assim?\n"
                        "(Dica: O Branch-and-Bound resolve a mesma instância ótima em milissegundos!)"
                    )
                    if not aviso:
                        self.lbl_status.config(text="Execução cancelada pelo usuário.")
                        return

                ciclo, tempo_ms, permutacoes = forca_bruta_maior_ciclo(self.grafo, origem)
                self.lbl_detalhes_busca.config(text=f"Permutações avaliadas: {permutacoes:,}")
            elif metodo == "Branch-and-Bound":
                ciclo, tempo_ms, nos, podas = branch_and_bound_maior_ciclo(self.grafo, origem)
                self.lbl_detalhes_busca.config(text=f"Nós: {nos:,} | Podas efetuadas: {podas:,}")
            else:  # Heurística
                ciclo, tempo_ms, passos = heuristica_maior_ciclo(self.grafo, origem)
                self.lbl_detalhes_busca.config(text=f"Passos gulosos realizados: {passos}")

            # Atualiza os dados na tela
            self.ciclo_destacado = ciclo
            self.lbl_tempo.config(text=f"Tempo: {tempo_ms:.3f} ms")
            
            if ciclo:
                qtd_estacoes = len(ciclo) - 1  # desconta a repetição final da origem
                self.lbl_metrica.config(text=f"Maior Ciclo: {qtd_estacoes} estações visitadas")
                self.lbl_status.config(text="Solução encontrada com sucesso!")

                # Exibe a sequência no painel de texto
                self.txt_resultado.delete("1.0", tk.END)
                self.txt_resultado.insert(tk.END, f"ROTA DO CICLO (Total: {qtd_estacoes} estações):\n")
                self.txt_resultado.insert(tk.END, "-" * 34 + "\n")
                for i, st in enumerate(ciclo):
                    if i == len(ciclo) - 1:
                        self.txt_resultado.insert(tk.END, f"🏁 Retorno: {st}\n")
                    elif i == 0:
                        self.txt_resultado.insert(tk.END, f"🚩 Partida: {st}\n")
                    else:
                        self.txt_resultado.insert(tk.END, f"  {i}. {st}\n")
            else:
                self.lbl_metrica.config(text="Métrica: Nenhum ciclo encontrado")
                self.lbl_status.config(text="Não existe ciclo simples a partir desta estação.")
                self.txt_resultado.delete("1.0", tk.END)
                self.txt_resultado.insert(tk.END, "Nenhum ciclo simples de tamanho >= 3 foi encontrado.")

            self.redesenhar_mapa()

        # -------------------------------------------------------------
        # CASO 2: PROBLEMA (B) - CONJUNTO DOMINANTE (INTEGRANTE 2)
        # -------------------------------------------------------------
        elif "Problema (b)" in problema:
            self.lbl_status.config(text="Executando Problema (b)...")
            res, tempo_ms, msg = resolver_problema_b(self.grafo, metodo)
            self.lbl_tempo.config(text=f"Tempo: {tempo_ms:.3f} ms")
            self.lbl_metrica.config(text=f"Guichês: {len(res)}")
            self.txt_resultado.delete("1.0", tk.END)
            self.txt_resultado.insert(tk.END, f"Módulo do Integrante 2:\n{msg}")

        # -------------------------------------------------------------
        # CASO 3: PROBLEMA (C) - COLORAÇÃO DE VÉRTICES (INTEGRANTE 3)
        # -------------------------------------------------------------
        elif "Problema (c)" in problema:
            self.lbl_status.config(text="Executando Problema (c)...")
            res, tempo_ms, msg = resolver_problema_c(self.grafo, metodo)
            self.lbl_tempo.config(text=f"Tempo: {tempo_ms:.3f} ms")
            self.lbl_metrica.config(text="Cores: --")
            self.txt_resultado.delete("1.0", tk.END)
            self.txt_resultado.insert(tk.END, f"Módulo do Integrante 3:\n{msg}")

    def _acao_limpar_destaques(self):
        """Limpa as marcações visuais e campos de texto."""
        self.ciclo_destacado = []
        self.lbl_tempo.config(text="Tempo: -- ms")
        self.lbl_metrica.config(text="Métrica: --")
        self.lbl_detalhes_busca.config(text="Nós / Podas: --")
        self.txt_resultado.delete("1.0", tk.END)
        self.lbl_status.config(text="Destaques limpos.")
        self.redesenhar_mapa()


# ======================================================================================
# 7. PONTO DE ENTRADA DA APLICAÇÃO
# ======================================================================================
if __name__ == "__main__":
    app = InterfaceMetro()
    app.mainloop()
