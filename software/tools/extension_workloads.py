"""Separately specified synthetic base cases; author-curated, not human-adjudicated."""

def extend(tasks,gold):
    def add(kind,index,request,answer=None,error=None):
        prefix='L' if kind=='leakage' else 'E'
        ident=f'{prefix}{index+17:02d}'
        split='development' if index<6 else 'evaluation'
        group=f'extension_{kind}_{index//2+1}'
        tasks.append({'id':ident,'canonical_id':ident,'group_id':group,'split':split,'kind':kind,'cycle':'2017-2018',
            'prompt':('Trace the declared label dependencies; return sorted excluded feature names or reject a cycle.' if kind=='leakage' else 'Apply the documented synthetic join, eligibility and weighted-mean policy. These are numerical test values, not clinical observations.'),'request':request})
        gold[ident]={'status':'reject' if error else 'answer','answer':{} if error else answer,'reason_code':error,'evidence':['POLICY:DEPENDENCY' if kind=='leakage' else 'POLICY:EXECUTION']}
    graphs=[
      (['Y'],{'F':['Y'],'G':['F'],'AGE':[]},['F','G'],None),
      (['Y','Z'],{'F':['A','B'],'A':['Y'],'B':['Z'],'C':[]},['A','B','F'],None),
      (['TARGET'],{'A':['RAW'],'B':['A'],'RAW':[]},[],None),
      (['Y'],{'Y':[],'COPY':['Y'],'SAFE':['U']},['COPY','Y'],None),
      (['Y'],{'A':['A'],'B':['Y']},None,'CYCLIC_DEPENDENCY'),
      (['Y'],{'F':['MISSING_INTERMEDIATE'],'G':[]},[],None),
      (['Z'],{'LEFT':['Z'],'RIGHT':['Z'],'MERGED':['LEFT','RIGHT'],'FREE':['X']},['LEFT','MERGED','RIGHT'],None),
      (['Y','X'],{'P':['Q'],'Q':['R'],'R':['X'],'W':['Z']},['P','Q','R'],None),
      (['RESULT'],{'RESULT':['RAW'],'DERIVED':['RESULT'],'OTHER':['RAW']},['DERIVED','RESULT'],None),
      ([],{'A':['B'],'B':[]},[],None),
      (['Y'],{'F':['Y'],'A':['B'],'B':['C'],'C':['A']},None,'CYCLIC_DEPENDENCY'),
      (['Y'],{'Y':['RAW'],'A':['RAW'],'B':['A'],'C':['B','Y']},['C','Y'],None),
    ]
    for i,(labels,features,excluded,error) in enumerate(graphs):
        add('leakage',i,{'label_sources':labels,'feature_dependencies':features},{'excluded_features':excluded},error)
    # Expected values are explicitly specified, without calling the production executor.
    cases=[
      ([(1,30,1),(2,50,2),(3,65,3),(4,9,9),(5,40,4)],[(1,0),(2,10),(3,30),(4,200)],20,{'joined_rows':5,'cohort_n':3,'weighted_mean':110/6},None),
      ([(21,30,None),(22,19,2),(23,40,0),(24,50,5)],[(21,1),(22,2),(23,3),(24,12.5)],20,{'joined_rows':4,'cohort_n':1,'weighted_mean':12.5},None),
      ([(31,18,2)],[(31,-4)],18,{'joined_rows':1,'cohort_n':1,'weighted_mean':-4.0},None),
      ([(41,30,1e308),(42,40,1e308)],[(41,1e308),(42,1e308)],20,{'joined_rows':2,'cohort_n':2,'weighted_mean':1e308},None),
      ([(51,30,1),(52,30,1),(53,30,1)],[(51,1e100),(52,1),(53,-1e100)],20,{'joined_rows':3,'cohort_n':3,'weighted_mean':1/3},None),
      ([(61,30,1),(62,50,2)],[(61,8),(62,10),(62,12)],20,None,'DUPLICATE_KEY'),
      ([(71,30,1),(72,40,2)],[(700,5)],20,None,'EMPTY_ANALYSIS'),
      ([(81,70,1e-200),(82,90,3e-200)],[(81,1),(82,5)],65,{'joined_rows':2,'cohort_n':2,'weighted_mean':4.0},None),
      ([(91,21,.25),(92,22,.75)],[(92,8),(91,2)],20,{'joined_rows':2,'cohort_n':2,'weighted_mean':6.5},None),
      ([(101,30,1),(102,31,1)],[(101,3),(999,4)],20,None,'MISSING_COLUMN'),
      ([(111,10,-1),(112,40,1)],[(111,8),(112,9)],20,None,'INVALID_WEIGHT'),
      ([(121,20,2),(122,50,1),(123,8,1),(124,30,0),(125,60,1),(126,25,None)],[(122,10),(121,-5),(123,4),(124,7),(126,8)],20,{'joined_rows':6,'cohort_n':2,'weighted_mean':0.0},None),
    ]
    for i,(left,right,age,expected,error) in enumerate(cases):
        req={'synthetic':True,'key':'id','age_column':'age','minimum_age':age,'weight_column':'w','value_column':'x',
            'left':[dict(id=k,age=a,w=w) for k,a,w in left],'right':[dict(id=k,x=x) for k,x in right]}
        if i==9:del req['right'][-1]['x']
        add('execution',i,req,expected,error)
