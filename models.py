from main import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Simple association table, without additional info
user_event = db.Table('user_event',  # db.Model.metadata,
                      db.Column('user_id', db.String(64), db.ForeignKey('user.id'), primary_key=True),
                      db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True))


# It is an object because it contains additional info
class Team_User(db.Model):
    __tablename__ = 'team_user'
    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('team.id'), primary_key=True)
    user_id = db.Column(db.String(64), db.ForeignKey('user.id'), primary_key=True)
    moderator = db.Column(db.Boolean, unique=False, nullable=True)
    user = db.relationship("User", back_populates="member_teams")
    team = db.relationship("Team", back_populates="users")


class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_name = db.Column(db.String(64), unique=True)
    created = db.Column(db.DateTime)
    uses_worktime = db.Column(db.Boolean, unique=False, default=False)

    creator_id = db.Column(db.String(64), db.ForeignKey('user.id'))
    creator = db.relationship("User", back_populates="owned_teams")
    users = db.relationship("Team_User", back_populates="team", lazy='dynamic', cascade="all, delete")
    announcements = db.relationship('Announcement', back_populates='team', cascade="all, delete")
    schedules = db.relationship('Schedule', back_populates='team', lazy='dynamic', cascade="all, delete")
    worktimes = db.relationship('WorkTime', back_populates='team', cascade="all, delete")
    events = db.relationship('Event', back_populates='team', lazy='dynamic', cascade="all, delete")


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(64), primary_key=True)
    first_name = db.Column(db.String(50), unique=False)
    last_name = db.Column(db.String(50), unique=False, nullable=True)

    color_id = db.Column(db.Integer, db.ForeignKey('color.id'), nullable=True, unique=False)
    color = db.relationship('Color', back_populates="users")

    owned_teams = db.relationship("Team", back_populates="creator")
    member_teams = db.relationship("Team_User", back_populates="user")

    worktimes = db.relationship('WorkTime', back_populates='user', cascade="all, delete")
    announcements = db.relationship('Announcement', back_populates='creator', cascade="all, delete")
    schedules = db.relationship("Schedule", back_populates="user", cascade="all, delete")
    events = db.relationship("Event", secondary=user_event, lazy='dynamic', back_populates="users", cascade="all, delete")
    tokens = db.relationship('FCMToken', back_populates='user', lazy='dynamic', cascade="all, delete")



class WorkTime(db.Model):
    __tablename__ = 'work_time'
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime)
    stop = db.Column(db.DateTime, nullable=True)
    confirmed = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    user_id = db.Column(db.String(64), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship("User", back_populates="worktimes")

    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('team.id'), nullable=False)
    team = db.relationship("Team", back_populates="worktimes")


class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime)
    name = db.Column(db.String, nullable=False)
    info = db.Column(db.String, nullable=True)

    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('team.id'), nullable=False)
    team = db.relationship("Team", back_populates="events")

    users = db.relationship("User", secondary=user_event, back_populates="events")


class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime)
    open = db.Column(db.DateTime)
    name = db.Column(db.String, nullable=False)
    info = db.Column(db.String, nullable=True)
    confirmed = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    color_id = db.Column(db.Integer, db.ForeignKey('color.id'), nullable=True, unique=False)
    color = db.relationship('Color', back_populates="announcements")

    creator_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    creator = db.relationship("User", back_populates="announcements")

    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('team.id'), nullable=False)
    team = db.relationship("Team", back_populates="announcements")


class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime)
    stop = db.Column(db.DateTime)
    confirmed = db.Column(db.Boolean, unique=False, nullable=False, default=False)
    holiday = db.Column(db.Boolean, unique=False, nullable=False, default=False)
    sickleave = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    user_id = db.Column(db.String(64), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship("User", back_populates="schedules")

    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('team.id'), nullable=False)
    team = db.relationship("Team", back_populates="schedules")


class Color(db.Model):
    __tablename__ = 'color'
    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(6), nullable=False)
    users = db.relationship('User', back_populates='color', lazy=True)
    announcements = db.relationship('Announcement', back_populates='color', lazy=True)


class FCMToken(db.Model):
    __tablename__ = 'fcmtoken'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, unique=True, nullable=False)
    locale = db.Column(db.String, unique=False, nullable=True)
    user_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="tokens")
