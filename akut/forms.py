from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

from akut.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('E-Mail',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    confirm_password = PasswordField('Passwort bestätigen',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrieren!')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username ist schon belegt, bitte einen anderen wählen.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('E-Mail ist schon belegt, bitte eine andere wählen.')


class LoginForm(FlaskForm):
    email = StringField('E-Mail',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    remember = BooleanField('Eingeloggt bleiben')
    submit = SubmitField('Login!')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Passwort-Reset beantragen')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Neues Passwort', validators=[DataRequired()])
    confirm_password = PasswordField('Neues Passwort bestätigen',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Passwort zurücksetzen')
