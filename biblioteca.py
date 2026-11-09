"""Regras do LivroLivre e acesso ao banco SQLite."""
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date
from pathlib import Path


class ErroBiblioteca(ValueError):
    """Dados inválidos ou operação indisponível."""


ESQUEMA = """
CREATE TABLE IF NOT EXISTS obras (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    autor TEXT NOT NULL,
    genero TEXT NOT NULL,
    ano INTEGER CHECK (ano BETWEEN 1 AND 9999)
);

CREATE TABLE IF NOT EXISTS exemplares (
    id INTEGER PRIMARY KEY,
    obra_id INTEGER NOT NULL REFERENCES obras(id)
);

CREATE TABLE IF NOT EXISTS leitores (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    contato TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emprestimos (
    id INTEGER PRIMARY KEY,
    exemplar_id INTEGER NOT NULL REFERENCES exemplares(id),
    leitor_id INTEGER NOT NULL REFERENCES leitores(id),
    retirada TEXT NOT NULL,
    prazo TEXT NOT NULL CHECK (prazo >= retirada),
    devolucao TEXT CHECK (devolucao >= retirada)
);

CREATE UNIQUE INDEX IF NOT EXISTS um_emprestimo_por_exemplar
ON emprestimos (exemplar_id) WHERE devolucao IS NULL;
"""

CONSULTA_EMPRESTIMOS = """
SELECT e.id, x.id AS exemplar, o.titulo, l.nome AS leitor,
       e.retirada, e.prazo, e.devolucao,
       CASE WHEN e.devolucao IS NOT NULL THEN 'Devolvido'
            WHEN e.prazo < ? THEN 'Em atraso'
            ELSE 'Em aberto'
       END AS situacao
FROM emprestimos e
JOIN exemplares x ON x.id = e.exemplar_id
JOIN obras o ON o.id = x.obra_id
JOIN leitores l ON l.id = e.leitor_id
"""


def texto_obrigatorio(valor, rotulo):
    valor = valor.strip()
    if not valor:
        raise ErroBiblioteca(f"Preencha o campo {rotulo}.")
    return valor


def inteiro_no_intervalo(texto, rotulo, minimo, maximo):
    try:
        valor = int(texto)
    except (ValueError, TypeError):
        valor = 0
    if not minimo <= valor <= maximo:
        raise ErroBiblioteca(f"{rotulo} deve ser um inteiro entre {minimo} e {maximo}.")
    return valor


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(letra for letra in texto if not unicodedata.combining(letra))


class Biblioteca:
    def __init__(self, caminho, hoje=date.today):
        self.caminho = Path(caminho)
        self.hoje = hoje
        with self.conectar() as banco:
            banco.executescript(ESQUEMA)

    @contextmanager
    def conectar(self):
        banco = sqlite3.connect(self.caminho, timeout=5)
        banco.row_factory = sqlite3.Row
        banco.execute("PRAGMA foreign_keys = ON")
        try:
            with banco:
                yield banco
        finally:
            banco.close()

    def cadastrar_obra(self, titulo, autor, genero, ano, quantidade):
        titulo = texto_obrigatorio(titulo, "Título")
        autor = texto_obrigatorio(autor, "Autor")
        genero = texto_obrigatorio(genero, "Gênero")
        ano = inteiro_no_intervalo(ano, "Ano", 1, 9999) if ano.strip() else None
        quantidade = inteiro_no_intervalo(quantidade, "Quantidade", 1, 1000)

        # O título e suas cópias fazem parte da mesma transação.
        with self.conectar() as banco:
            cursor = banco.execute(
                "INSERT INTO obras (titulo, autor, genero, ano) VALUES (?, ?, ?, ?)",
                (titulo, autor, genero, ano),
            )
            obra_id = cursor.lastrowid
            banco.executemany(
                "INSERT INTO exemplares (obra_id) VALUES (?)",
                ((obra_id,) for _ in range(quantidade)),
            )
        return obra_id

    def catalogo(self, busca=""):
        with self.conectar() as banco:
            obras = banco.execute("""
                SELECT o.id, o.titulo, o.autor, o.genero, o.ano,
                       COUNT(x.id) AS total,
                       COUNT(x.id) - COUNT(e.id) AS disponiveis
                FROM obras o
                JOIN exemplares x ON x.obra_id = o.id
                LEFT JOIN emprestimos e
                    ON e.exemplar_id = x.id AND e.devolucao IS NULL
                GROUP BY o.id
                ORDER BY o.titulo COLLATE NOCASE, o.id
            """).fetchall()
        busca = normalizar(busca.strip())
        return [
            obra for obra in obras
            if any(busca in normalizar(obra[campo]) for campo in ("titulo", "autor", "genero"))
        ]

    def exemplares(self, obra_id):
        with self.conectar() as banco:
            return banco.execute("""
                SELECT x.id, CASE WHEN e.id IS NULL THEN 1 ELSE 0 END AS disponivel
                FROM exemplares x
                LEFT JOIN emprestimos e
                    ON e.exemplar_id = x.id AND e.devolucao IS NULL
                WHERE x.obra_id = ?
                ORDER BY x.id
            """, (obra_id,)).fetchall()

    def cadastrar_leitor(self, nome, contato):
        nome = texto_obrigatorio(nome, "Nome")
        contato = texto_obrigatorio(contato, "Contato")
        with self.conectar() as banco:
            return banco.execute(
                "INSERT INTO leitores (nome, contato) VALUES (?, ?)",
                (nome, contato),
            ).lastrowid

    def leitores(self):
        with self.conectar() as banco:
            return banco.execute(
                "SELECT id, nome, contato FROM leitores ORDER BY nome COLLATE NOCASE, id"
            ).fetchall()

    def emprestar(self, exemplar_id, leitor_id, prazo):
        hoje = self.hoje()
        if prazo < hoje:
            raise ErroBiblioteca("O prazo de devolução não pode ser anterior à retirada.")

        with self.conectar() as banco:
            # A disponibilidade é verificada com o banco reservado para escrita.
            banco.execute("BEGIN IMMEDIATE")
            if banco.execute("SELECT 1 FROM leitores WHERE id = ?", (leitor_id,)).fetchone() is None:
                raise ErroBiblioteca("Selecione um leitor cadastrado.")
            if banco.execute("SELECT 1 FROM exemplares WHERE id = ?", (exemplar_id,)).fetchone() is None:
                raise ErroBiblioteca("Selecione um exemplar cadastrado.")
            if banco.execute(
                "SELECT 1 FROM emprestimos WHERE exemplar_id = ? AND devolucao IS NULL",
                (exemplar_id,),
            ).fetchone():
                raise ErroBiblioteca("Este exemplar já está emprestado. Escolha outro.")

            return banco.execute(
                """INSERT INTO emprestimos (exemplar_id, leitor_id, retirada, prazo)
                   VALUES (?, ?, ?, ?)""",
                (exemplar_id, leitor_id, hoje.isoformat(), prazo.isoformat()),
            ).lastrowid

    def devolver(self, emprestimo_id):
        with self.conectar() as banco:
            cursor = banco.execute("""
                UPDATE emprestimos SET devolucao = ?
                WHERE id = ? AND devolucao IS NULL
            """, (self.hoje().isoformat(), emprestimo_id))
            if cursor.rowcount == 0:
                raise ErroBiblioteca("O empréstimo selecionado já foi encerrado ou não existe.")

    def historico(self):
        with self.conectar() as banco:
            return banco.execute(
                CONSULTA_EMPRESTIMOS + " ORDER BY e.id DESC",
                (self.hoje().isoformat(),),
            ).fetchall()
