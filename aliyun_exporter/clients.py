from alibabacloud_tea_openapi.models import Config as OpenApiConfig
from alibabacloud_cms20190101.client import Client as CmsClient
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_rds20140815.client import Client as RdsClient
from alibabacloud_r_kvstore20150101.client import Client as RedisClient
from alibabacloud_slb20140515.client import Client as SlbClient
from alibabacloud_dds20151201.client import Client as DdsClient


class AliyunClients(object):
    def __init__(self, config: OpenApiConfig):
        self.cms = CmsClient(config)
        self.ecs = EcsClient(config)
        self.rds = RdsClient(config)
        self.redis = RedisClient(config)
        self.slb = SlbClient(config)
        self.dds = DdsClient(config)
