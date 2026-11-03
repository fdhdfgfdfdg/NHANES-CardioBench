"""Curate the finite release from preserved official metadata, not model answers."""
from pathlib import Path
import json, hashlib, copy, decimal

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'cardiobench'/'data'
FULL=json.loads((ROOT/'sources'/'parsed_codebooks.json').read_text())
TASKS=[]; GOLD={}

def fact(file,code):
    return FULL[file][code]

def add(kind,group,prompt,request,answer=None,evidence=None,status='answer',reason=None,canonical=None):
    prefix={'semantic':'S','coding':'C','weights':'W','leakage':'L','execution':'E'}[kind]
    n=1+sum(t['kind']==kind for t in TASKS)
    tid=f'{prefix}{n:02d}'
    task={'id':tid,'canonical_id':canonical or tid,'kind':kind,'group_id':group,'cycle':'2017-2018','prompt':prompt,'request':request}
    TASKS.append(task)
    GOLD[tid]={'status':status,'answer':answer or {},'evidence':evidence or [],'reason_code':reason}

routes=[]
semantic=[
 ('medical_history','MCQ_J','MCQ160F','self-reported history of clinician-diagnosed stroke'),
 ('medical_history','MCQ_J','MCQ160B','self-reported history of clinician-diagnosed congestive heart failure'),
 ('medical_history','MCQ_J','MCQ160C','self-reported history of clinician-diagnosed coronary heart disease'),
 ('medical_history','MCQ_J','MCQ160E','self-reported history of clinician-diagnosed myocardial infarction'),
 ('medical_history','MCQ_J','MCQ160D','self-reported history of clinician-diagnosed angina'),
 ('medical_history','MCQ_J','MCQ160A','self-reported history of clinician-diagnosed arthritis'),
 ('thyroid','MCQ_J','MCQ170M','current thyroid problem'),
 ('bp_questionnaire','BPQ_J','BPQ020','previous professional diagnosis of hypertension'),
 ('bp_questionnaire','BPQ_J','BPQ050A','current prescribed antihypertensive medication'),
 ('activity','PAQ_J','PAQ605','vigorous activity performed at work'),
 ('activity','PAQ_J','PAQ635','walking or cycling for transport'),
 ('activity','PAQ_J','PAD680','daily sedentary minutes'),
 ('diet','DR1TOT_J','DR1TSODI','first-day dietary sodium intake'),
 ('glucose','GLU_J','LBXGLU','fasting glucose in mg/dL'),
 ('lipids','TRIGLY_J','LBDLDL','Friedewald calculated LDL cholesterol'),
 ('lipids','HDL_J','LBDHDD','direct HDL cholesterol'),
]
for group,file,code,concept in semantic:
    f=fact(file,code)
    routes.append({'concept':concept,'variable':code,'file':file,'evidence_id':f['evidence_id']})
    add('semantic',group,f'For the 2017-2018 release, identify the variable and component for {concept}.',{'concept':concept},{'variable':code,'file':file},[f['evidence_id']])

units=[('blood_pressure','BPX_J','BPXSY1','mmHg'),('anthropometry','BMX_J','BMXBMI','kg/m2'),('glucose','GLU_J','LBXGLU','mg/dL'),('glucose','GLU_J','LBDGLUSI','mmol/L'),('glycohemoglobin','GHB_J','LBXGH','%'),('diet','DR1TOT_J','DR1TSODI','mg')]
for group,file,code,unit in units:
    add('coding',group,f'Return the documented measurement unit for {code}.',{'operation':'unit','file':file,'variable':code},{'unit':unit},[fact(file,code)['evidence_id']])
