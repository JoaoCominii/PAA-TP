"""
========================================================================================
PUC MINAS - ICEI - CIÊNCIA DA COMPUTAÇÃO
DISCIPLINA: PROJETO E ANÁLISE DE ALGORITMOS (PAA)
PROFESSOR: ALEXEI MACHADO
TRABALHO PRÁTICO: O METRÔ DE PARIS
========================================================================================
INTEGRANTES DO GRUPO:
- Henrique Lourenço Pinto Coelho
- João Comini César de Andrade
- Rafael Rehfeld Martins de Oliveira
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
import csv
import math
import multiprocessing
import os
import queue
import statistics
import sys
import traceback
import tracemalloc
from collections import deque
from dataclasses import dataclass
from itertools import combinations, permutations, product


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

    def limpar_trechos(self):
        """Remove todas as ligações, mantendo as estações e suas coordenadas."""
        self.adjacencias = {nome: {} for nome in self.estacoes}
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
def carregar_arquivo_estacoes(caminho_arquivo, grafo, avisos=None):
    """
    Lê o arquivo de estações no formato:
        NomeEstacao x y
    Exemplos aceitos:
        Nation 100 150
        Republique 50 100
        Gare du Nord 510 150 (suporta nomes compostos com espaços ou underlines)

    Um novo arquivo de estações substitui todo o grafo anterior (estações e linhas).
    Se 'avisos' for uma lista, recebe a descrição das linhas ignoradas ou repetidas.
    """
    if avisos is None:
        avisos = []
    grafo.limpar()
    total_lidas = 0
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        for numero_linha, linha in enumerate(f, start=1):
            linha = linha.strip()
            # Ignora linhas em branco ou comentários
            if not linha or linha.startswith("#"):
                continue

            # rsplit com maxsplit=2 garante que os dois últimos itens sejam as coordenadas x e y,
            # e todo o restante inicial seja tratado como o nome da estação (mesmo com espaços).
            partes = linha.rsplit(None, 2)
            if len(partes) != 3:
                avisos.append(f"Linha {numero_linha} ignorada (esperado 'Nome x y'): {linha}")
                continue
            nome = partes[0].strip()
            try:
                x = float(partes[1])
                y = float(partes[2])
            except ValueError:
                avisos.append(f"Linha {numero_linha} ignorada (coordenadas inválidas): {linha}")
                continue
            if nome in grafo.estacoes:
                avisos.append(f"Linha {numero_linha}: estação '{nome}' repetida; mantida a última posição.")
            else:
                total_lidas += 1
            grafo.adicionar_estacao(nome, x, y)
    return total_lidas


def carregar_arquivo_linhas(caminho_arquivo, grafo, avisos=None):
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
    Exige que o arquivo de estações já tenha sido carregado, pois é ele que permite separar
    "Gare du Nord Gare de l'Est" nas duas estações corretas.
    Um novo arquivo de linhas substitui as ligações anteriores, mantendo as estações.
    Trechos com estações desconhecidas são ignorados e registrados em 'avisos' (se for uma lista),
    assim como seções cuja quantidade de trechos não bate com o cabeçalho.
    """
    if avisos is None:
        avisos = []
    if not grafo.estacoes:
        raise ValueError("Carregue o arquivo de estações antes do arquivo de linhas.")
    grafo.limpar_trechos()
    total_trechos = 0
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [
            (numero, l.strip())
            for numero, l in enumerate(f, start=1)
            if l.strip() and not l.strip().startswith("#")
        ]

    estacoes_conhecidas = sorted(grafo.estacoes.keys(), key=lambda s: len(s), reverse=True)

    def eh_cabecalho(texto):
        # "LinhaX cor N": começa com 'Linha' e termina com a quantidade de trechos
        partes = texto.split()
        return len(partes) >= 3 and partes[0].lower().startswith("linha") and partes[-1].isdigit()

    def separar_estacoes(texto_trecho):
        # 1. Tentativa via delimitadores comuns (tabulação, ponto-e-vírgula ou hífen com espaços)
        for delim in ["\t", ";", " - "]:
            if delim in texto_trecho:
                pedacos = texto_trecho.split(delim, 1)
                return pedacos[0].strip(), pedacos[1].strip()
        # 2. Casa o início do texto com uma estação cadastrada (nomes mais longos primeiro)
        for est in estacoes_conhecidas:
            if texto_trecho.startswith(est + " "):
                resto = texto_trecho[len(est):].strip()
                if resto in grafo.estacoes:
                    return est, resto
        # 3. Fallback: duas palavras simples
        par = texto_trecho.split()
        if len(par) == 2:
            return par[0], par[1]
        return None, None

    total_trechos = 0
    i = 0
    while i < len(linhas):
        numero_cabecalho, texto = linhas[i]
        i += 1
        if not eh_cabecalho(texto):
            avisos.append(f"Linha {numero_cabecalho} ignorada (fora de uma seção 'LinhaX cor N'): {texto}")
            continue
        cabecalho = texto.split()
        nome_linha = cabecalho[0]
        cor = " ".join(cabecalho[1:-1])
        qtd_trechos = int(cabecalho[-1])
        lidos = 0
        while i < len(linhas) and not eh_cabecalho(linhas[i][1]):
            numero_trecho, texto_trecho = linhas[i]
            i += 1
            u, v = separar_estacoes(texto_trecho)
            if u is None:
                avisos.append(f"Linha {numero_trecho} ({nome_linha}): trecho não reconhecido: {texto_trecho}")
                continue
            desconhecidas = [nome for nome in (u, v) if nome not in grafo.estacoes]
            if desconhecidas:
                avisos.append(
                    f"Linha {numero_trecho} ({nome_linha}): estação não cadastrada "
                    f"{', '.join(repr(n) for n in desconhecidas)}; trecho ignorado."
                )
                continue
            if u == v:
                avisos.append(f"Linha {numero_trecho} ({nome_linha}): trecho liga '{u}' a ela mesma; ignorado.")
                continue
            grafo.adicionar_trecho(u, v, nome_linha, cor)
            total_trechos += 1
            lidos += 1
        if lidos != qtd_trechos:
            avisos.append(f"{nome_linha}: cabeçalho indica {qtd_trechos} trechos, mas {lidos} foram lidos.")
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
# 5. PROBLEMA (C) — COLORAÇÃO DE VÉRTICES (INTEGRANTE 3)
# ======================================================================================
"""
O PROBLEMA:
Determinar o menor número de períodos de manutenção tal que duas estações ligadas
diretamente por um trecho (de qualquer linha) nunca fiquem em manutenção no mesmo período.

MODELAGEM:
- Grafo não direcionado G(V, E): V = estações, E = trechos entre estações vizinhas.
- Cada período de manutenção é uma COR; estações vizinhas precisam ter cores diferentes.
- A resposta é o número cromático χ(G) e a cor (período) de cada estação.
- É a Coloração de Vértices, problema NP-Difícil.

CONTRATO USADO PELOS TRÊS MÉTODOS:
- Entrada: adjacencia (dict estação -> conjunto de vizinhos), simétrica e sem laços.
- Saída: ResultadoColoracao, com as cores numeradas de 0 a k-1.
- Os métodos exatos aceitam um limite de tempo e, se ele estourar, devolvem a melhor
  solução conhecida com interrompido_por_tempo=True.
"""

# Limite usado pela interface para que a força bruta e o B&B não congelem a janela
LIMITE_DE_TEMPO_GUI_SEGUNDOS = 30.0


@dataclass
class ResultadoColoracao:
    """
    Resultado devolvido por qualquer um dos três métodos de coloração.

    Campos:
    - cor_por_estacao: cor (período) atribuída a cada estação, de 0 a k-1.
    - quantidade_de_cores: k, número de cores (períodos) usadas.
    - nos_explorados: trabalho realizado, usado para comparar os métodos no relatório
      (atribuições testadas na força bruta, nós da árvore no B&B, testes no Welsh-Powell).
    - tempo_segundos: tempo de execução do algoritmo.
    - interrompido_por_tempo: True se o limite de tempo estourou antes do fim da busca.
    """
    cor_por_estacao: dict[str, int]
    quantidade_de_cores: int
    nos_explorados: int
    tempo_segundos: float
    interrompido_por_tempo: bool


def coloracao_eh_valida(adjacencia: dict[str, set[str]], cor_por_estacao: dict[str, int]) -> bool:
    """
    Verifica se uma coloração é válida para o grafo.

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.
    - cor_por_estacao: cor atribuída a cada estação.

    Retorno: True se todas as estações têm cor e nenhum par de vizinhas tem a mesma cor.
    Complexidade: O(|V| + |E|).
    """
    # 1. Toda estação precisa ter recebido uma cor
    for estacao in adjacencia:
        if estacao not in cor_por_estacao:
            return False
    # 2. Nenhum trecho pode ligar duas estações com a mesma cor
    for estacao, vizinhos in adjacencia.items():
        for vizinho in vizinhos:
            if cor_por_estacao[estacao] == cor_por_estacao.get(vizinho):
                return False
    return True


def tempo_esgotado(inicio: float, limite_de_tempo_segundos: float | None) -> bool:
    """
    Indica se o limite de tempo de um algoritmo já foi atingido.

    Parâmetros:
    - inicio: instante inicial, obtido com time.perf_counter().
    - limite_de_tempo_segundos: limite em segundos, ou None para executar sem limite.

    Retorno: True se existe limite e o tempo decorrido já chegou nele.
    """
    return limite_de_tempo_segundos is not None and time.perf_counter() - inicio >= limite_de_tempo_segundos


def colorir_cada_estacao_com_cor_distinta(adjacencia: dict[str, set[str]]) -> dict[str, int]:
    """
    Gera a coloração trivial em que cada estação recebe uma cor diferente (k = |V|).
    É sempre válida e serve de "melhor solução conhecida" quando a força bruta é
    interrompida antes de encontrar qualquer coloração.

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.

    Retorno: dict estação -> cor, com cores 0, 1, ..., |V|-1 na ordem do dicionário.
    """
    return {estacao: indice for indice, estacao in enumerate(adjacencia)}


def tamanho_de_clique_gulosa(adjacencia: dict[str, set[str]]) -> int:
    """
    Encontra de forma gulosa uma clique (conjunto de estações todas vizinhas entre si)
    e devolve o seu tamanho. Como os vértices de uma clique precisam de cores distintas,
    esse tamanho é um LIMITE INFERIOR para o número cromático χ(G).

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.

    Retorno: tamanho da clique encontrada (não necessariamente a maior clique do grafo).
    Complexidade: O(|V| log |V|) da ordenação + O(|V| * ω) dos testes, ω = tamanho da clique.
    """
    # Estações de maior grau primeiro: têm mais chance de pertencer a uma clique grande
    vertices_por_grau_decrescente = sorted(adjacencia, key=lambda estacao: -len(adjacencia[estacao]))
    clique: list[str] = []
    for estacao in vertices_por_grau_decrescente:
        # Só entra na clique se for vizinha de todas as estações que já estão nela
        if all(membro in adjacencia[estacao] for membro in clique):
            clique.append(estacao)
    return len(clique)


