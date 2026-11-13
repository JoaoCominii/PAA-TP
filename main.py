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
import sys
from collections import deque
from dataclasses import dataclass
from itertools import permutations, product


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


LIMITE_DE_TEMPO_GUI_SEGUNDOS = 30.0


@dataclass
class ResultadoColoracao:
    cor_por_estacao: dict[str, int]
    quantidade_de_cores: int
    nos_explorados: int
    tempo_segundos: float
    interrompido_por_tempo: bool


def coloracao_eh_valida(adjacencia: dict[str, set[str]], cor_por_estacao: dict[str, int]) -> bool:
    for estacao in adjacencia:
        if estacao not in cor_por_estacao:
            return False
    for estacao, vizinhos in adjacencia.items():
        for vizinho in vizinhos:
            if cor_por_estacao[estacao] == cor_por_estacao.get(vizinho):
                return False
    return True


def tempo_esgotado(inicio: float, limite_de_tempo_segundos: float | None) -> bool:
    return limite_de_tempo_segundos is not None and time.perf_counter() - inicio >= limite_de_tempo_segundos


def colorir_cada_estacao_com_cor_distinta(adjacencia: dict[str, set[str]]) -> dict[str, int]:
    return {estacao: indice for indice, estacao in enumerate(adjacencia)}


def tamanho_de_clique_gulosa(adjacencia: dict[str, set[str]]) -> int:
    vertices_por_grau_decrescente = sorted(adjacencia, key=lambda estacao: -len(adjacencia[estacao]))
    clique: list[str] = []
    for estacao in vertices_por_grau_decrescente:
        if all(membro in adjacencia[estacao] for membro in clique):
            clique.append(estacao)
    return len(clique)


def colorir_por_welsh_powell(adjacencia: dict[str, set[str]]) -> ResultadoColoracao:
    inicio = time.perf_counter()
    vertices_por_grau_decrescente = sorted(adjacencia, key=lambda estacao: -len(adjacencia[estacao]))
    cor_por_estacao: dict[str, int] = {}
    tentativas_de_colorir = 0
    cor_atual = 0
    while len(cor_por_estacao) < len(vertices_por_grau_decrescente):
        estacoes_com_cor_atual: set[str] = set()
        for estacao in vertices_por_grau_decrescente:
            if estacao in cor_por_estacao:
                continue
            tentativas_de_colorir += 1
            if adjacencia[estacao].isdisjoint(estacoes_com_cor_atual):
                cor_por_estacao[estacao] = cor_atual
                estacoes_com_cor_atual.add(estacao)
        cor_atual += 1
    return ResultadoColoracao(
        cor_por_estacao=cor_por_estacao,
        quantidade_de_cores=cor_atual,
        nos_explorados=tentativas_de_colorir,
        tempo_segundos=time.perf_counter() - inicio,
        interrompido_por_tempo=False,
    )


def colorir_por_forca_bruta(
    adjacencia: dict[str, set[str]], limite_de_tempo_segundos: float | None = None
) -> ResultadoColoracao:
    inicio = time.perf_counter()
    estacoes = list(adjacencia)
    quantidade_de_estacoes = len(estacoes)
    atribuicoes_testadas = 0
    for quantidade_de_cores in range(1, quantidade_de_estacoes + 1):
        for atribuicao_de_cores in product(range(quantidade_de_cores), repeat=quantidade_de_estacoes):
            if tempo_esgotado(inicio, limite_de_tempo_segundos):
                return ResultadoColoracao(
                    cor_por_estacao=colorir_cada_estacao_com_cor_distinta(adjacencia),
                    quantidade_de_cores=quantidade_de_estacoes,
                    nos_explorados=atribuicoes_testadas,
                    tempo_segundos=time.perf_counter() - inicio,
                    interrompido_por_tempo=True,
                )
            atribuicoes_testadas += 1
            cor_por_estacao = dict(zip(estacoes, atribuicao_de_cores))
            if coloracao_eh_valida(adjacencia, cor_por_estacao):
                return ResultadoColoracao(
                    cor_por_estacao=cor_por_estacao,
                    quantidade_de_cores=quantidade_de_cores,
                    nos_explorados=atribuicoes_testadas,
                    tempo_segundos=time.perf_counter() - inicio,
                    interrompido_por_tempo=False,
                )
    return ResultadoColoracao(
        cor_por_estacao={},
        quantidade_de_cores=0,
        nos_explorados=atribuicoes_testadas,
        tempo_segundos=time.perf_counter() - inicio,
        interrompido_por_tempo=False,
    )


