# -*- coding: utf-8 -*-
from flask import render_template, redirect, flash, url_for, json
import os
from app import app, db
from app.forms import LoginForm, RegisterForm, BaselineForm, ComparisonForm, AnalysisForm, PreAnnotatorForm, PreVisualizationForm, UploadTerminologyForm, GoldStandardForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Book, Author, Conll, Terminology, bookStructure, Baseline_Methods, Annotations, Annotation_user, Terminology_reference, partialAnnotations, goldStandard
from flask import request, jsonify, make_response
from werkzeug.urls import url_parse
from app import utils, wikipedia, Method_01, Method_02, Method_03, Method_04, Method_05, temp, conll_processor_2, computeAgreement
import re
from threading import Thread
 
@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, surname=form.surname.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("You are now a registered user!", "succes")
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/term_upload', methods=['GET','POST'])
@login_required
def term_upload():
    form =  UploadTerminologyForm()
    cap_lista = Conll.query.all()
    cap_lista = [x for x in cap_lista if not Terminology_reference.query.filter_by(cap = x.cap, bid = x.bid).first()]
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1] 
        f = request.files['text']
        content = f.stream.read().decode("UTF8")
        terms = [term for term in content.splitlines() if term]
        text = utils.conll_to_text0(Conll.query.filter_by(cap=cap, bid=bid).first().conll, 0)
        wikipedia.initialize_page(text, terms)
        for word in [x.lower() for x in terms if x]:
            if (Terminology.query.filter_by(lemma=word).first()):
                tid = Terminology.query.filter_by(lemma=word).first().tid
                if not(Terminology_reference.query.filter_by(tid=tid, cap=cap, bid=bid).first()):
                    term_ref = Terminology_reference(tid=tid, cap=cap, bid=bid)
                    db.session.add(term_ref)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('terminology_upload.html', form=form)

@app.route('/baseline', methods=['GET','POST'])
@login_required
def baseline():
    form = BaselineForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1]       
        conll = Conll.query.filter_by(bid=bid, cap=cap).first().conll
        words_id = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()
        words = [Terminology.query.filter_by(tid=word_id.tid).first() for word_id in words_id]
        if form.baseline_method.data == "1":
            global finished
            words = [word.lemma for word in words]
            baseline = Method_01.Method_1(words, bid, cap)
            finished = False
            load(baseline.method_1())
        elif form.baseline_method.data == "2":
            words = [word.lemma for word in words]
            text = utils.conll_to_text0(conll, 0)
            baseline = Method_02.Method_2(words, conll, text, bid, cap)
            load(baseline.method_2())
        elif form.baseline_method.data == "3":
            title = [word.wiki_url for word in words]
            words = [word.lemma for word in words]
            dictionary = dict(zip(words, title))
            load(Method_03.method_3(dictionary, bid, cap))
        elif form.baseline_method.data == "4":
            title = [word.wiki_url for word in words]
            words = [word.lemma for word in words]
            dictionary = dict(zip(words[0:int(len(words)*0.2)], title[0:int(len(words)*0.2)]))
            load(Method_04.method_4(dictionary, bid, cap))
        elif form.baseline_method.data == "5":
            words = [word.lemma for word in words]
            sections = bookStructure.query.filter_by(bid=bid).all()
            chapter = [chap for chap in sections if chap.section.startswith(cap + ".")]
            text = {}
            for i, chap in enumerate(chapter):
                if i+1 < len(chapter):
                    text[chap.section] = (utils.conll_to_text1(conll, chap.sentence, chapter[i+1].sentence))
                else:
                    text[chap.section] = (utils.conll_to_text0(conll, chap.sentence))
            baseline = Method_05.Method_5(words, text, bid, cap)
            load(baseline.method_5())
    return render_template('baseline.html', form=form)

