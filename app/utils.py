# -*- coding: utf-8 -*-
import requests, re, ast
import app
from app import db
import json
from nltk import WordNetLemmatizer
from conllu import parse
import pandas as pd
from app.graph_analyzer import create_graphs, compute_metrics, detect_loops, detect_transitive_edges, detect_clusters, create_graph_dict
from app.models import Baseline_Methods, Annotations, Annotation_user, Annotation_types, Terminology, goldStandard, Terminology_reference


def conll_gen(file):
    """" Takes a text as input (file) and return a conll file (sentence)"""
    
    files = {
           'data': file,
           'model' : (None, 'english-ewt-ud-2.4-190531'),
           'tokenizer': (None, ''),
           'tagger': (None, ''),
           'parser': (None, ''),
       }

    r = requests.post('http://lindat.mff.cuni.cz/services/udpipe/api/process', files=files)
    re = r.json()
    sentence = re['result']
    return sentence

def id_phrase(conll, result):
    """ Take a file conll and a list of phrases as input and return the phrase id of that phrases """
    sentence = parse(conll)
    phraseid = []
    
    for x in [frasi for frasi in result]:
        list_word = str(x).split()
        i = 0
        check = []
        for ids, phrase in enumerate(sentence):
            for words in phrase:
                if (words["form"] == list_word[i]):
                    check.append(words["form"])
                    i += 1
                    if all(word in check for word in list_word):
                        phraseid.append(ids)
                        i = 0
                        break
                else:
                    check.clear()
                    i = 0
                
    
    return(phraseid)

def conll_to_text0(conll, start):
    """ From conll format to string with an index for starting """
    sentence = parse(conll)    
    check = ""
    for phrase in sentence[start:]:
        for words in phrase:
            check += words["form"] + " "
    return(check)
        
def conll_to_text1(conll, start, end):
     """ From conll format to string with an index for starting and ending """
    sentence = parse(conll)
    check = ""
    for phrase in sentence[start:end]:
        for words in phrase:
            check += words["form"] + " "
    return(check)
    
def parse_sentId(conll):
    """ Get the id of all the phrases """
    sentence = parse(conll)
    sentList = []
    data = {}
    text = ""
    for ids, phrase in enumerate(sentence):
        for words in phrase:
            text += words["form"] + " "    
        data['sent_id'] = ids + 1    
        data['text'] = text
        data['type'] = 'normal sentence'
        json_data = json.dumps(data)
        sentList.append(json_data)
    return(sentList)
    
def parse_tokToConcept(conll, words):
    lemmatizer = WordNetLemmatizer()
    text = conll_to_text0(conll, 0)
    tokToConcept = {}
    flag = True
    for word in words:
        position = []
        list_word = str(word).split()
        
        print(list_word)
        for index, word in enumerate(text.split()):
            if(flag):
                check = [(word.lower())]
            else:
                check.append((word.lower()))
            if all(word.lower() in check for word in list_word):
                position.append(index)
                flag = True
                continue
            if all(word in list_word for word in check):
                flag = False
            else:
                flag = True
        phrase = ""
        for word in list_word:
            phrase += word + " "
        tokToConcept.update({phrase: position})
    for key in sorted(tokToConcept):
        print(key, tokToConcept[key])
            