def colorir_por_branch_and_bound(
    adjacencia: dict[str, set[str]], limite_de_tempo_segundos: float | None = None
) -> ResultadoColoracao:
    inicio = time.perf_counter()
    estacoes = list(adjacencia)
    quantidade_de_estacoes = len(estacoes)
    resultado_da_heuristica = colorir_por_welsh_powell(adjacencia)
    estado = {
        "melhor_coloracao": dict(resultado_da_heuristica.cor_por_estacao),
        "melhor_quantidade_de_cores": resultado_da_heuristica.quantidade_de_cores,
        "nos_explorados": 0,
        "interrompido_por_tempo": False,
        "otimo_provado": False,
    }
    limite_inferior = tamanho_de_clique_gulosa(adjacencia)
    if estado["melhor_quantidade_de_cores"] <= limite_inferior:
        estado["otimo_provado"] = True

    cor_por_estacao: dict[str, int] = {}
    quantidade_de_vizinhos_por_cor: dict[str, dict[int, int]] = {estacao: {} for estacao in estacoes}

    def pintar_estacao(estacao: str, cor: int) -> None:
        cor_por_estacao[estacao] = cor
        for vizinho in adjacencia[estacao]:
            contagem_do_vizinho = quantidade_de_vizinhos_por_cor[vizinho]
            contagem_do_vizinho[cor] = contagem_do_vizinho.get(cor, 0) + 1

    def despintar_estacao(estacao: str) -> None:
        cor = cor_por_estacao.pop(estacao)
        for vizinho in adjacencia[estacao]:
            contagem_do_vizinho = quantidade_de_vizinhos_por_cor[vizinho]
            contagem_do_vizinho[cor] -= 1
            if contagem_do_vizinho[cor] == 0:
                del contagem_do_vizinho[cor]

    def escolher_estacao_com_maior_saturacao() -> str:
        return max(
            (estacao for estacao in estacoes if estacao not in cor_por_estacao),
            key=lambda estacao: (len(quantidade_de_vizinhos_por_cor[estacao]), len(adjacencia[estacao])),
        )

    def busca_deve_parar() -> bool:
        if estado["otimo_provado"] or estado["interrompido_por_tempo"]:
            return True
        if tempo_esgotado(inicio, limite_de_tempo_segundos):
            estado["interrompido_por_tempo"] = True
            return True
        return False

    def ramificar(cores_usadas_no_ramo: int) -> None:
        if busca_deve_parar():
            return
        estado["nos_explorados"] += 1
        if cores_usadas_no_ramo >= estado["melhor_quantidade_de_cores"]:
            return
        if len(cor_por_estacao) == quantidade_de_estacoes:
            estado["melhor_coloracao"] = dict(cor_por_estacao)
            estado["melhor_quantidade_de_cores"] = cores_usadas_no_ramo
            if cores_usadas_no_ramo <= limite_inferior:
                estado["otimo_provado"] = True
            return
        estacao_escolhida = escolher_estacao_com_maior_saturacao()
        cores_proibidas = quantidade_de_vizinhos_por_cor[estacao_escolhida]
        for cor_ja_usada in range(cores_usadas_no_ramo):
            if cor_ja_usada in cores_proibidas:
                continue
            pintar_estacao(estacao_escolhida, cor_ja_usada)
            ramificar(cores_usadas_no_ramo)
            despintar_estacao(estacao_escolhida)
            if busca_deve_parar():
                return
        if cores_usadas_no_ramo + 1 < estado["melhor_quantidade_de_cores"]:
            pintar_estacao(estacao_escolhida, cores_usadas_no_ramo)
            ramificar(cores_usadas_no_ramo + 1)
            despintar_estacao(estacao_escolhida)

    limite_de_recursao_original = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limite_de_recursao_original, 2 * quantidade_de_estacoes + 100))
    try:
        ramificar(0)
    finally:
        sys.setrecursionlimit(limite_de_recursao_original)

    return ResultadoColoracao(
        cor_por_estacao=estado["melhor_coloracao"],
        quantidade_de_cores=estado["melhor_quantidade_de_cores"],
        nos_explorados=estado["nos_explorados"],
        tempo_segundos=time.perf_counter() - inicio,
        interrompido_por_tempo=estado["interrompido_por_tempo"],
    )