@app.route('/analysis', methods=['GET','POST'])
@login_required
def analysis():
    form = AnalysisForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    
    #Get baseline annotation 
    annotation = Baseline_Methods.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).first()
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).all()
        for user in userz:
            user = user.uid
            if user and user not in users:
                users.append(user)
                form.annotation_1.choices.append(("uid." + str(user), "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)))
                form.annotation_2.choices.append(("uid." + str(user), "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)))
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname + " "
        form.annotation_1.choices.append(("gold." + str(item.gid), "Annotazione gold di: " + str(nomeGold)))
        form.annotation_2.choices.append(("gold." + str(item.gid), "Annotazione gold di: " + str(nomeGold)))
    if(annotation):
        if(annotation.m1 is not None):
            form.annotation_1.choices.append((str(1), "Metodo uno"))
            form.annotation_2.choices.append((str(1), "Metodo uno"))
        if(annotation.m2 is not None):
            form.annotation_1.choices.append((str(2), "Metodo due"))
            form.annotation_2.choices.append((str(2), "Metodo due"))
        if(annotation.m3 is not None):
            form.annotation_1.choices.append((str(3), "Metodo tre"))
            form.annotation_2.choices.append((str(3), "Metodo tre"))
        if(annotation.m4 is not None):
            form.annotation_1.choices.append((str(4), "Metodo quattro"))
            form.annotation_2.choices.append((str(4), "Metodo quattro"))
        if(annotation.m5 is not None):
            form.annotation_1.choices.append((str(5), "Metodo cinque"))
            form.annotation_2.choices.append((str(5), "Metodo cinque"))
    
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1]       
        conll = Conll.query.filter_by(bid=bid, cap=cap).first().conll
        sentences = bookStructure.query.filter_by(bid=bid).all()
        sentences = [sentence for sentence in sentences if str(sentence.section).startswith(str(cap) + ".")]
        
        if form.analysis_type.data == "2":
            # load json with the requested datas
            json_relations = utils.linguistic_json(bid, cap, form.annotation_1.data.split(".")[1])
            json_relations = json.dumps(json_relations)
            # Gets all the words involveded in the book bid and chapter cap
            words_id = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()
            words = [Terminology.query.filter_by(tid=word_id.tid).first().lemma for word_id in words_id]
            conll_obj = Conll.query.filter_by(bid=bid, cap=cap).first()
            conll_processed = conll_obj.conll_processed
            conll = utils.conll_annotation(conll_obj.conll)
            sentences = bookStructure.query.filter_by(bid=bid).all()
            sentences = [x.sentence for x in sentences if x.section.startswith(cap)]
            conll_processed, sentList, tok_to_concept, concept_to_tok = conll_processor_2.conll_processor(conll_processed, 'PROVA', sentences, words)          
            return render_template('linguistic_analysis.html', file = {'json' : json_relations, 'concepts' : words,  'conll' : conll, 'tagged' : conll_processed, 'concepts' : words, 'tok_to_concept' : tok_to_concept, 'concept_to_tok' : concept_to_tok, 'sentence' : sentList})
        
        elif form.analysis_type.data == "1":
            # Gets all the words involveded in the book bid and chapter cap
            words_tid = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()           
            words = [Terminology.query.filter_by(tid=word.tid).first().lemma for word in words_tid]
            if("gold" in str(form.annotation_1.data)):
                dfAnnotation, df, metrics, words =  utils.create_dfAnnotation(bid, cap, form.annotation_1.data, conll, words)
                metrics = utils.data_summary(dfAnnotation, df, metrics, form.annotation_1.data)
            else:
                dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.annotation_1.data)
                metrics = utils.data_summary(dfAnnotation, df, metrics, form.annotation_1.data)
            return render_template('data_summary.html', file = metrics)
        
        elif form.analysis_type.data == "3":
            # Gets all the words involveded in the book bid and chapter cap
            words_tid = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()
            words = [Terminology.query.filter_by(tid=word.tid).first().lemma for word in words_tid]
            uid1 = form.annotation_1.data.split(".")[1]
            uid2 = form.annotation_2.data.split(".")[1]
            
            all_combs = computeAgreement.createAllComb(words)
            file1 = utils.agreement_json(bid, cap, uid1)
            file2 = utils.agreement_json(bid, cap, uid2)
            
            term_pairs={uid1:[], uid2:[]}
            term_pairs[uid1], all_combs = computeAgreement.createUserRel(file1, all_combs)
            term_pairs[uid2], all_combs = computeAgreement.createUserRel(file2, all_combs)
            
            metrics = computeAgreement.creaCoppieAnnot(uid1, uid2, term_pairs, all_combs)
            
            user1 = User.query.filter_by(uid=uid1).first()
            name1 = user1.name + " " + user1.surname
            user2 = User.query.filter_by(uid=uid2).first()
            name2 = user2.name + " " + user2.surname
            
            return render_template('agreement.html', file=metrics, rel1=name1, rel2=name2)
        else:
            return redirect(url_for('index'))
    return render_template('analysis.html', form=form)

@app.route('/analysis/<book>')
@login_required
def get_annotation(book):
    print(book)
    bid = book.split(",")[0]
    cap = book.split(",")[1]
    annotation = Baseline_Methods.query.filter_by(cap = cap, bid = bid).first()

    annotationList = []
    if (annotation):
        if(annotation.m1 is not None):
            annotationObj = {}
            annotationObj["id"] = 1
            annotationObj["name"] = "metodo uno"
            annotationList.append(annotationObj)
        if(annotation.m2 is not None):
            annotationObj = {}
            annotationObj["id"] = 2
            annotationObj["name"] = "metodo due"
            annotationList.append(annotationObj)
        if(annotation.m3 is not None):
            annotationObj = {}
            annotationObj["id"] = 3
            annotationObj["name"] = "metodo tre"
            annotationList.append(annotationObj)
        if(annotation.m4 is not None):
            annotationObj = {}
            annotationObj["id"] = 4
            annotationObj["name"] = "metodo quattro"
            annotationList.append(annotationObj)
        if(annotation.m5 is not None):
            annotationObj = {}
            annotationObj["id"] = 5
            annotationObj["name"] = "metodo cinque"
            annotationList.append(annotationObj)
    
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap, bid = bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).all()
        for user in userz:
            user = user.uid
            if user and user not in users:
                users.append(user)
                annotationObj = {}
                annotationObj["id"] = "uid." + str(user)
                annotationObj["name"] = "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)
                annotationList.append(annotationObj)
            
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap, bid = bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname + " "
        annotationObj = {}
        annotationObj["id"] = "gold." + str(item.gid)
        annotationObj["name"] = "Annotazione gold di: " + str(nomeGold)
        annotationList.append(annotationObj)
        
    return jsonify({'annotation': annotationList})
        
@app.route('/comparison', methods=['GET','POST'])
@login_required
def comparison():
    form = ComparisonForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    
    annotation = Baseline_Methods.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).first()
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).all()
        for user in userz:
            user = user.uid
            if user and user not in users:
                users.append(user)
                form.comparison_1.choices.append(("uid." + str(user), "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)))
                form.comparison_2.choices.append(("uid." + str(user), "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)))
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname + " "
        form.comparison_1.choices.append(("gold." + str(item.gid), "Annotazione gold di: " + str(nomeGold)))
        form.comparison_2.choices.append(("gold." + str(item.gid), "Annotazione gold di: " + str(nomeGold)))

    if(annotation):
        if(annotation.m1 is not None):
            form.comparison_1.choices.append((str(1), "Metodo uno"))
            form.comparison_2.choices.append((str(1), "Metodo uno"))
        if(annotation.m2 is not None):
            form.comparison_1.choices.append((str(2), "Metodo due"))
            form.comparison_2.choices.append((str(2), "Metodo due"))
        if(annotation.m3 is not None):
            form.comparison_1.choices.append((str(3), "Metodo tre"))
            form.comparison_2.choices.append((str(3), "Metodo tre"))
        if(annotation.m4 is not None):
            form.comparison_1.choices.append((str(4), "Metodo quattro"))
            form.comparison_2.choices.append((str(4), "Metodo quattro"))
        if(annotation.m5 is not None):
            form.comparison_1.choices.append((str(5), "Metodo cinque"))
            form.comparison_2.choices.append((str(5), "Metodo cinque"))
    
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1]       
        conll = Conll.query.filter_by(bid=bid, cap=cap).first().conll
        sentences = bookStructure.query.filter_by(bid=bid).all()
        sentences = [sentence for sentence in sentences if str(sentence.section).startswith(str(cap) + ".")]
        # Gets all the words involveded in the book bid and chapter cap
        words_tid = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()           
        words = [Terminology.query.filter_by(tid=word.tid).first().lemma for word in words_tid]
        if("gold" in str(form.comparison_1.data)):
            dfAnnotation, df, metrics, words =  utils.create_dfAnnotation(bid, cap, form.comparison_1.data, conll, words)
            metrics1 = utils.data_summary(dfAnnotation, df, metrics, form.comparison_1.data)
        else:
            dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.comparison_1.data)
            metrics1 = utils.data_summary(dfAnnotation, df, metrics, form.comparison_1.data)
        if("gold" in str(form.comparison_2.data)):
            dfAnnotation, df, metrics, words =  utils.create_dfAnnotation(bid, cap, form.comparison_2.data, conll, words)
            metrics2 = utils.data_summary(dfAnnotation, df, metrics, form.comparison_2.data)
        else:
            dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.comparison_2.data)
            metrics2 = utils.data_summary(dfAnnotation, df, metrics, form.comparison_2.data)
        return render_template('comparison_result.html', file1=metrics1, file2=metrics2)
    return render_template('comparison.html', form=form)

@app.route('/comparison/<book>')
@login_required
def get_annotation_comparison(book):
    bid = book.split(",")[0]
    cap = book.split(",")[1]
    annotation = Baseline_Methods.query.filter_by(cap = cap, bid = bid).first()

    #Get Baseline annotation
    annotationList = []
    if(annotation):
        if(annotation.m1 is not None):
            annotationObj = {}
            annotationObj["id"] = 1
            annotationObj["name"] = "metodo uno"
            annotationList.append(annotationObj)
        if(annotation.m2 is not None):
            annotationObj = {}
            annotationObj["id"] = 2
            annotationObj["name"] = "metodo due"
            annotationList.append(annotationObj)
        if(annotation.m3 is not None):
            annotationObj = {}
            annotationObj["id"] = 3
            annotationObj["name"] = "metodo tre"
            annotationList.append(annotationObj)
        if(annotation.m4 is not None):
            annotationObj = {}
            annotationObj["id"] = 4
            annotationObj["name"] = "metodo quattro"
            annotationList.append(annotationObj)
        if(annotation.m5 is not None):
            annotationObj = {}
            annotationObj["id"] = 5
            annotationObj["name"] = "metodo cinque"
            annotationList.append(annotationObj)
    
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap, bid = bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname
            annotationObj = {}
            annotationObj["id"] = "gold." + str(item.gid)
            annotationObj["name"] = str(nomeGold)
            annotationList.append(annotationObj)
            
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap, bid = bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).all()
        for user in userz:
            user = user.uid
            if user and user not in users:
                users.append(user)
                annotationObj = {}
                annotationObj["id"] = "uid." + str(user)
                annotationObj["name"] = "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)
                annotationList.append(annotationObj)
    
    return jsonify({'annotation': annotationList})

