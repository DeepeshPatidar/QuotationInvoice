import ast
try:
    with open('Quote.py', 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    print("✓ Quote.py syntax is valid")
except SyntaxError as e:
    print(f"✗ Syntax error in Quote.py: {e}")
