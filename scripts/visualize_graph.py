import os
import sys

# Ensure backend and agents are in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.m1.graphs.m1_graph import m1_graph

def main():
    # Generate Mermaid diagram syntax
    mermaid_syntax = m1_graph.get_graph().draw_mermaid()
    
    # Save it to a markdown file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'architecture', 'm1_graph_diagram.md')
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# M1 Agent Graph Diagram\n\n")
        f.write("> Auto-generated diagram representing the current flow of M1 Agent.\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_syntax)
        f.write("\n```\n")
    
    print(f"✅ Graph diagram successfully generated and saved to: {output_path}")
    print("\n--- Mermaid Syntax ---")
    print(mermaid_syntax)

if __name__ == "__main__":
    main()