def extrair_adjacencia_simples(grafo: GrafoMetro) -> dict[str, set[str]]:
    return {
        estacao: {
            vizinho
            for vizinho in grafo.adjacencias.get(estacao, {})
            if vizinho in grafo.estacoes and vizinho != estacao
        }
        for estacao in grafo.estacoes
    }


def montar_mensagem_da_coloracao(resultado: ResultadoColoracao) -> str:
    estacoes_por_periodo: dict[int, list[str]] = {}
    for estacao, cor in resultado.cor_por_estacao.items():
        estacoes_por_periodo.setdefault(cor, []).append(estacao)
    linhas_da_mensagem = [
        f"Períodos de manutenção (cores): {resultado.quantidade_de_cores}",
        f"Nós explorados: {resultado.nos_explorados:,}",
    ]
    if resultado.interrompido_por_tempo:
        linhas_da_mensagem.append(
            f"AVISO: limite de {LIMITE_DE_TEMPO_GUI_SEGUNDOS:.0f} s atingido; "
            "esta é a melhor solução encontrada, sem garantia de ótimo."
        )
    linhas_da_mensagem.append("")
    for cor in sorted(estacoes_por_periodo):
        linhas_da_mensagem.append(f"Período {cor + 1}: {', '.join(sorted(estacoes_por_periodo[cor]))}")
    return "\n".join(linhas_da_mensagem)


