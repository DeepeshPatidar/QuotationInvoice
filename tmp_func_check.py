import ast
f='Quote.py'
with open(f,'r',encoding='utf-8') as fh:
    src=fh.read()
mod=ast.parse(src)
funcs=[]
for n in ast.walk(mod):
    if isinstance(n, ast.FunctionDef):
        funcs.append((n.name, n.lineno))
print('functions',len(funcs))
for name,line in funcs:
    print(line,name)
dups={}
for name,line in funcs:
    dups.setdefault(name,[]).append(line)
for name,lines in dups.items():
    if len(lines)>1:
        print('duplicate',name,lines)
