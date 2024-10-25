import json
import boto3
import os

# Initialize AWS clients
ec2_client = boto3.client('ec2')
sns = boto3.client('sns')

# Retrieve SNS Topic ARN from environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:200493767521:Snapshot_EmailAlert')

def lambda_handler(event, context):
    # Extract details from the EventBridge event
    detail = event['detail']
    instance_id = detail.get('instance-id', 'N/A')
    
    # Safeguard: Only proceed if instance ID is found
    if instance_id != 'N/A':
        try:
            # Describe the instance to get details
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]

            # Extract instance tags and details
            instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unknown')
            private_ip = instance.get('PrivateIpAddress', 'N/A')
            public_ip = instance.get('PublicIpAddress', 'N/A')

            # Format message
            formatted_message = (
                f"EC2 Instance Details:\n"
                f"Server Name: {instance_name}\n"
                f"Private IP: {private_ip}\n"
                f"Public IP: {public_ip}\n\n"
                f"EBS Snapshot Notification\n"
                f"Time: {event['time']}\n"
                f"Result: {detail.get('result', 'Unknown')}\n"
                f"Start Time: {detail.get('startTime', 'Unknown')}\n"
                f"End Time: {detail.get('endTime', 'Unknown')}\n"
                f"Snapshot ID: {detail.get('snapshot_id', 'Unknown')}\n"
                f"Source: {detail.get('source', 'Unknown')}"
            )
        except Exception as e:
            # Error handling if instance details cannot be fetched
            print(f"Error fetching instance details: {str(e)}")
            formatted_message = f"Error fetching instance details: {str(e)}"
    else:
        # Handle case where instance_id is not found in the event
        formatted_message = (
            f"EBS Snapshot Notification\n"
            f"Time: {event['time']}\n"
            f"Result: {detail.get('result', 'Unknown')}\n\n"
            f"Start Time: {detail.get('startTime', 'Unknown')}\n"
            f"End Time: {detail.get('endTime', 'Unknown')}\n"
            f"Snapshot ID: {detail.get('snapshot_id', 'Unknown')}\n"
            f"Source: {detail.get('source', 'Unknown')}\n"
            f"Instance ID not found in event details."
        )
    
    # Send the formatted message to SNS
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=formatted_message,
        Subject="EBS Instance Details & Snapshot Alert"
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Notification Sent!')
    }
