from flask import request
from main import db
from flask_restful import Resource
import firebase_admin
from firebase_admin import credentials, auth
from sqlalchemy import extract
from datetime import datetime
from notifications import *


def authentication(f):
    token_header = f
    decoded_token = auth.verify_id_token(token_header)
    return decoded_token['uid']


def does_have_mod_permission(user_id, team_id):
    return Team_User.query.filter_by(user_id=user_id, team_id=team_id).first().moderator


class CheckWorking(Resource):
    def get(self):
        return "Helloworld!"


class CheckToken(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        user = User.query.filter_by(id=user_id).first()
        actual_token = request.headers['registration_token']
        list_of_user_tokens = []
        for token in user.tokens:
            list_of_user_tokens.append(token.token)
        if actual_token in list_of_user_tokens:
            return {"valid": True}
        else:
            new_token = FCMToken(token=actual_token, user=user)
            db.session.add(new_token)
            db.session.commit()
            return {"valid": True}


class CheckExistence(Resource):
    def get(self):
        user_id = authentication(request.headers['Authorization'])
        user = User.query.filter_by(id=user_id).first()
        if user is None:
            return {"exist": False}, 200
        else:
            return {"exist": True}, 200


class Register(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        color = Color.query.filter_by(id=data['color']).first()
        new_user = User(id=user_id, first_name=data['first_name'], last_name=data['last_name'], color=color)
        db.session.add(new_user)
        db.session.commit()
        return {"response": True}, 200


class Colors(Resource):
    def get(self):
        colorList = []
        colors = Color.query.all()
        for color in colors:
            colorObject = {
                'color_id': color.id,
                'color_hex': color.color
            }
            colorList.append(colorObject)
        return colorList, 200


class CreateTeam(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        dateTime = datetime.now()
        new_team = Team(
            id=uuid.uuid1(),
            team_name=data['team_name'],
            created=dateTime,
            creator_id=user_id,
            uses_worktime=False
        )
        association = Team_User(moderator=True)
        user = User.query.filter_by(id=user_id).first()
        association.user = user
        new_team.users.append(association)
        db.session.flush()
        db.session.commit()
        id = str(new_team.id)
        return {'team_id': id}, 201  # if not working return "string"


class JoinTeam(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        team = Team.query.filter_by(id=data['team_id']).first()
        association = Team_User(moderator=False)
        user = User.query.filter_by(id=user_id).first()
        association.user = user
        association.team = team
        team.users.append(association)
        db.session.commit()
        return True, 200


class TeamMembers(Resource):
    def get(self):
        userID = authentication(request.headers['Authorization'])
        teamID = request.headers['team_id']
        teamUsers = Team.query.filter_by(id=teamID).first().users
        output = []
        for teamUser in teamUsers:
            userObject = {
                'user_id': teamUser.user.id,
                'first_name': teamUser.user.first_name,
                'last_name': teamUser.user.last_name,
                'moderator': teamUser.moderator,
                'color': teamUser.user.color.color
            }
            output.append(userObject)
        return output, 200


class UserTeams(Resource):
    def get(self):
        userID = authentication(request.headers['Authorization'])
        userTeams = User.query.filter_by(id=userID).first().member_teams
        output = []
        for userTeam in userTeams:
            teamObject = {
                'name': userTeam.team.team_name,
                'team_id': str(userTeam.team.id),
                'uses_worktime': userTeam.team.uses_worktime,
                'creator_id': userTeam.team.creator_id
            }
            output.append(teamObject)
        return output, 200


class EventsClass(Resource):
    def get(self):
        userID = authentication(request.headers['Authorization'])
        month = request.headers['month']
        teamID = request.headers['team_id']
        output = []

        # if user has moderator permission query events through team.events
        if does_have_mod_permission(userID, teamID):
            events = Team.query.filter_by(id=teamID).first().events \
                .filter(extract('month', Event.start) == month).all()
        else:
            events = User.query.filter_by(id=userID).first().events \
                .filter(extract('month', Event.start) == month).all()

        for event in events:
            eventObject = {
                'event_id': event.id,
                'name': event.name,
                'info': event.info,
                'start': str(event.start)
            }
            userList = []
            for eventUser in event.users:
                userList.append(eventUser.id)
            eventObject['event_users_ids'] = userList
            output.append(eventObject)
        return output, 200

    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        team = Team.query.filter_by(id=data['team_id']).first()
        if data['event_id'] is None:
            event = Event(team=team, start=data['start'], name=data['name'], info=data['info'])
            for event_user in data['event_users_ids']:
                user = User.query.filter_by(id=event_user).first()
                user.events.append(event)
            db.session.add(event)
            db.session.commit()
            send_notification_to_specific_team_members(event.team_id,data['event_users_ids'], user_id, "new_event", team.team_name)
            return {"event_id": event.id}, 201

        else:
            event = Event.query.filter_by(id=data['event_id']).first()
            event.start = data['start']
            event.name = data['name']
            event.info = data['info']
            newUserList = []
            for event_user_id in data['event_users_ids']:
                user = User.query.filter_by(id=event_user_id).first()
                newUserList.append(user)
            difList = list(set(newUserList) ^ set(event.users))
            # TODO probably to change
            for event_user in difList:
                if event_user in event.users:
                    event.users.remove(event_user)
            event.users = newUserList
            # TODO do ogarnięcia
            db.session.commit()
            return {"event_id": event.id}, 200

    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        event = Event.query.filter_by(id=request.headers['event_id']).first()
        event_users = event.users
        event_users_ids = []

        for event_user in event_users:
            event_users_ids.append(event_user.id)

        db.session.delete(event)
        send_notification_to_specific_team_members(event.team_id,event_users_ids, user_id, "delete_event", event.team.team_name)
        db.session.commit()
        return True, 200


class ConfirmWorkTime(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        dataObj = request.get_json()
        idList = []
        base_work_time = WorkTime.query.filter_by(id=dataObj[0]).first()
        confirmed_worktime_user_id = base_work_time.user_id
        for id in dataObj:
            workTime = WorkTime.query.filter_by(id=id).first()
            workTime.confirmed = True
            db.session.commit()
            idList.append(workTime.id)
        send_notification_to_specific_team_members(base_work_time.team.id,[confirmed_worktime_user_id], user_id, "confirm_work_time",
                                                   base_work_time.team.team_name)
        return {'id_list': idList}, 200


class WorkTimeClass(Resource):
    def get(self):
        userID = authentication(request.headers['Authorization'])
        month = request.headers['month']
        teamID = request.headers['team_id']

        if does_have_mod_permission(userID, teamID):
            work_time_list = WorkTime.query.filter_by(team_id=teamID).filter(extract('year', WorkTime.start) == 2021,
                                                                             extract('month',
                                                                                     WorkTime.start) == month).all()
        else:
            work_time_list = WorkTime.query.filter_by(user_id=userID).filter(extract('year', WorkTime.start) == 2021,
                                                                             extract('month',
                                                                                     WorkTime.start) == month).all()
        work_time = []

        for workTime in work_time_list:
            workTimeObject = {
                'id': workTime.id,
                'user_id': workTime.user_id,
                'start': str(workTime.start)
            }
            if workTime.stop is None:
                workTimeObject['stop'] = workTime.stop
            else:
                workTimeObject['stop'] = str(workTime.stop)

            workTimeObject['confirmation'] = workTime.confirmed
            work_time.append(workTimeObject)
        return work_time, 200

    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        dateTime = datetime.now()
        if data['user_id'] is not None:
            user_id = data['user_id']
        workTime = WorkTime.query.filter_by(user_id=user_id, stop=None).first()
        if workTime is None:
            workTime = WorkTime(start=dateTime, confirmed=data['confirmation'], user_id=user_id,
                                team_id=data['team_id'])
            db.session.add(workTime)
            db.session.commit()
            return {
                       'id': workTime.id,
                       'user_id': user_id,
                       'start': str(workTime.start),
                       'stop': workTime.stop,
                       'confirmation': workTime.confirmed
                   }, 200
        else:
            workTime.stop = dateTime
            db.session.commit()
            return {
                       'id': workTime.id,
                       'start': str(workTime.start),
                       'stop': str(workTime.stop),
                       'confirmation': workTime.confirmed
                   }, 200


class ConfirmSchedule(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        schedule = Schedule()
        dataObj = request.get_json()
        idList = []
        for id in dataObj:
            schedule = Schedule.query.filter_by(id=id).first()
            schedule.confirmed = True
            db.session.commit()
            idList.append(schedule.id)
        send_notification_to_specific_team_members(schedule.team_id,[schedule.user_id], user_id, "confirm_schedule", schedule.team.team_name,)
        return {'id_list': idList}, 200


class ScheduleClass(Resource):
    def get(self):
        user_id = authentication(request.headers['Authorization'])
        team_id = request.headers['team_id']
        month = request.headers['month']
        schedules = Team.query.filter_by(id=team_id).first().schedules. \
            filter(extract('year', Schedule.start) == 2021, extract('month', Schedule.start) == month)
        final_schedule = []
        for schedule in schedules:
            scheduleObject = {
                'schedule_id': schedule.id,
                'start': str(schedule.start),
                'stop': str(schedule.stop),
                'user_id': schedule.user_id,
                'confirmation': schedule.confirmed,
                'sickleave': schedule.sickleave,
                'holiday': schedule.holiday,
                'team_id': str(schedule.team_id)
            }
            final_schedule.append(scheduleObject)
        return final_schedule

    def put(self):
        user_id = authentication(request.headers['Authorization'])
        dataObj = request.get_json()
        scheduleList = []
        team = Team.query.filter_by(id=dataObj[0]['team_id']).first()
        for data in dataObj:
            sender_user_id = data['user_id']
            start = data['start']
            stop = data['stop']
            confirmation = data['confirmation']
            holiday = data['holiday']
            sickleave = data['sickleave']
            if data['schedule_id'] is None:
                schedule = Schedule(team=team, user_id=sender_user_id, start=start, stop=stop,
                                    confirmed=confirmation, sickleave=sickleave, holiday=holiday)
                db.session.add(schedule)
                db.session.flush()
                scheduleList.append(schedule)
            else:
                schedule = Schedule.query.filter_by(id=data['schedule_id']).first()
                schedule.start = start
                schedule.stop = stop
                schedule.confirmed = confirmation
                schedule.holiday = holiday
                schedule.sickleave = sickleave  # TODO zmienić bo źle
                db.session.flush()
                scheduleList.append(schedule)
        db.session.commit()
        send_notification_to_specific_team_members(team.id, [dataObj[0]['user_id']], user_id, "create_schedule", team.team_name,)
        final_schedule = []
        for schedule in scheduleList:
            scheduleObject = {
                'schedule_id': schedule.id,
                'start': str(schedule.start),
                'stop': str(schedule.stop),
                'user_id': schedule.user_id,
                'confirmation': schedule.confirmed,
                'sickleave': schedule.sickleave,
                'holiday': schedule.holiday,
                'team_id': str(schedule.team_id)
            }
            final_schedule.append(scheduleObject)
        return final_schedule, 200

    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        schedule = Schedule.query.filter_by(id=request.headers['schedule_id']).first()
        db.session.delete(schedule)
        send_notification_to_specific_team_members(schedule.team_id, [schedule.user_id], user_id, "delete_schedule", schedule.team.team_name)
        db.session.commit()
        return True, 200


class AnnouncementClass(Resource):
    def get(self):
        user_id = authentication(request.headers['Authorization'])
        team_id = request.headers['team_id']
        month = request.headers['month']
        announcements = Announcement.query.filter_by(team_id=team_id).filter(
            extract('month', Announcement.created) == month).all()
        output = []
        for announcement in announcements:
            announcementObject = {
                'name': announcement.name,
                'info': announcement.info,
                'announcement_id': announcement.id,
                'created': str(announcement.created),
                'creator_id': announcement.creator_id,
                'open': str(announcement.open),
                'color': announcement.color.color,
                'confirmation': announcement.confirmed
            }
            output.append(announcementObject)
        return output, 200

    def post(self):
        data = request.get_json()
        user_id = authentication(request.headers['Authorization'])
        team_id = data['team_id']
        dateTime = datetime.now()
        announcement_name = data['name']
        announcement_info = data['info']
        announcement_creator = data['creator_id']
        announcement_open = data['open']
        announcement_confirmation = data['confirmation']
        team = Team.query.filter_by(id=team_id).first()
        color = Color.query.filter_by(id=data['color_id']).first()
        if data['announcement_id'] is None:
            newAnnouncement = Announcement(
                team_id=team_id,
                name=announcement_name,
                info=announcement_info,
                created=dateTime,
                creator_id=announcement_creator,
                open=announcement_open,
                color=color,
                confirmed=announcement_confirmation
            )
            db.session.add(newAnnouncement)
            db.session.commit()
            send_notification_to_whole_team(team_id, user_id, "create_announcement", team.team_name)
            return {'announcement_id': newAnnouncement.id}, 200
        else:
            announcement = Announcement.query.filter_by(id=data['announcement_id']).first()
            announcement.name = data['name']
            announcement.info = data['info']
            announcement.color = color
            db.session.commit()
            send_notification_to_whole_team(team_id, user_id, "update_announcement", team.team_name)
            return {'announcement_id': announcement.id}, 200

    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        announcement = Announcement.query.filter_by(id=request.headers['announcement_id']).first()
        db.session.delete(announcement)
        send_notification_to_whole_team(announcement.team_id, user_id, "delete_announcement", announcement.team.team_name)

        db.session.commit()
        return True, 200


class NewChatMessageNotification(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        full_message = data['message_content']
        notification_body = full_message
        if len(full_message) > 80:
            full_message = full_message[:80].rpartition(' ')[0]
            notification_body = ''.join((full_message, '...'))
        user = User.query.filter_by(id=user_id).first()
        send_chat_message_notification(data['team_id'], user_id, "message", user.first_name, notification_body)


### UPDATE VIEWS


class ConfirmAnnouncement(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        announcement = Announcement.query.filter_by(id=data['announcement_id']).first()
        announcement.confirmed = True
        db.session.commit()
        return {"success": True}


class UpdateFirstName(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        user = User.query.filter_by(id=user_id).first()
        user.first_name = data['first_name']
        db.session.commit()
        return {"success": True}


class UpdateLastName(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        user = User.query.filter_by(id=user_id).first()
        user.last_name = data['last_name']
        db.session.commit()
        return {"success": True}


class UpdateColor(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        user = User.query.filter_by(id=user_id).first()
        user.color_id = data['color_id']
        db.session.commit()
        return {"success": True}


class PromoteUser(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        team = Team.query.filter_by(id=data['team_id']).first()
        team.users.filter_by(user_id=data['user_id']).first().moderator = True
        db.session.commit()
        send_notification_to_specific_team_members(team.id, [data['user_id']], user_id, "promotion", team.team_name)
        return {"success": True}


class DegradateUser(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        association = Team_User.query.filter_by(user_id=data['user_id'], team_id=data['team_id']).first()
        association.moderator = False
        db.session.commit()
        return {"success": True}


class SwitchWorkTime(Resource):
    def post(self):
        user_id = authentication(request.headers['Authorization'])
        data = request.get_json()
        team = Team.query.filter_by(id=data['team_id']).first()
        team.uses_worktime = data['uses_worktime']
        db.session.commit()
        return {"success": True}


class DeleteTeam(Resource):
    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        team_id = request.headers['team_id']
        team = Team.query.filter_by(id=team_id).first()
        db.session.delete(team)
        db.session.commit()
        return {"success": True}


class DeleteAccount(Resource):
    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        user = User.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        return {"success": True}


class DeleteMember(Resource):
    def delete(self):
        user_id = authentication(request.headers['Authorization'])
        member_id = request.headers['user_id']
        team_id = request.headers['team_id']
        team_user = Team_User.query.filter_by(user_id=member_id, team_id=team_id).first()
        db.session.delete(team_user)
        db.session.commit()
        return {"success": True}