def colorir_por_welsh_powell(adjacencia: dict[str, set[str]]) -> ResultadoColoracao:
    """
    ABORDAGEM 3: HEURÍSTICA GULOSA DE WELSH-POWELL

    Explicações:
    - Ordena as estações por grau decrescente (as mais conectadas, mais difíceis de
      colorir, são tratadas primeiro).
    - Para cada cor nova, percorre a lista ordenada e pinta com essa cor toda estação
      ainda sem cor que não seja vizinha de nenhuma estação já pintada com essa cor.
    - Repete até todas as estações estarem coloridas. Não há backtracking: a saída é
      sempre válida, mas não necessariamente ótima.
    - GARANTIA: usa no máximo Δ+1 cores (Δ = maior grau do grafo).
    - Complexidade de tempo: O(|V| log |V|) da ordenação + no máximo Δ+1 passadas de
      O(|V| + |E|) cada, ou seja O(|V| log |V| + (Δ+1)(|V| + |E|)); como Δ < |V|, no pior
      caso fica O(|V| * (|V| + |E|)).
    - Complexidade de memória: O(|V|) (lista ordenada, cores e conjunto da cor atual).
    - Exemplo em que NÃO acha o ótimo: grafo "coroa" (K_n,n sem o emparelhamento perfeito,
      u_i ligado a w_j sempre que i != j) na ordem u0, w0, u1, w1, ...; todos têm o mesmo
      grau, então a heurística pinta {u_i, w_i} juntos e usa n cores, enquanto χ = 2.

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.

    Retorno: ResultadoColoracao (interrompido_por_tempo é sempre False).
    """
    inicio = time.perf_counter()
    # Ordenação estável por grau decrescente: empates mantêm a ordem do dicionário
    vertices_por_grau_decrescente = sorted(adjacencia, key=lambda estacao: -len(adjacencia[estacao]))
    cor_por_estacao: dict[str, int] = {}
    tentativas_de_colorir = 0
    cor_atual = 0
    while len(cor_por_estacao) < len(vertices_por_grau_decrescente):
        # Nova cor: começa sem nenhuma estação pintada com ela
        estacoes_com_cor_atual: set[str] = set()
        for estacao in vertices_por_grau_decrescente:
            if estacao in cor_por_estacao:
                continue
            tentativas_de_colorir += 1
            # Pode receber a cor atual se nenhum vizinho já estiver com ela
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
    """
    ABORDAGEM 1: FORÇA BRUTA PURA (GENERATE-AND-TEST - SEM PODAS)

    Explicações:
    - É a referência exaustiva: não usa recursão, backtracking nem poda.
    - Testa k = 1, 2, ..., |V| cores. Para cada k, gera cegamente com itertools.product
      TODAS as k^|V| atribuições de cores às estações e testa cada uma com
      coloracao_eh_valida.
    - A primeira atribuição válida encontrada é ótima: como os k são testados em ordem
      crescente, qualquer coloração com menos cores já teria sido achada antes.
    - Complexidade de tempo: O(Σ_{k=1..χ} k^|V| * (|V| + |E|)), exponencial; no pior caso
      (χ = |V|) chega a O(|V|^|V| * (|V| + |E|)).
    - Complexidade de memória: O(|V| + |E|), pois o product gera uma atribuição por vez.
    - Se o limite de tempo estourar, devolve a coloração trivial com uma cor por estação
      (sempre válida), com interrompido_por_tempo=True.

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.
    - limite_de_tempo_segundos: limite em segundos, ou None para executar sem limite.

    Retorno: ResultadoColoracao; nos_explorados = número de atribuições testadas.
    """
    inicio = time.perf_counter()
    estacoes = list(adjacencia)
    quantidade_de_estacoes = len(estacoes)
    atribuicoes_testadas = 0
    # Testa as quantidades de cores em ordem crescente: a primeira válida é o ótimo
    for quantidade_de_cores in range(1, quantidade_de_estacoes + 1):
        # Gera todas as k^n atribuições possíveis (posição i = cor da estação i)
        for atribuicao_de_cores in product(range(quantidade_de_cores), repeat=quantidade_de_estacoes):
            # Estourou o limite: devolve a coloração trivial, que é sempre válida
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
            # Teste direto da atribuição candidata
            if coloracao_eh_valida(adjacencia, cor_por_estacao):
                return ResultadoColoracao(
                    cor_por_estacao=cor_por_estacao,
                    quantidade_de_cores=quantidade_de_cores,
                    nos_explorados=atribuicoes_testadas,
                    tempo_segundos=time.perf_counter() - inicio,
                    interrompido_por_tempo=False,
                )
    # Só chega aqui com o grafo vazio: nenhuma estação, nenhuma cor
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
    """
    ABORDAGEM 2: BRANCH-AND-BOUND COM RAMIFICAÇÃO DSATUR

    Explicações:
    - Produz o mesmo χ(G) da força bruta, explorando muito menos nós.
    - LIMITE SUPERIOR (melhor solução conhecida):
      Começa com a coloração do Welsh-Powell. Toda coloração completa melhor encontrada
      na busca passa a ser o novo limite superior.
    - LIMITE INFERIOR:
      Tamanho de uma clique encontrada de forma gulosa (os vértices de uma clique exigem
      cores distintas). Se o limite superior igualar o inferior, o ótimo está provado e a
      busca para imediatamente (às vezes sem explorar nenhum nó).
    - RAMIFICAÇÃO (estilo DSatur):
      Em cada nó, escolhe a estação sem cor com maior saturação (número de cores distintas
      nos vizinhos), desempatando pelo maior grau. Tenta primeiro as cores já usadas no
      ramo que não conflitam com os vizinhos e, por último, uma cor nova.
    - PODA (BOUND):
      Se as cores usadas no ramo já são >= melhor k encontrado, o ramo não pode melhorar
      a solução e é descartado. A cor nova só é tentada se ainda puder dar menos cores.
    - Complexidade de tempo: exponencial no pior caso, O(k^|V|) nós com O(|V| + Δ) de
      trabalho por nó (escolha da estação e atualização da saturação); na prática as podas
      e os limites cortam a maior parte da árvore.
    - Complexidade de memória: O(|V| * k + |E|) para as contagens de cores dos vizinhos,
      mais O(|V|) de pilha de recursão (profundidade = número de estações).
    - Se o limite de tempo estourar, devolve a melhor coloração conhecida (no mínimo a do
      Welsh-Powell) com interrompido_por_tempo=True.

    Parâmetros:
    - adjacencia: estação -> conjunto de estações vizinhas.
    - limite_de_tempo_segundos: limite em segundos, ou None para executar sem limite.

    Retorno: ResultadoColoracao; nos_explorados = nós da árvore de busca visitados.
    """
    inicio = time.perf_counter()
    estacoes = list(adjacencia)
    quantidade_de_estacoes = len(estacoes)
    # Limite superior inicial: solução da heurística de Welsh-Powell
    resultado_da_heuristica = colorir_por_welsh_powell(adjacencia)
    estado = {
        "melhor_coloracao": dict(resultado_da_heuristica.cor_por_estacao),
        "melhor_quantidade_de_cores": resultado_da_heuristica.quantidade_de_cores,
        "nos_explorados": 0,
        "interrompido_por_tempo": False,
        "otimo_provado": False,
    }
    # Limite inferior: tamanho da clique gulosa; se a heurística já o atinge, é ótima
    limite_inferior = tamanho_de_clique_gulosa(adjacencia)
    if estado["melhor_quantidade_de_cores"] <= limite_inferior:
        estado["otimo_provado"] = True

    cor_por_estacao: dict[str, int] = {}
    # Para cada estação: cor -> quantos vizinhos têm essa cor (saturação = nº de chaves)
    quantidade_de_vizinhos_por_cor: dict[str, dict[int, int]] = {estacao: {} for estacao in estacoes}

    def pintar_estacao(estacao: str, cor: int) -> None:
        """Atribui a cor à estação e atualiza a contagem de cores dos seus vizinhos. O(grau)."""
        cor_por_estacao[estacao] = cor
        for vizinho in adjacencia[estacao]:
            contagem_do_vizinho = quantidade_de_vizinhos_por_cor[vizinho]
            contagem_do_vizinho[cor] = contagem_do_vizinho.get(cor, 0) + 1

    def despintar_estacao(estacao: str) -> None:
        """Desfaz pintar_estacao (backtracking), removendo a cor dos contadores dos vizinhos. O(grau)."""
        cor = cor_por_estacao.pop(estacao)
        for vizinho in adjacencia[estacao]:
            contagem_do_vizinho = quantidade_de_vizinhos_por_cor[vizinho]
            contagem_do_vizinho[cor] -= 1
            # Nenhum vizinho tem mais essa cor: ela deixa de contar na saturação
            if contagem_do_vizinho[cor] == 0:
                del contagem_do_vizinho[cor]

    def escolher_estacao_com_maior_saturacao() -> str:
        """
        Regra DSatur: devolve a estação sem cor com maior saturação; empate pelo maior grau
        e, persistindo, pela ordem do dicionário. O(|V|).
        """
        return max(
            (estacao for estacao in estacoes if estacao not in cor_por_estacao),
            key=lambda estacao: (len(quantidade_de_vizinhos_por_cor[estacao]), len(adjacencia[estacao])),
        )

    def busca_deve_parar() -> bool:
        """
        Retorno: True se o ótimo já foi provado ou se o limite de tempo estourou
        (neste caso marca interrompido_por_tempo).
        """
        if estado["otimo_provado"] or estado["interrompido_por_tempo"]:
            return True
        if tempo_esgotado(inicio, limite_de_tempo_segundos):
            estado["interrompido_por_tempo"] = True
            return True
        return False

    def ramificar(cores_usadas_no_ramo: int) -> None:
        """
        Expande um nó da árvore de busca (DFS recursiva).

        Parâmetros:
        - cores_usadas_no_ramo: quantas cores distintas a coloração parcial atual usa
          (as cores do ramo são sempre 0..cores_usadas_no_ramo-1).
        """
        if busca_deve_parar():
            return
        estado["nos_explorados"] += 1
        # PODA: o ramo já usa tantas cores quanto a melhor solução, não pode melhorar
        if cores_usadas_no_ramo >= estado["melhor_quantidade_de_cores"]:
            return
        # Todas as estações coloridas: nova melhor solução (novo limite superior)
        if len(cor_por_estacao) == quantidade_de_estacoes:
            estado["melhor_coloracao"] = dict(cor_por_estacao)
            estado["melhor_quantidade_de_cores"] = cores_usadas_no_ramo
            # Atingiu o limite inferior: ótimo provado, encerra toda a busca
            if cores_usadas_no_ramo <= limite_inferior:
                estado["otimo_provado"] = True
            return
        estacao_escolhida = escolher_estacao_com_maior_saturacao()
        cores_proibidas = quantidade_de_vizinhos_por_cor[estacao_escolhida]
        # Ramos 1..k: cores já usadas no ramo que nenhum vizinho tem
        for cor_ja_usada in range(cores_usadas_no_ramo):
            if cor_ja_usada in cores_proibidas:
                continue
            pintar_estacao(estacao_escolhida, cor_ja_usada)
            ramificar(cores_usadas_no_ramo)
            # Backtracking
            despintar_estacao(estacao_escolhida)
            if busca_deve_parar():
                return
        # Último ramo: cor nova, só se ainda puder dar menos cores que a melhor solução
        if cores_usadas_no_ramo + 1 < estado["melhor_quantidade_de_cores"]:
            pintar_estacao(estacao_escolhida, cores_usadas_no_ramo)
            ramificar(cores_usadas_no_ramo + 1)
            despintar_estacao(estacao_escolhida)

    # A profundidade da recursão cresce com o nº de estações: aumenta o limite temporariamente
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
    """
    Converte o GrafoMetro na adjacência simples usada pelos algoritmos dos problemas (b) e (c):
    só importa se duas estações são vizinhas, não por quais linhas.

    Parâmetros:
    - grafo: GrafoMetro já carregado com estações e trechos.

    Retorno: dict estação -> conjunto de vizinhos, incluindo estações sem trechos.
    Descarta laços e vizinhos que não estão em grafo.estacoes (o parser pode criar
    adjacência para nomes desconhecidos, o que quebraria os algoritmos).
    Complexidade: O(|V| + |E|).
    """
    return {
        estacao: {
            vizinho
            for vizinho in grafo.adjacencias.get(estacao, {})
            if vizinho in grafo.estacoes and vizinho != estacao
        }
        for estacao in grafo.estacoes
    }


