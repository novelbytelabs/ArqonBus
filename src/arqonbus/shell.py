
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import print
from rich.prompt import Prompt

from arqonbus.compiler import compiler
from arqonbus.holonomy import engine, HolonomyVerdict

console = Console()

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]ARQON TOPOLOGICAL TRUTH SHELL v1.0[/bold cyan]\n"
        "[dim]Phase 7: Truth Verification (Rust Kernel)[/dim]",
        border_style="cyan"
    ))

def print_result(text, result):
    status = result.get("status")
    
    if status != "SUCCESS":
        console.print(f"[bold red]❌ RLM Compilation Failed:[/bold red] {result.get('error')}")
        return

    entities = result.get("entities", {})
    triplets = result.get("triplets", [])
    
    # Grid Layout
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column(justify="right")
    
    # Entity Table
    e_table = Table(title="Entities", show_header=True, header_style="bold magenta")
    e_table.add_column("Name", style="cyan")
    e_table.add_column("ID", justify="right", style="green")
    for name, eid in entities.items():
        e_table.add_row(name, str(eid))
        
    # Triplet Table
    t_table = Table(title="Topological Triplets", show_header=True, header_style="bold yellow")
    t_table.add_column("Subject", justify="center")
    t_table.add_column("Relation", justify="center")
    t_table.add_column("Object", justify="center")
    t_table.add_column("Verdict", justify="center")
    
    for t in triplets:
        if len(t) != 3: continue
        u, w, v = t
        
        # Re-verify to be sure (stateful)
        verdict = engine.verify_triplet(u, v, w)
        
        rel_str = "==" if w == 0 else "!="
        verdict_str = "[green]CONSISTENT[/green]"
        if verdict == HolonomyVerdict.CONTRADICTION:
            verdict_str = "[bold red]LIE DETECTED[/bold red]"
            
        t_table.add_row(str(u), rel_str, str(v), verdict_str)
        
    console.print(Panel(e_table, title="Knowledge Graph", border_style="magenta"))
    console.print(Panel(t_table, title="Verification", border_style="yellow"))

def main():
    if not engine.kernel:
        console.print("[bold red]CRITICAL: Kernel missing. Check engine initialization.[/bold red]")
        return
        
    if not compiler:
        console.print("[bold red]CRITICAL: RLM Compiler missing (No API Key?).[/bold red]")
        return

    print_banner()
    console.print("[dim]Type 'exit' or 'quit' to stop.[/dim]\n")
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]Query[/bold green]")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            if not user_input.strip():
                continue
                
            with console.status("[bold cyan]rlm::decompose...[/bold cyan]", spinner="dots"):
                # Compile & Verify
                result = compiler.compile(user_input)
                
            print_result(user_input, result)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
