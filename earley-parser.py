from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import sys


@dataclass(frozen=True)
class Rule:
    """A grammar rule consisting of a head symbol and body symbols."""
    head: str
    body: Tuple[str, ...]
    
    def __str__(self):
        return f"{self.head} → {' '.join(self.body) if self.body else 'ε'}"


@dataclass(frozen=True)
class State:
    """A state in the Earley parsing algorithm."""
    rule: Rule
    dot: int
    start: int
    backpointers: Tuple[Tuple[int, int], ...]

    @property
    def next_symbol(self) -> Optional[str]:
        """Return the symbol after the dot, or None if dot is at the end."""
        if self.dot < len(self.rule.body):
            return self.rule.body[self.dot]
        return None

    def is_complete(self) -> bool:
        """Return True if the dot is at the end of the rule."""
        return self.dot >= len(self.rule.body)

    def __str__(self):
        body = list(self.rule.body) if self.rule.body else ['ε']
        body.insert(self.dot, "•")
        return f"{self.rule.head} → {' '.join(body)} ({self.start})"


class ParseTree:
    """A parse tree node containing a symbol and child nodes."""
    def __init__(self, symbol: str, children: List['ParseTree'] = None):
        self.symbol = symbol
        self.children = children or []

    def __str__(self):
        return self._to_string_visual()

    def _to_string_visual(self, prefix: str = "", is_tail: bool = True) -> str:
        """Create a visually appealing tree representation."""
        BRANCH_TAIL = "└── "
        BRANCH_MID = "├── " 
        INDENT_TAIL = "    "
        INDENT_MID = "│   "

        result = prefix + (BRANCH_TAIL if is_tail else BRANCH_MID) + self.symbol + "\n"
        
        if self.children:
            for i, child in enumerate(self.children):
                is_last = i == len(self.children) - 1
                new_prefix = prefix + (INDENT_TAIL if is_tail else INDENT_MID)
                result += child._to_string_visual(new_prefix, is_last)
                
        return result


class EarleyParser:
    """An implementation of the Earley parsing algorithm."""
    
    @classmethod
    def from_file(cls, filename: str) -> 'EarleyParser':
        """Create a parser from a grammar file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                grammar_rules = [line.strip() for line in f if line.strip()]
            return cls(grammar_rules)
        except FileNotFoundError:
            print(f"Error: Grammar file '{filename}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading grammar file: {e}")
            sys.exit(1)

    def __init__(self, grammar_rules: List[str]):
        """Initialize the parser with grammar rules."""
        self.rules = []
        self.chart = []
        
        for rule_str in grammar_rules:
            try:
                head, body_str = rule_str.split('→')
                head = head.strip()
                alternatives = [alt.strip() for alt in body_str.split('|')]

                for alt in alternatives:
                    if alt == 'ε':  
                        self.rules.append(Rule(head, ()))
                    else:
                        body = tuple(alt.split())
                        self.rules.append(Rule(head, body))
            except ValueError:
                print(f"Error parsing rule '{rule_str}'")
                continue

    def predict(self, state: State, position: int) -> None:
        """Add states for expanding a non-terminal."""
        next_symbol = state.next_symbol
        if next_symbol and next_symbol[0].isupper():
            print(f"[PREDICT] Expanding {next_symbol} at position {position}")
            for rule in self.rules:
                if rule.head == next_symbol:
                    new_state = State(rule, 0, position, ())
                    self._add_to_chart(new_state, position)

                    # Immediately complete epsilon rules
                    if not rule.body:
                        self.complete(new_state, position)

    def scan(self, state: State, position: int, words: List[str]) -> None:
        """Advance over a terminal symbol that matches the input."""
        if position < len(words):
            next_symbol = state.next_symbol
            if next_symbol and next_symbol == words[position]:
                print(f"[SCAN] Matching '{next_symbol}' at position {position}")
                new_state = State(
                    rule=state.rule, 
                    dot=state.dot + 1, 
                    start=state.start, 
                    backpointers=state.backpointers + ((position, position + 1),)
                )
                self._add_to_chart(new_state, position + 1)

    def complete(self, state: State, position: int) -> None:
        """Complete a rule and advance states waiting for this rule."""
        if not state.is_complete():
            return

        print(f"[COMPLETE] Completing rule {state.rule} from position {state.start} to {position}")
        for s in self.chart[state.start]:
            if not s.is_complete() and s.next_symbol == state.rule.head:
                new_backpointers = s.backpointers + ((state.start, position),)
                new_state = State(s.rule, s.dot + 1, s.start, new_backpointers)
                self._add_to_chart(new_state, position)

    def _add_to_chart(self, state: State, position: int) -> None:
        """Add a state to the chart if not already present."""
        if position >= len(self.chart):
            return
        if state not in self.chart[position]:
            self.chart[position].append(state)

    def _build_tree(self, state: State, pos: int, words: List[str]) -> ParseTree:
        """Build a parse tree from the completed chart."""
        if not state.rule.body: 
            return ParseTree(state.rule.head)

        children = []
        
        for i, symbol in enumerate(state.rule.body):
            start_pos, end_pos = state.backpointers[i]
            
            if symbol[0].isupper():  # Non-terminal
                for s in self.chart[end_pos]:
                    if (s.is_complete() and s.rule.head == symbol and 
                        s.start == start_pos):
                        children.append(self._build_tree(s, end_pos, words))
                        break
            else:  # Terminal
                children.append(ParseTree(words[start_pos]))

        return ParseTree(state.rule.head, children)

    def parse(self, sentence: str) -> Tuple[bool, Optional[ParseTree]]:
        """Parse a sentence using the Earley algorithm."""
        words = sentence.split() if sentence.strip() else []
        
        # Initialize chart
        self.chart = [[] for _ in range(len(words) + 1)]
        
        # Add initial state
        start_rule = Rule('γ', ('S',))
        self._add_to_chart(State(start_rule, 0, 0, ()), 0)
        
        # Process all states
        for i in range(len(words) + 1):
            j = 0
            while j < len(self.chart[i]):
                state = self.chart[i][j]
                if not state.is_complete():
                    if state.next_symbol and state.next_symbol[0].isupper():
                        self.predict(state, i)
                    else:
                        self.scan(state, i, words)
                else:
                    self.complete(state, i)
                j += 1

        # Print the final chart
        print("\n--- Chart ---")
        for idx, states in enumerate(self.chart):
            print(f"Chart[{idx}]:")
            for s in states:
                print(f"  {s}")

        # Check if input is accepted
        for state in self.chart[len(words)]:
            if (state.rule.head == 'γ' and state.is_complete() and 
                state.start == 0):
                # Find the S state
                s_state = None
                for s in self.chart[len(words)]:
                    if (s.is_complete() and s.rule.head == 'S' and 
                        s.start == 0 and len(s.backpointers) > 0):
                        s_state = s
                        break
                
                if s_state:
                    parse_tree = self._build_tree(s_state, len(words), words)
                    print("\n--- Parse Tree ---")
                    print(parse_tree)
                    return True, parse_tree
                return True, None

        return False, None


def main():
    """Main function to run the parser."""
    if len(sys.argv) > 1:
        grammar_file = sys.argv[1]
    else:
        grammar_file = 'grammar.txt'

    parser = EarleyParser.from_file(grammar_file)
    
    input_string = input("Enter a string to parse: ")
    print(f"\nParsing: '{input_string if input_string else 'ε'}'")
    accepted, tree = parser.parse(input_string)
    
    if accepted:
        print("✓ Accepted by the grammar")
    else:
        print("✗ Not accepted by the grammar")


if __name__ == "__main__":
    main()