@app.route('/pre_annotator', methods=['GET','POST'])
@login_required
def pre_annotator():
    form = PreAnnotatorForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1]       
        # Gets all the words involveded in the book bid and chapter cap
        words_id = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()
        words = [Terminology.query.filter_by(tid=word_id.tid).first().lemma for word_id in words_id]
        conll_obj = Conll.query.filter_by(bid=bid, cap=cap).first()
        conll_processed = conll_obj.conll_processed
        conll = utils.conll_annotation(conll_obj.conll)
        sentences = bookStructure.query.filter_by(bid=bid).all()
        sentences = [x.sentence for x in sentences if x.section.startswith(cap)]
        conll_processed, sentList, tok_to_concept, concept_to_tok = conll_processor_2.conll_processor(conll_processed, 'PROVA', sentences, words)
        #utils.parse_tokToConcept(conll, words)
        #print(tokToConcept)
        parObj = partialAnnotations.query.filter_by(uid = current_user.uid, bid = bid, cap = cap).first()
        if (parObj):
            return render_template("annotator.html", file = {'bid': bid, 'cap': cap, 'concepts': words, 'conll': conll, 'json': parObj.annotation, 'tagged': conll_processed, 'concepts': words, 'tok_to_concept': tok_to_concept, 'concept_to_tok': concept_to_tok, 'sent': sentList})
        return render_template("annotator.html", file = {'bid': bid, 'cap': cap, 'concepts': words,  'conll': conll, 'tagged': conll_processed, 'concepts': words, 'tok_to_concept': tok_to_concept, 'concept_to_tok': concept_to_tok, 'sent': sentList})
    return render_template('pre_annotator.html', form=form)

