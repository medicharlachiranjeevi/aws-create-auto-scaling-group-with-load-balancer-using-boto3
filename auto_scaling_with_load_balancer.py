import boto3
def vpccreate():
# create VPC
    ec2 = boto3.resource('ec2')

    vpc = ec2.create_vpc(CidrBlock='192.168.0.0/16')
    # we can assign a name to vpc, or any resource, by using tag
    vpc.create_tags(Tags=[{"Key": "Name", "Value": "default_1vpc"}])
    vpc.wait_until_available()
    print(vpc.id)

    # create then attach internet gateway
    ig = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=ig.id)
    print(ig.id)
    ec2Client = boto3.client('ec2')
    ec2Client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
    ec2Client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )
    # create a route table and a public route
    route_table = vpc.create_route_table()
    route = route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=ig.id
    )
    print(route_table.id)

    # create subnet
    subnet1 = ec2.create_subnet(AvailabilityZone='us-east-1b',
                                CidrBlock='192.168.48.0/20', 
                                VpcId=vpc.id
                                )
    subnet2 = ec2.create_subnet(AvailabilityZone='us-east-1c',
                                CidrBlock='192.168.80.0/20',
                                VpcId=vpc.id
                                )
    print(subnet1.id)

    # associate the route table with the subnet
    route_table.associate_with_subnet(SubnetId=subnet1.id)
    route_table.associate_with_subnet(SubnetId=subnet2.id)
    return vpc,subnet1.id,subnet2.id


# Create sec group
def security(vpc):
    ec2 = boto3.resource('ec2')
    client=boto3.client('ec2')
    sec_group = ec2.create_security_group(
        GroupName='slice_0', Description='slice_0 sec group', VpcId=vpc.id)
    sec_group.authorize_ingress(
        CidrIp='0.0.0.0/0',
        IpProtocol='TCP',
        FromPort=0,
        ToPort=600
    )

    client.enable_vpc_classic_link(
        VpcId=vpc
    )
    print(sec_group.id)
    return sec_group.id

#image from running ec2
def imagecreate():
    ec2 = boto3.resource('ec2')
    host = ec2.Instance('i-06e707d92fc1318c6')
    image = host.create_image(Name='dev' + '_2')
    print(image.id)
    return image.id
#wait up to image create
def wait(imageid):
    ec2 = boto3.client('ec2')
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[imageid])
#creates auto scaling launch config group
def autoscaling(name,configname,subnet1,subnet2):
    client = boto3.client('autoscaling')
    response = client.create_auto_scaling_group(
    AutoScalingGroupName='testauto',
    LaunchConfigurationName=configname,
    LoadBalancerNames=[name],
    VPCZoneIdentifier=subnet1+','+subnet2,
    MinSize=1,
    MaxSize=2,)
#creates auto scaling  group
def launch(imageid,secid,configname,vpc):
    client = boto3.client('autoscaling')
    response1 = client.create_launch_configuration(
    LaunchConfigurationName=configname,
    ImageId=imageid,
    ClassicLinkVPCId=vpc,
    KeyName='chiru_test',
    InstanceType='t2.micro',
    SecurityGroups=[
        secid
    ],
     ClassicLinkVPCSecurityGroups=[
        secid
    ]
    )

def loadbalancer(secid,name,subnet1,subnet2):
    client = boto3.client('elb')
    response = client.create_load_balancer(
        LoadBalancerName=name,
        Listeners=[
            {
                'Protocol': 'TCP',
                'LoadBalancerPort': 80,
                'InstanceProtocol': 'TCP',
                'InstancePort': 80
            },
        ],
        SecurityGroups=[
            secid
        ]

        ,
    Subnets=[
        subnet1,subnet2
    ]
    )
    response = client.modify_load_balancer_attributes(
    LoadBalancerAttributes={
        'CrossZoneLoadBalancing': {
            'Enabled': True,
        },
    },
        LoadBalancerName=name,
    )
def main():
    #create vpc and subnets
    vpc,subnet1,subnet2=vpccreate()
    #create security group for vpc
    vpc='vpc-a063e0da'
    secid=security(vpc)
    #create image backup fo running ec2 instance 
    imageid=imagecreate()
    #wait until the instance is image is done
    wait(imageid)
    #create a load balancer 
    loadbalancername='testload'
    loadbalancer(secid,loadbalancername,subnet1,subnet2)
    #create a launch template 
    configname='first'
    launch(imageid,secid,configname,vpc)
    #creates a auto scaling group with loadbalancer
    autoscaling(loadbalancername,configname,subnet1,subnet2)
main()
