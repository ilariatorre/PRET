#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 15:23:05 2019

@author: Andre
"""

from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    uid = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(128))
    surname = db.Column(db.String(128)) 
    email = db.Column(db.String(120), index = True, unique = True)
    psw = db.Column(db.String(128))
    books = db.relationship('bookStructure', backref='loader',
                            lazy='dynamic')

    
    def __repr__(self):
        return '<User {}>'.format(self.email)
    
    def set_password(self, password):
        self.psw = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.psw, password)
    
    def get_id(self):
           return (self.uid)
    

    
    
class bookStructure (db.Model):
    bid = db.Column(db.Integer, db.ForeignKey('book.bid'), primary_key = True)
    section = db.Column(db.String(20), primary_key = True)
    sentence = db.Column(db.Integer)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'))
    
    def __repr__(self):
        return '<Book_Structure {}>'.format(self.bid)
    
class Conll (db.Model):
    bid = db.Column(db.Integer, primary_key = True)
    cap = db.Column(db.Integer, primary_key = True)
    conll = db.Column(db.Text)
    conll_processed = db.Column(db.Text)
    
    def __repr__(self):
        return '<Conll {}>'.format(self.conll)
    
class Book (db.Model):
    bid = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(120))
    year = db.Column(db.Integer)
    category = db.Column(db.String(100))
    authors = db.relationship('Author', backref='books',
                            lazy='dynamic')
    
    
    def __repr__(self):
        return '<Book {}>'.format(self.title)
    
class Author (db.Model):
    bid = db.Column(db.Integer, db.ForeignKey('book.bid'), primary_key = True)
    name = db.Column(db.String(120), primary_key = True) 
    
    def __repr__(self):
        return '<Author {}>'.format(self.name)
    
class Terminology (db.Model):
    tid = db.Column(db.Integer, primary_key = True)
    lemma = db.Column(db.String(120), unique = True)
    wiki_url = db.Column(db.Text)
    
    def __repr__(self):
        return '<Terminology {}>'.format(self.lemma)
    
class Terminology_reference (db.Model):
    tid = db.Column(db.Integer, db.ForeignKey('terminology.tid'), primary_key = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'), primary_key = True)
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'), primary_key = True)
    
    def __repr__(self):
        return '<Terminology_reference {}>'.format(self.tid)
    
class Baseline_Methods (db.Model):
    lemma1 = db.Column(db.Integer, db.ForeignKey('terminology.tid'), primary_key = True)
    lemma2 = db.Column(db.Integer, db.ForeignKey('terminology.tid'), primary_key = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'), primary_key = True)
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'), primary_key = True)
    m1 = db.Column(db.Float)
    m2 = db.Column(db.Float)
    m2_sentence = db.Column(db.Integer)
    m3 = db.Column(db.Float)
    m4 = db.Column(db.Integer)
    m4a = db.Column(db.Float)
    m4b = db.Column(db.Float)
    m5 = db.Column(db.Float)
    
    def __repr__(self):
        return '<Baseline_Methods {}>'.format(self.lemma1)
    
class Annotation_user (db.Model):
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), primary_key = True)
    aid = db.Column(db.Integer, db.ForeignKey('annotations.aid'), primary_key = True)
    ann_type = db.Column(db.Integer, db.ForeignKey('annotation_types.tid'))
    
class Annotations (db.Model):
    aid = db.Column(db.Integer, primary_key = True)
    lemma1 = db.Column(db.Integer, db.ForeignKey('terminology.tid'), index = True)
    lemma2 = db.Column(db.Integer, db.ForeignKey('terminology.tid'), index = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'))
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'))
    id_phrase = db.Column(db.Integer)
    
class partialAnnotations (db.Model):
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), primary_key = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'))
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'))
    annotation = db.Column(db.Text)

class goldStandard (db.Model):
    gid = db.Column(db.Integer, primary_key = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'))
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'))
    uids = db.Column(db.String(120))
    gold =  db.Column(db.Text)
    
class User_Experience (db.Model):
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), primary_key = True)
    bid = db.Column(db.Integer, db.ForeignKey('conll.bid'))
    cap = db.Column(db.Integer, db.ForeignKey('conll.cap'))
    exp_type = db.Column(db.Integer, db.ForeignKey('experience_types.tid'))
    
class Annotation_types (db.Model):
    tid = db.Column(db.Integer, primary_key = True)
    ann_type = db.Column(db.String(64), unique = True)    
    
class Experience_types (db.Model):
    tid = db.Column(db.Integer, primary_key = True)
    exp_type = db.Column(db.String(64), unique = True) 
    