import argparse
import ast
import json
import math
import os
import re
import subprocess
import sys
import shutil
from collections import Counter,defaultdict,deque
from pathlib import Path
PY_EXTENSIONS={'.py'}
IGNORE_DIRS={'.git','.hg','.svn','.venv','venv','env','node_modules','__pycache__','.mypy_cache','.pytest_cache','.idea','.vscode','dist','build','site-packages'}
PYTHON_KEYWORDS=set('False None True and as assert async await break case class continue def del elif else except finally for from global if import in is lambda match nonlocal not or pass raise return try while with yield'.split())
TOKEN_RE=re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
VERSION_RE=re.compile(r'\b(?:v?\d+\.\d+(?:\.\d+)?)\b')
def run_git(path,args):
    try:
        p=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
        return p.returncode,p.stdout,p.stderr
    except Exception as e:
        return 1,'',str(e)
def is_test_file(path):
    n=path.name.lower()
    return n.startswith('test_') or n.endswith('_test.py') or 'tests' in {p.lower() for p in path.parts}
def safe_read(path):
    try:
        return path.read_text(encoding='utf-8',errors='replace')
    except Exception:
        return ''
def discover_files(root):
    out=[]
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in PY_EXTENSIONS:
            out.append(p)
    return sorted(out)
def relative_module(root,path):
    rel=path.relative_to(root).with_suffix('')
    parts=list(rel.parts)
    if parts and parts[-1]=='__init__':
        parts=parts[:-1]
    return '.'.join(parts)