def data_analysis(conll, words, sentences, bid, cap, method):
    """ Create the two csv to use graph analyzer """
    lemmatizer = WordNetLemmatizer()
    df = pd.DataFrame(columns=['ID', 'name', 'frequence', 'sections', 'sentence', 'subsidiaries'])  
    dfAnnotation = pd.DataFrame(columns=['prerequisites', 'subsidiaries'])
    metrics = {}
    text = ""
    sentPhrase = ""
    sent = []
    appear = []
    section = []
    subsidiaries = []
    sentence = parse(conll)
    metrics['default concepts'] = len(words)
    
    # Add manual added concept if manual annotation
    if method not in ["1", "2", "3"]:
        new_words = set([])
        rel = Annotations.query.filter_by(bid=bid, cap=cap).all()
        uid = method.split(".")[1]
        for item in rel:
            try:
                int(item.lemma1)
            except ValueError:
                if (Annotation_user.query.filter_by(aid=item.aid).first() and str(Annotation_user.query.filter_by(aid=item.aid).first().uid) == str(uid)):
                    new_words.add(item.lemma1.lower())
            try:
                int(item.lemma2)
            except ValueError:
                if (Annotation_user.query.filter_by(aid=item.aid).first() and str(Annotation_user.query.filter_by(aid=item.aid).first().uid) == str(uid)):
                    new_words.add(item.lemma2.lower())
        metrics['entered concepts'] = len(new_words)
        words.extend(new_words)
    
    
    # Prepare sentence and text
    for ids, phrase in enumerate(sentence):
        for word in phrase:
            text += lemmatizer.lemmatize(word["form"]) + " "
            sentPhrase += lemmatizer.lemmatize(word["form"]) + " "
        sent.append(sentPhrase)
        sentPhrase = ""
      
    metrics['tokens'] = len(words)
    metrics['sentences'] = len(sentence)
    metrics['strong relations'] = 0
    metrics['weak relations'] = 0
    metrics['unique relations'] = []
     
    for i, word in enumerate(words):
        freq = text.count(word)
        # Check if a word is in a sent
        for k, phrase in enumerate(sent):
            if word in phrase:
                appear.append(k)
        # Check if a word is in a section
        for j, number in enumerate(sentences):
            if (j + 1) < len(sentences):
                if any(phraseId > number.sentence and phraseId < sentences[j+1].sentence for phraseId in appear):
                    section.append(int(number.section.split(".")[-1]))
            else:
                if any(phraseId > number.sentence for phraseId in appear):
                    section.append(int(number.section.split(".")[-1]))
        # Get all the relationship for baseline methods            
        if method in ["1", "2", "3"]:
            subsidiaries = Baseline_Methods.query.filter_by(lemma2=word, bid=bid, cap=cap).all()
            if method == "1":
                subsidiaries = [candidate.lemma1 for candidate in subsidiaries if candidate.m1 == 1]
                for subs in subsidiaries:
                    row = pd.Series({"prerequisites": word, "subsidiaries": subs})
                    dfAnnotation = dfAnnotation.append(row, ignore_index=True)
            elif method == "2":
                subsidiaries = [candidate.lemma1 for candidate in subsidiaries if candidate.m2 == 1]
                for subs in subsidiaries:
                    row = pd.Series({"prerequisites": word, "subsidiaries": subs})
                    dfAnnotation = dfAnnotation.append(row, ignore_index=True)
            elif method == "3":
                subsidiaries = [candidate.lemma1 for candidate in subsidiaries if candidate.m3 and (candidate.m3 > 0.1)]
                for subs in subsidiaries:
                    row = pd.Series({"prerequisites": word, "subsidiaries": subs})
                    dfAnnotation = dfAnnotation.append(row, ignore_index=True)
        # Get relationships for users annotation
        else:
            uid = method.split(".")[1]
            
            
            subsidiaries_aid = Annotations.query.filter_by(lemma2=find_term(word), bid=bid, cap=cap).all()
            for candidate in subsidiaries_aid:
                annUsr = Annotation_user.query.filter_by(aid=candidate.aid, uid=uid).first()
                if annUsr:
                    if annUsr.ann_type == 1:
                        metrics['weak relations'] += 1
                    elif annUsr.ann_type == 2:
                        metrics['strong relations'] += 1
                    if (candidate.lemma1, candidate.lemma2) not in metrics["unique relations"]:
                        metrics["unique relations"].append((candidate.lemma1, candidate.lemma2))
                    
                    term = Terminology.query.filter_by(tid=candidate.lemma1).first()
                    if(term):
                        term = term.lemma.lower()
                        subsidiaries.append(term)
                    else:
                        term = candidate.lemma1.lower()
                        subsidiaries.append(candidate.lemma1.lower())
                        
                        
                    row = pd.Series({"prerequisites": word.lower(), "subsidiaries": term})
                    dfAnnotation = dfAnnotation.append(row, ignore_index=True)     
                            
            
        
        
        row = pd.Series({"ID": i, "name": word, "frequence": freq, "sections": section, "sentence": appear, "subsidiaries" : [sub for sub in subsidiaries]})
        df = df.append(row, ignore_index=True)
            
        appear = []
        section = []
        subsidiaries = []
    
    
    return (dfAnnotation, df, metrics, words)

