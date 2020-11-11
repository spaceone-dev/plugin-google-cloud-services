from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import ReferenceModel
from spaceone.inventory.model.disk.data import *
from spaceone.inventory.model.disk.cloud_service import *
from spaceone.inventory.connector.disk import DiskConnector
from spaceone.inventory.model.disk.cloud_service_type import CLOUD_SERVICE_TYPES
from datetime import datetime
import time

class DiskManager(GoogleCloudManager):
    connector_name = 'DiskConnector'
    cloud_service_types = CLOUD_SERVICE_TYPES

    def collect_cloud_service(self, params):
        print("** Disk START **")
        start_time = time.time()
        """
        Args:
            params:
                - options
                - schema
                - secret_data
                - filter
                - zones
        Response:
            CloudServiceResponse
        """
        secret_data = params['secret_data']
        disk_conn: DiskConnector = self.locator.get_connector(self.connector_name, **params)
        resource_policies = {}
        current_region = ''
        for zone in params.get('zones', []):
            print(f"====== ZONE: {zone} ======")
            disks = disk_conn.list_disks(zone)

            if len(disks) > 0:

                if current_region != self.generate_region_from_zone(zone):
                    current_region = self.generate_region_from_zone(zone)

                if current_region not in resource_policies:
                    resource_policies_under_region = disk_conn.list_resource_policies(current_region)
                    resource_policies.update({current_region: resource_policies_under_region})

            for disk in disks:
                disk_type = self._get_disk_type(disk.get('type'))
                disk_size = float(disk.get('sizeGb'))

                snapshots = self.get_matched_snapshot(current_region, disk, resource_policies)

                disk.update({
                    'project': secret_data['project_id'],
                    'zone': zone,
                    'region': self.generate_region_from_zone(zone),
                    'in_used_by': self._get_in_used_by(disk.get('users', [])),
                    'source_image_display': self._get_source_image_display(disk),
                    'disk_type': disk_type,
                    'labels': self._get_labels(disk),
                    'snapshot_schedule': snapshots,
                    'snapshot_schedule_display': self._get_snapshot_schedule(disk),
                    'encryption': self._get_encryption(disk),
                    'size_display': str(disk_size) + ' GB',
                    'size': disk_size,
                    'read_iops': self.get_iops_rate(disk_type, disk_size, 'read'),
                    'write_iops': self.get_iops_rate(disk_type, disk_size, 'write'),
                    'read_throughput': self.get_throughput_rate(disk_type, disk_size),
                    'write_throughput': self.get_throughput_rate(disk_type, disk_size)
                })

                disk_data = Disk(disk, strict=False)
                disk_resource = DiskResource({
                    'data': disk_data,
                    'region_code': disk['region'],
                    'reference': ReferenceModel(disk_data.reference())
                })
                self.set_region_code(disk['region'])
                yield DiskResponse({'resource': disk_resource})

        print(f'** Disk Finished {time.time() - start_time} Seconds **')

    def get_iops_rate(self, disk_type, disk_size, flag):
        const = self._get_iops_constant(disk_type, flag)
        return disk_size * const

    def get_throughput_rate(self, disk_type, disk_size):
        const = self._get_throughput_constant(disk_type)
        return disk_size * const

    def get_matched_snapshot(self, region, disk, resource_policies):
        matched_policies = []
        policy_self_links = disk.get('resourcePolicies', [])
        policies = resource_policies.get(region)
        for self_link in policy_self_links:
            for policy in policies:
                if policy.get('selfLink') == self_link:
                    snapshot_schedule_policy = policy.get('snapshotSchedulePolicy', {})
                    snapshot_prop = snapshot_schedule_policy.get('snapshotProperties', {})
                    retention = snapshot_schedule_policy.get('retentionPolicy', {})
                    retention.update({'max_retention_days_display': str(retention.get('maxRetentionDays')) + ' days'})
                    policy_schedule = snapshot_schedule_policy.get('schedule', {})

                    policy.update({'snapshot_schedule_policy': {
                                        'schedule_display': self._get_schedule_display(policy_schedule),
                                        'schedule': policy_schedule,
                                        'retention_policy': retention,
                                    },
                                   'region': self._get_disk_type(policy.get('region')),
                                   'labels': self._get_labels(snapshot_prop),
                                   'storage_locations': snapshot_prop.get('storageLocations', [])
                                   })
                    matched_policies.append(policy)
        return matched_policies

    def _get_schedule_display(self, schedule):
        schedule_display = []
        if 'weeklySchedule' in schedule:
            week_schedule = schedule.get('weeklySchedule', {})
            weeks = week_schedule.get('dayOfWeeks', [])
            for week in weeks:
                schedule_display.append(week.get('day').title() + self._get_readable_time(week))

        elif 'dailySchedule' in schedule:
            daily = schedule.get('dailySchedule')
            schedule_display.append(f'Every day{self._get_readable_time(daily)}')

        elif 'hourlySchedule' in schedule:
            hourly = schedule.get('hourlySchedule')
            cycle = str(hourly.get('hoursInCycle'))
            hourly_schedule = f'Every {cycle} hours'
            schedule_display.append(hourly_schedule)

        return schedule_display

    @staticmethod
    def _get_readable_time(day_of_weeks):
        start_time = day_of_weeks.get('startTime')
        time_frame = start_time.split(':')
        first = int(time_frame[0]) + 1
        second = int(time_frame[1])

        d = datetime.strptime(start_time, "%H:%M")
        start = d.strftime("%I:%M %p")
        e = datetime.strptime(f'{first}:{second}', "%H:%M")
        end = e.strftime("%I:%M %p")

        return f' between {start} and {end}'

    @staticmethod
    def _get_labels(instance):
        labels = []
        for k, v in instance.get('labels', {}).items():
            labels.append(Labels({
                'key': k,
                'value': v
            }, strict=False))
        return labels

    @staticmethod
    def _get_iops_constant(disk_type, flag):
        constant = 0
        if flag == 'read':
            if disk_type == 'pd-standard':
                constant = 0.75
            elif disk_type == 'pd-balanced':
                constant = 6.0
            elif disk_type == 'pd-ssd':
                constant = 30.0
        else:
            if disk_type == 'pd-standard':
                constant = 1.5
            elif disk_type == 'pd-balanced':
                constant = 6.0
            elif disk_type == 'pd-ssd':
                constant = 30.0
        return constant

    @staticmethod
    def _get_throughput_constant(disk_type):
        constant = 0
        if disk_type == 'pd-standard':
            constant = 0.12
        elif disk_type == 'pd-balanced':
            constant = 0.28
        elif disk_type == 'pd-ssd':
            constant = 0.48

        return constant

    @staticmethod
    def _get_source_image_display(disk):
        source_image_display = ''
        source_image = disk.get('sourceImage')
        if source_image:
            source_image_display = source_image[source_image.rfind('/') + 1:]
        return source_image_display

    @staticmethod
    def _get_snapshot_schedule(disk):
        snapshot_schedule = []
        policies = disk.get('resourcePolicies', [])
        for policy in policies:
            snapshot_schedule.append(policy[policy.rfind('/') + 1:])
        return snapshot_schedule

    @staticmethod
    def _get_in_used_by(users):
        in_used_by = []
        for user in users:
            used_single = user[user.rfind('/') + 1:]
            in_used_by.append(used_single)
        return in_used_by

    @staticmethod
    def _get_encryption(disk):
        encryption = 'Google managed'
        disk_encryption = disk.get('diskEncryptionKey')
        if disk_encryption:
            if 'kmsKeyName' in disk_encryption or 'kmsKeyServiceAccount' in disk_encryption:
                encryption = 'Customer managed'
            else:
                encryption = 'Customer supplied'
        return encryption

    @staticmethod
    def _get_disk_type(type):
        return type[type.rfind('/') + 1:]