clean=[
 ('medical_history','MCQ_J','MCQ160F',[1,2,7,9,None],[1,2,None,None,None]),
 ('bp_questionnaire','BPQ_J','BPQ050A',[1,2,7,9,None],[1,2,None,None,None]),
 ('activity','PAQ_J','PAQ605',[1,2,7,9,None],[1,2,None,None,None]),
 ('activity','PAQ_J','PAQ640',[1,7,77,99,None],[1,7,None,None,None]),
 ('activity','PAQ_J','PAD680',[60,7777,9999,None],[60,None,None,None]),
 ('demography','DEMO_J','RIDAGEYR',[7,9,77,80,None],[7,9,77,80,None]),
 ('demography','DEMO_J','INDFMPIR',[0,5,1.2,None],[0,5,1.2,None]),
 ('anthropometry','BMX_J','BMXBMI',[17.2,None,34],[17.2,None,34]),
]
for group,file,code,values,expected in clean:
    f=fact(file,code)
    exceptional={str(r['code']) for r in f['values'] if r['meaning'].casefold() in ['refused',"don't know",'missing']}
    documented=[None if v is None or str(v) in exceptional else v for v in values]
    assert documented==expected,(code,documented,expected)
    add('coding',group,f'Recode documented refused, unknown and missing responses for {code}; retain all other supplied values.',{'operation':'clean','file':file,'variable':code,'values':values},{'values':expected},[f['evidence_id']])
add('coding','glucose','Convert 100 and 126 mg/dL fasting glucose to mmol/L using the documented factor and rounding.',{'operation':'convert_glucose','values':[100,126]},{'values':[5.551,6.994]},['GLU_J:CONVERSION'])
add('coding','unsupported','Give the documented unit for LBDGLUS in this preserved release; do not invent a code.',{'operation':'unit','file':'GLU_J','variable':'LBDGLUS'},evidence=['CORPUS:MANIFEST'],status='abstain',reason='NOT_IN_RELEASE')

weights=[
 ('design_interview',['DEMO_J'],'WTINT2YR','DEMO_J:WTINT2YR'),
 ('design_interview',['DEMO_J','MCQ_J'],'WTINT2YR','DEMO_J:WTINT2YR'),
 ('design_interview',['DEMO_J','BPQ_J'],'WTINT2YR','DEMO_J:WTINT2YR'),
 ('design_interview',['DEMO_J','PAQ_J'],'WTINT2YR','DEMO_J:WTINT2YR'),
 ('design_mec',['DEMO_J','BMX_J'],'WTMEC2YR','DEMO_J:WTMEC2YR'),
 ('design_mec',['DEMO_J','BPX_J'],'WTMEC2YR','DEMO_J:WTMEC2YR'),
 ('design_mec',['DEMO_J','GHB_J'],'WTMEC2YR','DEMO_J:WTMEC2YR'),
 ('design_mec',['DEMO_J','TCHOL_J','HDL_J'],'WTMEC2YR','DEMO_J:WTMEC2YR'),
 ('design_fasting',['DEMO_J','GLU_J'],'WTSAF2YR','GLU_J:WTSAF2YR'),
 ('design_fasting',['DEMO_J','TRIGLY_J'],'WTSAF2YR','TRIGLY_J:WTSAF2YR'),
 ('design_fasting',['DEMO_J','GLU_J','TRIGLY_J'],'WTSAF2YR','GLU_J:WTSAF2YR'),
 ('design_diet',['DEMO_J','DR1TOT_J'],'WTDRD1','DR1TOT_J:WTDRD1'),
 ('design_diet',['DEMO_J','BMX_J','DR1TOT_J'],'WTDRD1','DR1TOT_J:WTDRD1'),
]
for group,files,w,e in weights:
    add('weights',group,'Select the analysis weight and design fields for these components in 2017-2018: '+', '.join(files)+'.',{'files':files,'analysis_cycle':'2017-2018'},{'weight':w,'stratum':'SDMVSTRA','psu':'SDMVPSU'},[e,'WEIGHTING:SELECTION'])
for files in [['DEMO_J','GLU_J','DR1TOT_J'],['DEMO_J','TRIGLY_J','DR1TOT_J']]:
    add('weights','joint_design','Select a unique joint weight for fasting and first-day dietary records without a supplied joint nonresponse adjustment.',{'files':files,'analysis_cycle':'2017-2018'},evidence=['POLICY:JOINT_WEIGHT'],status='abstain',reason='JOINT_WEIGHT_NOT_SPECIFIED')