@app.route('/annotation_upload', methods=['POST'])
@login_required
def annotation_upload():
    req = request.get_json()
    delAnnotation = partialAnnotations.query.filter_by(uid=current_user.uid, bid=req["bid"], cap=req["cap"]).first()
    if(delAnnotation):
        db.session.delete(delAnnotation)
    parAnnotation = partialAnnotations(uid=current_user.uid, bid=req["bid"], cap=req["cap"], annotation=req["data"])
    db.session.add(parAnnotation)
    db.session.commit()
    message = "The partial annotation was added to the Database"
    res = make_response(jsonify(message))
    return res

@app.route('/final_annotation_upload', methods=['POST'])
@login_required
def final_annotation_upload():
    req = request.get_json()
    delAnnotation = partialAnnotations.query.filter_by(uid=current_user.uid, bid=req["bid"], cap=req["cap"]).first()
    if(delAnnotation):
        db.session.delete(delAnnotation)
    aidAnnotations = Annotations.query.filter_by(bid=req["bid"], cap=req["cap"]).all()
    for item in aidAnnotations:
        delAnnotationUsr = Annotation_user.query.filter_by(aid=item.aid, uid=current_user.uid).first()
        if (delAnnotationUsr):
            db.session.delete(delAnnotationUsr)
    print(req["data"])
    utils.upload_Annotation(json.loads(req["data"]), req["bid"], req["cap"], current_user.uid)
    message = "The annotation was added to the Database"
    res = make_response(jsonify(message))
    return res


