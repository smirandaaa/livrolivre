"""Abre o LivroLivre com um acervo e um atraso fictícios."""
import tempfile
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path

from biblioteca import Biblioteca
from main import LivroLivre


def preparar_demonstracao(caminho, hoje):
    retirada = hoje - timedelta(days=8)
    biblioteca = Biblioteca(caminho, hoje=lambda: retirada)
    biblioteca.cadastrar_obra("A Máquina do Tempo", "H. G. Wells", "Ficção", "1895", "2")
    outra_obra = biblioteca.cadastrar_obra("O Jardim Secreto", "Frances Hodgson Burnett", "Romance", "1911", "1")
    leitora = biblioteca.cadastrar_leitor("Leitora de demonstração", "leitora@example.com")
    exemplar = biblioteca.exemplares(outra_obra)[0]["id"]
    biblioteca.emprestar(exemplar, leitora, retirada + timedelta(days=7))
    return Biblioteca(caminho, hoje=lambda: hoje)


def main():
    with tempfile.TemporaryDirectory(prefix="livrolivre-demo-") as pasta:
        biblioteca = preparar_demonstracao(Path(pasta) / "demonstracao.db", date.today())
        janela = tk.Tk()
        app = LivroLivre(janela, biblioteca)
        janela.title("LivroLivre | Demonstração com dados fictícios")
        app.status.set("Demonstração · acervo fictício com duas cópias livres e um atraso.")
        janela.mainloop()


if __name__ == "__main__":
    main()