add('weights','unsupported','Select the weight for a 2019-2020 release using only this 2017-2018 corpus.',{'files':['DEMO_J'],'analysis_cycle':'2019-2020'},evidence=['CORPUS:MANIFEST'],status='abstain',reason='CYCLE_OUT_OF_SCOPE')

def leakage(group,label_sources,features,expected):
    add('leakage',group,'Apply the declared dependency policy: exclude any feature with a transitive dependency on a label source.',{'label_sources':label_sources,'feature_dependencies':features},{'excluded_features':sorted(expected)},['POLICY:DEPENDENCY'])
leakage('medical_history',['MCQ160F'],{'MCQ160F':[],'RIDAGEYR':[],'BMXBMI':[]},['MCQ160F'])
leakage('medical_history',['MCQ160B'],{'MCQ160B':[],'RIAGENDR':[]},['MCQ160B'])
leakage('medical_history',['MCQ160B','MCQ160C','MCQ160D','MCQ160E','MCQ160F'],{'MCQ160C':[],'RIDAGEYR':[],'CVD_COPY':['MCQ160B','MCQ160E']},['MCQ160C','CVD_COPY'])
leakage('blood_pressure',['BPXSY1','BPXSY2'],{'MEAN_SBP':['BPXSY1','BPXSY2'],'RIDAGEYR':[]},['MEAN_SBP'])
leakage('blood_pressure',['BPXSY1','BPXSY2'],{'BPXSY2':[],'BMXBMI':[]},['BPXSY2'])
leakage('blood_pressure',['BPXSY1','BPXDI1','BPQ050A'],{'BPXDI1':[],'HBP_COPY':['BPXSY1','BPXDI1','BPQ050A'],'RIAGENDR':[]},['BPXDI1','HBP_COPY'])
leakage('glucose',['LBXGLU'],{'LBDGLUSI':['LBXGLU'],'RIDAGEYR':[]},['LBDGLUSI'])
leakage('lipids',['LBDHDD'],{'NONHDL':['LBXTC','LBDHDD'],'LBXTC':[],'INDFMPIR':[]},['NONHDL'])
leakage('diet',['DR1TSODI'],{'SODIUM_DENSITY':['DR1TSODI','DR1TKCAL'],'RIDAGEYR':[]},['SODIUM_DENSITY'])
leakage('glycohemoglobin',['LBXGH'],{'LBXGH':[],'RIDAGEYR':[]},['LBXGH'])
leakage('anthropometry',['BMXBMI'],{'BMI_COPY':['BMXBMI'],'RIAGENDR':[]},['BMI_COPY'])
leakage('medical_history',['MCQ160F'],{'RIDAGEYR':[],'RIAGENDR':[],'INDFMPIR':[]},[])
leakage('blood_pressure',['BPXSY1'],{'RIDAGEYR':[],'BMXBMI':[]},[])
leakage('glucose',['LBXGLU'],{'GLU_ALIAS':['LBXGLU'],'SECOND_ALIAS':['GLU_ALIAS'],'RIDAGEYR':[]},['GLU_ALIAS','SECOND_ALIAS'])
leakage('anthropometry',['BMXBMI'],{'HEIGHT':['BMXHT'],'WEIGHT':['BMXWT']},[])
add('leakage','dependency_invalid','Detect a cyclic dependency graph before attempting label-source tracing.',{'label_sources':['LBXGLU'],'feature_dependencies':{'A':['B'],'B':['A']}},evidence=['POLICY:DEPENDENCY'],status='reject',reason='CYCLIC_DEPENDENCY')

left=[{'SEQN':101+i,'RIDAGEYR':age,'WTMEC2YR':w,'RIAGENDR':1+i%2,'RIDRETH3':1+i%5} for i,(age,w) in enumerate([(20,1),(45,2),(19,1),(80,3),(35,0),(30,2),(50,1),(9,2)])]
right=[{'SEQN':101+i,'BPXSY1':x} for i,x in enumerate([110,130,120,None,140,90,160,120])]
base={'synthetic':True,'left':left,'right':right,'key':'SEQN','age_column':'RIDAGEYR','minimum_age':20,'value_column':'BPXSY1','weight_column':'WTMEC2YR'}

