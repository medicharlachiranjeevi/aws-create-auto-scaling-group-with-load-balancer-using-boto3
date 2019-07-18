
import boto3
import paramiko
import time
import os
import pickle
class CreateResource:
    def __init__(self,loadbalancername,vpc_id,secid,key,path):
        self.loadbalancername=loadbalancername
        self.path=path
        self.secid=secid
        self.vpc_id=vpc_id
        self.key=key
        try:
            self.version  = pickle.load(open("version.pickle", "rb"))
            name,ver, rev = str(self.version['old_name']).split('.')
            versionname=name+'.'+ver + '.' + str(int(rev)+1) 
            self.version['new_name']=versionname
        except (OSError, IOError,EOFError) :
            #self.version['new_ami'] ='test'
            self.version={}
            self.version['new_name'] ="test.1.9"
            self.version['old_image_id']='ami-012c812410e60ba30'



    def create_ec2(self):
        ec2 = boto3.resource('ec2')
        instance = ec2.create_instances(ImageId = self.version['old_image_id']
            ,MinCount = 1
            ,MaxCount = 1,
            InstanceType = 't2.micro',
            KeyName = self.key,
            SecurityGroupIds=[
                    self.secid,
                ])
        host = instance[0]
        print(host)
        host.wait_until_running()
        host = ec2.Instance(host.id)
        ec2 = boto3.client('ec2')
        #time.sleep(60)
        return host
    
    def ec2_wait(self,host):
        print('wait')
        ec2 = boto3.client('ec2')
        waiter = ec2.get_waiter('system_status_ok')
        waiter.wait(InstanceIds=[host.id])
        host = host.public_ip_address

    def run_cap(self,host):
            #os.system()
            print('cap')

    def image_create(self,instance_id):
        print('created image')
        ec2 = boto3.resource('ec2')
        host = ec2.Instance(instance_id)
        image = host.create_image(Name=self.version['new_name'])
        print(image.id)
        self.version['ImageId']=image.id
        self.image_wait()

    def image_wait(self):
        print('image wait')
        ec2 = boto3.client('ec2')
        waiter = ec2.get_waiter('image_available')
        waiter.wait(ImageIds=[self.version['ImageId']])

    def deleteec2(self,host):
        print('delete existing ec2')
        ec2 = boto3.resource('ec2')
        ec2.instances.filter(InstanceIds = [host]).terminate() 

    def launch_config(self):
        print('lanuch config')
        client = boto3.client('autoscaling')
        response = client.create_launch_configuration(
        LaunchConfigurationName=self.version['new_name'],
        ImageId=self.version['ImageId'],
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',

                'Ebs': {
                    
                    'VolumeSize': 40,
                },
            },
        ],
        KeyName=self.key,
        InstanceType='t2.micro',
        SecurityGroups=[
           self.secid
        ]
        )
    def get_subnets(self):
        client=boto3.client('ec2')
        response = client.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        self.vpc_id,
                       ],
                },
                ],
        )
        subnets=''
        for i in response['Subnets']:
            subnets=subnets+i['SubnetId']+','
        self.version['subnets']=subnets[:-1]
        
    def auto_scaling(self):
        print('create autosacling')
        client = boto3.client('autoscaling')
        response = client.create_auto_scaling_group(
        AutoScalingGroupName=self.version['new_name'],
        LaunchConfigurationName=self.version['new_name'],
        LoadBalancerNames=[self.loadbalancername],
        VPCZoneIdentifier=self.version['subnets'],
        MinSize=1,
        MaxSize=2,)

    def scaling_polacy(self):
        print('attach')
        ec2 = boto3.client('autoscaling')
        response = ec2.put_scaling_policy(
        AutoScalingGroupName=self.version['new_name'],
        PolicyName=self.version['new_name'],
        PolicyType='TargetTrackingScaling',
        AdjustmentType='ChangeInCapacity',
        Cooldown=123,
        EstimatedInstanceWarmup=123,
        
        TargetTrackingConfiguration={
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ASGAverageCPUUtilization'
            },
                'TargetValue': 80,
                'DisableScaleIn': True
            }
        )

    def auto_scaling_describe_instances(self):
        ec2 = boto3.client('autoscaling')
        response = ec2.describe_auto_scaling_groups(
        AutoScalingGroupNames=[self.version['new_name']
                ,
        ]
        )
        InstanceId= response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
        self.wait_instances_state(InstanceId)
        
    def wait_instances_state(self,instance_id):
        print('active')
        client = boto3.client('elb')
        response = client.describe_instance_health(
            LoadBalancerName=self.loadbalancername,
            Instances=[
                {
                    'InstanceId': instance_id
                },
            ]
        )
        while response['InstanceStates'][0]['State']!='InService':
            response = client.describe_instance_health(
                LoadBalancerName=self.loadbalancername,
                Instances=[
                    {
                        'InstanceId': instance_id
                    },
                ]
            )
            time.sleep(60)
    

    def pickle_save(self):
        pickle_out = open("version.pickle","wb")
        pickle.dump(self.version, pickle_out)
        pickle_out.close()
        pass