@app.route('/annotator')
@login_required
def annotator():
    return render_template("annotator.html")

@app.route('/matrix')
@login_required
def matrix():
    return render_template("matrix.html")

@app.route('/comparison_result')
@login_required 
def comparison_result():
    return render_template("comparison_result.html")
    

@app.route('/arc_diagram')
@login_required
def arc_diagram():
    return render_template("arc_diagram.html")

@app.route('/simple_graph')
@login_required
def simple_graph():
    return render_template("simple_graph.html")

@app.route('/bezier_graph')
@login_required
def bezier_graph():
    return render_template("bezier_graph.html")

@app.route('/gantt')
@login_required
def gantt():
    return render_template("gantt.html")


@app.route('/pre_visualization', methods=['GET','POST'])
@login_required
def pre_visualization():
    form = PreVisualizationForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    
    user_list = []
    #form.author.choices = []
    annotations = Annotations.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    for relationship in annotations:
        users_annotations = Annotation_user.query.filter_by(aid = relationship.aid).all()
        for poss_user in users_annotations:
            if poss_user.uid not in user_list:
                user_list.append(poss_user.uid)
                user = User.query.filter_by(uid = poss_user.uid).first()
                form.author.choices.append(("uid." + str(user.uid), "Annotazione di: " + str(user.name)+ " " + str(user.surname)))
    
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname + " "
        form.author.choices.append(("gold." + str(item.gid), "Annotazione gold di: " + str(nomeGold)))
    
             
        
    
    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1] 
        words_tid = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()           
        words = [Terminology.query.filter_by(tid=word.tid).first().lemma for word in words_tid]
        sentences = bookStructure.query.filter_by(bid=bid).all()
        sentences = [sentence for sentence in sentences if str(sentence.section).startswith(str(cap) + ".")]
        conll = Conll.query.filter_by(bid=bid, cap=cap).first().conll
            
        if form.visualization_type.data == "1":
            if("gold" in str(form.author.data)):
                dfAnnotation, df, metrics, words = utils.create_dfAnnotation(bid, cap, form.author.data, conll, words)
                metrics = utils.process_for_matrix_gold(dfAnnotation, df, form.author.data, words)
            else:
                dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.author.data)
                metrics = utils.process_for_matrix(dfAnnotation, df, form.author.data, words)
            return render_template('matrix.html', file=metrics)
        elif form.visualization_type.data == "2":
            if("gold" in str(form.author.data)):
                dfAnnotation, df, metrics, words = utils.create_dfAnnotation(bid, cap, form.author.data, conll, words)
                metrics = utils.process_for_matrix_gold(dfAnnotation, df, form.author.data, words)
            else:
                dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.author.data)
                metrics = utils.process_for_matrix(dfAnnotation, df, form.author.data, words)
            return render_template('arc_diagram.html', file=metrics)
        elif form.visualization_type.data == "3":
           if("gold" in str(form.author.data)):
                dfAnnotation, df, metrics, words = utils.create_dfAnnotation(bid, cap, form.author.data, conll, words)
                metrics = utils.process_for_matrix_gold(dfAnnotation, df, form.author.data, words)
           else:
                dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.author.data)
                metrics = utils.process_for_matrix(dfAnnotation, df, form.author.data, words)
           return render_template('simple_graph.html', file=metrics)
        elif form.visualization_type.data == "4":
            if("gold" in str(form.author.data)):
                dfAnnotation, df, metrics, words = utils.create_dfAnnotation(bid, cap, form.author.data, conll, words)
                metrics = utils.process_for_matrix_gold(dfAnnotation, df, form.author.data, words)
            else:
                dfAnnotation, df, metrics, words = utils.data_analysis(conll, words, sentences, bid, cap, form.author.data)
                metrics = utils.process_for_matrix(dfAnnotation, df, form.author.data, words)
            return render_template('bezier_graph.html', file=metrics)
        elif form.visualization_type.data == "5":
            return redirect(url_for('gantt'))
    return render_template('pre_visualization.html', form=form)