def data_summary(dfAnnotation, df, metrics, method):
    
    """ Takes the two csv to create the metrics for data summary """
    G_nx, G_ig, annotator = create_graphs(dfAnnotation, df, method)
    partial_metrics = compute_metrics(G_nx, G_ig)
    metrics['unique relations'] = len(metrics['unique relations'])
    metrics['transitive'] = detect_transitive_edges(G_nx, 2, find_also_not_inserted=False)
    metrics['transitive'] = len(metrics['transitive'])
    metrics['loops'] = detect_loops(G_nx, G_ig, df, remove=False)
    # metrics['loops'] = len(metrics['loops'])
    metrics['links'] = partial_metrics['num_edges']
    metrics['leaves'] = 0 
    
    for node in G_nx:
        if G_nx.out_degree(node)==0:
            metrics['leaves'] += 1
    
    metrics['diameter'] = partial_metrics['diameter']
    metrics['max out degree'] = partial_metrics['max out degree']
    metrics['max in degree'] = partial_metrics['max in degree']
    
    return(metrics)
    
def process_for_matrix(dfAnnotation, df, method, words):
    """ Takes the two csv to create the table that is required for compute graph analyzer method """
    
    G_nx, G_ig, annotator = create_graphs(dfAnnotation, df, method)
    partial_metrics = compute_metrics(G_nx, G_ig)
    transitives = detect_transitive_edges(G_nx, 2, find_also_not_inserted=False)
    loops = detect_loops(G_nx, G_ig, df, remove=False)
    memberships = detect_clusters(G_ig)
    
    dfMatrix = pd.DataFrame(index = [name for name in words], columns = [name for name in words])
    dfMatrix = dfMatrix.fillna(0)
    for row in df.itertuples():
        name = row.name
        relations = dfAnnotation.loc[dfAnnotation.prerequisites == name, 'subsidiaries'].tolist()
        for word in relations:
            if type(dfMatrix.loc[name, word]) is list:
                dfMatrix.loc[name, word] = dfMatrix.loc[name, word].append(method)
            else:
                dfMatrix.loc[name, word] = [method]
                
            
            
    final = create_graph_dict(df, dfMatrix, method, partial_metrics, loops, transitives, memberships, G_nx)
    final["__comment__"] = "..."

    final = json.dumps(final, indent=4,
                                 sort_keys=True,
                                 separators=(',', ': '))  
    return(final)

def process_for_matrix_gold(dfAnnotation, df, method, words):
    """ Takes the two csv to create the table for the gold standard that is required for compute graph analyzer method """
    
    G_nx, G_ig, annotator = create_graphs(dfAnnotation, df, method)
    partial_metrics = compute_metrics(G_nx, G_ig)
    transitives = detect_transitive_edges(G_nx, 2, find_also_not_inserted=False)
    loops = detect_loops(G_nx, G_ig, df, remove=False)
    memberships = detect_clusters(G_ig)
    
    uids = goldStandard.query.filter_by(gid=method.split(".")[1]).first().uids
    listaUids = uids.split(" ")
    listaUids = [uid for uid in listaUids if uid]
    
    dfMatrix = pd.DataFrame(index = [name for name in words], columns = [name for name in words])
    dfMatrix = dfMatrix.fillna(0)
    for index, row in df.iterrows():
        name = row["name"]
        for uid in listaUids:
            if not pd.isna(row[uid]):
                wordsList = ast.literal_eval(row[uid])
                for word in wordsList:
                    if type(dfMatrix.loc[name, word]) is list:
                        dfMatrix.loc[name, word] = dfMatrix.loc[name, word].append(uid)
                    else:
                        dfMatrix.loc[name, word] = [uid]
                                   
            
    final = create_graph_dict(df, dfMatrix, listaUids, partial_metrics, loops, transitives, memberships, G_nx)
    final["__comment__"] = "..."
    

    
    final = json.dumps(final, indent=4,
                                 sort_keys=True,
                                 separators=(',', ': ')) 
    
    return(final)
    
    
