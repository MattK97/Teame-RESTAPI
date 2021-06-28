from models import *
from firebase_admin import messaging
import json


notification_json_file = open('notifications_locale.json', encoding='utf-8')
notification_dictionary = json.load(notification_json_file)

available_locales = ['pl_PL', 'us_US']

def create_message(notification_type, title, body, registration_tokens):
    return messaging.MulticastMessage(
        data={'type': notification_type, 'sound': 'default'},
        notification=messaging.Notification(
            title=title,
            body=body,
        ),

        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default"
                ),
            ),
        ),

        tokens=registration_tokens,
    )


def create_team_locales_list(team_id):
    locales_list = []
    team = Team.query.filter_by(id=team_id).first()
    for team_member in team.users:
        for token in team_member.user.tokens:
            if token.locale not in locales_list:
                locales_list.append(token.locale)
    return locales_list


def create_whole_team_registration_token_list(locale, team_id, sender_id):
    registration_tokens = []
    team_users = Team.query.filter_by(id=team_id).first().users
    for team_user in team_users:
        if team_user.user_id != sender_id:
            for token in team_user.user.tokens.all():
                if token.locale == locale:
                    registration_tokens.append(token.token)
    return registration_tokens


def create_specific_team_users_registration_token_list(locale, receivers_ids_list, sender_id):
    registration_tokens = []
    for member_id in receivers_ids_list:
        if sender_id != member_id:
            user = User.query.filter_by(id=member_id).first()
            for token in user.tokens:
                if token.locale == locale:
                    registration_tokens.append(token.token)

    return registration_tokens


def send_notification_to_specific_team_members(team_id, receivers_ids_list, sender_id, notification_type, title):
    locales_list = create_team_locales_list(team_id)
    for locale in locales_list:
        registration_tokens = create_specific_team_users_registration_token_list(locale, receivers_ids_list, sender_id)
        if locale not in available_locales:
            body = notification_dictionary["us_US"][notification_type]
        else:
            body = notification_dictionary[locale][notification_type]
        message = create_message(notification_type, title, body, registration_tokens)
        response = messaging.send_multicast(message)
        # See the BatchResponse reference documentation
        # for the contents of response.
        print('{0} messages were sent successfully, in locale {1}'.format(response.success_count, locale))


def send_notification_to_whole_team(team_id, sender_id, notification_type, title):
    locales_list = create_team_locales_list(team_id)
    for locale in locales_list:
        registration_tokens = create_whole_team_registration_token_list(locale, team_id, sender_id)
        if locale not in available_locales:
            body = notification_dictionary["us_US"][notification_type]
        else:
            body = notification_dictionary[locale][notification_type]
        message = create_message(notification_type, title, body, registration_tokens)
        response = messaging.send_multicast(message)
        # See the BatchResponse reference documentation
        # for the contents of response.
        print('{0} messages were sent successfully, in locale {1}'.format(response.success_count, locale))


def send_chat_message_notification(team_id, sender_id, notification_type, title, body):
    locales_list = create_team_locales_list(team_id)
    team_name = Team.query.filter_by(id=team_id).first().team_name
    for locale in locales_list:
        registration_tokens = create_whole_team_registration_token_list(locale, team_id, sender_id)
        if locale not in available_locales:
            subtitle = notification_dictionary["us_US"][notification_type] + f" {team_name}"
        else:
            subtitle = notification_dictionary[locale][notification_type] + f" {team_name}"

        message = messaging.MulticastMessage(
            data={
                'type': notification_type
            },
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            subtitle=subtitle
                        ),
                        sound="default"
                    ),


                ),
            ),
            tokens=registration_tokens,
        )
        response = messaging.send_multicast(message)
        # See the BatchResponse reference documentation
        # for the contents of response.
        print('{0} messages were sent successfully, in locale {1}'.format(response.success_count, locale))

