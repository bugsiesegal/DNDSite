import os
import random
from math import tanh
from flask import jsonify

import bcrypt
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user, current_user
from flask_dance.contrib.discord import make_discord_blueprint, discord
from flask_dance.consumer import oauth_authorized
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "0"
os.environ["OAUTHLIB_IGNORE_SCOPE_CHANGE"] = "0"

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'sqlite:///project.db')

# Replace CLIENT_ID and CLIENT_SECRET with your Discord app's values
CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.environ.get('REDIRECT_URL')

# Set up Discord OAuth2 with Flask-Dance
discord_blueprint = make_discord_blueprint(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scope=["identify", "guilds"],
    redirect_url=DISCORD_REDIRECT_URI,  # Update with your app's URL
)
app.register_blueprint(discord_blueprint, url_prefix="/login")
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return UserModel.query.get(int(user_id))


# Models

class AttackModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Set default value to 1
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    damage_modifier_stat = db.Column(db.String)
    damage_modifier_multiplier = db.Column(db.Float)
    accuracy = db.Column(db.Float)
    damage = db.Column(db.Float)
    number_of_targets = db.Column(db.Integer)

    skill_id = db.Column(db.Integer, db.ForeignKey('skill_model.id'))


class SkillModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Set default value to 1
    name = db.Column(db.Text)
    description = db.Column(db.Text)

    bonus_strength = db.Column(db.Float)
    bonus_dexterity = db.Column(db.Float)
    bonus_constitution = db.Column(db.Float)
    bonus_intelligence = db.Column(db.Float)
    bonus_wisdom = db.Column(db.Float)
    bonus_charisma = db.Column(db.Float)

    multiplier_strength = db.Column(db.Float)
    multiplier_dexterity = db.Column(db.Float)
    multiplier_constitution = db.Column(db.Float)
    multiplier_intelligence = db.Column(db.Float)
    multiplier_wisdom = db.Column(db.Float)
    multiplier_charisma = db.Column(db.Float)

    skill_cost = db.Column(db.Integer)

    actions = db.relationship('AttackModel', backref='skills', lazy=True)


class EntityModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Set default value to 1
    name = db.Column(db.Text)
    description = db.Column(db.Text)

    level = db.Column(db.Integer)
    experience = db.Column(db.Integer)
    unassigned_stat_points = db.Column(db.Integer)

    base_strength = db.Column(db.Float)
    base_dexterity = db.Column(db.Float)
    base_constitution = db.Column(db.Float)
    base_intelligence = db.Column(db.Float)
    base_wisdom = db.Column(db.Float)
    base_charisma = db.Column(db.Float)

    bonus_strength = db.Column(db.Float)
    bonus_dexterity = db.Column(db.Float)
    bonus_constitution = db.Column(db.Float)
    bonus_intelligence = db.Column(db.Float)
    bonus_wisdom = db.Column(db.Float)
    bonus_charisma = db.Column(db.Float)

    multiplier_strength = db.Column(db.Float)
    multiplier_dexterity = db.Column(db.Float)
    multiplier_constitution = db.Column(db.Float)
    multiplier_intelligence = db.Column(db.Float)
    multiplier_wisdom = db.Column(db.Float)
    multiplier_charisma = db.Column(db.Float)

    health = db.Column(db.Float)
    max_health = db.Column(db.Float)

    health_regen = db.Column(db.Float)
    max_health_regen = db.Column(db.Float)

    evasion = db.Column(db.Float)
    max_evasion = db.Column(db.Float)

    psi = db.Column(db.Float)
    max_psi = db.Column(db.Float)

    psi_regen = db.Column(db.Float)
    max_psi_regen = db.Column(db.Float)

    skills = db.relationship('SkillModel', secondary='entity_skill',
                             backref=db.backref('entities', lazy='dynamic'))

    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=True)


entity_skill = db.Table('entity_skill',
                        db.Column('entity_id', db.Integer, db.ForeignKey('entity_model.id')),
                        db.Column('skill_id', db.Integer, db.ForeignKey('skill_model.id')))

players_games = db.Table('players_games',
                         db.Column('user_id', db.Integer, db.ForeignKey('user_model.id')),
                         db.Column('game_id', db.Integer, db.ForeignKey('game_model.id')))

games_entities = db.Table(
    'games_entities',
    db.Column('game_id', db.Integer, db.ForeignKey('game_model.id'), primary_key=True),
    db.Column('entity_id', db.Integer, db.ForeignKey('entity_model.id'), primary_key=True)
)