def resolver_problema_c(grafo, metodo):
    """
    PROBLEMA (C) - COLORAÇÃO DE VÉRTICES (PERÍODOS DE MANUTENÇÃO)
    Responsável: Integrante 3
    Métodos: 'forca_bruta', 'branch_and_bound', 'heuristica'
    """
    adjacencia = extrair_adjacencia_simples(grafo)
    # Normaliza o nome do método para ser robusto a acentos e variações de string
    metodo_norm = metodo.lower().replace("ç", "c").replace("á", "a").replace("é", "e").replace("ó", "o").replace("í", "i").replace("ú", "u")
    if "bruta" in metodo_norm or metodo_norm == "forca_bruta":
        resultado = colorir_por_forca_bruta(adjacencia, limite_de_tempo_segundos=LIMITE_DE_TEMPO_GUI_SEGUNDOS)
    elif "bound" in metodo_norm or metodo_norm == "branch_and_bound":
        resultado = colorir_por_branch_and_bound(adjacencia, limite_de_tempo_segundos=LIMITE_DE_TEMPO_GUI_SEGUNDOS)
    elif "heur" in metodo_norm:
        resultado = colorir_por_welsh_powell(adjacencia)
    else:
        return {}, 0.0, f"Método desconhecido: {metodo}"
    tempo_ms = resultado.tempo_segundos * 1000.0
    return resultado.cor_por_estacao, tempo_ms, montar_mensagem_da_coloracao(resultado)


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
        self.ciclo_destacado = []       # Problema (a): lista de estações do ciclo encontrado
        self.estacao_selecionada = None # Problema (a): estação de partida selecionada
        self.coloracao_destacada = {}   # Problema (c): dicionário { nome_estacao: id_periodo (int) }

        # Paleta de cores visuais para os períodos de manutenção (Problema c).
        # Cada índice de período (0, 1, 2, ...) recebe uma cor distinta e legível no Canvas escuro.
        # Adicionamos 20 cores para suportar grafos com número cromático alto.
        self.paleta_periodos = [
            "#E74C3C",  # 0 - Vermelho
            "#3498DB",  # 1 - Azul
            "#2ECC71",  # 2 - Verde
            "#F39C12",  # 3 - Laranja
            "#9B59B6",  # 4 - Roxo
            "#1ABC9C",  # 5 - Turquesa
            "#F1C40F",  # 6 - Amarelo
            "#E67E22",  # 7 - Laranja escuro
            "#EC407A",  # 8 - Rosa
            "#00BCD4",  # 9 - Ciano
            "#8BC34A",  # 10 - Verde limão
            "#FF7043",  # 11 - Coral
            "#7E57C2",  # 12 - Lilás
            "#26C6DA",  # 13 - Azul claro
            "#D4E157",  # 14 - Verde amarelado
            "#FF8A65",  # 15 - Salmão
            "#AB47BC",  # 16 - Violeta
            "#29B6F6",  # 17 - Azul céu
            "#66BB6A",  # 18 - Verde médio
            "#FFA726",  # 19 - Âmbar
        ]

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

            # Define cor e raio do vértice de acordo com o estado atual da interface:
            # - Problema (a) ativo: estação de partida fica ciano, estações do ciclo ficam douradas.
            # - Problema (c) ativo: cada estação recebe a cor do período de manutenção calculado.
            # - Estado padrão (sem resultado): círculo branco.
            if self.coloracao_destacada:
                # Problema (c): pinta o círculo com a cor do período de manutenção
                id_periodo = self.coloracao_destacada.get(nome, -1)
                if id_periodo >= 0:
                    idx_paleta = id_periodo % len(self.paleta_periodos)
                    cor_fundo = self.paleta_periodos[idx_paleta]
                    borda = "#FFFFFF"
                else:
                    # Estação sem período atribuído (não deveria ocorrer numa solução válida)
                    cor_fundo = "#888888"
                    borda = "#FFFFFF"
                r = raio + 2  # Ligeiramente maior para destacar bem a cor

            elif nome == self.estacao_selecionada:
                # Problema (a): estação de partida selecionada pelo usuário
                cor_fundo = "#00FFFF"  # Ciano
                borda = "#FFFFFF"
                r = raio + 3
            elif nome in self.ciclo_destacado:
                # Problema (a): estação que faz parte do ciclo encontrado
                cor_fundo = "#FFD700"  # Ouro
                borda = "#000000"
                r = raio + 2
            else:
                # Estado padrão sem nenhum resultado ativo
                cor_fundo = "#FFFFFF"
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

        # 6. Desenha a legenda de períodos de manutenção (Problema c)
        # Exibe uma caixinha no canto inferior esquerdo do Canvas mostrando
        # cada período com sua cor correspondente, para que o usuário entenda o mapa.
        if self.coloracao_destacada:
            ids_unicos = sorted(set(self.coloracao_destacada.values()))
            x_leg, y_leg = 15, largura_canvas - 20 - len(ids_unicos) * 22
            self.canvas.create_rectangle(
                x_leg - 5, y_leg - 8,
                x_leg + 155, y_leg + len(ids_unicos) * 22 + 4,
                fill="#222222", outline="#555555"
            )
            self.canvas.create_text(
                x_leg + 75, y_leg - 2, text="Períodos de Manutenção",
                fill="#FFFFFF", font=("Segoe UI", 8, "bold"), anchor=tk.N
            )
            for i, id_periodo in enumerate(ids_unicos):
                cor = self.paleta_periodos[id_periodo % len(self.paleta_periodos)]
                yy = y_leg + 18 + i * 22
                # Quadrado colorido
                self.canvas.create_rectangle(x_leg, yy - 8, x_leg + 16, yy + 8, fill=cor, outline="#FFFFFF")
                # Rótulo do período
                self.canvas.create_text(
                    x_leg + 22, yy, text=f"Período {id_periodo + 1}",
                    fill="#FFFFFF", font=("Segoe UI", 9), anchor=tk.W
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
            self.lbl_status.config(text="Executando Problema (c)... Aguarde.")
            self.update_idletasks()

            res, tempo_ms, msg = resolver_problema_c(self.grafo, metodo)

            # Guarda o dicionário { estacao: id_periodo } para o redesenho colorido do mapa
            self.coloracao_destacada = res if res else {}
            # Garante que o ciclo do Problema (a) seja apagado ao exibir o Problema (c)
            self.ciclo_destacado = []

            self.lbl_tempo.config(text=f"Tempo: {tempo_ms:.3f} ms")

            if res:
                num_cores = len(set(res.values()))
                self.lbl_metrica.config(text=f"Número cromático χ(G) = {num_cores} período(s)")
                self.lbl_status.config(text=f"Coloração calculada: {num_cores} períodos de manutenção.")
            else:
                self.lbl_metrica.config(text="Cores: Nenhuma solução encontrada")
                self.lbl_status.config(text="Não foi possível calcular a coloração.")

            self.lbl_detalhes_busca.config(text="Veja painel lateral para detalhes.")
            self.txt_resultado.delete("1.0", tk.END)
            self.txt_resultado.insert(tk.END, msg)

            # Redesenha o mapa com as estações coloridas por período
            self.redesenhar_mapa()

    def _acao_limpar_destaques(self):
        """Limpa as marcações visuais e campos de texto de todos os problemas."""
        self.ciclo_destacado = []       # Limpa o ciclo do Problema (a)
        self.coloracao_destacada = {}   # Limpa a coloração do Problema (c)
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