@app.route('/visualization/<book>')
@login_required
def get_authors(book):
    bid = book.split(",")[0]
    cap = book.split(",")[1]
    user_list = []
    annotationList = []
        
    #Get gold annotation
    annotationGold = goldStandard.query.filter_by(cap = cap, bid = bid).all()
    for item in annotationGold:
        nomeGold = ""
        listaUids = item.uids.split(" ")
        listaUids = [uid for uid in listaUids if uid]
        for uid in listaUids:
            user = User.query.filter_by(uid=uid.split(".")[1]).first()
            nomeGold += user.name + " " + user.surname + " "
        annotationObj = {}
        annotationObj["id"] = "gold." + str(item.gid)
        annotationObj["name"] = "Annotazione gold di: " + str(nomeGold)
        annotationList.append(annotationObj)
            
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap, bid = bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).all()
        for user in userz:
            user = user.uid
            if user and user not in users:
                users.append(user)
                annotationObj = {}
                annotationObj["id"] = "uid." + str(user)
                annotationObj["name"] = "Annotazione di: " + str(User.query.filter_by(uid=user).first().name) + " " + str(User.query.filter_by(uid=user).first().surname)
                annotationList.append(annotationObj)
        
    return jsonify({'annotation': annotationList})

@app.route('/linguistic_analysis')
@login_required
def linguistic_analysis():
    return render_template("linguistic_analysis.html")

@app.route('/data_summary')
@login_required
def data_summary():
    return render_template("data_summary.html")

@app.route('/agreement')
@login_required
def agreement():
    return render_template("agreement.html")

@app.route('/visualization')
@login_required
def visualization():
    return render_template("visualization.html")  

@app.route('/gold_standard', methods=['GET','POST'])
@login_required
def gold_standard():
    form = GoldStandardForm()
    cap_lista = Conll.query.all()
    form.book_cap.choices = [(str(str(cap.bid) + ',' + str(cap.cap)), ("Title: " + (db.session.query(Book.title).join(Conll, cap.bid == Book.bid).first()).title + "-- Chapter: " + str(cap.cap))) for cap in cap_lista]
    
    user_list = []
    #form.author.choices = []
    annotations = Annotations.query.filter_by(cap = cap_lista[0].cap, bid = cap_lista[0].bid).all()
    for relationship in annotations:
        users_annotations = Annotation_user.query.filter_by(aid = relationship.aid).all()
        for poss_user in users_annotations:
            if poss_user.uid not in user_list:
                user_list.append(poss_user.uid)
                user = User.query.filter_by(uid = poss_user.uid).first()
                form.annotation.choices.append(("uid." + str(user.uid), "Annotazione di: " + str(user.name) + " " + str(user.surname)))
                

    if form.validate_on_submit():
        value = form.book_cap.data.split(",")
        bid = value[0]
        cap = value[1]
        words_tid = Terminology_reference.query.filter_by(bid=bid, cap=cap).all()           
        sentences = bookStructure.query.filter_by(bid=bid).all()
        sentences = [sentence for sentence in sentences if str(sentence.section).startswith(str(cap) + ".")]
        conll = Conll.query.filter_by(bid=bid, cap=cap).first().conll
        words = [Terminology.query.filter_by(tid=word.tid).first().lemma for word in words_tid]
        uids = request.form.getlist('annotation')
        df = utils.create_gold(uids, bid, cap, words, conll, sentences)
        uids_lista = ""
        for uid in uids:
            uids_lista += uid + " "
        goldStd = goldStandard(bid=bid, cap=cap, uids=uids_lista, gold=df)
        db.session.add(goldStd)
        db.session.commit()
        flash("The gold has been created!", "succes")
        return render_template('gold_standard.html', form=form)
    return render_template('gold_standard.html', form=form)