def parse_file(root,path):
    text=safe_read(path)
    lines=text.splitlines()
    loc=sum(1 for line in lines if line.strip())
    try:
        tree=ast.parse(text or ' ')
    except SyntaxError:
        return {'path':str(path.relative_to(root)),'module':relative_module(root,path),'loc':loc,'functions':0,'classes':0,'imports':[],'complexity':max(1,loc//20+1),'syntax_error':True,'test':is_test_file(path),'tokens':0,'docstrings':0}
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.extend(a.name.split('.')[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.append(node.module.split('.')[0])
    functions=sum(1 for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
    classes=sum(1 for n in ast.walk(tree) if isinstance(n,ast.ClassDef))
    branch_nodes=(ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.With,ast.AsyncWith,ast.IfExp,ast.BoolOp,ast.Match,ast.comprehension,ast.ExceptHandler)
    complexity=1+sum(1 for n in ast.walk(tree) if isinstance(n,branch_nodes))
    docstrings=sum(1 for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Module)) and ast.get_docstring(n))
    tokens=len(TOKEN_RE.findall(text))
    return {'path':str(path.relative_to(root)),'module':relative_module(root,path),'loc':loc,'functions':functions,'classes':classes,'imports':sorted(set(imports)),'complexity':complexity,'syntax_error':False,'test':is_test_file(path),'tokens':tokens,'docstrings':docstrings}
def git_churn(root):
    code,out,err=run_git(root,['log','--numstat','--format=__COMMIT__%H|%ct|%s'])
    if code!=0:
        return {'available':False,'commits':0,'file_stats':{},'commit_times':[],'error':err.strip()}
    commits=0
    file_stats=defaultdict(lambda:{'added':0,'deleted':0,'commits':0,'last_commit':0})
    commit_times=[]
    current=None
    for line in out.splitlines():
        if line.startswith('__COMMIT__'):
            commits+=1
            parts=line[10:].split('|',2)
            current={'hash':parts[0],'time':int(parts[1]) if parts[1].isdigit() else 0}
            commit_times.append(current['time'])
            continue
        parts=line.split('\t')
        if current and len(parts)==3 and parts[2].strip():
            a,d,f=parts
            try:
                added=0 if a=='-' else int(a)
            except ValueError:
                added=0
            try:
                deleted=0 if d=='-' else int(d)
            except ValueError:
                deleted=0
            rel=f.replace('\\','/')
            s=file_stats[rel]
            s['added']+=added
            s['deleted']+=deleted
            s['commits']+=1
            s['last_commit']=max(s['last_commit'],current['time'])
    return {'available':True,'commits':commits,'file_stats':dict(file_stats),'commit_times':commit_times,'error':''}
def map_git_stats(file_stats):
    mapped={}
    for k,v in file_stats.items():
        mapped[Path(k).as_posix()]=v
    return mapped
def local_import_targets(root,modules):
    mapping={m:p for p,m in modules.items() if m}
    return mapping
def build_graph(root,files,meta):
    module_to_file={m['module']:m['path'] for m in meta if m['module']}
    graph=defaultdict(set)
    unresolved=Counter()
    for m in meta:
        src=m['path']
        graph[src]
        for imp in m['imports']:
            candidates=[mod for mod in module_to_file if mod==imp or mod.startswith(imp+'.')]
            if candidates:
                target=module_to_file[sorted(candidates,key=len)[0]]
                if target!=src:
                    graph[src].add(target)
            else:
                unresolved[imp]+=1
    return graph,unresolved
def reverse_graph(graph):
    rev=defaultdict(set)
    for a,targets in graph.items():
        for b in targets:
            rev[b].add(a)
    return rev
def bfs_reach(graph,start,limit=1000):
    seen={start}
    q=deque([(start,0)])
    while q:
        node,depth=q.popleft()
        if depth>=limit:
            continue
        for nxt in graph.get(node,()):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt,depth+1))
    return seen
def percentile(values,p):
    if not values:
        return 0.0
    xs=sorted(values)
    if len(xs)==1:
        return float(xs[0])
    k=(len(xs)-1)*p
    f=math.floor(k)
    c=math.ceil(k)
    if f==c:
        return float(xs[f])
    return xs[f]+(xs[c]-xs[f])*(k-f)
def normalize(x,low,high):
    if high<=low:
        return 0.0
    return max(0.0,min(1.0,(x-low)/(high-low)))
def analyze(root):
    files=discover_files(root)
    meta=[parse_file(root,p) for p in files]
    git=git_churn(root)
    stats=map_git_stats(git['file_stats']) if git['available'] else {}
    graph,unresolved=build_graph(root,files,meta)
    rev=reverse_graph(graph)
    total_loc=sum(m['loc'] for m in meta)
    total_complexity=sum(m['complexity'] for m in meta)
    tests=sum(1 for m in meta if m['test'])
    source_files=max(0,len(meta)-tests)
    test_ratio=tests/source_files if source_files else 0.0
    syntax_errors=sum(1 for m in meta if m['syntax_error'])
    all_complex=[m['complexity'] for m in meta]
    hotspot_data=[]
    for m in meta:
        s=stats.get(m['path'],{'added':0,'deleted':0,'commits':0,'last_commit':0})
        churn=s['added']+s['deleted']
        dependents=len(rev.get(m['path'],set()))
        deps=len(graph.get(m['path'],set()))
        impact=len(bfs_reach(rev,m['path']))-1
        complexity=m['complexity']
        density=(complexity/max(1,m['loc']))*100
        risk=0.0
        risk+=normalize(churn,0,250)*24
        risk+=normalize(s['commits'],0,20)*18
        risk+=normalize(complexity,1,40)*18
        risk+=normalize(dependents,0,12)*18
        risk+=normalize(impact,0,max(1,len(meta)-1))*12
        risk+=6 if m['syntax_error'] else 0
        if m['test']:
            risk*=0.65
        hotspot_data.append({'path':m['path'],'risk':round(min(100,risk),2),'loc':m['loc'],'complexity':m['complexity'],'churn':churn,'commits':s['commits'],'dependents':dependents,'dependencies':deps,'impact':impact,'test':m['test'],'syntax_error':m['syntax_error'],'complexity_density':round(density,4)})
    hotspot_data.sort(key=lambda x:(-x['risk'],-x['churn'],-x['complexity'],x['path']))
    graph_nodes=len(graph)
    graph_edges=sum(len(v) for v in graph.values())
    avg_complexity=total_complexity/max(1,len(meta))
    p95_complexity=percentile(all_complex,0.95)
    high_complex=sum(1 for x in hotspot_data if x['complexity']>=15)
    high_risk=sum(1 for x in hotspot_data if x['risk']>=60)
    risk_score=0.0
    risk_score+=min(25,high_risk*4)
    risk_score+=min(20,normalize(avg_complexity,1,15)*20)
    risk_score+=min(15,normalize(p95_complexity,1,30)*15)
    risk_score+=min(15,normalize((1-test_ratio) if source_files else 0,0,1)*15)
    risk_score+=min(10,normalize(graph_edges,0,max(1,graph_nodes*3))*10)
    risk_score+=min(10,normalize(git['commits'],0,100)*10) if git['available'] else 0
    risk_score+=min(5,syntax_errors*2)
    risk_score=round(min(100,risk_score),2)
    rating='LOW'
    if risk_score>=70:
        rating='HIGH'
    elif risk_score>=40:
        rating='MEDIUM'
    return {'project':root.name or str(root),'path':str(root.resolve()),'summary':{'files':len(meta),'source_files':source_files,'test_files':tests,'total_loc':total_loc,'average_complexity':round(avg_complexity,2),'p95_complexity':round(p95_complexity,2),'syntax_errors':syntax_errors,'test_ratio':round(test_ratio,4),'risk_score':risk_score,'risk_level':rating,'git_available':git['available'],'commits':git['commits']},'graph':{'nodes':graph_nodes,'edges':graph_edges,'unresolved_external_imports':unresolved.most_common(20)},'hotspots':hotspot_data[:25],'files':hotspot_data,'git':{'commits':git['commits'],'available':git['available']}}
def format_text(report):
    s=report['summary']
    lines=[]
    lines.append(f"RepoRisk: {report['project']}")
    lines.append(f"Path: {report['path']}")
    lines.append(f"Risk: {s['risk_level']} ({s['risk_score']}/100)")
    lines.append(f"Python Files: {s['files']} | Source: {s['source_files']} | Tests: {s['test_files']}")
    lines.append(f"LOC: {s['total_loc']} | Avg Complexity: {s['average_complexity']} | P95 Complexity: {s['p95_complexity']}")
    lines.append(f"Git: {'available' if s['git_available'] else 'unavailable'} | Commits: {s['commits']}")
    lines.append(f"Import Graph: {report['graph']['nodes']} nodes / {report['graph']['edges']} edges")
    lines.append('Top Risk Hotspots:')
    for i,item in enumerate(report['hotspots'][:10],1):
        lines.append(f"{i}. {item['path']} | risk={item['risk']} churn={item['churn']} complexity={item['complexity']} dependents={item['dependents']} impact={item['impact']}")
    return '\n'.join(lines)
def write_report(report,path):
    Path(path).write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
def make_sample_repo(base):
    root=Path(base)/'sample_repo'
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root/'app.py').write_text('from service import run\nfrom utils import normalize\ndef main(x):\n    if x>10:\n        return run(normalize(x))\n    return run(x)\n',encoding='utf-8')
    (root/'service.py').write_text('from utils import normalize\ndef run(x):\n    total=0\n    for i in range(x):\n        if i%2==0:\n            total+=i\n    return normalize(total)\n',encoding='utf-8')
    (root/'utils.py').write_text('def normalize(x):\n    if x<0:\n        return 0\n    return x\n',encoding='utf-8')
    (root/'test_app.py').write_text('from app import main\ndef test_main():\n    assert main(2)>=0\n',encoding='utf-8')
    (root/'README.md').write_text('# Sample\n',encoding='utf-8')
    code,_,_=run_git(root,['init'])
    if code==0:
        run_git(root,['config','user.email','test@example.com'])
        run_git(root,['config','user.name','RepoRisk Test'])
        run_git(root,['add','.'])
        run_git(root,['commit','-m','initial'])
        (root/'service.py').write_text('from utils import normalize\ndef run(x):\n    total=0\n    for i in range(x):\n        if i%2==0:\n            if i>10:\n                total+=i*2\n            else:\n                total+=i\n    return normalize(total)\n',encoding='utf-8')
        run_git(root,['add','.'])
        run_git(root,['commit','-m','increase service branching'])
    return root
