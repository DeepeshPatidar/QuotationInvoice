import ast, pathlib
p = pathlib.Path('Quote.py')
text = p.read_text(encoding='utf-8')
mod = ast.parse(text)
for node in mod.body:
    if isinstance(node, ast.ClassDef):
        print('CLASS', node.name)
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef):
                print('  FUNC', sub.name, 'line', sub.lineno)