@app.route('/gold_standard/<book>')
@login_required
def get_annotations(book):
    bid = book.split(",")[0]
    cap = book.split(",")[1]
    annotationList = []
    #Get users annotation
    annotationRel = Annotations.query.filter_by(cap = cap, bid = bid).all()
    users = []
    for annotations in annotationRel:
        userz = Annotation_user.query.filter_by(aid = annotations.aid).first()
        if userz and userz.uid not in users:
                users.append(userz.uid)
                annotationObj = {}
                annotationObj["id"] = "uid." + str(userz.uid)
                annotationObj["name"] = "Annotazione di: " + str(User.query.filter_by(uid=userz.uid).first().name) + " " + str(User.query.filter_by(uid=userz.uid).first().surname)
                annotationList.append(annotationObj)
        
    return jsonify({'annotation': annotationList})

@app.route('/guidelines')
@login_required
def guidelines():
    return render_template("guidelines.html")
    

@app.route('/text_upload', methods=['GET'])
@login_required
def text_upload():
    return render_template('text_upload.html')

@app.route("/text_upload", methods=['POST'])
def email_process():
    
    req = request.get_json()
    book = Book.query.filter_by(title=req["book"], year=req["year"]).first()
    if book:
        
        book_structure = bookStructure.query.filter_by(bid=book.bid, section=req["cap"]).first()
        if book_structure:
            message = "This chapter was already in the Database"
            res = make_response(jsonify(message))
            return res
    
    
    conll = utils.conll_gen(req["text"])
    idPhrase = utils.id_phrase(conll, req["result"])
    
    
    if(len(idPhrase) == len(req["result"])):
        
        
        # check if someone already register the book
        book = Book.query.filter_by(title=req["book"], year=req["year"]).first()
        if not book:
            # Add book to database
            book = Book(title=req["book"], year=req["year"], category=req["category"])
            db.session.add(book)
            db.session.commit()
            
            # Add authors to database
            authors = req["author"].split(",")
            for name in authors:
                author = Author(name=name, books=book)
                db.session.add(author)
                db.session.commit()
        else:
            # the email exists
            pass
        
        book_structure = bookStructure.query.filter_by(bid=book.bid, section=req["cap"]).first()
        if not book_structure:
            # Add structure to database
            book_structure = bookStructure(bid=book.bid, section=req["cap"], uid = current_user.uid, sentence = 1)
            db.session.add(book_structure)
            db.session.commit()
        
            for i, phrase in enumerate(req["result"]):
                curr_section = re.search(r'(\d*\.\d*)*', phrase).group()
                book_structure = bookStructure(bid=book.bid, section=curr_section, sentence = str(idPhrase[i]), loader = current_user)
                db.session.add(book_structure)
                db.session.commit()
        
        # get the processed conll
            conll_processed = utils.processConll(conll, book.bid)
    
        # Add connl to database
            conll = Conll(bid=book.bid, cap=req["cap"], conll=conll, conll_processed=conll_processed)       
            db.session.add(conll)
            db.session.commit() 
        
        else:
            # The book cap is already in the DB 
            message = "This chapter was already in the Database"
            res = make_response(jsonify(message))
            return res
    
        message = "The chapter and the annotation was added to the Database"
        res = make_response(jsonify(message))
        return res
    else:
        message = "There was a problem with the chapter identification"
        res = make_response(jsonify(message))
        return res
    #     if (request.method == 'POST'):
#        data = request.form
##       data = data["book"]
       
#        return render_template("result.html",result = data)

def load(method):
    global th
    global finished
    finished = False
    th = Thread(method, args=())
    th.start()
    flash("Baseline method completed", "success")
    return render_template('index.html')


@app.route('/result')
def result():
    """ Just give back the result of your heavy work """
    return 'Done'


@app.route('/status')
def thread_status():
    """ Return the status of the worker thread """
    return jsonify(dict(status=('finished' if finished else 'running')))