def independent_expected(r):
    # A separate Decimal oracle for the finite synthetic checks.
    for side in ['left','right']:
        ids=[x[r['key']] for x in r[side]]
        if len(ids)!=len(set(ids)):return None,'DUPLICATE_KEY'
    for row in r['left']:
        if r['age_column'] not in row or r['weight_column'] not in row:return None,'MISSING_COLUMN'
        w=row[r['weight_column']]
        if w is not None and w<0:return None,'INVALID_WEIGHT'
    if any(r['value_column'] not in row for row in r['right']):return None,'MISSING_COLUMN'
    selected=[]
    for a in r['left']:
        matches=[b for b in r['right'] if a[r['key']]==b[r['key']]]
        x=matches[0][r['value_column']] if matches else None
        w=a[r['weight_column']]
        if a[r['age_column']]>=r['minimum_age'] and x is not None and w is not None and w>0:
            selected.append((decimal.Decimal(str(x)),decimal.Decimal(str(w))))
    if not selected:return None,'EMPTY_ANALYSIS'
    mean=sum(x*w for x,w in selected)/sum(w for x,w in selected)
    return {'joined_rows':len(r['left']),'cohort_n':len(selected),'weighted_mean':float(mean)},None

variants=[]
variants.append(('base',copy.deepcopy(base)))
r=copy.deepcopy(base);r['left'].reverse();r['right']=r['right'][3:]+r['right'][:3];variants.append(('permuted_rows',r))
r=copy.deepcopy(base);r['right'].append({'SEQN':999,'BPXSY1':999});variants.append(('unmatched_right_row',r))
r=copy.deepcopy(base);r['left']=[x for x in r['left'] if x['SEQN']!=103];variants.append(('minor_removed',r))
r=copy.deepcopy(base);r['right']=[x for x in r['right'] if x['SEQN']!=107];variants.append(('missing_match',r))
r=copy.deepcopy(base)
for x in r['right']:x['BPXSY1']=None
variants.append(('all_values_missing',r))
r=copy.deepcopy(base);r['left'].append(copy.deepcopy(r['left'][0]));variants.append(('duplicate_left',r))
r=copy.deepcopy(base);r['right'].append(copy.deepcopy(r['right'][1]));variants.append(('duplicate_right',r))
r=copy.deepcopy(base);r['left'][0]['WTMEC2YR']=-1;variants.append(('negative_weight',r))
r=copy.deepcopy(base);r['left'][0]['WTMEC2YR']=None;variants.append(('missing_weight',r))
r=copy.deepcopy(base)
for x in r['left']:x['WTMEC2YR']=0
variants.append(('all_weights_zero',r))
r=copy.deepcopy(base);r['left'][-1]['RIDAGEYR']=77;variants.append(('age_77_is_valid',r))
r=copy.deepcopy(base);r['value_column']='BPXDI1'
for x,v in zip(r['right'],[0,80,72,None,87,60,95,70]):x['BPXDI1']=v
variants.append(('zero_diastolic_is_retained',r))
r=copy.deepcopy(base)
for x in r['left']:x['WTMEC2YR']*=1000
variants.append(('weight_scale',r))
r=copy.deepcopy(base);del r['left'][0]['RIDAGEYR'];variants.append(('missing_column',r))
r=copy.deepcopy(base)
for x in r['left']:x['RIAGENDR']=3-x['RIAGENDR'];x['RIDRETH3']=9
variants.append(('irrelevant_group_labels',r))
for name,r in variants:
    expected,error=independent_expected(r)
    add('execution','synthetic_execution','Execute the declared left join, adult domain filter and positive-weight complete-case mean on the synthetic fixture: '+name+'.',r,expected,['POLICY:EXECUTION'],status='reject' if error else 'answer',reason=error,canonical='E01')

