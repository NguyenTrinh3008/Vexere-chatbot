"""
Visualize the LangGraph pipeline.

Usage:
  - In notebooks: simply run this file's contents or import visualize_graph()
  - CLI: python visualize_graph.py (will save graph to graph.png if display not available)
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.graph import compile_graph


def visualize_graph():
    compiled = compile_graph()
    try:
        from IPython.display import Image, display  # type: ignore
        try:
            display(Image(compiled.get_graph().draw_mermaid_png()))
            return
        except Exception:
            pass
    except Exception:
        # Not running in an IPython environment
        pass

    # Fallback: attempt to save PNG to file
    try:
        png_bytes = compiled.get_graph().draw_mermaid_png()
        with open("graph.png", "wb") as f:
            f.write(png_bytes)
        print(" Saved graph visualization to graph.png")
    except Exception as e:
        # Last resort: print mermaid source for external rendering
        try:
            mermaid = compiled.get_graph().draw_mermaid()
            print("Mermaid source (copy into a Mermaid renderer):\n")
            print(mermaid)
        except Exception:
            print(f" Unable to render or export graph: {e}")


if __name__ == "__main__":
    visualize_graph()


