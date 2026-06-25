"""Tools the risk-investigator agent can call.

The plain `_functions` hold the logic and are unit-testable offline. `make_tools`
wraps them as LangChain tools bound to a specific repo + change, for the agent.
"""
from langchain_core.tools import tool

from .rules import score_rules


def _read_code(repo, path):
    return repo.get(path, f"(no file '{path}' in the provided context)")


def _search_repo(repo, query):
    hits = []
    for path, content in repo.items():
        for i, line in enumerate(content.splitlines(), 1):
            if query in line:
                hits.append(f"{path}:{i}: {line.strip()}")
    return "\n".join(hits) if hits else f"(no matches for '{query}')"


def _check_tests(repo, name):
    tests = [p for p, c in repo.items() if "test" in p.lower() and name in c]
    return "tests reference it: " + ", ".join(tests) if tests else "no test references it"


def _run_rules(diff):
    risk, reasons, block = score_rules(diff)
    return f"rules say risk={risk}, block_secret={block}, reasons={reasons}"


def make_tools(repo, diff):
    @tool
    def read_code(path: str) -> str:
        """Read the full contents of a file in the repository."""
        return _read_code(repo, path)

    @tool
    def search_repo(query: str) -> str:
        """Find every line in the repo containing a string (e.g. a function name),
        to understand where something is used (its blast radius)."""
        return _search_repo(repo, query)

    @tool
    def check_tests(name: str) -> str:
        """Check whether any test file references a given name."""
        return _check_tests(repo, name)

    @tool
    def run_rules(note: str = "") -> str:
        """Run the fast deterministic risk rules on this change and see their result."""
        return _run_rules(diff)

    return [read_code, search_repo, check_tests, run_rules]
