import uuid
import datetime

from flask_restplus import Namespace, fields, Resource, reqparse
from flask import abort
from werkzeug.datastructures import FileStorage

from app import logger
from models import db
from models.application import Application
from models.service import Service
from models.evaluation_data import EvaluationData
from core.drucker_dashboard_client import DruckerDashboardClient
from apis.common import DatetimeToTimestamp


app_info_namespace = Namespace('applications', description='Application Endpoint.')
success_or_not = app_info_namespace.model('Success', {
    'status': fields.Boolean(
        required=True
    ),
    'message': fields.String(
        required=True
    )
})
app_info = app_info_namespace.model('Application', {
    'application_id': fields.Integer(
        readOnly=True,
        description='Application ID.'
    ),
    'application_name': fields.String(
        required=True,
        description='Application name.',
        example='drucker-sample'
    ),
    'kubernetes_id': fields.Integer(
        required=False,
        description='Kubernetes cluster ID.'
    ),
    'description': fields.String(
        required=False,
        description='Description.',
        example='This is a sample.'
    ),
    'register_date': DatetimeToTimestamp(
        readOnly=True,
        description='Register date.'
    ),
    'confirm_date': DatetimeToTimestamp(
        readOnly=True,
        description='Existance confirmation date.'
    )
})


@app_info_namespace.route('/')
class ApiApplications(Resource):
    add_worker_parser = reqparse.RequestParser()
    add_worker_parser.add_argument('host', type=str, required=True, location='form')
    add_worker_parser.add_argument('description', type=str, required=False, location='form')

    @app_info_namespace.marshal_list_with(app_info)
    def get(self):
        """get_applications"""
        return Application.query.all()

    @app_info_namespace.marshal_with(success_or_not)
    @app_info_namespace.expect(add_worker_parser)
    def post(self):
        """add_non-kube_worker"""
        args = self.add_worker_parser.parse_args()
        host = args['host']
        display_name = uuid.uuid4().hex
        description = args['description']

        drucker_dashboard_application = DruckerDashboardClient(logger=logger, host=host)
        service_info = drucker_dashboard_application.run_service_info()
        application_name = service_info["application_name"]
        service_name = service_info["service_name"]
        service_level = service_info["service_level"]

        aobj = db.session.query(Application).filter(
            Application.application_name == application_name,
            Application.kubernetes_id == None).one_or_none()
        if aobj is None:
            aobj = Application(application_name=application_name,
                               description=description)
            db.session.add(aobj)
            db.session.flush()
        sobj = db.session.query(Service).filter(
            Service.service_name == service_name).one_or_none()
        if sobj is None:
            sobj = Service(application_id=aobj.application_id,
                           service_name=service_name,
                           display_name=display_name,
                           service_level=service_level,
                           host=host,
                           description=description)
            db.session.add(sobj)
            db.session.flush()
        response_body = {"status": True, "message": "Success."}
        db.session.commit()
        db.session.close()
        return response_body

@app_info_namespace.route('/<int:application_id>')
class ApiApplications(Resource):
    edit_app_info_parser = reqparse.RequestParser()
    edit_app_info_parser.add_argument('description', type=str, required=True, location='form')

    @app_info_namespace.marshal_with(app_info)
    def get(self, application_id:int):
        """get_application"""
        return Application.query.filter_by(application_id=application_id).first_or_404()

    @app_info_namespace.marshal_with(success_or_not)
    @app_info_namespace.expect(edit_app_info_parser)
    def patch(self, application_id:int):
        """update_application"""
        args = self.edit_app_info_parser.parse_args()
        description = args['description']
        res = db.session.query(Application).filter(Application.application_id == application_id).one()
        res.description = description
        response_body = {"status": True, "message": "Success."}
        db.session.commit()
        db.session.close()
        return response_body

@app_info_namespace.route('/<int:application_id>/evaluation')
class ApiEvaluation(Resource):
    upload_parser = reqparse.RequestParser()
    upload_parser.add_argument('file', location='files', type=FileStorage, required=True)

    @app_info_namespace.expect(upload_parser)
    def post(self, application_id:int):
        """update data to be evaluated"""
        args = self.upload_parser.parse_args()
        file = args['file']
        eval_data_path = "eval-{0:%Y%m%d%H%M%S}".format(datetime.datetime.utcnow())

        sobj = Service.query.filter_by(application_id=application_id).first_or_404()

        drucker_dashboard_application = DruckerDashboardClient(logger=logger, host=sobj.host)
        response_body = drucker_dashboard_application.run_upload_evaluation_data(file, eval_data_path)

        if response_body['status']:
            eobj = EvaluationData(application_id=application_id, data_path=eval_data_path)
            db.session.add(eobj)
            db.session.commit()
            db.session.close()

        return response_body

@app_info_namespace.route('/<int:application_id>/evaluation/<int:eval_data_id>')
class ApiEvaluation(Resource):
    def delete(self, application_id:int, eval_data_id:int):
        """delete data to be evaluated"""
        eval_data_query = db.session.query.filter(application_id=application_id,
                                                  evaluation_data_id=eval_data_id)
        if not eval_data_query.exists():
            abort(404)

        eval_data_query.delete()
        db.session.flush()
        db.session.commit()
        db.session.close()

        return {"status": True, "message": "Success."}
