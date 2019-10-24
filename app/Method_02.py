# -*- coding: utf-8 -*-
"""
Created on Sun Jun 16 22:10:13 2019

@author: io
"""
import nltk;
from nltk.corpus import wordnet as wn;
from nltk.corpus import PlaintextCorpusReader
from app import db
from app.models import Baseline_Methods, Conll
from app.utils import id_phrase
from conllu import parse




class Method_2():
    """ Class for evaluating prerequisite relationship using 
        hyponyms, hypernyms and meronyms and lexical pattern"""
    
    lex_pattern = ["y such as a x", "such y as an x", "x is a y", "x is an y", "y includes x", "y includs x", "y including x", "x is called y", "x are called y", "x, one of y", "x and other y", "x or other y", "y consist of x", "y consists of x", "y like x", "y, specially x", "x in y", "x belong to y"]
    
    def __init__(self, words, conll, text, bid, cap):
        self.sentence = parse(conll)
        self.words = words
        self.text = text
        self.bid = bid
        self.cap = cap
        self.pre_req = dict.fromkeys(words)
        self.phrase_id = {}
        for word in self.pre_req:
            self.pre_req[word] = []


    def hyponyms(self, concept):
        """get a concept and takes all meanings from wordnet. Then gets all the hyponyms of 
            that word and check if it's inside the list words""" 
        meanings = wn.synsets(concept)
        for word in meanings:
            for types in word.hyponyms():
                for lemma in types.lemmas():
                    self.search_hypo(concept, lemma.name().lower())
    
    def hypernyms(self, concept):
        """ get a concept and takes all meanings from wordnet. Then gets all the hypernyms of 
            that word and check if it's inside the list words"""
        meanings = wn.synsets(concept)
        for word in meanings:
            for paths in (word.hypernym_paths()):
                for level in paths:
                    for lemma in level.lemmas():
                        self.search(concept, lemma.name().lower())
    
    def meronyms(self, concept):
        """ get a concept and takes all meanings from wordnet. Then gets all the different meronyms of 
            that word and check if it's inside the list words"""
        meanings = wn.synsets(concept)
        for word in meanings:
            for meronym in word.part_meronyms():
                for lemma in meronym.lemmas():
                    self.search(concept, lemma.name().lower())
            for meronym in word.substance_meronyms():
                for lemma in meronym.lemmas():
                    self.search(concept, lemma.name().lower())
            for meronym in word.member_holonyms():
                for lemma in meronym.lemmas():
                    self.search(concept, lemma.name().lower())
                    
    
    def search(self, concept, lemma):
        if(lemma in self.words):
            self.pre_req[concept].append(lemma)
            
    def search_hypo(self, concept, lemma):
        if(lemma in self.words):
            self.pre_req[lemma].append(concept)
    
    def pattern(self, word, prereq):
        for phrase in self.lex_pattern:
                phrase = phrase.replace("x", word)
                phrase = phrase.replace("y", prereq)
                result = self.text.find(phrase)
                if(result != -1):
                    sentence_id = self.id_to_sentence(result)
                    if (sentence_id not in list(self.phrase_id.values())):
                        self.pre_req[word].append(prereq)
                        self.phrase_id[word + "_" + prereq] = sentence_id
               
    def id_to_sentence(self, key):
        stop = 0
        for ids, phrase in enumerate(self.sentence):
            for words in phrase:
                stop += len(words["form"]) 
            if (stop > key):
                return ids
                 
            
        
    
    def populate_db(self, words, bid, cap):
        for concept in words:
            for lemma in [lemma for lemma in words if concept != lemma]:
                bs = Baseline_Methods.query.filter_by(bid=bid, cap=cap, lemma1=concept, lemma2=lemma).first()
                if not bs:
                    if lemma in self.pre_req[concept]:
                        try:
                            phrase = int(self.phrase_id[concept + "_" + lemma])
                        except:
                            phrase = 0
                        bs = Baseline_Methods(bid=bid, cap=cap, lemma1=concept, lemma2=lemma, m2=1, m2_sentence = phrase)
                        db.session.add(bs)
                    else:
                        bs = Baseline_Methods(bid=bid, cap=cap, lemma1=concept, lemma2=lemma, m2=0, m2_sentence = 0)
                        db.session.add(bs)
                else: 
                   if lemma in self.pre_req[concept]:
                       try:
                           phrase = int(self.phrase_id[concept + "_" + lemma])
                       except:
                           phrase = 0
                       bs.m2 = 1    
                       bs.m2_sentence = phrase
                   else:
                       bs.m2 = 0
                       bs.m2_sentence = 0
                       
        db.session.commit()

    def method_2(self):
        for word in self.words:
            self.hyponyms(word)
            self.hypernyms(word)
            self.meronyms(word)
            for prereq in [x for x in self.words if x != word]: 
                self.pattern(word, prereq)        
        
        print(self.phrase_id)
        self.populate_db(self.words, self.bid, self.cap)        
            
                
    
                
