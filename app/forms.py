# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from flask import flash, redirect, url_for
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, RadioField, FileField, SelectMultipleField
from wtforms.validators import InputRequired, Email, EqualTo, ValidationError, Optional
from flask_wtf.file import FileRequired, FileAllowed
from app.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    surname = StringField('Surname', validators=[InputRequired()])
    email = StringField('Email', validators =[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    repeat_password = PasswordField('Repeat Password', validators=[InputRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            flash("Email already used", "danger")
            raise ValidationError('')

class BaselineForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    baseline_method = SelectField('Baseline method', choices = [('1','Hyponyms/Hypernym/Meronyms '), ('2','Lexico-syntax patterns'), ('3','RefD'), ('4','Wikipedia pages'), ('5','TocDistance')])
    submit = SubmitField('Launch Method')
    
class GoldStandardForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    annotation = SelectMultipleField('Annotation', choices = [])
    submit = SubmitField('Launch Creation')
    
class AnalysisForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    annotation_1 = SelectField('Annotation/Method', choices = [])
    annotation_2 = SelectField('Annotation/Method', choices = [('Default', 'Choose an annotation or a method')], default='Default')
    analysis_type = SelectField('Type of Analysis', choices = [('1','Data Summary'), ('2','Linguistic Analysis'), ('3','Agreement Calculation')])
    submit = SubmitField('Launch Analysis')
    
class ComparisonForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    comparison_1 = SelectField('Item 1', choices = [])
    comparison_2 = SelectField('Item 2',choices = [])
    submit = SubmitField('Launch Comparison')
    
class PreAnnotatorForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    submit = SubmitField('Start')
    
class PreVisualizationForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    author = SelectField('Author', choices = [])
    visualization_type = SelectField('Type of Visualization', choices = [('1','Matrix'), ('2','Arc Diagram'), ('3','Simple Graph'), ('4','Bezier Graph'),('5','Gantt Graph')])
    submit = SubmitField('Launch Visualization')
    
class UploadTerminologyForm(FlaskForm):
    book_cap = SelectField('Book', choices = [])
    text = FileField('Text', validators=[
            FileRequired(),
            FileAllowed(['txt'], 'File txt only')
            ])
    submit = SubmitField('Upload')
    
    
            