def montar_mensagem_da_coloracao(resultado: ResultadoColoracao) -> str:
    """
    Monta o texto exibido na interface para o problema (c).

    Parâmetros:
    - resultado: ResultadoColoracao devolvido por um dos três métodos.

    Retorno: texto com o nº de períodos, os nós explorados, o aviso de interrupção por
    tempo (se houver) e a lista "Período k: estação, estação, ..." agrupada por cor.
    """
    # Agrupa as estações pela cor recebida
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
    # Períodos numerados a partir de 1 (cor + 1), estações em ordem alfabética
    for cor in sorted(estacoes_por_periodo):
        linhas_da_mensagem.append(f"Período {cor + 1}: {', '.join(sorted(estacoes_por_periodo[cor]))}")
    return "\n".join(linhas_da_mensagem)


def resolver_problema_c(grafo, metodo):
    """
    PROBLEMA (C) - COLORAÇÃO DE VÉRTICES (PERÍODOS DE MANUTENÇÃO)
    Responsável: Integrante 3
    Métodos: 'forca_bruta', 'branch_and_bound', 'heuristica'
    Também aceita os textos do menu da interface: 'Força Bruta', 'Branch-and-Bound', 'Heurística'.
    Força bruta e branch-and-bound rodam com limite de LIMITE_DE_TEMPO_GUI_SEGUNDOS.
    Retorno: (cor_por_estacao, tempo_ms, mensagem_detalhada)
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
    # A interface espera o tempo em milissegundos
    tempo_ms = resultado.tempo_segundos * 1000.0
    return resultado.cor_por_estacao, tempo_ms, montar_mensagem_da_coloracao(resultado)


# ======================================================================================
# 6. PROBLEMA (B) — CONJUNTO DOMINANTE MÍNIMO / GUICHÊS (INTEGRANTE 2)
# ======================================================================================
"""
O PROBLEMA:
Escolher o menor conjunto de estações para receber guichês de modo que toda estação tenha
um guichê nela mesma ou em uma estação vizinha (no máximo uma parada de distância).
É o Conjunto Dominante Mínimo (Minimum Dominating Set), problema NP-Difícil.

REPRESENTAÇÃO:
As estações são numeradas de 0 a n-1 e um conjunto de estações é um inteiro usado como
máscara de bits (bit i ligado = estação i está no conjunto). A "cobertura" da estação i é
a máscara de i e de seus vizinhos, ou seja, as estações atendidas por um guichê em i.
Juntar coberturas vira um OR entre inteiros e contar estações vira bit_count().
"""


@dataclass
class ResultadoGuiches:
    estacoes_com_guiche: list[str]
    nos_explorados: int
    podas: int
    tempo_segundos: float
    interrompido_por_tempo: bool
    observacao: str = ""


def montar_coberturas(adjacencia: dict[str, set[str]]) -> tuple[list[str], list[int]]:
    estacoes = sorted(adjacencia)
    indice_da_estacao = {estacao: indice for indice, estacao in enumerate(estacoes)}
    coberturas = []
    for estacao in estacoes:
        mascara = 1 << indice_da_estacao[estacao]
        for vizinho in adjacencia[estacao]:
            mascara |= 1 << indice_da_estacao[vizinho]
        coberturas.append(mascara)
    return estacoes, coberturas


def indices_da_mascara(mascara: int) -> list[int]:
    indices = []
    while mascara:
        bit_mais_baixo = mascara & -mascara
        indices.append(bit_mais_baixo.bit_length() - 1)
        mascara ^= bit_mais_baixo
    return indices


def guiches_atendem_todas(adjacencia: dict[str, set[str]], estacoes_com_guiche: list[str]) -> bool:
    guiches = set(estacoes_com_guiche)
    return all(
        estacao in guiches or not guiches.isdisjoint(vizinhos)
        for estacao, vizinhos in adjacencia.items()
    )


def guiches_por_guloso(adjacencia: dict[str, set[str]]) -> ResultadoGuiches:
    """
    HEURÍSTICA GULOSA (Chvátal) + REMOÇÃO DE REDUNDANTES
    A cada passo instala o guichê na estação que atende mais estações ainda descobertas.
    No fim, retira os guichês cujas estações já são atendidas pelos demais.
    Tempo: no máximo n passos, cada um avaliando as n estações: O(n²) operações de máscara,
    polinomial no pior caso.
    Garantia: o resultado é no máximo (1 + ln(Δ + 1)) vezes o ótimo, onde Δ é o maior grau.
    """
    inicio = time.perf_counter()
    estacoes, coberturas = montar_coberturas(adjacencia)
    todas = (1 << len(estacoes)) - 1
    escolhidas: list[int] = []
    atendidas = 0
    avaliacoes = 0
    while atendidas != todas:
        descobertas = todas & ~atendidas
        melhor_estacao, maior_ganho = -1, 0
        for indice, cobertura in enumerate(coberturas):
            avaliacoes += 1
            ganho = (cobertura & descobertas).bit_count()
            if ganho > maior_ganho:
                melhor_estacao, maior_ganho = indice, ganho
        escolhidas.append(melhor_estacao)
        atendidas |= coberturas[melhor_estacao]
    # Tenta retirar primeiro os guichês que atendem menos estações
    for candidata in sorted(escolhidas, key=lambda indice: coberturas[indice].bit_count()):
        atendidas_sem_ela = 0
        for outra in escolhidas:
            if outra != candidata:
                atendidas_sem_ela |= coberturas[outra]
        if atendidas_sem_ela == todas:
            escolhidas.remove(candidata)
    return ResultadoGuiches(
        estacoes_com_guiche=[estacoes[indice] for indice in escolhidas],
        nos_explorados=avaliacoes,
        podas=0,
        tempo_segundos=time.perf_counter() - inicio,
        interrompido_por_tempo=False,
    )


def guiches_por_forca_bruta(
    adjacencia: dict[str, set[str]], limite_de_tempo_segundos: float | None = None
) -> ResultadoGuiches:
    """
    FORÇA BRUTA
    Testa todos os grupos de 1 estação, depois todos os de 2, de 3, e assim por diante.
    O primeiro grupo que atende todas as estações é, garantidamente, o menor possível.
    Tempo: soma de C(n, k) para k = 1..γ (γ = mínimo de guichês), O(2^n) no pior caso.
    """
    inicio = time.perf_counter()
    estacoes, coberturas = montar_coberturas(adjacencia)
    quantidade_de_estacoes = len(estacoes)
    todas = (1 << quantidade_de_estacoes) - 1
    grupos_testados = 0
    for tamanho in range(1, quantidade_de_estacoes + 1):
        for grupo in combinations(range(quantidade_de_estacoes), tamanho):
            grupos_testados += 1
            if grupos_testados % 4096 == 0 and tempo_esgotado(inicio, limite_de_tempo_segundos):
                return ResultadoGuiches(
                    estacoes_com_guiche=list(estacoes),
                    nos_explorados=grupos_testados,
                    podas=0,
                    tempo_segundos=time.perf_counter() - inicio,
                    interrompido_por_tempo=True,
                    observacao=(
                        f"Todos os grupos com menos de {tamanho} guichês foram testados "
                        "e nenhum atende todas as estações."
                    ),
                )
            atendidas = 0
            for indice in grupo:
                atendidas |= coberturas[indice]
            if atendidas == todas:
                return ResultadoGuiches(
                    estacoes_com_guiche=[estacoes[indice] for indice in grupo],
                    nos_explorados=grupos_testados,
                    podas=0,
                    tempo_segundos=time.perf_counter() - inicio,
                    interrompido_por_tempo=False,
                )
    return ResultadoGuiches([], grupos_testados, 0, time.perf_counter() - inicio, False)


def guiches_por_branch_and_bound(
    adjacencia: dict[str, set[str]], limite_de_tempo_segundos: float | None = None
) -> ResultadoGuiches:
    """
    BRANCH-AND-BOUND
    Monta grupos de estações como a força bruta, mas guiando a escolha e descartando ramos.
    Solução inicial: a da heurística gulosa. A busca só aceita grupos menores que ela.
    Ramificação: escolhe a estação descoberta com MENOS opções de atendimento (ela mesma
    ou um vizinho disponível). Uma delas precisa receber guichê, então cada opção é um ramo.
    Sem repetição: no i-ésimo ramo, as opções anteriores ficam proibidas, pois os grupos
    que as contêm já foram explorados nos ramos anteriores.
    Limite inferior: se faltam D estações descobertas e nenhuma estação disponível atende
    mais que G delas, ainda são necessários ao menos ceil(D / G) guichês.
    Se guichês_atuais + ceil(D / G) >= melhor_encontrado, o ramo é podado.
    Inviabilidade: se uma estação descoberta só podia ser atendida por estações proibidas,
    o ramo é podado.
    """
    inicio = time.perf_counter()
    estacoes, coberturas = montar_coberturas(adjacencia)
    todas = (1 << len(estacoes)) - 1
    indice_da_estacao = {estacao: indice for indice, estacao in enumerate(estacoes)}
    solucao_gulosa = guiches_por_guloso(adjacencia)
    estado = {
        "melhor": [indice_da_estacao[estacao] for estacao in solucao_gulosa.estacoes_com_guiche],
        "nos_explorados": 0,
        "podas": 0,
        "interrompido_por_tempo": False,
    }
    escolhidas: list[int] = []

    def ramificar(atendidas: int, proibidas: int) -> None:
        estado["nos_explorados"] += 1
        if estado["nos_explorados"] % 1024 == 0 and tempo_esgotado(inicio, limite_de_tempo_segundos):
            estado["interrompido_por_tempo"] = True
        if estado["interrompido_por_tempo"]:
            return
        if atendidas == todas:
            if len(escolhidas) < len(estado["melhor"]):
                estado["melhor"] = list(escolhidas)
            return
        descobertas = todas & ~atendidas
        disponiveis = todas & ~proibidas
        maior_ganho = max(
            ((coberturas[indice] & descobertas).bit_count() for indice in indices_da_mascara(disponiveis)),
            default=0,
        )
        if maior_ganho == 0:
            estado["podas"] += 1
            return
        guiches_que_ainda_faltam = -(-descobertas.bit_count() // maior_ganho)
        if len(escolhidas) + guiches_que_ainda_faltam >= len(estado["melhor"]):
            estado["podas"] += 1
            return
        estacao_alvo_opcoes = 0
        for indice in indices_da_mascara(descobertas):
            opcoes = coberturas[indice] & disponiveis
            if opcoes == 0:
                estado["podas"] += 1
                return
            if estacao_alvo_opcoes == 0 or opcoes.bit_count() < estacao_alvo_opcoes.bit_count():
                estacao_alvo_opcoes = opcoes
        opcoes_por_ganho = sorted(
            indices_da_mascara(estacao_alvo_opcoes),
            key=lambda indice: -(coberturas[indice] & descobertas).bit_count(),
        )
        for opcao in opcoes_por_ganho:
            escolhidas.append(opcao)
            ramificar(atendidas | coberturas[opcao], proibidas)
            escolhidas.pop()
            proibidas |= 1 << opcao
            if estado["interrompido_por_tempo"]:
                return

    ramificar(0, 0)
    return ResultadoGuiches(
        estacoes_com_guiche=[estacoes[indice] for indice in estado["melhor"]],
        nos_explorados=estado["nos_explorados"],
        podas=estado["podas"],
        tempo_segundos=time.perf_counter() - inicio,
        interrompido_por_tempo=estado["interrompido_por_tempo"],
    )


def montar_mensagem_dos_guiches(adjacencia: dict[str, set[str]], resultado: ResultadoGuiches) -> str:
    guiches = sorted(resultado.estacoes_com_guiche)
    linhas_da_mensagem = [
        f"Guichês necessários: {len(guiches)}",
        f"Nós explorados: {resultado.nos_explorados:,}",
    ]
    if resultado.podas:
        linhas_da_mensagem.append(f"Podas: {resultado.podas:,}")
    if resultado.interrompido_por_tempo:
        linhas_da_mensagem.append(
            f"AVISO: limite de {LIMITE_DE_TEMPO_GUI_SEGUNDOS:.0f} s atingido; "
            "esta é a melhor solução encontrada, sem garantia de ótimo."
        )
    if resultado.observacao:
        linhas_da_mensagem.append(resultado.observacao)
    validos = guiches_atendem_todas(adjacencia, guiches)
    linhas_da_mensagem.append(
        "Verificação: toda estação está a no máximo 1 parada de um guichê."
        if validos
        else "ERRO: há estações sem guichê a 1 parada."
    )
    linhas_da_mensagem.append("")
    linhas_da_mensagem.append("Estações com guichê:")
    linhas_da_mensagem.extend(f"  - {estacao}" for estacao in guiches)
    linhas_da_mensagem.append("")
    linhas_da_mensagem.append("Atendimento das demais estações:")
    conjunto_de_guiches = set(guiches)
    for estacao in sorted(adjacencia):
        if estacao in conjunto_de_guiches:
            continue
        atendentes = sorted(conjunto_de_guiches & adjacencia[estacao])
        linhas_da_mensagem.append(f"  {estacao} -> {', '.join(atendentes) or 'nenhum'}")
    return "\n".join(linhas_da_mensagem)


def resolver_problema_b(grafo, metodo):
    """
    PROBLEMA (B) - CONJUNTO DOMINANTE MÍNIMO (GUICHÊS DE VENDAS)
    Responsável: Integrante 2
    Métodos: 'Força Bruta', 'Branch-and-Bound', 'Heurística' (texto do menu da interface)
    Retorno: (lista_de_estacoes_com_guiche, tempo_ms, mensagem_detalhada)
    """
    adjacencia = extrair_adjacencia_simples(grafo)
    metodo_minusculo = metodo.lower()
    if "bruta" in metodo_minusculo:
        resultado = guiches_por_forca_bruta(adjacencia, limite_de_tempo_segundos=LIMITE_DE_TEMPO_GUI_SEGUNDOS)
    elif "bound" in metodo_minusculo:
        resultado = guiches_por_branch_and_bound(adjacencia, limite_de_tempo_segundos=LIMITE_DE_TEMPO_GUI_SEGUNDOS)
    elif "heur" in metodo_minusculo:
        resultado = guiches_por_guloso(adjacencia)
    else:
        return [], 0.0, f"Método desconhecido: {metodo}"
    tempo_ms = resultado.tempo_segundos * 1000.0
    return sorted(resultado.estacoes_com_guiche), tempo_ms, montar_mensagem_dos_guiches(adjacencia, resultado)


# ======================================================================================
# 6.1 BENCHMARKS E AUTOMAÇÃO DE TESTES (INTEGRANTE 3)
# ======================================================================================
"""
O BENCHMARK:
Mede tempo, memória e nós explorados dos 9 algoritmos (3 problemas x 3 métodos) em
instâncias crescentes do metrô, para os gráficos e tabelas do relatório.

