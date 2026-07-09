from alibabacloud_cms20190101 import models as cms_models
from alibabacloud_cms20190101.client import Client as CmsClient
from flask import (
    Flask, render_template
)
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from aliyun_exporter import CollectorConfig
from aliyun_exporter.credential import build_credential_client, build_openapi_config
from aliyun_exporter.utils import format_metric, format_period


def create_app(config: CollectorConfig):

    app = Flask(__name__, instance_relative_config=True)

    credential_client = build_credential_client(config.credential)
    openapi_config = build_openapi_config(config.credential['region_id'], credential_client)
    client = CmsClient(openapi_config)

    @app.route("/")
    def projectIndex():
        req = cms_models.DescribeProjectMetaRequest(page_size=100)
        try:
            resp = client.describe_project_meta(req)
        except Exception as e:
            return render_template("error.html", errorMsg=e)
        projects = [r.to_map() for r in resp.body.resources.resource]
        return render_template("index.html", projects=projects)

    @app.route("/projects/<string:name>")
    def projectDetail(name):
        req = cms_models.DescribeMetricMetaListRequest(page_size=100, namespace=name)
        try:
            resp = client.describe_metric_meta_list(req)
        except Exception as e:
            return render_template("error.html", errorMsg=e)
        metrics = [r.to_map() for r in resp.body.resources.resource]
        return render_template("detail.html", metrics=metrics, project=name)

    @app.route("/yaml/<string:name>")
    def projectYaml(name):
        req = cms_models.DescribeMetricMetaListRequest(page_size=100, namespace=name)
        try:
            resp = client.describe_metric_meta_list(req)
        except Exception as e:
            return render_template("error.html", errorMsg=e)
        metrics = [r.to_map() for r in resp.body.resources.resource]
        return render_template("yaml.html", metrics=metrics, project=name)

    app.jinja_env.filters['formatmetric'] = format_metric
    app.jinja_env.filters['formatperiod'] = format_period

    app_dispatch = DispatcherMiddleware(app, {
        '/metrics': make_wsgi_app()
    })
    return app_dispatch