class GameModel(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_name = db.Column(db.String, unique=True, nullable=False)
    discord_guild_id = db.Column(db.String, nullable=True)
    creator_id = db.Column(db.Integer)

    players = db.relationship('UserModel', secondary=players_games,
                              backref=db.backref('games', lazy='dynamic'))

    entities = db.relationship('EntityModel', secondary=games_entities,
                               backref=db.backref('games', lazy='dynamic'))

    def get_players(self):
        print(self.players[0])
        return self.players


class UserModel(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String, unique=True, nullable=False)
    username = db.Column(db.String, nullable=False)
    discriminator = db.Column(db.String, nullable=False)
    avatar_url = db.Column(db.String, nullable=True)
    player_entity = db.relationship('EntityModel', backref='owner', lazy=True, uselist=False)

    def __repr__(self):
        return f'<User {self.username}>'


# DND stuff
def attack(attacker: EntityModel, defender: EntityModel, attack_type: AttackModel):
    # Calculate the attacker's stat value based on the attack's damage modifier stat
    if attack_type.damage_modifier_stat == "strength":
        stat_value = attacker.base_strength * attacker.multiplier_strength + attacker.bonus_strength
    elif attack_type.damage_modifier_stat == "dexterity":
        stat_value = attacker.base_dexterity * attacker.multiplier_dexterity + attacker.bonus_dexterity
    elif attack_type.damage_modifier_stat == "constitution":
        stat_value = attacker.base_constitution * attacker.multiplier_constitution + attacker.bonus_constitution
    elif attack_type.damage_modifier_stat == "intelligence":
        stat_value = attacker.base_intelligence * attacker.multiplier_intelligence + attacker.bonus_intelligence
    elif attack_type.damage_modifier_stat == "wisdom":
        stat_value = attacker.base_wisdom * attacker.multiplier_wisdom + attacker.bonus_wisdom
    elif attack_type.damage_modifier_stat == "charisma":
        stat_value = attacker.base_charisma * attacker.multiplier_charisma + attacker.bonus_charisma
    else:
        raise ValueError("Invalid damage_modifier_stat value.")

    # Calculate the attack's damage
    attack_damage = attack_type.damage + stat_value * attack_type.damage_modifier_multiplier

    # Calculate the chance of the attack hitting the target
    hit_chance = attack_type.accuracy * defender.evasion

    # Check if the attack hits
    if random.random() < hit_chance:
        defender.health -= attack_damage
        if defender.health < 0:
            defender.health = 0
        return f"{attacker.name} attacked {defender.name} with {attack_type.name}, dealing {attack_damage} damage!"
    else:
        return f"{attacker.name} missed {defender.name} with {attack_type.name}!"


# Forms
class CreateGameForm(FlaskForm):
    game_name = StringField('Game Name', validators=[DataRequired(), Length(min=2, max=50)])
    discord_guild_id = StringField("Guild Id", validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Create Game')


# Website

@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        name = request.form['name']
        description = request.form['description']
        damage_modifier_stat = request.form['damage_modifier_stat']
        damage_modifier_multiplier = request.form['damage_modifier_multiplier']
        accuracy = request.form['accuracy']
        damage = request.form['damage']
        number_of_targets = request.form['number_of_targets']

        new_ability = AttackModel(name=name, description=description,
                                  damage_modifier_stat=damage_modifier_stat,
                                  damage_modifier_multiplier=damage_modifier_multiplier,
                                  accuracy=accuracy, damage=damage,
                                  number_of_targets=number_of_targets)
        db.session.add(new_ability)
        db.session.commit()

    attacks = AttackModel.query.all()

    skills = SkillModel.query.all()

    entities = EntityModel.query.all()

    return render_template("admin.html", attacks=attacks, skills=skills, entities=entities)


@app.route('/add_skill', methods=["POST"])
def add_skill():
    name = request.form['name']
    description = request.form['description']
    bonus_strength = request.form['bonus_strength']
    bonus_dexterity = request.form['bonus_dexterity']
    bonus_constitution = request.form['bonus_constitution']
    bonus_intelligence = request.form['bonus_intelligence']
    bonus_wisdom = request.form['bonus_wisdom']
    bonus_charisma = request.form['bonus_charisma']
    multiplier_strength = request.form['multiplier_strength']
    multiplier_dexterity = request.form['multiplier_dexterity']
    multiplier_constitution = request.form['multiplier_constitution']
    multiplier_intelligence = request.form['multiplier_intelligence']
    multiplier_wisdom = request.form['multiplier_wisdom']
    multiplier_charisma = request.form['multiplier_charisma']
    skill_cost = request.form['skill_cost']
    attack_ids = request.form.getlist('attacks[]')
    attacks = AttackModel.query.filter(AttackModel.id.in_(attack_ids)).all()

    new_skill = SkillModel(name=name, description=description, bonus_strength=bonus_strength,
                           bonus_dexterity=bonus_dexterity, bonus_constitution=bonus_constitution,
                           bonus_intelligence=bonus_intelligence, bonus_wisdom=bonus_wisdom,
                           bonus_charisma=bonus_charisma, multiplier_strength=multiplier_strength,
                           multiplier_dexterity=multiplier_dexterity, multiplier_constitution=multiplier_constitution,
                           multiplier_intelligence=multiplier_intelligence, multiplier_wisdom=multiplier_wisdom,
                           multiplier_charisma=multiplier_charisma, skill_cost=skill_cost, actions=attacks)

    db.session.add(new_skill)
    db.session.commit()

    return redirect(url_for('admin'))


@app.route('/add_entity', methods=["POST"])
def add_entity():
    name = request.form['name']
    description = request.form['description']
    level = int(request.form['level'])
    experience = int(request.form['experience'])
    unassigned_stat_points = int(request.form['unassigned_stat_points'])
    base_strength = float(request.form['base_strength'])
    base_dexterity = float(request.form['base_dexterity'])
    base_constitution = float(request.form['base_constitution'])
    base_intelligence = float(request.form['base_intelligence'])
    base_wisdom = float(request.form['base_wisdom'])
    base_charisma = float(request.form['base_charisma'])

    skill_ids = request.form.getlist('skills[]')
    skills = SkillModel.query.filter(SkillModel.id.in_(skill_ids)).all()

    # Calculate the total bonuses and multipliers from skills
    total_bonus_strength = 0
    total_bonus_dexterity = 0
    total_bonus_constitution = 0
    total_bonus_intelligence = 0
    total_bonus_wisdom = 0
    total_bonus_charisma = 0

    total_multiplier_strength = 1
    total_multiplier_dexterity = 1
    total_multiplier_constitution = 1
    total_multiplier_intelligence = 1
    total_multiplier_wisdom = 1
    total_multiplier_charisma = 1

    for skill in skills:
        total_bonus_strength += skill.bonus_strength
        total_bonus_dexterity += skill.bonus_dexterity
        total_bonus_constitution += skill.bonus_constitution
        total_bonus_intelligence += skill.bonus_intelligence
        total_bonus_wisdom += skill.bonus_wisdom
        total_bonus_charisma += skill.bonus_charisma

        total_multiplier_strength += skill.multiplier_strength
        total_multiplier_dexterity += skill.multiplier_dexterity
        total_multiplier_constitution += skill.multiplier_constitution
        total_multiplier_intelligence += skill.multiplier_intelligence
        total_multiplier_wisdom += skill.multiplier_wisdom
        total_multiplier_charisma += skill.multiplier_charisma

    health = base_constitution * total_multiplier_constitution + total_bonus_constitution
    max_health = base_constitution * total_multiplier_constitution + total_bonus_constitution

    health_regen = (tanh(((base_constitution * total_multiplier_constitution +
                           total_bonus_constitution - 100) / 50)) + 1) / 2
    max_health_regen = (tanh(((base_constitution * total_multiplier_constitution +
                               total_bonus_constitution - 100) / 50)) + 1) / 2

    evasion = 1 - (tanh(((base_dexterity * total_multiplier_dexterity + total_bonus_dexterity) * 0.01) - 2) + 1) / 2
    max_evasion = 1 - (tanh(((base_dexterity * total_multiplier_dexterity + total_bonus_dexterity) * 0.01) - 2) + 1) / 2

    psi = base_intelligence * total_multiplier_intelligence + total_bonus_intelligence
    max_psi = base_intelligence * total_multiplier_intelligence + total_bonus_intelligence

    psi_regen = (tanh(((base_intelligence * total_multiplier_intelligence +
                        total_bonus_intelligence - 100) / 50)) + 1) / 2
    max_psi_regen = (tanh(((base_intelligence * total_multiplier_intelligence +
                            total_bonus_intelligence - 100) / 50)) + 1) / 2

    new_entity = EntityModel(name=name, description=description, level=level,
                             experience=experience, unassigned_stat_points=unassigned_stat_points,
                             base_strength=base_strength, base_dexterity=base_dexterity,
                             base_constitution=base_constitution, base_intelligence=base_intelligence,
                             base_wisdom=base_wisdom, base_charisma=base_charisma, skills=skills,
                             bonus_strength=total_bonus_strength, bonus_dexterity=total_bonus_dexterity,
                             bonus_constitution=total_bonus_constitution, bonus_intelligence=total_bonus_intelligence,
                             bonus_wisdom=total_bonus_wisdom, bonus_charisma=total_bonus_charisma,
                             multiplier_strength=total_multiplier_strength,
                             multiplier_dexterity=total_multiplier_dexterity,
                             multiplier_constitution=total_multiplier_constitution,
                             multiplier_intelligence=total_multiplier_intelligence,
                             multiplier_wisdom=total_multiplier_wisdom, multiplier_charisma=total_multiplier_charisma,
                             health=health, max_health=max_health, health_regen=health_regen,
                             max_health_regen=max_health_regen, evasion=evasion, max_evasion=max_evasion,
                             psi=psi, max_psi=max_psi, psi_regen=psi_regen, max_psi_regen=max_psi_regen
                             )

    db.session.add(new_entity)
    db.session.commit()

    return redirect(url_for('admin'))


@app.route('/create-entity', methods=['GET', 'POST'])
@login_required
def create_entity():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        level = int(request.form['level'])
        experience = int(request.form['experience'])
        unassigned_stat_points = int(request.form['unassigned_stat_points'])
        base_strength = float(request.form['base_strength'])
        base_dexterity = float(request.form['base_dexterity'])
        base_constitution = float(request.form['base_constitution'])
        base_intelligence = float(request.form['base_intelligence'])
        base_wisdom = float(request.form['base_wisdom'])
        base_charisma = float(request.form['base_charisma'])

        skill_ids = request.form.getlist('skills[]')
        skills = SkillModel.query.filter(SkillModel.id.in_(skill_ids)).all()

        # Calculate the total bonuses and multipliers from skills
        total_bonus_strength = 0
        total_bonus_dexterity = 0
        total_bonus_constitution = 0
        total_bonus_intelligence = 0
        total_bonus_wisdom = 0
        total_bonus_charisma = 0

        total_multiplier_strength = 1
        total_multiplier_dexterity = 1
        total_multiplier_constitution = 1
        total_multiplier_intelligence = 1
        total_multiplier_wisdom = 1
        total_multiplier_charisma = 1

        for skill in skills:
            total_bonus_strength += skill.bonus_strength
            total_bonus_dexterity += skill.bonus_dexterity
            total_bonus_constitution += skill.bonus_constitution
            total_bonus_intelligence += skill.bonus_intelligence
            total_bonus_wisdom += skill.bonus_wisdom
            total_bonus_charisma += skill.bonus_charisma

            total_multiplier_strength += skill.multiplier_strength
            total_multiplier_dexterity += skill.multiplier_dexterity
            total_multiplier_constitution += skill.multiplier_constitution
            total_multiplier_intelligence += skill.multiplier_intelligence
            total_multiplier_wisdom += skill.multiplier_wisdom
            total_multiplier_charisma += skill.multiplier_charisma

        health = base_constitution * total_multiplier_constitution + total_bonus_constitution
        max_health = base_constitution * total_multiplier_constitution + total_bonus_constitution

        health_regen = (tanh(((base_constitution * total_multiplier_constitution +
                               total_bonus_constitution - 100) / 50)) + 1) / 2
        max_health_regen = (tanh(((base_constitution * total_multiplier_constitution +
                                   total_bonus_constitution - 100) / 50)) + 1) / 2

        evasion = 1 - (tanh(((base_dexterity * total_multiplier_dexterity + total_bonus_dexterity) * 0.01) - 2) + 1) / 2
        max_evasion = 1 - (
                tanh(((base_dexterity * total_multiplier_dexterity + total_bonus_dexterity) * 0.01) - 2) + 1) / 2

        psi = base_intelligence * total_multiplier_intelligence + total_bonus_intelligence
        max_psi = base_intelligence * total_multiplier_intelligence + total_bonus_intelligence

        psi_regen = (tanh(((base_intelligence * total_multiplier_intelligence +
                            total_bonus_intelligence - 100) / 50)) + 1) / 2
        max_psi_regen = (tanh(((base_intelligence * total_multiplier_intelligence +
                                total_bonus_intelligence - 100) / 50)) + 1) / 2

        new_entity = EntityModel(name=name, description=description, level=level,
                                 experience=experience, unassigned_stat_points=unassigned_stat_points,
                                 base_strength=base_strength, base_dexterity=base_dexterity,
                                 base_constitution=base_constitution, base_intelligence=base_intelligence,
                                 base_wisdom=base_wisdom, base_charisma=base_charisma, skills=skills,
                                 bonus_strength=total_bonus_strength, bonus_dexterity=total_bonus_dexterity,
                                 bonus_constitution=total_bonus_constitution,
                                 bonus_intelligence=total_bonus_intelligence,
                                 bonus_wisdom=total_bonus_wisdom, bonus_charisma=total_bonus_charisma,
                                 multiplier_strength=total_multiplier_strength,
                                 multiplier_dexterity=total_multiplier_dexterity,
                                 multiplier_constitution=total_multiplier_constitution,
                                 multiplier_intelligence=total_multiplier_intelligence,
                                 multiplier_wisdom=total_multiplier_wisdom,
                                 multiplier_charisma=total_multiplier_charisma,
                                 health=health, max_health=max_health, health_regen=health_regen,
                                 max_health_regen=max_health_regen, evasion=evasion, max_evasion=max_evasion,
                                 psi=psi, max_psi=max_psi, psi_regen=psi_regen, max_psi_regen=max_psi_regen,
                                 user_id=current_user.id
                                 )

        db.session.add(new_entity)
        db.session.commit()
        flash('Entity created successfully')
        return redirect(url_for('index'))

    skills = SkillModel.query.all()

    return render_template('create_entity.html', skills=skills)


class AddEntityForm(FlaskForm):
    entity = SelectField('Non-Player Entity', validators=[DataRequired()])
    submit = SubmitField('Add Entity')

class RemoveEntityForm(FlaskForm):
    entity = SelectField('Non-Player Entity', validators=[DataRequired()])
    submit = SubmitField('Remove Entity')



@app.route('/attack', methods=['POST'])
@login_required
def perform_attack():
    attacker = current_user.player_entity
    defender_id = request.form.get('defender_id')
    attack_id = request.form.get('attack_id')

    defender = EntityModel.query.get(defender_id)
    attack_type = AttackModel.query.get(attack_id)

    if attacker and defender and attack:
        result = attack(attacker, defender, attack_type)
        db.session.commit()
        flash(result)

        if 'attack_logs' not in session:
            session['attack_logs'] = []

        session['attack_logs'].append(result)
        session.modified = True

        return redirect(url_for('game_players'))
    else:
        flash("Error: attacker, defender, or attack not found")


@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if not discord.authorized:
        print(1)
        return redirect(url_for('discord.login'))
    else:
        account_info = discord.get('/api/users/@me')
        print("account_info:", account_info.json())  # Debugging line
        if account_info.ok:
            user_data = account_info.json()
            print("user_data:", user_data)  # Debugging line
            user_id = user_data['id']
            user = UserModel.query.filter_by(discord_id=user_id).first()

            if user is not None:
                login_user(user)
                flash("Logged in successfully.", category="success")
                return redirect(url_for('index'))
            else:
                flash("Error: user not found in the database.", category="error")
                return redirect(url_for('discord.login'))
        else:
            flash("Error: could not fetch user information from Discord.", category="error")
            return redirect(url_for('login'))

    return render_template('login.html')


@oauth_authorized.connect_via(discord_blueprint)
def discord_logged_in(blueprint, token):
    resp = blueprint.session.get('/api/users/@me')
    print(resp)
    if not resp.ok:
        flash('Failed to fetch user information from Discord')
        return False
    user_data = resp.json()
    print("user_data:", user_data)  # Debugging line

    # Fetch the user's guilds
    guilds_resp = blueprint.session.get('/api/users/@me/guilds')
    if not guilds_resp.ok:
        flash('Failed to fetch user guilds from Discord')
        return False
    guilds_data = guilds_resp.json()

    # Check if the user already exists in the database
    user = UserModel.query.filter_by(discord_id=user_data['id']).first()

    # If not, create a new user and store their information
    if not user:
        user = UserModel(
            discord_id=user_data['id'],
            username=user_data['username'],
            discriminator=user_data['discriminator'],
            avatar_url=f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
        )
        db.session.add(user)
        db.session.commit()

    # You can store the user's ID in the session to keep them logged in
    session['user_id'] = user.id

    if guilds_data:
        # Store the first guild's ID in the session
        print(guilds_data)
        session['guild_id'] = [guild['id'] for guild in guilds_data]


@app.route('/login/discord/authorized')
def authorized():
    resp = discord.authorized_response()
    print(resp)
    if resp is None or resp.get('access_token') is None:
        flash('Access denied: reason=%s error=%s' % (
            request.args['error'],
            request.args['error_description']
        ))
        return redirect(url_for('login'))

    session['discord_token'] = (resp['access_token'], '')
    user_data = discord.get('/users/@me').data
    print(user_data)

    # Add your logic for handling user_data here
    # (e.g., storing it in the database, creating a session, etc.)

    return redirect(url_for('index'))  # Replace 'dashboard' with the desired route after successful login


@app.route('/create-game', methods=['GET', 'POST'])
@login_required
def create_game():
    form = CreateGameForm()

    if form.validate_on_submit():
        game_name = form.game_name.data
        guild_id = form.discord_guild_id.data

        # Check if a game with the same name already exists
        existing_game = GameModel.query.filter_by(game_name=game_name).first()

        if existing_game:
            flash('A game with that name already exists')
            return redirect(url_for('create_game'))

        # Create the new game and add the creator as a player
        game = GameModel(game_name=game_name, creator_id=current_user.id, discord_guild_id=guild_id)
        game.players.append(current_user)
        db.session.add(game)
        db.session.commit()

        flash('Game created successfully')
        return redirect(url_for('index'))

    return render_template('create_game.html', form=form)


@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id', None)
    logout_user()
    return redirect(url_for('admin'))


@app.route('/select-game', methods=['POST'])
@login_required
def select_game():
    game_id = request.form.get('game_id')
    if game_id:
        session['selected_game_id'] = int(game_id)
        return redirect(url_for('game_players'))
    else:
        flash('Please select a game')
        return redirect(url_for('index'))


@app.route('/game-players')
@login_required
def game_players():
    game_id = session.get('selected_game_id')
    if game_id:
        game = GameModel.query.get(game_id)
        if game:
            players = game.get_players()
            entities = EntityModel.query.filter(EntityModel.user_id.is_(None)).all()
            player_entity = EntityModel.query.filter_by(user_id=current_user.id).first()
            attack_logs = session.get('attack_logs', [])

            form = AddEntityForm()
            form.entity.choices = [(entity.id, entity.name) for entity in EntityModel.query.filter(
                EntityModel.id.notin_([player.id for player in game.players])).all()]

            if form.validate_on_submit():
                entity_id = form.entity.data
                entity = EntityModel.query.get(entity_id)
                if entity:
                    game.entities.append(entity)
                    db.session.commit()
                    flash('Entity added successfully')
                else:
                    flash('Entity not found')

            remove_form = RemoveEntityForm()
            remove_form.entity.choices = [(entity.id, entity.name) for entity in game.entities]

            if remove_form.validate_on_submit():
                entity_id = remove_form.entity.data
                entity = EntityModel.query.get(entity_id)
                if entity:
                    game.entities.remove(entity)
                    db.session.commit()
                    flash('Entity removed successfully')
                else:
                    flash('Entity not found')

            return render_template('game_players.html', players=players, attack_logs=attack_logs,
                                   player_entity=player_entity, entities=entities, form=form, remove_form=remove_form)
        else:
            flash('Game not found')
            return redirect(url_for('index'))
    else:
        flash('Please select a game first')
        return redirect(url_for('index'))


@app.route('/get_updated_data')
def get_updated_data():
    # Query the updated data from your database (e.g., entities with their health)
    entities = [
        {
            'id': entity.id,
            'name': entity.name,
            'health': entity.health,
            'max_health': entity.max_health
        }
        for entity in EntityModel.query.all()
    ]

    # Return the data as JSON
    return jsonify({'entities': entities})


@app.route('/')
def index():
    if current_user.is_authenticated:
        games = current_user.games.all()
        entities = EntityModel.query.filter(EntityModel.user_id.is_(None)).all()
        player_entity = current_user.player_entity
        return render_template('index.html', games=games, entities=entities, player_entity=player_entity)
    else:
        return redirect(url_for('login'))


if app.debug:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