def self_test():
    base=Path(os.getenv('TMPDIR') or os.getenv('TEMP') or '/tmp')/'reporisk_selftest'
    root=make_sample_repo(base)
    report=analyze(root)
    checks=[]
    checks.append(report['summary']['files']==4)
    checks.append(report['summary']['git_available'] is True)
    checks.append(report['summary']['commits']>=2)
    checks.append(report['graph']['edges']>=2)
    checks.append(len(report['hotspots'])==4)
    checks.append(report['summary']['risk_score']>=0)
    checks.append(any(x['path']=='service.py' for x in report['hotspots']))
    if not all(checks):
        raise RuntimeError('self-test failed: '+json.dumps({'checks':checks,'summary':report['summary'],'graph':report['graph']},sort_keys=True))
    print('REPORISK SELF-TEST: PASS')
    print(f"Files: {report['summary']['files']}")
    print(f"Commits: {report['summary']['commits']}")
    print(f"Risk Score: {report['summary']['risk_score']}")
    print(f"Risk Level: {report['summary']['risk_level']}")
    print(f"Hotspots: {len(report['hotspots'])}")
def build_parser():
    p=argparse.ArgumentParser(prog='repo_risk.py',description='Repository risk analyzer')
    p.add_argument('path',nargs='?',help='repository path')
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--json',dest='json_path')
    p.add_argument('--text',dest='text_path')
    p.add_argument('--top',type=int,default=10)
    return p
def main():
    args=build_parser().parse_args()
    if args.self_test or not args.path:
        self_test()
        return 0
    root=Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f'Error: directory not found: {root}',file=sys.stderr)
        return 1
    report=analyze(root)
    print(format_text(report))
    if args.top>0 and args.top<10:
        print('')
        for i,item in enumerate(report['hotspots'][:args.top],1):
            print(f"{i}. {item['path']} | risk={item['risk']}")
    if args.json_path:
        write_report(report,args.json_path)
        print(f'JSON report: {Path(args.json_path).resolve()}')
    if args.text_path:
        Path(args.text_path).write_text(format_text(report),encoding='utf-8')
        print(f'Text report: {Path(args.text_path).resolve()}')
    return 0
if __name__=='__main__':
    sys.exit(main())
