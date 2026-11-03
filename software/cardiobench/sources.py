"""Deterministic parser for the preserved NHANES HTML codebook structure."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib, json, re
from .core import ROOT, read_json

class Node:
    def __init__(self,tag,attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def find_all(self,tag):
        for item in self.children:
            if isinstance(item,Node):
                if item.tag==tag:yield item
                yield from item.find_all(tag)
    def text(self):
        return ' '.join(' '.join(x.text() if isinstance(x,Node) else x for x in self.children).split())

class Tree(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node('root');self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag not in self.VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)

def parse_component(raw,component,url):
    tree=Tree();tree.feed(raw);tree.close();out={}
    for section in tree.root.find_all('div'):
        if 'pagebreak' not in section.attrs.get('class','').split():continue
        headers=list(section.find_all('h3'))
        if not headers:continue
        header=headers[0];anchor=header.attrs.get('id')
        definitions={};key=None
        for dl in section.find_all('dl'):
            for node in dl.children:
                if not isinstance(node,Node):continue
                if node.tag=='dt':key=node.text().rstrip(':').strip()
                elif node.tag=='dd' and key:definitions[key]=node.text();key=None
        if 'Variable Name' not in definitions:raise ValueError('MISSING_VARIABLE: '+component)
        variable=definitions['Variable Name'].upper()
        if variable in out:raise ValueError('DUPLICATE_VARIABLE: '+component+':'+variable)
        if not anchor:raise ValueError('MISSING_ANCHOR: '+variable)
        values=[]
        for table in section.find_all('table'):
            if 'values' not in table.attrs.get('class','').split():continue
            for row in table.find_all('tr'):
                cells=list(row.find_all('td'))
                if len(cells)>=2:values.append({'code':cells[0].text(),'meaning':cells[1].text()})
        out[variable]={'variable':variable,'file':component,'cycle':'2017-2018','label':definitions.get('SAS Label',header.text()),
                       'question':definitions.get('English Text',''),'target':definitions.get('Target',''),'values':values,
                       'evidence_id':component+':'+variable,'url':url+'#'+anchor,
                       'section_sha256':hashlib.sha256(section.text().encode('utf-8')).hexdigest()}
    if not out:raise ValueError('EMPTY_CODEBOOK: '+component)
    return out

def parse_sources(root=ROOT):
    root=Path(root);manifest=read_json(root/'sources/manifest.json');out={}
    for item in manifest:
        p=root/item['path'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('SOURCE_HASH_MISMATCH: '+item['id'])
        if item['id']=='WEIGHTING':continue
        out[item['id']]=parse_component(raw.decode('utf-8-sig'),item['id'],item['url'])
    return out

def verify_parsed(root=ROOT):
    actual=parse_sources(root);expected=read_json(Path(root)/'sources/parsed_codebooks.json')
    if actual!=expected:raise ValueError('PARSED_METADATA_MISMATCH')
    return {'components':len(actual),'variable_occurrences':sum(len(v) for v in actual.values()),
            'section_hash_scheme':'sha256 of HTMLParser section text; whitespace collapsed, UTF-8; v1',
            'parsed_metadata_equal':True}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--out',type=Path);args=p.parse_args()
    if args.out:
        # Explicit output only; the parser never silently changes bundled inputs.
        from .io_safety import atomic_bytes, guard_output
        inputs=[args.source_root/'sources/manifest.json',*[args.source_root/x['path'] for x in read_json(args.source_root/'sources/manifest.json')]]
        try:guard_output(args.out,inputs)
        except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
        raw=json.dumps(parse_sources(args.source_root),indent=2).encode('utf-8')
        atomic_bytes(args.out,raw,inputs)
    else:print(json.dumps(verify_parsed(args.source_root),indent=2))
if __name__=='__main__':main()