def processConll(conll, bid):
    """ Process and save the conll as is required by the conll_processor module"""    
    
    df = pd.DataFrame(columns=['doc_id', 'paragraph_id', 'sentence_id', 'sentence', 'token_id', 'token', 'lemma', 'upos', 'xpos', 'feats', 'head_token_id', 'dep_rel', 'deps', 'misc'])  
    conll = re.sub(r"\t", " ", conll)
    lines = conll.splitlines()
    stop_paragraph = '# newpar'
    stop_sent = '# sent_id'
    paragraph = 0
    sent_id = 0
    for line in lines[1:]:
        if line == stop_paragraph:
            paragraph += 1
            continue
        if line.startswith(stop_sent):
            sent_id += 1
            continue
        if line.startswith('# text'):
            text = line.split('= ', 1)[1]
            continue
        if not line:
            continue
        
        elements = line.split()
        token_id, token, lemma, upos, xpos, feats, head_token_id, dep_rel, deps, misc = [item for item in elements] 
        
        row = pd.Series({'doc_id': bid, 'paragraph_id': paragraph, 'sentence_id': sent_id, 'sentence': text, 'token_id': token_id, 'token': token, 'lemma': lemma, 'upos':upos, 'xpos': xpos, 'feats': feats, 'head_token_id': head_token_id, 'dep_rel': dep_rel, 'deps': deps, 'misc': misc})
        df = df.append(row, ignore_index=True)
    return df.to_csv()

def conll_annotation(conll):
    final_conll = []
    conll = re.sub(r"\t", " ", conll)
    lines = conll.splitlines()
    stop_paragraph = '# newpar'
    stop_sent = '# sent_id'
    sent_id = 0
    tok_id = 0
    
    for line in lines[1:]:
        if line == stop_paragraph:
            continue
        if line.startswith(stop_sent):
            sent_id += 1
            continue
        if line.startswith('# text'):
            continue
        if not line:
            continue
        
        tok_id += 1
        elements = line.split()
        token_id, token, lemma, upos, xpos, feats, head_token_id, dep_rel, deps, misc = [item for item in elements] 
        
        data = {}
    
        data['tok_id'] = tok_id
        data['sent_id'] = sent_id
        data['pos_in_sent'] = str(token_id)
        data['forma'] = token
        data['lemma'] = lemma
        data['pos_coarse'] = upos
        data['pos_fine'] = xpos
        data['iob'] = '_'
        data['part_of_concept'] = ''
        final_conll.append(data)
        
    return final_conll
    
def upload_Annotation(json, bid, cap, uid):
    """ Takes the json and create the rows that will be saved in the database """
    
    types = Annotation_types.query.all()
    dictionary = {}
    for item in types:
        dictionary[item.ann_type] = item.tid
        
    for item in json["savedInsertedRelations"]:
        lemma1 = find_term(item["advanced"])
        if not (Terminology_reference.query.filter_by(tid=lemma1, bid=bid,cap=cap).first()):
            lemma1 = item["advanced"].upper()
        lemma2 = find_term(item["prerequisite"])
        if not (Terminology_reference.query.filter_by(tid=lemma2, bid=bid, cap=cap).first()):
            lemma2 = item["prerequisite"].upper()
        id_phrase = item["sent"]
        weight = dictionary[item["weight"]]
        annotationObj = Annotations.query.filter_by(bid=bid, cap=cap, lemma1=lemma1, lemma2=lemma2).first()
        if (annotationObj):
            aid = annotationObj.aid
            annotationUserObj = Annotation_user(uid=uid, aid=aid, ann_type=weight)
            db.session.add(annotationUserObj)
        else:
            annotationObj = Annotations(bid=bid, cap=cap, lemma1=lemma1, lemma2=lemma2, id_phrase=id_phrase)
            db.session.add(annotationObj)
            aid = Annotations.query.filter_by(bid=bid, cap=cap, lemma1=lemma1, lemma2=lemma2, id_phrase=id_phrase).first().aid
            annotationUserObj = Annotation_user(uid=uid, aid=aid, ann_type=weight)
            db.session.add(annotationUserObj)
    db.session.commit()
    
