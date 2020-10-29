from schematics.types import ModelType, StringType, PolyModelType

from spaceone.inventory.model.instance_template.data import InstanceTemplate
from spaceone.inventory.libs.schema.metadata.dynamic_field import TextDyField, DateTimeDyField, EnumDyField, ListDyField
from spaceone.inventory.libs.schema.metadata.dynamic_layout import ItemDynamicLayout, TableDynamicLayout, ListDynamicLayout
from spaceone.inventory.libs.schema.cloud_service import CloudServiceResource, CloudServiceResponse, CloudServiceMeta

'''
INSTANCE
'''
# TAB - Instance Template
instance_template_meta = ItemDynamicLayout.set_fields('Instance', fields=[
    TextDyField.data_source('ID', 'data.id'),
    TextDyField.data_source('Name', 'data.name'),
    TextDyField.data_source('Description', 'data.description'),
    TextDyField.data_source('Fingerprint', 'data.fingerprint'),
    ListDyField.data_source('In Used By', 'data.in_used_by',
                            default_badge={'type': 'outline', 'delimiter': '<br>'}),
    TextDyField.data_source('Machine Type', 'data.machine.machine_type'),
    ListDyField.data_source('Affected Rules', 'data.affected_rules',
                            default_badge={'type': 'outline', 'delimiter': '<br>'}),
    EnumDyField.data_source('IP Forward', 'data.ip_forward', default_badge={
        'indigo.500': ['true'], 'coral.600': ['false']
    }),
    TextDyField.data_source('Self Link', 'data.self_link'),
    DateTimeDyField.data_source('Creation Time', 'data.creation_timestamp'),
])

# TAB - Network
# instance_template_meta_network
it_meta_machine = ItemDynamicLayout.set_fields('Machine Info', root_path='data.machine', fields=[
    TextDyField.data_source('Name', 'machine_type'),
    TextDyField.data_source('Core', 'core'),
    TextDyField.data_source('Memory', 'memory')
])

# TAB - Service Account
it_meta_service_account = ItemDynamicLayout.set_fields('Network Interface', root_path='data.service_account', fields=[
    TextDyField.data_source('E-mail', 'email'),
    ListDyField.data_source('Scopes', 'scopes',
                            default_badge={'type': 'outline', 'delimiter': '<br>'})
])

instance_template = ListDynamicLayout.set_layouts('Instance Template', layouts=[instance_template_meta, it_meta_machine, it_meta_service_account])

# TAB - Network
# instance_template_meta_network
it_meta_network = TableDynamicLayout.set_fields('Network Interface', root_path='data.network_interfaces', fields=[
    TextDyField.data_source('Name', 'name'),
    TextDyField.data_source('Network', 'network'),
    TextDyField.data_source('Subnetwork', 'subnetwork'),
    ListDyField.data_source('Access Configs', 'configs'),
    ListDyField.data_source('Network Tier', 'network_tier'),
    TextDyField.data_source('Kind', 'network'),
])

# TAB - Disk
# instance_template_meta_disk
it_meta_disk = TableDynamicLayout.set_fields('Database',  root_path='data.disks', fields=[
    TextDyField.data_source('Index', 'device_index'),
    TextDyField.data_source('Name', 'device'),
    TextDyField.data_source('Size(GB)', 'size'),
    EnumDyField.data_source('Disk Type', 'tags.disk_type',
                            default_outline_badge=['local-ssd', 'pd-balanced', 'pd-ssd', 'pd-standard']),
    TextDyField.data_source('Source Image', 'tags.source_image_display'),
    TextDyField.data_source('Read IOPS', 'tags.read_iops'),
    TextDyField.data_source('Write IOPS', 'tags.write_iops'),
    TextDyField.data_source('Read Throughput(MB/s)', 'tags.read_throughput'),
    TextDyField.data_source('Write Throughput(MB/s)', 'tags.write_throughput'),
    EnumDyField.data_source('Auto Delete', 'tags.auto_delete', default_badge={
        'indigo.500': ['true'], 'coral.600': ['false']
    }),
])

it_meta_labels = TableDynamicLayout.set_fields('Labels', root_path='data.labels', fields=[
    TextDyField.data_source('Key', 'key'),
    TextDyField.data_source('Value', 'value'),
])

instance_template_meta = CloudServiceMeta.set_layouts([instance_template, it_meta_network, it_meta_disk,
                                                       it_meta_service_account, it_meta_labels])


class ComputeEngineResource(CloudServiceResource):
    cloud_service_group = StringType(default='ComputeEngine')


class InstanceTemplateResource(ComputeEngineResource):
    cloud_service_type = StringType(default='InstanceTemplate')
    data = ModelType(InstanceTemplate)
    _metadata = ModelType(CloudServiceMeta, default=instance_template_meta, serialized_name='metadata')


class InstanceTemplateResponse(CloudServiceResponse):
    resource = PolyModelType(InstanceTemplateResource)