COMO FUNCIONA:
1. Instâncias: grafos com as primeiras k linhas do metrô, k = 2, 4, 6, 8 e 10, lidos dos
   arquivos dados/estacoes_XX.txt e dados/linhas_XX.txt.
2. Medição: cada algoritmo roda em um processo separado (spawn) com limite de tempo
   (padrão 60 s); o processo é encerrado se estourar. São 3 repetições só de tempo
   (usa-se a mediana) e 1 rodada extra só para o pico de memória com tracemalloc,
   porque o tracemalloc distorce o tempo.
3. Conferência: força bruta x branch-and-bound devem dar o mesmo valor; as heurísticas
   precisam ser válidas e são comparadas com o ótimo.
4. Saída: resultados_benchmark.csv e graficos/tempos_problema_{a,b,c}.dat (pgfplots).

USO: python main.py --benchmark [--limite N]   ou   python main.py --graficos
"""

# Quantidades de linhas do metrô de cada instância do benchmark
QUANTIDADES_DE_LINHAS_DAS_INSTANCIAS = (2, 4, 6, 8, 10)
PASTA_DAS_INSTANCIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")


@dataclass
class InstanciaDeBenchmark:
    """
    Uma instância do benchmark.

    Campos:
    - quantidade_de_linhas: k, número de linhas do metrô usadas no grafo.
    - grafo: GrafoMetro só com as estações e trechos dessas linhas.
    - estacao_de_partida_do_problema_a: estação de partida usada no problema (a).
    - quantidade_de_estacoes: |V| da instância.
    - quantidade_de_trechos: |E| da instância (trechos distintos).
    """
    quantidade_de_linhas: int
    grafo: GrafoMetro
    estacao_de_partida_do_problema_a: str
    quantidade_de_estacoes: int
    quantidade_de_trechos: int


def gerar_instancia_com_primeiras_linhas(arquivo_de_estacoes, arquivo_de_linhas, quantidade_de_linhas) -> GrafoMetro:
    """
    Carrega os arquivos do metrô e monta um grafo só com as primeiras linhas.

    Parâmetros:
    - arquivo_de_estacoes: caminho do arquivo de estações.
    - arquivo_de_linhas: caminho do arquivo de linhas.
    - quantidade_de_linhas: quantas linhas usar, na ordem em que aparecem no arquivo.

    Retorno: GrafoMetro com as estações e os trechos dessas linhas.
    """
    grafo_completo = GrafoMetro()
    carregar_arquivo_estacoes(arquivo_de_estacoes, grafo_completo)
    carregar_arquivo_linhas(arquivo_de_linhas, grafo_completo)
    # Lista os nomes das linhas na ordem do arquivo, sem repetir
    linhas_na_ordem_do_arquivo: list[str] = []
    for _, _, nome_linha, _ in grafo_completo.trechos:
        if nome_linha not in linhas_na_ordem_do_arquivo:
            linhas_na_ordem_do_arquivo.append(nome_linha)
    linhas_escolhidas = set(linhas_na_ordem_do_arquivo[:quantidade_de_linhas])
    trechos_das_linhas_escolhidas = [
        trecho for trecho in grafo_completo.trechos if trecho[2] in linhas_escolhidas
    ]
    grafo_da_instancia = GrafoMetro()
    # Primeiro só as estações que aparecem nos trechos escolhidos, depois os trechos
    for estacao_origem, estacao_destino, _, _ in trechos_das_linhas_escolhidas:
        for estacao in (estacao_origem, estacao_destino):
            if estacao not in grafo_da_instancia.estacoes:
                coordenada_x, coordenada_y = grafo_completo.estacoes[estacao]
                grafo_da_instancia.adicionar_estacao(estacao, coordenada_x, coordenada_y)
    for estacao_origem, estacao_destino, nome_linha, cor in trechos_das_linhas_escolhidas:
        grafo_da_instancia.adicionar_trecho(estacao_origem, estacao_destino, nome_linha, cor)
    return grafo_da_instancia


def escolher_estacao_de_maior_grau(grafo: GrafoMetro) -> str:
    """
    Escolhe a estação de partida do problema (a) de forma determinística.

    Parâmetros:
    - grafo: GrafoMetro da instância.

    Retorno: estação de maior grau; empate resolvido pela ordem alfabética do nome.
    """
    return min(grafo.obter_todos_os_vertices(), key=lambda estacao: (-grafo.grau(estacao), estacao))


def contar_trechos_distintos(grafo: GrafoMetro) -> int:
    """
    Conta as arestas distintas do grafo (um mesmo par de estações em linhas diferentes
    conta uma vez só), que é o |E| visto pelos algoritmos.

    Parâmetros:
    - grafo: GrafoMetro da instância.

    Retorno: soma dos graus / 2.
    """
    return sum(grafo.grau(estacao) for estacao in grafo.obter_todos_os_vertices()) // 2


def gerar_instancias_para_benchmark() -> list[InstanciaDeBenchmark]:
    """
    Monta uma instância para cada valor de QUANTIDADES_DE_LINHAS_DAS_INSTANCIAS,
    lendo os arquivos dados/estacoes_XX.txt e dados/linhas_XX.txt (XX = k com 2 dígitos).

    Retorno: lista de InstanciaDeBenchmark em ordem crescente de k.
    """
    instancias = []
    for quantidade_de_linhas in QUANTIDADES_DE_LINHAS_DAS_INSTANCIAS:
        arquivo_de_estacoes = os.path.join(PASTA_DAS_INSTANCIAS, f"estacoes_{quantidade_de_linhas:02d}.txt")
        arquivo_de_linhas = os.path.join(PASTA_DAS_INSTANCIAS, f"linhas_{quantidade_de_linhas:02d}.txt")
        grafo = gerar_instancia_com_primeiras_linhas(arquivo_de_estacoes, arquivo_de_linhas, quantidade_de_linhas)
        instancias.append(
            InstanciaDeBenchmark(
                quantidade_de_linhas=quantidade_de_linhas,
                grafo=grafo,
                estacao_de_partida_do_problema_a=escolher_estacao_de_maior_grau(grafo),
                quantidade_de_estacoes=len(grafo.estacoes),
                quantidade_de_trechos=contar_trechos_distintos(grafo),
            )
        )
    return instancias


# Limite de tempo de cada execução no benchmark (pode ser trocado com --limite N)
LIMITE_DE_TEMPO_PADRAO_SEGUNDOS = 60.0
# Repetições só de tempo; o tempo registrado é a mediana delas
QUANTIDADE_DE_REPETICOES_DA_MEDICAO = 3
# Espera máxima para o processo filho subir e avisar que começou (não conta no limite)
LIMITE_DE_TEMPO_PARA_INICIAR_PROCESSO_SEGUNDOS = 60.0


@dataclass
class ResultadoDoAlgoritmoParaBenchmark:
    """
    Saída padronizada de um algoritmo no benchmark.

    Campos:
    - resultado: valor da solução ((a) nº de estações do ciclo, (b) nº de guichês, (c) nº de cores).
    - nos_explorados: medida de trabalho do algoritmo (nós, permutações, passos...).
    - solucao: a solução em si (ciclo, lista de guichês ou cores), usada para validar.
    """
    resultado: int
    nos_explorados: int
    solucao: object


@dataclass
class ResultadoDaMedicao:
    """
    Resultado da medição de um algoritmo em uma instância.

    Campos:
    - resultado: valor da solução, ou None se foi interrompido por tempo.
    - tempo_mediano_segundos: mediana das repetições; se interrompido, igual ao limite.
    - pico_de_memoria_kb: pico de memória do algoritmo, ou None se não foi medido.
    - nos_explorados: medida de trabalho, ou None se foi interrompido por tempo.
    - interrompido_por_tempo: True se alguma repetição estourou o limite.
    - tempos_das_repeticoes_segundos: tempos de cada repetição concluída.
    - solucao: solução devolvida pelo algoritmo (None se interrompido).
    """
    resultado: int | None
    tempo_mediano_segundos: float
    pico_de_memoria_kb: float | None
    nos_explorados: int | None
    interrompido_por_tempo: bool
    tempos_das_repeticoes_segundos: list[float]
    solucao: object = None


def contar_estacoes_do_ciclo(ciclo: list[str]) -> int:
    """
    Parâmetros:
    - ciclo: lista de estações começando e terminando na partida, ou vazia.

    Retorno: nº de estações distintas do ciclo (sem contar o retorno); 0 se vazio.
    """
    return len(ciclo) - 1 if ciclo else 0


"""
WRAPPERS DO BENCHMARK:
As 9 funções *_para_benchmark abaixo recebem só o GrafoMetro, chamam o algoritmo de cada
problema/método e devolvem um ResultadoDoAlgoritmoParaBenchmark. Ficam no nível do módulo
para poderem ser enviadas (pickle) ao processo filho criado com spawn. Os problemas (b) e (c)
são chamados sem limite interno de tempo: o limite é aplicado pelo processo separado.
"""


def maior_ciclo_por_forca_bruta_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (a), força bruta, partindo da estação de maior grau; nós = permutações avaliadas."""
    ciclo, _, permutacoes_avaliadas = forca_bruta_maior_ciclo(grafo, escolher_estacao_de_maior_grau(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(contar_estacoes_do_ciclo(ciclo), permutacoes_avaliadas, ciclo)


def maior_ciclo_por_branch_and_bound_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (a), branch-and-bound, partindo da estação de maior grau; nós = nós expandidos."""
    ciclo, _, nos_expandidos, _ = branch_and_bound_maior_ciclo(grafo, escolher_estacao_de_maior_grau(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(contar_estacoes_do_ciclo(ciclo), nos_expandidos, ciclo)


def maior_ciclo_por_heuristica_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (a), heurística gulosa, partindo da estação de maior grau; nós = passos."""
    ciclo, _, passos = heuristica_maior_ciclo(grafo, escolher_estacao_de_maior_grau(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(contar_estacoes_do_ciclo(ciclo), passos, ciclo)


def guiches_por_forca_bruta_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (b), força bruta; resultado = nº de guichês."""
    resultado = guiches_por_forca_bruta(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(len(resultado.estacoes_com_guiche), resultado.nos_explorados, resultado.estacoes_com_guiche)


def guiches_por_branch_and_bound_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (b), branch-and-bound; resultado = nº de guichês."""
    resultado = guiches_por_branch_and_bound(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(len(resultado.estacoes_com_guiche), resultado.nos_explorados, resultado.estacoes_com_guiche)


def guiches_por_heuristica_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (b), heurística gulosa; resultado = nº de guichês."""
    resultado = guiches_por_guloso(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(len(resultado.estacoes_com_guiche), resultado.nos_explorados, resultado.estacoes_com_guiche)


def coloracao_por_forca_bruta_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (c), força bruta; resultado = nº de cores; nós = atribuições testadas."""
    resultado = colorir_por_forca_bruta(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(resultado.quantidade_de_cores, resultado.nos_explorados, resultado.cor_por_estacao)


def coloracao_por_branch_and_bound_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (c), branch-and-bound; resultado = nº de cores; nós = nós da árvore."""
    resultado = colorir_por_branch_and_bound(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(resultado.quantidade_de_cores, resultado.nos_explorados, resultado.cor_por_estacao)


def coloracao_por_heuristica_para_benchmark(grafo: GrafoMetro) -> ResultadoDoAlgoritmoParaBenchmark:
    """Problema (c), Welsh-Powell; resultado = nº de cores; nós = testes de vértice."""
    resultado = colorir_por_welsh_powell(extrair_adjacencia_simples(grafo))
    return ResultadoDoAlgoritmoParaBenchmark(resultado.quantidade_de_cores, resultado.nos_explorados, resultado.cor_por_estacao)


# Tabela (problema, método, função) com os 9 algoritmos, na ordem em que o benchmark roda
ALGORITMOS_PARA_BENCHMARK = [
    ("a", "forca_bruta", maior_ciclo_por_forca_bruta_para_benchmark),
    ("a", "branch_and_bound", maior_ciclo_por_branch_and_bound_para_benchmark),
    ("a", "heuristica", maior_ciclo_por_heuristica_para_benchmark),
    ("b", "forca_bruta", guiches_por_forca_bruta_para_benchmark),
    ("b", "branch_and_bound", guiches_por_branch_and_bound_para_benchmark),
    ("b", "heuristica", guiches_por_heuristica_para_benchmark),
    ("c", "forca_bruta", coloracao_por_forca_bruta_para_benchmark),
    ("c", "branch_and_bound", coloracao_por_branch_and_bound_para_benchmark),
    ("c", "heuristica", coloracao_por_heuristica_para_benchmark),
]


def executar_algoritmo_no_processo_filho(funcao, grafo, deve_medir_memoria, fila_de_mensagens) -> None:
    """
    Código executado dentro do processo filho: roda o algoritmo uma vez e envia o
    resultado ao processo pai pela fila.

    Parâmetros:
    - funcao: um dos wrappers *_para_benchmark.
    - grafo: GrafoMetro da instância (já desserializado no filho).
    - deve_medir_memoria: se True, mede o pico de memória com tracemalloc.
    - fila_de_mensagens: fila multiprocessing para falar com o pai.

    Mensagens enviadas: ("iniciado", None), depois ("concluido", (resultado, tempo, pico_kb))
    ou ("erro", traceback).
    """
    # Avisa o pai que o processo já subiu: o limite de tempo só começa a contar daqui
    fila_de_mensagens.put(("iniciado", None))
    try:
        # tracemalloc começa depois do grafo carregado: o pico mede só o algoritmo
        if deve_medir_memoria:
            tracemalloc.start()
        inicio = time.perf_counter()
        resultado_do_algoritmo = funcao(grafo)
        tempo_segundos = time.perf_counter() - inicio
        pico_de_memoria_kb = None
        if deve_medir_memoria:
            _, pico_de_memoria_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            pico_de_memoria_kb = pico_de_memoria_bytes / 1024.0
        fila_de_mensagens.put(("concluido", (resultado_do_algoritmo, tempo_segundos, pico_de_memoria_kb)))
    except Exception:
        fila_de_mensagens.put(("erro", traceback.format_exc()))


def executar_em_processo_separado_com_timeout(funcao, grafo, deve_medir_memoria, limite_de_tempo_segundos):
    """
    Roda o algoritmo em um processo novo (spawn) e o encerra se passar do limite de tempo.
    Usar um processo separado permite interromper qualquer algoritmo, mesmo os que não
    checam o tempo internamente.

    Parâmetros:
    - funcao: um dos wrappers *_para_benchmark.
    - grafo: GrafoMetro da instância.
    - deve_medir_memoria: se True, o filho mede o pico de memória.
    - limite_de_tempo_segundos: tempo máximo após o filho avisar que iniciou.

    Retorno: tupla (ResultadoDoAlgoritmoParaBenchmark, tempo_segundos, pico_kb) ou None
    se estourou o limite. Lança RuntimeError se o algoritmo falhou no filho.
    """
    contexto = multiprocessing.get_context("spawn")
    fila_de_mensagens = contexto.Queue()
    processo = contexto.Process(
        target=executar_algoritmo_no_processo_filho,
        args=(funcao, grafo, deve_medir_memoria, fila_de_mensagens),
        daemon=True,
    )
    processo.start()
    try:
        # 1ª mensagem: "iniciado" (exclui do limite o custo de criar o processo e importar)
        fila_de_mensagens.get(timeout=LIMITE_DE_TEMPO_PARA_INICIAR_PROCESSO_SEGUNDOS)
        # 2ª mensagem: resultado ou erro, dentro do limite de tempo
        tipo_da_mensagem, conteudo = fila_de_mensagens.get(timeout=limite_de_tempo_segundos)
    except queue.Empty:
        return None
    finally:
        # Mata o filho se ele ainda estiver rodando (timeout) e libera os recursos
        if processo.is_alive():
            processo.terminate()
        processo.join()
        fila_de_mensagens.close()
    if tipo_da_mensagem == "erro":
        raise RuntimeError(f"Falha ao executar {funcao.__name__}:\n{conteudo}")
    return conteudo


def medir_execucao(funcao, grafo, limite_de_tempo_segundos=LIMITE_DE_TEMPO_PADRAO_SEGUNDOS) -> ResultadoDaMedicao:
    """
    Mede um algoritmo em uma instância: QUANTIDADE_DE_REPETICOES_DA_MEDICAO execuções só
    de tempo (fica a mediana) e uma execução extra só para o pico de memória.

    Parâmetros:
    - funcao: um dos wrappers *_para_benchmark.
    - grafo: GrafoMetro da instância.
    - limite_de_tempo_segundos: limite de cada execução.

    Retorno: ResultadoDaMedicao. Se alguma repetição estourar o limite, para na hora e
    devolve interrompido_por_tempo=True com tempo = limite (cota inferior para o gráfico).
    """
    tempos_das_repeticoes_segundos: list[float] = []
    resultado_do_algoritmo = None
    # Repetições só de tempo, sem tracemalloc (ele deixaria o algoritmo mais lento)
    for _ in range(QUANTIDADE_DE_REPETICOES_DA_MEDICAO):
        saida = executar_em_processo_separado_com_timeout(funcao, grafo, False, limite_de_tempo_segundos)
        if saida is None:
            return ResultadoDaMedicao(
                resultado=None,
                tempo_mediano_segundos=limite_de_tempo_segundos,
                pico_de_memoria_kb=None,
                nos_explorados=None,
                interrompido_por_tempo=True,
                tempos_das_repeticoes_segundos=tempos_das_repeticoes_segundos,
            )
        resultado_do_algoritmo, tempo_segundos, _ = saida
        tempos_das_repeticoes_segundos.append(tempo_segundos)
    # Rodada extra só para memória; se estourar o tempo, o pico fica sem medição (None)
    saida_com_memoria = executar_em_processo_separado_com_timeout(funcao, grafo, True, limite_de_tempo_segundos)
    pico_de_memoria_kb = saida_com_memoria[2] if saida_com_memoria is not None else None
    return ResultadoDaMedicao(
        resultado=resultado_do_algoritmo.resultado,
        tempo_mediano_segundos=statistics.median(tempos_das_repeticoes_segundos),
        pico_de_memoria_kb=pico_de_memoria_kb,
        nos_explorados=resultado_do_algoritmo.nos_explorados,
        interrompido_por_tempo=False,
        tempos_das_repeticoes_segundos=tempos_das_repeticoes_segundos,
        solucao=resultado_do_algoritmo.solucao,
    )


ARQUIVO_DE_RESULTADOS_DO_BENCHMARK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_benchmark.csv")
# Colunas do CSV, uma linha por (problema, método, instância)
COLUNAS_DO_CSV_DE_BENCHMARK = [
    "problema",
    "metodo",
    "quantidade_de_linhas",
    "quantidade_de_estacoes",
    "quantidade_de_trechos",
    "resultado",
    "tempo_mediano_segundos",
    "pico_de_memoria_kb",
    "nos_explorados",
    "interrompido_por_tempo",
]
# Problema (a) maximiza o ciclo; (b) e (c) minimizam (guichês e cores)
PROBLEMAS_DE_MAXIMIZACAO = {"a"}
# Ordem de preferência para obter o valor ótimo: força bruta, senão branch-and-bound
METODOS_EXATOS = ("forca_bruta", "branch_and_bound")


def ciclo_eh_valido(grafo: GrafoMetro, ciclo: list[str], estacao_de_partida: str) -> bool:
    """
    Valida uma solução do problema (a).

    Parâmetros:
    - grafo: GrafoMetro da instância.
    - ciclo: lista de estações começando e terminando na partida.
    - estacao_de_partida: estação em que o ciclo deve começar e terminar.

    Retorno: True se o ciclo é simples, tem ao menos 3 estações distintas e todas as
    estações consecutivas são ligadas por trechos. Ciclo vazio conta como válido
    (significa "não achou"; a diferença para o ótimo já cobre esse caso).
    """
    if not ciclo:
        return True
    # Precisa começar e terminar na estação de partida
    if ciclo[0] != estacao_de_partida or ciclo[-1] != estacao_de_partida:
        return False
    # Pelo menos 3 estações e nenhuma repetida
    estacoes_sem_o_retorno = ciclo[:-1]
    if len(estacoes_sem_o_retorno) < 3 or len(set(estacoes_sem_o_retorno)) != len(estacoes_sem_o_retorno):
        return False
    # Todo par consecutivo precisa ser um trecho do grafo
    return all(
        estacao_seguinte in grafo.adjacencias.get(estacao_atual, {})
        for estacao_atual, estacao_seguinte in zip(ciclo, ciclo[1:])
    )


def solucao_eh_valida(problema: str, instancia: InstanciaDeBenchmark, solucao) -> bool:
    """
    Valida a solução de qualquer problema, fora do tempo medido.

    Parâmetros:
    - problema: "a", "b" ou "c".
    - instancia: instância em que a solução foi obtida.
    - solucao: ciclo (a), lista de estações com guichê (b) ou cor por estação (c).

    Retorno: True se a solução respeita as regras do problema.
    """
    if problema == "a":
        return ciclo_eh_valido(instancia.grafo, solucao, instancia.estacao_de_partida_do_problema_a)
    adjacencia = extrair_adjacencia_simples(instancia.grafo)
    if problema == "b":
        return guiches_atendem_todas(adjacencia, solucao)
    return coloracao_eh_valida(adjacencia, solucao)


def formatar_valor_para_csv(valor) -> str:
    """
    Converte um valor para texto do CSV: None vira vazio e float fica com 6 casas decimais.
    """
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def montar_linha_do_csv(problema, metodo, instancia: InstanciaDeBenchmark, medicao: ResultadoDaMedicao) -> list[str]:
    """
    Parâmetros:
    - problema, metodo: identificam o algoritmo medido.
    - instancia: instância usada.
    - medicao: resultado da medição.

    Retorno: valores já formatados, na ordem de COLUNAS_DO_CSV_DE_BENCHMARK.
    """
    valores = [
        problema,
        metodo,
        instancia.quantidade_de_linhas,
        instancia.quantidade_de_estacoes,
        instancia.quantidade_de_trechos,
        medicao.resultado,
        medicao.tempo_mediano_segundos,
        medicao.pico_de_memoria_kb,
        medicao.nos_explorados,
        medicao.interrompido_por_tempo,
    ]
    return [formatar_valor_para_csv(valor) for valor in valores]


def descrever_medicao(medicao: ResultadoDaMedicao) -> str:
    """
    Retorno: resumo de uma medição em uma linha (resultado, tempo em ms, memória e nós)
    para o acompanhamento no terminal.
    """
    if medicao.interrompido_por_tempo:
        return f"interrompido por tempo (>= {medicao.tempo_mediano_segundos:.0f} s)"
    pico_de_memoria = f"{medicao.pico_de_memoria_kb:.1f} KB" if medicao.pico_de_memoria_kb is not None else "sem medição"
    return (
        f"resultado={medicao.resultado} tempo={medicao.tempo_mediano_segundos * 1000:.3f} ms "
        f"memória={pico_de_memoria} nós={medicao.nos_explorados}"
    )


def listar_problemas_do_benchmark() -> list[str]:
    """Retorno: problemas presentes em ALGORITMOS_PARA_BENCHMARK, em ordem ("a", "b", "c")."""
    return sorted({problema for problema, _, _ in ALGORITMOS_PARA_BENCHMARK})


def obter_valor_otimo(medicoes, problema, quantidade_de_linhas):
    """
    Parâmetros:
    - medicoes: dict (problema, método, k) -> ResultadoDaMedicao.
    - problema: "a", "b" ou "c".
    - quantidade_de_linhas: k da instância.

    Retorno: valor ótimo da força bruta se ela terminou, senão do branch-and-bound;
    None se os dois métodos exatos foram interrompidos.
    """
    for metodo in METODOS_EXATOS:
        medicao = medicoes.get((problema, metodo, quantidade_de_linhas))
        if medicao is not None and not medicao.interrompido_por_tempo:
            return medicao.resultado
    return None


def conferir_forca_bruta_contra_branch_and_bound(instancias, medicoes) -> list[str]:
    """
    Confere se os dois métodos exatos dão o mesmo valor em cada instância e imprime o resumo.

    Parâmetros:
    - instancias: lista de InstanciaDeBenchmark.
    - medicoes: dict (problema, método, k) -> ResultadoDaMedicao.

    Retorno: lista de textos descrevendo cada divergência (vazia se tudo bateu).
    """
    print("\n=== Conferência: força bruta x branch-and-bound ===")
    divergencias = []
    quantidade_de_conferencias = 0
    for problema in listar_problemas_do_benchmark():
        for instancia in instancias:
            k = instancia.quantidade_de_linhas
            medicao_da_forca_bruta = medicoes[(problema, "forca_bruta", k)]
            medicao_do_branch_and_bound = medicoes[(problema, "branch_and_bound", k)]
            # Só dá para comparar quando os dois terminaram dentro do limite
            if medicao_da_forca_bruta.interrompido_por_tempo or medicao_do_branch_and_bound.interrompido_por_tempo:
                continue
            quantidade_de_conferencias += 1
            if medicao_da_forca_bruta.resultado != medicao_do_branch_and_bound.resultado:
                divergencias.append(
                    f"DIVERGÊNCIA problema ({problema}) k={k}: força bruta={medicao_da_forca_bruta.resultado}, "
                    f"branch-and-bound={medicao_do_branch_and_bound.resultado}"
                )
    for divergencia in divergencias:
        print(divergencia)
    print(f"{quantidade_de_conferencias} instâncias conferidas, {len(divergencias)} divergência(s).")
    return divergencias


def conferir_heuristicas(instancias, medicoes) -> list[str]:
    """
    Valida a solução de cada heurística e compara o seu valor com o ótimo, imprimindo
    a diferença absoluta e percentual.

    Parâmetros:
    - instancias: lista de InstanciaDeBenchmark.
    - medicoes: dict (problema, método, k) -> ResultadoDaMedicao.

    Retorno: lista "problema (x) k=..." das heurísticas com solução inválida.
    """
    print("\n=== Conferência: heurísticas ===")
    heuristicas_com_solucao_invalida = []
    for problema in listar_problemas_do_benchmark():
        for instancia in instancias:
            k = instancia.quantidade_de_linhas
            medicao_da_heuristica = medicoes[(problema, "heuristica", k)]
            if medicao_da_heuristica.interrompido_por_tempo:
                print(f"problema ({problema}) k={k}: heurística interrompida por tempo")
                continue
            solucao_valida = solucao_eh_valida(problema, instancia, medicao_da_heuristica.solucao)
            if not solucao_valida:
                heuristicas_com_solucao_invalida.append(f"problema ({problema}) k={k}")
            valor_otimo = obter_valor_otimo(medicoes, problema, k)
            if valor_otimo is None:
                comparacao_com_otimo = "ótimo desconhecido (métodos exatos interrompidos)"
            else:
                # Diferença sempre >= 0: em (a) a heurística acha menos, em (b)/(c) acha mais
                diferenca_para_otimo = (
                    valor_otimo - medicao_da_heuristica.resultado
                    if problema in PROBLEMAS_DE_MAXIMIZACAO
                    else medicao_da_heuristica.resultado - valor_otimo
                )
                percentual_da_diferenca = 100.0 * diferenca_para_otimo / valor_otimo if valor_otimo else 0.0
                comparacao_com_otimo = f"ótimo={valor_otimo} diferença={diferenca_para_otimo} ({percentual_da_diferenca:.1f}%)"
            print(
                f"problema ({problema}) k={k}: heurística={medicao_da_heuristica.resultado} "
                f"{'válida' if solucao_valida else 'INVÁLIDA'} {comparacao_com_otimo}"
            )
    if heuristicas_com_solucao_invalida:
        print("Heurísticas com solução INVÁLIDA: " + ", ".join(heuristicas_com_solucao_invalida))
    return heuristicas_com_solucao_invalida


def resumir_interrupcoes_da_forca_bruta(instancias, medicoes) -> None:
    """
    Imprime, para cada problema, em quais instâncias (k) a força bruta estourou o limite.

    Parâmetros:
    - instancias: lista de InstanciaDeBenchmark.
    - medicoes: dict (problema, método, k) -> ResultadoDaMedicao.
    """
    print("\n=== Força bruta interrompida por tempo ===")
    for problema in listar_problemas_do_benchmark():
        quantidades_de_linhas_interrompidas = [
            instancia.quantidade_de_linhas
            for instancia in instancias
            if medicoes[(problema, "forca_bruta", instancia.quantidade_de_linhas)].interrompido_por_tempo
        ]
        descricao = ", ".join(f"k={k}" for k in quantidades_de_linhas_interrompidas) or "terminou em todas"
        print(f"problema ({problema}): {descricao}")


def executar_bateria_de_benchmark(limite_de_tempo_segundos=LIMITE_DE_TEMPO_PADRAO_SEGUNDOS) -> None:
    """
    Ponto de entrada do modo --benchmark: mede os 9 algoritmos em todas as instâncias,
    grava o CSV, faz as conferências e gera os arquivos .dat dos gráficos.

    Parâmetros:
    - limite_de_tempo_segundos: limite de cada execução (padrão 60 s, ou --limite N).
    """
    instancias = gerar_instancias_para_benchmark()
    medicoes = {}
    print(f"Limite de tempo por execução: {limite_de_tempo_segundos:.0f} s", flush=True)
    with open(ARQUIVO_DE_RESULTADOS_DO_BENCHMARK, "w", encoding="utf-8", newline="") as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        escritor_csv.writerow(COLUNAS_DO_CSV_DE_BENCHMARK)
        for instancia in instancias:
            for problema, metodo, funcao in ALGORITMOS_PARA_BENCHMARK:
                medicao = medir_execucao(funcao, instancia.grafo, limite_de_tempo_segundos)
                medicoes[(problema, metodo, instancia.quantidade_de_linhas)] = medicao
                escritor_csv.writerow(montar_linha_do_csv(problema, metodo, instancia, medicao))
                # Grava linha a linha: se a bateria longa cair, os dados já medidos ficam salvos
                arquivo_csv.flush()
                print(
                    f"k={instancia.quantidade_de_linhas:2d} ({problema}) {metodo:16s} {descrever_medicao(medicao)}",
                    flush=True,
                )
    print(f"\nCSV gravado em {ARQUIVO_DE_RESULTADOS_DO_BENCHMARK}")
    conferir_forca_bruta_contra_branch_and_bound(instancias, medicoes)
    conferir_heuristicas(instancias, medicoes)
    resumir_interrupcoes_da_forca_bruta(instancias, medicoes)
    gerar_arquivos_dat_para_graficos()


PASTA_DOS_ARQUIVOS_DAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficos")
# (método no CSV, sufixo da coluna no .dat): gera tempo_fb, tempo_bb, tempo_heuristica...
METODOS_NAS_COLUNAS_DO_DAT = [
    ("forca_bruta", "fb"),
    ("branch_and_bound", "bb"),
    ("heuristica", "heuristica"),
]
# Tempo de execução interrompida: o pgfplots não desenha "nan", o relatório marca "> 60 s"
VALOR_SEM_TEMPO_NO_DAT = "nan"


def ler_resultados_do_csv(arquivo_csv: str) -> dict[tuple[str, str, int], dict[str, str]]:
    """
    Parâmetros:
    - arquivo_csv: caminho do CSV gerado pelo benchmark.

    Retorno: dict (problema, método, k) -> linha do CSV (dict coluna -> texto).
    """
    with open(arquivo_csv, "r", encoding="utf-8", newline="") as arquivo:
        return {
            (linha["problema"], linha["metodo"], int(linha["quantidade_de_linhas"])): linha
            for linha in csv.DictReader(arquivo)
        }


def formatar_tempo_e_interrupcao_para_dat(linha_do_csv: dict[str, str] | None) -> tuple[str, str]:
    """
    Parâmetros:
    - linha_do_csv: linha do CSV de um algoritmo em uma instância, ou None se não existe.

    Retorno: (tempo em segundos em notação científica ou "nan", "1" se interrompido senão "0").
    """
    if linha_do_csv is None:
        return VALOR_SEM_TEMPO_NO_DAT, "0"
    if linha_do_csv["interrompido_por_tempo"] == "True":
        return VALOR_SEM_TEMPO_NO_DAT, "1"
    return f"{float(linha_do_csv['tempo_mediano_segundos']):.6e}", "0"


def gerar_arquivos_dat_para_graficos(
    arquivo_csv: str = ARQUIVO_DE_RESULTADOS_DO_BENCHMARK, pasta_de_saida: str = PASTA_DOS_ARQUIVOS_DAT
) -> list[str]:
    """
    Gera um arquivo tempos_problema_X.dat por problema, a partir do CSV, para os gráficos
    do relatório em pgfplots. Cada linha é uma instância (k) com o tempo e a flag de
    interrupção de cada método. Ponto de entrada do modo --graficos (não refaz a bateria).

    Parâmetros:
    - arquivo_csv: CSV de resultados do benchmark.
    - pasta_de_saida: pasta onde os .dat são gravados (criada se não existir).

    Retorno: caminhos dos arquivos .dat gerados.
    """
    resultados_por_chave = ler_resultados_do_csv(arquivo_csv)
    problemas = sorted({problema for problema, _, _ in resultados_por_chave})
    quantidades_de_linhas = sorted({k for _, _, k in resultados_por_chave})
    cabecalho = (
        ["linhas"]
        + [f"tempo_{sufixo}" for _, sufixo in METODOS_NAS_COLUNAS_DO_DAT]
        + [f"interrompido_{sufixo}" for _, sufixo in METODOS_NAS_COLUNAS_DO_DAT]
    )
    os.makedirs(pasta_de_saida, exist_ok=True)
    arquivos_gerados = []
    for problema in problemas:
        linhas_do_dat = [cabecalho]
        for k in quantidades_de_linhas:
            tempos_e_interrupcoes = [
                formatar_tempo_e_interrupcao_para_dat(resultados_por_chave.get((problema, metodo, k)))
                for metodo, _ in METODOS_NAS_COLUNAS_DO_DAT
            ]
            linhas_do_dat.append(
                [str(k)]
                + [tempo for tempo, _ in tempos_e_interrupcoes]
                + [interrompido for _, interrompido in tempos_e_interrupcoes]
            )
        # Alinha as colunas pela maior largura de cada uma, para o .dat ficar legível
        larguras_das_colunas = [max(len(linha[indice]) for linha in linhas_do_dat) for indice in range(len(cabecalho))]
        caminho_do_dat = os.path.join(pasta_de_saida, f"tempos_problema_{problema}.dat")
        with open(caminho_do_dat, "w", encoding="utf-8", newline="\n") as arquivo_dat:
            for linha in linhas_do_dat:
                arquivo_dat.write(
                    "  ".join(valor.ljust(largura) for valor, largura in zip(linha, larguras_das_colunas)).rstrip() + "\n"
                )
        arquivos_gerados.append(caminho_do_dat)
    print("\nArquivos .dat para pgfplots:")
    for caminho_do_dat in arquivos_gerados:
        print(f"  {caminho_do_dat}")
    return arquivos_gerados


def ler_limite_de_tempo_dos_argumentos(argumentos: list[str]) -> float:
    """
    Parâmetros:
    - argumentos: sys.argv.

    Retorno: valor N de "--limite N" se informado, senão LIMITE_DE_TEMPO_PADRAO_SEGUNDOS.
    """
    if "--limite" in argumentos:
        return float(argumentos[argumentos.index("--limite") + 1])
    return LIMITE_DE_TEMPO_PADRAO_SEGUNDOS


# ======================================================================================
# 7. INTERFACE GRÁFICA (TKINTER) - INTEGRANTE 1
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
        self.guiches_destacados = set()  # Problema (b): estações que recebem guichê

        # Controle de Zoom e Pan (Navegação dinâmica no Canvas)
        self.fator_zoom = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self._pos_mouse_anterior = (0, 0)
        self._mouse_inicio_clique = (0, 0)
        self._arrastando_mouse = False

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

        # Controles de Zoom e Centralização
        frame_zoom = ttk.Frame(frame_topo)
        frame_zoom.grid(row=1, column=5, padx=5, pady=5, sticky="e")

        ttk.Label(frame_zoom, text="Zoom:").pack(side=tk.LEFT, padx=(0, 2))
        btn_zoom_out = ttk.Button(frame_zoom, text="➖", width=3, command=self._acao_zoom_out)
        btn_zoom_out.pack(side=tk.LEFT, padx=1)

        self.lbl_zoom = ttk.Label(frame_zoom, text="100%", width=5, anchor="center")
        self.lbl_zoom.pack(side=tk.LEFT, padx=1)

        btn_zoom_in = ttk.Button(frame_zoom, text="➕", width=3, command=self._acao_zoom_in)
        btn_zoom_in.pack(side=tk.LEFT, padx=1)

        btn_reset_zoom = ttk.Button(frame_zoom, text="↺ Ajustar", command=self._acao_reset_zoom)
        btn_reset_zoom.pack(side=tk.LEFT, padx=(3, 0))

        # -------------------------------------------------------------
        # ÁREA PRINCIPAL: MAPA (CANVAS) + PAINEL LATERAL DE RESULTADOS
        # -------------------------------------------------------------
        frame_corpo = ttk.Frame(self)
        frame_corpo.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Canvas para desenho do mapa do Metrô
        self.canvas = tk.Canvas(frame_corpo, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda event: self.redesenhar_mapa())

        # Interações de Navegação no Canvas (Zoom e Pan)
        self.canvas.bind("<ButtonPress-1>", self._ao_pressionar_mouse)
        self.canvas.bind("<B1-Motion>", self._ao_arrastar_mouse)
        self.canvas.bind("<ButtonRelease-1>", self._ao_soltar_mouse)

        # Botão direito ou do meio para arrastar o mapa livremente
        self.canvas.bind("<ButtonPress-2>", self._ao_pressionar_mouse)
        self.canvas.bind("<B2-Motion>", self._ao_arrastar_mouse)
        self.canvas.bind("<ButtonPress-3>", self._ao_pressionar_mouse)
        self.canvas.bind("<B3-Motion>", self._ao_arrastar_mouse)

        # Zoom pelo scroll do mouse
        self.canvas.bind("<MouseWheel>", self._ao_scroll_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_no_ponto(1.2, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_no_ponto(0.8, e.x, e.y))

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
            self,
            text="Dicas: Scroll do mouse para Zoom | Arraste (ou botão direito) para Mover | Clique na estação para selecionar",
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
            avisos = []
            total = carregar_arquivo_estacoes(caminho, self.grafo, avisos)
            self._descartar_resultados()
            self._atualizar_dropdown_estacoes()
            self.fator_zoom = 1.0
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0
            self._atualizar_rotulo_zoom()
            self.redesenhar_mapa()
            self.lbl_status.config(text=f"{total} estações carregadas. Agora carregue o arquivo de linhas.")
            self._mostrar_resultado_da_leitura(f"{total} estações carregadas!", avisos)
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
            avisos = []
            total = carregar_arquivo_linhas(caminho, self.grafo, avisos)
            self._descartar_resultados()
            self.fator_zoom = 1.0
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0
            self._atualizar_rotulo_zoom()
            self.redesenhar_mapa()
            self.lbl_status.config(text=f"{total} trechos de linha carregados.")
            self._mostrar_resultado_da_leitura(f"{total} trechos carregados com sucesso!", avisos)
        except Exception as e:
            messagebox.showerror("Erro ao Carregar", f"Falha ao ler arquivo de linhas:\n{e}")

    def _mostrar_resultado_da_leitura(self, mensagem_sucesso, avisos):
        """Mostra o resumo da leitura; se houver avisos, lista os primeiros para o usuário corrigir o arquivo."""
        if not avisos:
            messagebox.showinfo("Sucesso", mensagem_sucesso)
            return
        limite = 15
        lista = "\n".join(avisos[:limite])
        if len(avisos) > limite:
            lista += f"\n... e mais {len(avisos) - limite} aviso(s)."
        messagebox.showwarning(
            "Leitura com avisos",
            f"{mensagem_sucesso}\n\n{len(avisos)} aviso(s):\n{lista}",
        )

    def _descartar_resultados(self):
        """Apaga os resultados calculados, que deixam de valer quando o grafo muda."""
        self.ciclo_destacado = []
        self.coloracao_destacada = {}
        self.guiches_destacados = set()

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
    # CONTROLES DE ZOOM, PAN E NAVEGAÇÃO NO CANVAS
    # =================================================================
    def _obter_parametros_escala(self):
        """Calcula escala e ponto central considerando tamanho do Canvas, zoom e pan."""
        estacoes = self.grafo.estacoes
        if not estacoes:
            return None

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
        escala_base = min(escala_x, escala_y)
        escala = escala_base * self.fator_zoom

        centro_x = (min_x + max_x) / 2.0
        centro_y = (min_y + max_y) / 2.0
        centro_cx = (largura_canvas / 2.0) + self.pan_offset_x
        centro_cy = (altura_canvas / 2.0) + self.pan_offset_y

        return centro_cx, centro_cy, centro_x, centro_y, escala, escala_base, largura_canvas, altura_canvas

    def _atualizar_rotulo_zoom(self):
        """Atualiza o texto com a porcentagem de zoom na barra superior."""
        if hasattr(self, "lbl_zoom"):
            self.lbl_zoom.config(text=f"{int(round(self.fator_zoom * 100))}%")

    def _zoom_no_ponto(self, fator, foco_x=None, foco_y=None):
        """Aplica zoom proporcional ancorado no ponto do cursor ou no centro da tela."""
        novo_zoom = max(0.2, min(self.fator_zoom * fator, 25.0))
        if abs(novo_zoom - self.fator_zoom) < 1e-4:
            return

        largura_canvas = max(self.canvas.winfo_width(), 400)
        altura_canvas = max(self.canvas.winfo_height(), 400)

        if foco_x is None:
            foco_x = largura_canvas / 2.0
        if foco_y is None:
            foco_y = altura_canvas / 2.0

        razao = novo_zoom / self.fator_zoom
        cx = largura_canvas / 2.0 + self.pan_offset_x
        cy = altura_canvas / 2.0 + self.pan_offset_y

        self.pan_offset_x = foco_x - (foco_x - cx) * razao - (largura_canvas / 2.0)
        self.pan_offset_y = foco_y - (foco_y - cy) * razao - (altura_canvas / 2.0)
        self.fator_zoom = novo_zoom
        self._atualizar_rotulo_zoom()
        self.redesenhar_mapa()

    def _acao_zoom_in(self):
        """Aumenta o zoom em 25%."""
        self._zoom_no_ponto(1.25)

    def _acao_zoom_out(self):
        """Diminui o zoom em 20%."""
        self._zoom_no_ponto(0.8)

    def _acao_reset_zoom(self):
        """Redefine o zoom para 100% e centraliza o mapa do metrô."""
        self.fator_zoom = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self._atualizar_rotulo_zoom()
        self.redesenhar_mapa()

    def _ao_scroll_zoom(self, event):
        """Zoom interativo pela roda de rolagem do mouse (Mouse Wheel)."""
        if event.delta > 0:
            self._zoom_no_ponto(1.15, event.x, event.y)
        elif event.delta < 0:
            self._zoom_no_ponto(1.0 / 1.15, event.x, event.y)

    def _ao_pressionar_mouse(self, event):
        """Guarda o ponto de início de clique/arraste."""
        self._pos_mouse_anterior = (event.x, event.y)
        self._mouse_inicio_clique = (event.x, event.y)
        self._arrastando_mouse = False

    def _ao_arrastar_mouse(self, event):
        """Desloca (pan) a câmera pelo Canvas ao arrastar o mouse."""
        dx = event.x - self._pos_mouse_anterior[0]
        dy = event.y - self._pos_mouse_anterior[1]
        self._pos_mouse_anterior = (event.x, event.y)

        dist = math.hypot(event.x - self._mouse_inicio_clique[0], event.y - self._mouse_inicio_clique[1])
        if dist > 4:
            self._arrastando_mouse = True

        self.pan_offset_x += dx
        self.pan_offset_y += dy
        self.redesenhar_mapa()

    def _ao_soltar_mouse(self, event):
        """Ao soltar o mouse: se foi apenas um clique rápido, seleciona a estação."""
        if not self._arrastando_mouse:
            self._selecionar_estacao_por_clique(event.x, event.y)
        self._arrastando_mouse = False

    def _selecionar_estacao_por_clique(self, clique_x, clique_y):
        """Encontra a estação mais próxima dentro do raio de tolerância do clique."""
        params = self._obter_parametros_escala()
        if not params:
            return
        centro_cx, centro_cy, centro_x, centro_y, escala, _, _, _ = params

        estacao_mais_proxima = None
        menor_distancia = max(15.0, 18.0 * (self.fator_zoom ** 0.35))

        for nome, (x, y) in self.grafo.estacoes.items():
            cx = centro_cx + (x - centro_x) * escala
            cy = centro_cy + (y - centro_y) * escala
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
    # RENDERIZAÇÃO GRÁFICA NO CANVAS (AUTO-ESCALA E DESTAQUES)
    # =================================================================
    def redesenhar_mapa(self):
        """
        Desenha todo o sistema de metrô no Canvas com cálculo dinâmico de escala,
        zoom e translação (pan).
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

        params = self._obter_parametros_escala()
        if not params:
            return
        centro_cx, centro_cy, centro_x, centro_y, escala, escala_base, largura_canvas, altura_canvas = params

        def para_canvas(x, y):
            cx = centro_cx + (x - centro_x) * escala
            cy = centro_cy + (y - centro_y) * escala
            return cx, cy

        # Espessura das arestas e dimensões dos nós adaptativas ao nível de zoom
        largura_trilho = max(2, min(int(3 * (self.fator_zoom ** 0.3)), 8))
        largura_ciclo = max(4, min(int(7 * (self.fator_zoom ** 0.3)), 16))
        raio = max(5, min(int(7 * (self.fator_zoom ** 0.35)), 15))
        tam_fonte = max(8, min(int(9 * (self.fator_zoom ** 0.25)), 13))
        fonte_rotulo = ("Segoe UI", tam_fonte, "bold")

        # 2. Desenha todos os trechos normais (arestas)
        for u, v, linha, cor_nome in self.grafo.trechos:
            if u in estacoes and v in estacoes:
                x1, y1 = para_canvas(*estacoes[u])
                x2, y2 = para_canvas(*estacoes[v])
                cor_hex = obter_cor_hex(cor_nome)
                self.canvas.create_line(x1, y1, x2, y2, fill=cor_hex, width=largura_trilho, capstyle=tk.ROUND)

        # 3. Desenha o destaque do ciclo (se houver um ciclo calculado)
        if self.ciclo_destacado and len(self.ciclo_destacado) > 1:
            for i in range(len(self.ciclo_destacado) - 1):
                u = self.ciclo_destacado[i]
                v = self.ciclo_destacado[i + 1]
                if u in estacoes and v in estacoes:
                    x1, y1 = para_canvas(*estacoes[u])
                    x2, y2 = para_canvas(*estacoes[v])
                    # Linha externa dourada espessa
                    self.canvas.create_line(x1, y1, x2, y2, fill="#FFD700", width=largura_ciclo, capstyle=tk.ROUND)
                    # Linha interna de contraste
                    self.canvas.create_line(x1, y1, x2, y2, fill="#FFFFFF", width=max(1, largura_ciclo // 3), capstyle=tk.ROUND)

        # 4. Desenha as estações (vértices)
        for nome, (x, y) in estacoes.items():
            cx, cy = para_canvas(x, y)

            # Define cor e raio do vértice de acordo com o estado atual da interface:
            # - Problema (a) ativo: estação de partida fica ciano, estações do ciclo ficam douradas.
            # - Problema (c) ativo: cada estação recebe a cor do período de manutenção calculado.
            # - Problema (b) ativo: estações com guichê ficam verdes com anel externo.
            # - Estado padrão (sem resultado): círculo branco.
            if self.coloracao_destacada:
                # Problema (c): pinta o círculo com a cor do período de manutenção
                id_periodo = self.coloracao_destacada.get(nome, -1)
                if id_periodo >= 0:
                    idx_paleta = id_periodo % len(self.paleta_periodos)
                    cor_fundo = self.paleta_periodos[idx_paleta]
                    borda = "#FFFFFF"
                else:
                    cor_fundo = "#888888"
                    borda = "#FFFFFF"
                r = raio + 2

            elif self.guiches_destacados:
                # Problema (b): estações com guichê ficam verdes, com um anel em volta
                if nome in self.guiches_destacados:
                    cor_fundo = "#2ECC71"
                    borda = "#FFFFFF"
                    r = raio + 3
                    self.canvas.create_oval(
                        cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5,
                        outline="#2ECC71", width=2
                    )
                else:
                    cor_fundo = "#FFFFFF"
                    borda = "#333333"
                    r = raio

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
                anchor=tk.W, font=fonte_rotulo, tags=("texto_vertice",)
            )

        # 5. Desenha a numeração de visita no ciclo (Problema a)
        if self.ciclo_destacado and len(self.ciclo_destacado) > 1:
            for idx, nome in enumerate(self.ciclo_destacado[:-1], start=1):
                if nome in estacoes:
                    cx, cy = para_canvas(*estacoes[nome])
                    self.canvas.create_text(
                        cx, cy - r - 7, text=f"#{idx}", fill="#FFD700",
                        font=("Segoe UI", max(8, min(int(9 * (self.fator_zoom ** 0.25)), 13)), "bold")
                    )

        # 6. Desenha a legenda de períodos de manutenção (Problema c)
        if self.coloracao_destacada:
            ids_unicos = sorted(set(self.coloracao_destacada.values()))
            x_leg = 15
            y_leg = altura_canvas - 20 - len(ids_unicos) * 22
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

        # 7. Desenha a legenda dos guichês (Problema b)
        if self.guiches_destacados:
            x_leg = 15
            y_leg = altura_canvas - 60
            self.canvas.create_rectangle(
                x_leg - 5, y_leg - 8, x_leg + 215, y_leg + 48,
                fill="#222222", outline="#555555"
            )
            self.canvas.create_oval(
                x_leg + 2, y_leg + 2, x_leg + 16, y_leg + 16,
                fill="#2ECC71", outline="#FFFFFF", width=2
            )
            self.canvas.create_text(
                x_leg + 24, y_leg + 9, anchor=tk.W, fill="#FFFFFF", font=("Segoe UI", 9),
                text=f"Estação com guichê ({len(self.guiches_destacados)})"
            )
            self.canvas.create_oval(
                x_leg + 4, y_leg + 25, x_leg + 14, y_leg + 35,
                fill="#FFFFFF", outline="#333333", width=2
            )
            self.canvas.create_text(
                x_leg + 24, y_leg + 30, anchor=tk.W, fill="#FFFFFF", font=("Segoe UI", 9),
                text="Atendida por guichê vizinho"
            )

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

            # Atualiza os dados na tela (os destaques dos problemas b e c deixam de ser exibidos)
            self.coloracao_destacada = {}
            self.guiches_destacados = set()
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
            self.lbl_status.config(text=f"Executando {metodo} para o Problema (b)... Aguarde.")
            self.update_idletasks()
            res, tempo_ms, msg = resolver_problema_b(self.grafo, metodo)
            self.guiches_destacados = set(res)
            self.ciclo_destacado = []
            self.coloracao_destacada = {}
            self.lbl_tempo.config(text=f"Tempo: {tempo_ms:.3f} ms")
            if res:
                self.lbl_metrica.config(text=f"Guichês necessários: {len(res)}")
                self.lbl_status.config(text=f"{len(res)} guichês atendem todas as estações.")
            else:
                self.lbl_metrica.config(text="Guichês: nenhuma solução")
                self.lbl_status.config(text="Não foi possível calcular os guichês.")
            self.lbl_detalhes_busca.config(text="Veja painel lateral para detalhes.")
            self.txt_resultado.delete("1.0", tk.END)
            self.txt_resultado.insert(tk.END, msg)
            self.redesenhar_mapa()

        # -------------------------------------------------------------
        # CASO 3: PROBLEMA (C) - COLORAÇÃO DE VÉRTICES (INTEGRANTE 3)
        # -------------------------------------------------------------
        elif "Problema (c)" in problema:
            self.lbl_status.config(text="Executando Problema (c)... Aguarde.")
            self.update_idletasks()

            res, tempo_ms, msg = resolver_problema_c(self.grafo, metodo)

            # Guarda o dicionário { estacao: id_periodo } para o redesenho colorido do mapa
            self.coloracao_destacada = res if res else {}
            # Garante que os destaques dos Problemas (a) e (b) sejam apagados ao exibir o Problema (c)
            self.ciclo_destacado = []
            self.guiches_destacados = set()

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
        self.guiches_destacados = set()  # Limpa os guichês do Problema (b)
        self.lbl_tempo.config(text="Tempo: -- ms")
        self.lbl_metrica.config(text="Métrica: --")
        self.lbl_detalhes_busca.config(text="Nós / Podas: --")
        self.txt_resultado.delete("1.0", tk.END)
        self.lbl_status.config(text="Destaques limpos.")
        self.redesenhar_mapa()


# ======================================================================================
# 8. PONTO DE ENTRADA DA APLICAÇÃO
# ======================================================================================
if __name__ == "__main__":
    # Modo benchmark: python main.py --benchmark [--limite N]
    if "--benchmark" in sys.argv:
        executar_bateria_de_benchmark(ler_limite_de_tempo_dos_argumentos(sys.argv))
    # Só regenera os .dat a partir do CSV existente: python main.py --graficos
    elif "--graficos" in sys.argv:
        gerar_arquivos_dat_para_graficos()
    else:
        app = InterfaceMetro()
        app.mainloop()