def create_dfAnnotation(bid, cap, gid, conll, words):
    """ Create the dfAnnotation and df tables starting from conll """
    metrics = {}
    metrics['strong relations'] = 0
    metrics['weak relations'] = 0
    metrics['unique relations'] = []
    sentence = parse(conll)
    metrics['default concepts'] = len(words)
    gold_standard = goldStandard.query.filter_by(gid=gid.split(".")[1]).first().gold
    uids = goldStandard.query.filter_by(gid=gid.split(".")[1]).first().uids
    listaUids = uids.split(" ")
    listaUids = [uid for uid in listaUids if uid]
        
    
    df = pd.read_csv(pd.compat.StringIO(gold_standard))    
    new_words = set([])
    dfAnnotation = pd.DataFrame(columns=['prerequisites', 'subsidiaries'])
    for index, row in df.iterrows():
        for uid in listaUids:
            try:
                wordsList = ast.literal_eval(row[uid])
                name = row["name"]
                for word in wordsList:
                    row = pd.Series({"prerequisites": name, "subsidiaries": word})
                    dfAnnotation = dfAnnotation.append(row, ignore_index=True)
            except:
                continue
            
    for row in dfAnnotation.itertuples():
        lemma1 = find_term(row.subsidiaries)
        if type(lemma1) == int:
            term = Terminology_reference.query.filter_by(tid=lemma1, cap=cap, bid=bid).first()
            if not term:
                lemma1 = row.subsidiaries.upper()
        lemma2 = find_term(row.prerequisites)
        if type(lemma2) == int:
            term = Terminology_reference.query.filter_by(tid=lemma2, cap=cap, bid=bid).first()
            if not term:
                lemma2 = word.upper()
                    
        aids = Annotations.query.filter_by(lemma1=lemma1, lemma2=lemma2, bid=bid, cap=cap).all()
        for uid in listaUids:
            for aid in aids:
                annType = Annotation_user.query.filter_by(aid=aid.aid, uid=uid.split(".")[1]).first()
                if(annType):
                    annType = annType.ann_type
                    if annType == 1:
                        metrics['weak relations'] += 1
                    elif annType == 2:
                        metrics['strong relations'] += 1
                    if (row.subsidiaries, row.prerequisites) not in metrics["unique relations"]:
                        metrics["unique relations"].append((row.subsidiaries, row.prerequisites))
                    try:
                        int(aid.lemma1)
                    except ValueError:
                        new_words.add(aid.lemma1.lower())
                    try:
                        int(aid.lemma2)
                    except ValueError:
                        new_words.add(aid.lemma2.lower())
                
            
    metrics['tokens'] = len(words)
    metrics['sentences'] = len(sentence)
    metrics['entered concepts'] = len(new_words)   
    words.extend(new_words)
    
    return dfAnnotation, df, metrics, words
    
    