class delprevious:
    def __init__(self):
        self.version = pickle.load(open("version.pickle","rb"))
        pass
    def swap(self):
        self.version['old_name']= self.version['new_name']
        self.version['old_image_id']=self.version['ImageId']
        pickle_out = open("version.pickle","wb")
        pickle.dump(self.version, pickle_out)
        pickle_out.close()
        
        pass
    def amidel(self):
        ec2 = boto3.client('ec2')
        snapid=ec2.describe_images(ImageIds=[self.version['old_image_id']])['Images'][0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        response = ec2.deregister_image(
            ImageId=self.version['old_image_id']
        )
        self.snapdel(snapid)
    def snapdel(self,snapid):
        ec2 = boto3.client('ec2')
        response = ec2.delete_snapshot(
        SnapshotId=snapid
        )

    def delete_lanch(self):
        client = boto3.client('autoscaling')        
        response = client.delete_launch_configuration(
        LaunchConfigurationName=self.version['old_name']
    )
    def delete_autoscalinggroup(self):
         client = boto3.client('autoscaling')        
         response = client.delete_auto_scaling_group(
                    AutoScalingGroupName=self.version['old_name'],
                    ForceDelete=True
                )
if __name__ == "__main__":
    vpc_id='vpc-135bab69'
    secid='sg-0e16d8c80e55887bc'
    key='greyv19'
    loadbalancername='greycampusv19'
    path=''
    createresource=CreateResource(loadbalancername,vpc_id,secid,key,path)
    host=createresource.create_ec2()
    createresource.ec2_wait(host)
    createresource.run_cap(host)
    createresource.image_create(host.id)
    createresource.deleteec2(host.id)
    createresource.launch_config()
    createresource.get_subnets()
    createresource.auto_scaling()
    createresource.scaling_polacy()
    time.sleep(40)
    createresource.auto_scaling_describe_instances()
    createresource.pickle_save()
    delete_perivous=delprevious()
    delete_perivous.delete_autoscalinggroup()
    delete_perivous.delete_lanch()
    delete_perivous.amidel()
    delete_perivous.swap()
    pass

vpc_id='vpc-135bab69'
secid='sg-0e16d8c80e55887bc'
key='greyv19'
loadbalancername='greycampusv19'
path=''
create=CreateResource(loadbalancername,vpc_id,secid,key,path)
host=create.create_ec2()
create.ec2_wait(host)
create.run_cap(host)
create.image_create(host.id)
create.deleteec2(host.id)
create.launch_config()
create.get_subnets()
create.auto_scaling()
create.scaling_polacy()
time.sleep(40)
create.auto_scaling_describe_instances()
create.pickle_save()
delete_perivous=delprevious()
delete_perivous.delete_autoscalinggroup()
delete_perivous.delete_lanch()
delete_perivous.amidel()
delete_perivous.swap()
