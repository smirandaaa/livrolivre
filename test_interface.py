import tempfile
import tkinter as tk
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from biblioteca import Biblioteca
from main import LivroLivre


class TesteInterface(unittest.TestCase):
    def test_t12_fluxo_completo_na_janela(self):
        with tempfile.TemporaryDirectory() as pasta:
            banco = Path(pasta) / "gui.db"
            hoje = lambda: date(2026, 11, 9)
            janela = tk.Tk()
            try:
                app = LivroLivre(janela, Biblioteca(banco, hoje=hoje))
                janela.update()
                dados = ("A Máquina do Tempo", "H. G. Wells", "Ficção", "1895", "2")
                for campo, valor in zip(app.campos_obra.values(), dados):
                    campo.set(valor)
                app.cadastrar_obra()
                self.assertEqual(str(app.acervo.item("1", "values")[-1]), "2")

                app.busca.set("maquina")
                self.assertEqual(app.acervo.get_children(), ("1",))
                app.campos_leitor["Nome"].set("Leitor de teste")
                app.campos_leitor["Contato"].set("leitor@example.com")
                app.cadastrar_leitor()
                app.seletor_leitor.current(0)
                app.seletor_obra.current(0)
                app.atualizar_exemplares()
                app.seletor_exemplar.current(0)

                app.prazo.set("31/02/2026")
                with patch("main.messagebox.showwarning") as aviso:
                    app.botao_emprestar.invoke()
                    self.assertIn("prazo válido", aviso.call_args.args[1])
                self.assertFalse(app.historico.get_children())

                app.novo_prazo()
                app.botao_emprestar.invoke()
                self.assertEqual(str(app.acervo.item("1", "values")[-1]), "1")
                self.assertEqual(app.historico.item("1", "values")[-1], "Em aberto")

                app.seletor_exemplar.current(0)
                with patch("main.messagebox.showwarning") as aviso:
                    app.botao_emprestar.invoke()
                    self.assertIn("já está emprestado", aviso.call_args.args[1])
                self.assertEqual(app.historico.get_children(), ("1",))

                app.historico.selection_set("1")
                janela.update()
                app.botao_devolver.invoke()
                self.assertEqual(str(app.acervo.item("1", "values")[-1]), "2")
                self.assertEqual(app.historico.item("1", "values")[-1], "Devolvido")

                reaberta = Biblioteca(banco, hoje=hoje)
                self.assertEqual(reaberta.historico()[0]["situacao"], "Devolvido")
            finally:
                janela.destroy()


if __name__ == "__main__":
    unittest.main()