def create_gold(uids, bid, cap, words, conll, sentences):
    """ Create df table for a gold """
    lemmatizer = WordNetLemmatizer()
    text = ""
    sentPhrase = ""
    sent = []
    appear = []
    section = []
    sentence = parse(conll)
    
    
    new_words = set([])
    rel = Annotations.query.filter_by(bid=bid, cap=cap).all()
    for uid in uids:
        uid = uid.split('.')[1]
        for item in rel:
            try:
                int(item.lemma1)
            except ValueError:
                if (Annotation_user.query.filter_by(aid=item.aid).first() and str(Annotation_user.query.filter_by(aid=item.aid).first().uid) == str(uid)):
                    new_words.add(item.lemma1.lower())
            try:
                int(item.lemma2)
            except ValueError:
                if (Annotation_user.query.filter_by(aid=item.aid).first() and str(Annotation_user.query.filter_by(aid=item.aid).first().uid) == str(uid)):
                    new_words.add(item.lemma2.lower())
    words.extend(new_words)
    
    df = pd.DataFrame(columns=['ID', 'name', 'frequence', 'sections', 'sentence'])  
    for uid in uids:
        df[uid] = ""
    
    for ids, phrase in enumerate(sentence):
        for word in phrase:
            text += lemmatizer.lemmatize(word["form"]) + " "
            sentPhrase += lemmatizer.lemmatize(word["form"]) + " "
        sent.append(sentPhrase)
        sentPhrase = ""
      
    for i, word in enumerate(words):
        dictionary = {}
        freq = text.count(word)
        # Check if a word is in a sent
        for k, phrase in enumerate(sent):
            if word in phrase:
                appear.append(k)
        # Check if a word is in a section
        for j, number in enumerate(sentences):
            if (j + 1) < len(sentences):
                if any(phraseId > number.sentence and phraseId < sentences[j+1].sentence for phraseId in appear):
                    section.append(int(number.section.split(".")[-1]))
            else:
                if any(phraseId > number.sentence for phraseId in appear):
                    section.append(int(number.section.split(".")[-1]))
        
        for uid in uids:
            name = uid
            uid = uid.split(".")[1]
            lemma2 = find_term(word)
            if type(lemma2) == int:
                term = Terminology_reference.query.filter_by(tid=lemma2, cap=cap, bid=bid).first()
                if not term:
                    lemma2 = word.upper()
            subsidiaries_aid = Annotations.query.filter_by(lemma2=lemma2, bid=bid, cap=cap).all()
            temp = []
            for candidate in subsidiaries_aid:
                annUsr = Annotation_user.query.filter_by(aid=candidate.aid, uid=uid).first()
                if annUsr:
                    for candidate in subsidiaries_aid:
                        if Annotation_user.query.filter_by(aid=candidate.aid, uid=uid).first():
                            term = Terminology.query.filter_by(tid = candidate.lemma1).first()
                            if(term and not term.lemma.lower() in temp):
                                temp.append(term.lemma.lower())
                            elif(not candidate.lemma1.lower() in temp):
                                temp.append(candidate.lemma1.lower())  
            dictionary[name] = temp
            
        row = pd.Series({"ID": i, "name": word, "frequence": freq, "sections": section, "sentence": appear})
        df = df.append(row, ignore_index=True)
        
        appear = []
        section = []
        
        
        if dictionary:
            for uid in uids:
                try:  
                    df.iloc[-1, df.columns.get_loc(uid)] = dictionary[uid]
                except:
                    pass
                
    return df.to_csv()
    
def find_term(lemma):
    lemmaObj = Terminology.query.filter_by(lemma=lemma.lower()).first()
    if (lemmaObj):
        return lemmaObj.tid
    else:
        return lemma.upper()
            
        
def agreement_json(bid, cap, uid):
    ann_list = []
    dict_list = []
    ann_list = Annotations.query.filter_by(bid=bid, cap=cap).all()
    for item in ann_list:
        dictionary = {}
        ann = Annotation_user.query.filter_by(uid=uid, aid=item.aid).first()
        if(ann):
            print(1)
            dictionary["sent"] = item.id_phrase
            
            if(type(item.lemma1) == int):
                dictionary["advanced"] = Terminology.query.filter_by(tid = item.lemma1).first().lemma
            else:
                dictionary["advanced"] = item.lemma1
                
            if(type(item.lemma2) == int):
                dictionary["prerequisite"] = Terminology.query.filter_by(tid = item.lemma2).first().lemma
            else:
                dictionary["prerequisite"] = item.lemma2
                
            dictionary["weight"] = Annotation_types.query.filter_by(tid = ann.ann_type).first().ann_type
            
            dict_list.append(dictionary)
        
    return dict_list

def linguistic_json(bid, cap, uid):
    dict_list = []
    ann_list = Annotations.query.filter_by(bid=bid, cap=cap).all()
    for item in ann_list:
        dictionary = {}
        ann = Annotation_user.query.filter_by(uid=uid, aid=item.aid).first()
        if(ann):
            print(1)
            dictionary["sent"] = item.id_phrase
            
            if(type(item.lemma1) == int):
                dictionary["advanced"] = Terminology.query.filter_by(tid = item.lemma1).first().lemma
            else:
                dictionary["advanced"] = item.lemma1
                
            if(type(item.lemma2) == int):
                dictionary["prerequisite"] = Terminology.query.filter_by(tid = item.lemma2).first().lemma
            else:
                dictionary["prerequisite"] = item.lemma2
                
            dictionary["weight"] = Annotation_types.query.filter_by(tid = ann.ann_type).first().ann_type
            
            dict_list.append(dictionary)
    final = {}
    final["savedInsertedRelations"] = dict_list
    
    return final
        
    
    
            