#!/usr/bin/python
##Rebalance ECS Tasks on all available cluster instances

"""Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License."""

import boto3
import botocore
import os

#Initialize ecs client
ecs = boto3.client('ecs');

#Cluster name is passed in from a exported CloudFormation value
cluster_name=os.environ['ECSClusterName']

def lambda_handler(event, context):

    #Return all services deployed in the cluster
    def get_cluster_services():
        isTruncated = "True"
        nextToken = ""
        all_services = []

        while ("True" == isTruncated):
            if "" == nextToken:
                response = ecs.list_services(
                    cluster=cluster_name
                )
            else:
                response = ecs.list_services(
                    cluster=cluster_name,
                    nextToken=nextToken
                )

            if  response.has_key("nextToken"):
                nextToken = response["nextToken"]
            else:
                isTruncated = "False"

            #For each service, figure out the taskDefinition, register a new version
            #and update the service -- This sequence will rebalance the tasks on all
            #available and connected instances
            desc_response = ecs.describe_services(
                cluster=cluster_name,
                services=response["serviceArns"]
            )

            for service in desc_response["services"]:
                all_services.append(service)

        return all_services

    #Rebalance ECS tasks of all services deployed in the cluster
    def rebalance_tasks():
        all_services = get_cluster_services()

        for service in all_services:

            print ("service : ", service)

            response = ecs.update_service(
                cluster=cluster_name,
                service=service["serviceArn"],
                forceNewDeployment=True
            )

            print ("Rebalanced the service ", service)

        print ("Rebalanced all of the services")

    ###############################################

    ##Get details about the ECS container instance from the event
    event_detail = event["detail"]
    containerInstanceArn = event_detail["containerInstanceArn"]
    agentConnected = event_detail["agentConnected"]
    ec2InstanceId = event_detail["ec2InstanceId"]

    ##Describe the container instance that caused the event.
    response = ecs.describe_container_instances(
        cluster=cluster_name,
        containerInstances=[containerInstanceArn]
    )

    containerInstances = response["containerInstances"]
    print "Number of container instances", len(containerInstances)
    if(len(containerInstances) != 0):
        containerInstance = containerInstances[0]
        numberOfRunningTasks = containerInstance["runningTasksCount"]
        numberOfPendingTasks = containerInstance["pendingTasksCount"]
        version = containerInstance["version"]

        if numberOfRunningTasks == 0 and numberOfPendingTasks == 0 and agentConnected == True:
            print ("Rebalancing the tasks due to the event.")
            rebalance_tasks()
        else :
            print ("Event does not warrant task rebalancing.")