development={'bp_questionnaire','activity','demography','design_interview','design_mec','thyroid'}
for t in TASKS:t['split']='development' if t['group_id'] in development else 'evaluation'
from extension_workloads import extend
extend(TASKS,GOLD)
assert len(TASKS)==104
assert len({t['canonical_id'] for t in TASKS})==89
assert set(t['group_id'] for t in TASKS if t['split']=='development').isdisjoint(t['group_id'] for t in TASKS if t['split']=='evaluation')
catalog={'cycle':'2017-2018','variables':[v for f in FULL.values() for v in f.values()],'units':{code:unit for _,_,code,unit in units},'conversion':{'from':'LBXGLU','to':'LBDGLUSI','factor':0.05551,'decimals':3},'policy_evidence':{
 'GLU_J:CONVERSION':'The official GLU_J processing notes specify multiplication by 0.05551 and rounding to three decimals.',
 'WEIGHTING:SELECTION':'Use the appropriate documented analysis weight and the masked stratum and PSU fields; component applicability is required.',
 'CORPUS:MANIFEST':'Absence from the preserved 2017-2018 corpus supports only a release-scoped abstention.',
 'POLICY:JOINT_WEIGHT':'This suite declines to infer a unique joint fasting/dietary weight without a declared joint selection or nonresponse adjustment. This is an author-defined conservative policy.',
 'POLICY:DEPENDENCY':'Any feature transitively depending on a declared label source is excluded under the suite policy. Cycles in dependency graphs are rejected. This is an author-defined policy, not a CDC rule.',
 'POLICY:EXECUTION':'Synthetic fixtures use a validated one-to-one left join, age >= minimum_age, finite nonmissing values and positive finite weights. Duplicate keys and negative weights are rejected. The weighted mean is sum(w*x)/sum(w).'}
}
for name,obj in [('tasks.json',TASKS),('gold.json',GOLD),('catalog.json',catalog),('positive_control_routes.json',routes)]:
    (DATA/name).write_bytes(json.dumps(obj,indent=2,allow_nan=False).encode('utf-8'))
summary={'version':'0.4.8','cycle':'2017-2018','families':{k:sum(t['kind']==k for t in TASKS) for k in ['semantic','coding','weights','leakage','execution']},'canonical_workloads':89,'checks':104,'development_checks':sum(t['split']=='development' for t in TASKS),'evaluation_checks':sum(t['split']=='evaluation' for t in TASKS),'source_rule_groups':len({t['group_id'] for t in TASKS}),'expected_abstentions':sum(g['status']=='abstain' for g in GOLD.values()),'expected_rejections':sum(g['status']=='reject' for g in GOLD.values()),'official_variable_occurrences':len(catalog['variables']),'snapshots':13,'section_hash_scheme':'sha256 of HTMLParser section text; whitespace collapsed, UTF-8; v1','independent_human_annotation':'not performed','patient_records':'none; execution fixtures are synthetic'}
(DATA/'release.json').write_bytes(json.dumps(summary,indent=2).encode('utf-8'))
print(json.dumps(summary,indent=2))

policy={'version':'0.4.8','review_status':'author-defined alternative evidence; independent human adjudication pending','alternatives':{'W11':[['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION'],['GLU_J:WTSAF2YR','TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION']]},'rationale':{'W11':'Both requested component codebooks document WTSAF2YR as the Fasting Subsample 2 Year MEC Weight for the same cycle. The strict historical score is retained separately.'},'source_ids':['GLU_J:WTSAF2YR','TRIGLY_J:WTSAF2YR']}
import hashlib
policy['task_fingerprints']={t['id']:hashlib.sha256(json.dumps(t,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest() for t in TASKS if t['id'] in policy['alternatives']}
policy['gold_fingerprints']={tid:hashlib.sha256(json.dumps(GOLD[tid],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest() for tid in policy['alternatives']}
(DATA/'evidence_policy.json').write_bytes(json.dumps(policy,indent=2).encode('utf-8'))
