"""Interface gráfica do LivroLivre."""
import argparse
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from biblioteca import Biblioteca, ErroBiblioteca


def data_br(valor):
    return date.fromisoformat(valor).strftime("%d/%m/%Y") if valor else "—"


class LivroLivre:
    def __init__(self, janela, biblioteca):
        self.janela = janela
        self.biblioteca = biblioteca
        janela.title("LivroLivre | Biblioteca")
        janela.geometry("1020x660")
        janela.minsize(820, 560)
        janela.configure(bg="#eef3f3")

        estilo = ttk.Style(janela)
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#eef3f3")
        estilo.configure("TLabel", background="#eef3f3", foreground="#183234", font=("Segoe UI", 10))
        estilo.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        estilo.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        estilo.configure("Primary.TButton", background="#11645f", foreground="#ffffff")
        estilo.map("Primary.TButton", background=[("active", "#174c49")])
        estilo.configure("Treeview", rowheight=31, font=("Segoe UI", 10))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=6)
        estilo.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10))

        topo = tk.Frame(janela, bg="#123c3b", padx=22, pady=14)
        topo.pack(fill="x")
        tk.Label(topo, text="LivroLivre", bg="#123c3b", fg="white",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(topo, text="Controle de acervo e circulação", bg="#123c3b", fg="#d0e9e6",
                 font=("Segoe UI", 10)).pack(anchor="w")

        self.abas = ttk.Notebook(janela)
        self.abas.pack(fill="both", expand=True, padx=16, pady=(14, 0))
        self.criar_acervo()
        self.criar_leitores()
        self.criar_emprestimos()

        self.status = tk.StringVar(value="Pronto para começar.")
        ttk.Label(janela, textvariable=self.status, padding=(20, 8)).pack(fill="x")
        self.atualizar()

    def aba(self, nome):
        painel = ttk.Frame(self.abas, padding=14)
        self.abas.add(painel, text=nome)
        return painel

    def formulario(self, painel, campos):
        linha = ttk.Frame(painel)
        linha.pack(fill="x", pady=(7, 9))
        variaveis = {}
        for coluna, (rotulo, inicial) in enumerate(campos):
            linha.columnconfigure(coluna, weight=1)
            ttk.Label(linha, text=rotulo).grid(row=0, column=coluna, sticky="w", padx=(0, 8))
            variavel = tk.StringVar(value=inicial)
            ttk.Entry(linha, textvariable=variavel, width=12).grid(
                row=1, column=coluna, sticky="ew", padx=(0, 8), pady=(3, 0)
            )
            variaveis[rotulo] = variavel
        return linha, variaveis

    def tabela(self, painel, colunas):
        area = ttk.Frame(painel)
        area.pack(fill="both", expand=True, pady=(7, 0))
        tabela = ttk.Treeview(
            area, columns=[rotulo for rotulo, _ in colunas], show="headings",
            selectmode="browse",
        )
        barra = ttk.Scrollbar(area, orient="vertical", command=tabela.yview)
        tabela.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        tabela.pack(side="left", fill="both", expand=True)
        for rotulo, largura in colunas:
            tabela.heading(rotulo, text=rotulo)
            tabela.column(rotulo, width=largura, minwidth=min(largura, 55))
        tabela.tag_configure("atraso", foreground="#8a3d20")
        return tabela

    def preencher_tabela(self, tabela, linhas):
        selecionado = tabela.selection()
        tabela.delete(*tabela.get_children())
        for identificador, valores, tags in linhas:
            tabela.insert("", "end", iid=identificador, values=valores, tags=tags)
        if selecionado and tabela.exists(selecionado[0]):
            tabela.selection_set(selecionado[0])

    def criar_acervo(self):
        painel = self.aba("Acervo")
        ttk.Label(painel, text="Cadastrar título e exemplares", style="Title.TLabel").pack(anchor="w")
        linha, self.campos_obra = self.formulario(painel, [
            ("Título", ""), ("Autor", ""), ("Gênero", ""), ("Ano opcional", ""), ("Exemplares", "1")
        ])
        ttk.Button(linha, text="Cadastrar livro", style="Primary.TButton",
                   command=self.cadastrar_obra).grid(row=1, column=5, sticky="e")

        filtro = ttk.Frame(painel)
        filtro.pack(fill="x", pady=(12, 0))
        ttk.Label(filtro, text="Buscar por título, autor ou gênero").pack(side="left")
        self.busca = tk.StringVar()
        ttk.Entry(filtro, textvariable=self.busca, width=28).pack(side="left", padx=9)
        self.apenas_disponiveis = tk.BooleanVar()
        ttk.Checkbutton(filtro, text="Só disponíveis", variable=self.apenas_disponiveis,
                        command=self.atualizar_acervo).pack(side="left")
        self.contagem = tk.StringVar()
        ttk.Label(filtro, textvariable=self.contagem).pack(side="right")

        self.acervo = self.tabela(painel, [
            ("Título", 230), ("Autor", 190), ("Gênero", 130), ("Ano", 75),
            ("Exemplares", 95), ("Disponíveis", 95),
        ])
        self.busca.trace_add("write", lambda *_: self.atualizar_acervo())

    def criar_leitores(self):
        painel = self.aba("Leitores")
        ttk.Label(painel, text="Cadastrar leitor", style="Title.TLabel").pack(anchor="w")
        linha, self.campos_leitor = self.formulario(painel, [("Nome", ""), ("Contato", "")])
        ttk.Button(linha, text="Cadastrar leitor", style="Primary.TButton",
                   command=self.cadastrar_leitor).grid(row=1, column=2)
        self.lista_leitores = self.tabela(painel, [("Código", 85), ("Nome", 260), ("Contato", 300)])

    def criar_emprestimos(self):
        painel = self.aba("Empréstimos")
        ttk.Label(painel, text="Registrar empréstimo", style="Title.TLabel").pack(anchor="w")
        linha = ttk.Frame(painel)
        linha.pack(fill="x", pady=(7, 8))
        for coluna, nome in enumerate(("Leitor", "Livro", "Exemplar", "Prazo (DD/MM/AAAA)")):
            linha.columnconfigure(coluna, weight=1)
            ttk.Label(linha, text=nome).grid(row=0, column=coluna, sticky="w")
        self.seletor_leitor = ttk.Combobox(linha, state="readonly", width=17)
        self.seletor_obra = ttk.Combobox(linha, state="readonly", width=20)
        self.seletor_exemplar = ttk.Combobox(linha, state="readonly", width=13)
        self.prazo = tk.StringVar()
        entrada_prazo = ttk.Entry(linha, textvariable=self.prazo, width=15)
        for coluna, campo in enumerate((
            self.seletor_leitor, self.seletor_obra, self.seletor_exemplar, entrada_prazo
        )):
            campo.grid(row=1, column=coluna, sticky="ew", padx=(0, 8), pady=(3, 0))
        self.seletor_obra.bind("<<ComboboxSelected>>", self.atualizar_exemplares)
        self.botao_emprestar = ttk.Button(linha, text="Registrar", style="Primary.TButton",
                                          command=self.emprestar)
        self.botao_emprestar.grid(row=1, column=4)
        self.novo_prazo()

        historico = ttk.Frame(painel)
        historico.pack(fill="x", pady=(12, 0))
        ttk.Label(historico, text="Histórico", style="Title.TLabel").pack(side="left")
        self.filtro_historico = ttk.Combobox(
            historico, state="readonly", width=13,
            values=("Todos", "Ativos", "Em atraso", "Devolvidos"),
        )
        self.filtro_historico.current(0)
        self.filtro_historico.pack(side="left", padx=12)
        self.filtro_historico.bind("<<ComboboxSelected>>", lambda _: self.atualizar_historico())
        ttk.Button(historico, text="Atualizar", command=self.atualizar).pack(side="left")
        self.botao_devolver = ttk.Button(historico, text="Registrar devolução", command=self.devolver)
        self.botao_devolver.pack(side="right")
        self.historico = self.tabela(painel, [
            ("Código", 58), ("Livro", 185), ("Exemplar", 76), ("Leitor", 150),
            ("Retirada", 96), ("Prazo", 96), ("Devolução", 96), ("Situação", 105),
        ])
        self.historico.bind("<<TreeviewSelect>>", self.atualizar_botao_devolver)

    def novo_prazo(self):
        self.prazo.set((self.biblioteca.hoje() + timedelta(days=7)).strftime("%d/%m/%Y"))

    def atualizar_acervo(self):
        obras = self.biblioteca.catalogo(self.busca.get())
        exibidas = [o for o in obras if not self.apenas_disponiveis.get() or o["disponiveis"]]
        self.contagem.set(f"{len(exibidas)} título(s)")
        self.preencher_tabela(self.acervo, [
            (o["id"], (o["titulo"], o["autor"], o["genero"], o["ano"] or "—",
                       o["total"], o["disponiveis"]), ()) for o in exibidas
        ])

    def atualizar_seletor(self, seletor, opcoes):
        anterior = seletor.get()
        seletor.configure(values=list(opcoes))
        seletor.set(anterior if anterior in opcoes else "")

    def atualizar_exemplares(self, _evento=None):
        obra = self.opcoes_obras.get(self.seletor_obra.get())
        self.opcoes_exemplares = {
            f'EX-{x["id"]:04} · {"Disponível" if x["disponivel"] else "Emprestado"}': x["id"]
            for x in (self.biblioteca.exemplares(obra) if obra is not None else [])
        }
        self.atualizar_seletor(self.seletor_exemplar, self.opcoes_exemplares)

    def atualizar_historico(self):
        filtro = self.filtro_historico.get()
        self.emprestimos_exibidos = {
            str(e["id"]): e for e in self.biblioteca.historico()
            if filtro == "Todos" or (filtro == "Ativos" and not e["devolucao"])
            or (filtro == "Em atraso" and e["situacao"] == "Em atraso")
            or (filtro == "Devolvidos" and e["devolucao"])
        }
        self.preencher_tabela(self.historico, [
            (i, (e["id"], e["titulo"], f'EX-{e["exemplar"]:04}', e["leitor"],
                 data_br(e["retirada"]), data_br(e["prazo"]), data_br(e["devolucao"]), e["situacao"]),
             ("atraso",) if e["situacao"] == "Em atraso" else ())
            for i, e in self.emprestimos_exibidos.items()
        ])
        self.atualizar_botao_devolver()

    def atualizar_botao_devolver(self, _evento=None):
        selecionados = self.historico.selection()
        emprestimo = self.emprestimos_exibidos.get(selecionados[0]) if selecionados else None
        self.botao_devolver.state(["!disabled"] if emprestimo and not emprestimo["devolucao"] else ["disabled"])

    def atualizar(self):
        self.atualizar_acervo()
        leitores = self.biblioteca.leitores()
        self.preencher_tabela(self.lista_leitores, [
            (l["id"], (l["id"], l["nome"], l["contato"]), ()) for l in leitores
        ])
        self.opcoes_leitores = {f'{l["id"]} · {l["nome"]}': l["id"] for l in leitores}
        self.opcoes_obras = {
            f'{o["id"]} · {o["titulo"]}': o["id"] for o in self.biblioteca.catalogo()
        }
        self.atualizar_seletor(self.seletor_leitor, self.opcoes_leitores)
        self.atualizar_seletor(self.seletor_obra, self.opcoes_obras)
        self.atualizar_exemplares()
        self.atualizar_historico()

    def executar(self, operacao, mensagem):
        try:
            operacao()
        except (ErroBiblioteca, sqlite3.Error) as erro:
            self.status.set(str(erro))
            messagebox.showwarning("LivroLivre", str(erro), parent=self.janela)
            return False
        self.atualizar()
        self.status.set(mensagem)
        return True

    def cadastrar_obra(self):
        valores = [campo.get() for campo in self.campos_obra.values()]
        if self.executar(lambda: self.biblioteca.cadastrar_obra(*valores), "Livro e exemplares cadastrados."):
            for campo in self.campos_obra.values():
                campo.set("")
            self.campos_obra["Exemplares"].set("1")

    def cadastrar_leitor(self):
        valores = [campo.get() for campo in self.campos_leitor.values()]
        if self.executar(lambda: self.biblioteca.cadastrar_leitor(*valores), "Leitor cadastrado."):
            for campo in self.campos_leitor.values():
                campo.set("")

    def emprestar(self):
        def registrar():
            leitor = self.opcoes_leitores.get(self.seletor_leitor.get())
            exemplar = self.opcoes_exemplares.get(self.seletor_exemplar.get())
            if leitor is None or exemplar is None:
                raise ErroBiblioteca("Selecione o leitor, o livro e o exemplar.")
            try:
                prazo = datetime.strptime(self.prazo.get().strip(), "%d/%m/%Y").date()
            except ValueError as erro:
                raise ErroBiblioteca("Informe um prazo válido no formato DD/MM/AAAA.") from erro
            self.biblioteca.emprestar(exemplar, leitor, prazo)

        self.executar(registrar, "Empréstimo registrado. Veja a nova linha no histórico.")

    def devolver(self):
        selecionados = self.historico.selection()
        if selecionados:
            self.executar(lambda: self.biblioteca.devolver(int(selecionados[0])),
                          "Devolução registrada. O exemplar foi liberado.")


def main():
    parser = argparse.ArgumentParser(description="LivroLivre | Controle de acervo e circulação")
    parser.add_argument("--banco", type=Path, default=Path(__file__).with_name("livrolivre.db"),
                        help="caminho do banco SQLite")
    args = parser.parse_args()

    janela = tk.Tk()
    try:
        LivroLivre(janela, Biblioteca(args.banco))
    except sqlite3.Error as erro:
        messagebox.showerror("LivroLivre", f"Não foi possível abrir o banco.\n{erro}", parent=janela)
        janela.destroy()
        return
    janela.mainloop()


if __name__ == "__main__":
    main()
