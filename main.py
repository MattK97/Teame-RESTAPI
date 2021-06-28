from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os


app = Flask(__name__)
api = Api(app)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


from views import *

api.add_resource(CheckWorking, '/check')
api.add_resource(CheckToken, '/checkToken')
api.add_resource(CheckExistence, '/checkexistence')
api.add_resource(Register, '/register')
api.add_resource(Colors, '/colorList')
api.add_resource(CreateTeam, '/createTeam')
api.add_resource(JoinTeam, '/joinTeam')
api.add_resource(UserTeams, '/userTeamList')
api.add_resource(TeamMembers, '/teamMemberList')
api.add_resource(EventsClass, '/event')
api.add_resource(ScheduleClass, '/schedule')
api.add_resource(AnnouncementClass, '/announcement')
api.add_resource(WorkTimeClass, '/worktime')
api.add_resource(ConfirmWorkTime, '/confirmWorkTime')
api.add_resource(ConfirmSchedule, '/confirmSchedules')
api.add_resource(ConfirmAnnouncement, '/confirmAnnouncement')
api.add_resource(NewChatMessageNotification, '/notifyChat')
api.add_resource(UpdateFirstName, '/updateFirstName')
api.add_resource(UpdateLastName, '/updateLastName')
api.add_resource(UpdateColor, '/updateColor')
api.add_resource(PromoteUser, '/promoteUser')
api.add_resource(DegradateUser, '/degradateUser')
api.add_resource(SwitchWorkTime, '/switchWorkTime')
api.add_resource(DeleteTeam, '/deleteTeam')
api.add_resource(DeleteAccount, '/deleteAccount')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
