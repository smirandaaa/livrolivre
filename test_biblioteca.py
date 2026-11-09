import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier

from biblioteca import Biblioteca, ErroBiblioteca


class TesteBiblioteca(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.caminho = Path(pasta.name) / "teste.db"
        self.data = date(2026, 11, 9)
        self.biblioteca = Biblioteca(self.caminho, hoje=lambda: self.data)

    def cadastrar_livro(self, quantidade="2"):
        obra = self.biblioteca.cadastrar_obra("A Máquina do Tempo", "H. G. Wells", "Ficção", "1895", quantidade)
        return [linha["id"] for linha in self.biblioteca.exemplares(obra)]

    def preparar_emprestimo(self):
        exemplares = self.cadastrar_livro()
        leitor = self.biblioteca.cadastrar_leitor("Leitor de teste", "leitor@example.com")
        return exemplares, leitor

    def test_t01_cadastro_de_obra_cria_duas_copias_distintas(self):
        a, b = self.cadastrar_livro()
        obra = self.biblioteca.catalogo()[0]
        self.assertNotEqual(a, b)
        self.assertEqual((obra["total"], obra["disponiveis"]), (2, 2))

    def test_t02_campos_invalidos_nao_gravam_registros(self):
        for titulo, ano, quantidade in [
            ("   ", "1895", "2"), ("Livro", "zero", "2"),
            ("Livro", "1895", "0"), ("Livro", "1895", "1.5"),
        ]:
            with self.subTest(titulo=titulo, ano=ano, quantidade=quantidade):
                with self.assertRaises(ErroBiblioteca):
                    self.biblioteca.cadastrar_obra(titulo, "Autor", "Gênero", ano, quantidade)
        with self.assertRaises(ErroBiblioteca):
            self.biblioteca.cadastrar_leitor("Nome", " ")
        self.assertEqual((self.biblioteca.catalogo(), self.biblioteca.leitores()), ([], []))

    def test_t03_busca_titulo_autor_genero_sem_acentos(self):
        self.cadastrar_livro()
        for consulta in ("maquina", "WELLS", "ficcao"):
            with self.subTest(consulta=consulta):
                self.assertEqual(len(self.biblioteca.catalogo(consulta)), 1)
        self.assertEqual(self.biblioteca.catalogo("inexistente"), [])

    def test_t04_emprestimo_afeta_so_o_exemplar_escolhido(self):
        (a, b), leitor = self.preparar_emprestimo()
        self.biblioteca.emprestar(a, leitor, self.data)
        obra = self.biblioteca.catalogo()[0]
        self.assertEqual(obra["disponiveis"], 1)
        self.assertEqual(
            [(x["id"], x["disponivel"]) for x in self.biblioteca.exemplares(obra["id"])],
            [(a, 0), (b, 1)],
        )

    def test_t05_exemplar_emprestado_bloqueia_duplicidade(self):
        (a, _), leitor = self.preparar_emprestimo()
        self.biblioteca.emprestar(a, leitor, self.data)
        with self.assertRaisesRegex(ErroBiblioteca, "já está emprestado"):
            self.biblioteca.emprestar(a, leitor, self.data)
        self.assertEqual(len(self.biblioteca.historico()), 1)

    def test_t06_devolucao_reabre_disponibilidade_e_preserva_historico(self):
        (a, _), leitor = self.preparar_emprestimo()
        emprestimo = self.biblioteca.emprestar(a, leitor, self.data)
        self.biblioteca.devolver(emprestimo)
        self.assertEqual(self.biblioteca.catalogo()[0]["disponiveis"], 2)
        self.assertEqual(self.biblioteca.historico()[0]["situacao"], "Devolvido")
        with self.assertRaisesRegex(ErroBiblioteca, "já foi encerrado"):
            self.biblioteca.devolver(emprestimo)
        self.assertNotEqual(self.biblioteca.emprestar(a, leitor, self.data), emprestimo)

    def test_t07_atraso_comeca_no_dia_seguinte_ao_prazo(self):
        (a, _), leitor = self.preparar_emprestimo()
        self.biblioteca.emprestar(a, leitor, date(2026, 11, 10))
        self.data = date(2026, 11, 10)
        self.assertEqual(self.biblioteca.historico()[0]["situacao"], "Em aberto")
        self.data = date(2026, 11, 11)
        self.assertEqual(self.biblioteca.historico()[0]["situacao"], "Em atraso")

    def test_t08_prazo_anterior_e_ids_invalidos_sao_recusados(self):
        (a, _), leitor = self.preparar_emprestimo()
        for exemplar, pessoa, prazo in [(a, leitor, date(2026, 11, 8)), (a, 999, self.data), (999, leitor, self.data)]:
            with self.subTest(exemplar=exemplar, pessoa=pessoa, prazo=prazo):
                with self.assertRaises(ErroBiblioteca):
                    self.biblioteca.emprestar(exemplar, pessoa, prazo)
        self.assertEqual(self.biblioteca.historico(), [])

    def test_t09_banco_persiste_ao_reabrir(self):
        (a, _), leitor = self.preparar_emprestimo()
        emprestimo = self.biblioteca.emprestar(a, leitor, self.data)
        reaberta = Biblioteca(self.caminho, hoje=lambda: self.data)
        self.assertEqual(reaberta.catalogo()[0]["disponiveis"], 1)
        self.assertEqual(reaberta.leitores()[0]["id"], leitor)
        self.assertEqual(reaberta.historico()[0]["id"], emprestimo)

    def test_t10_duas_operacoes_concorrentes_tem_um_unico_emprestimo(self):
        (a, _), leitor = self.preparar_emprestimo()
        barreira = Barrier(2)

        def tentar():
            barreira.wait(timeout=5)
            try:
                self.biblioteca.emprestar(a, leitor, self.data)
            except ErroBiblioteca:
                return "recusado"
            return "gravado"

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(executor.map(lambda _: tentar(), range(2)), ["gravado", "recusado"])
        self.assertEqual(len(self.biblioteca.historico()), 1)

    def test_t11_banco_impoe_a_regra_mesmo_fora_da_interface(self):
        (a, _), leitor = self.preparar_emprestimo()
        self.biblioteca.emprestar(a, leitor, self.data)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.biblioteca.conectar() as banco:
                banco.execute(
                    "INSERT INTO emprestimos (exemplar_id, leitor_id, retirada, prazo) VALUES (?, ?, ?, ?)",
                    (a, leitor, "2026-11-09", "2026-11-09"),
                )


if __name__ == "__main__":
    unittest.main()
