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
    volume_id = detail.get('source', 'Unknown').split('/')[-1]  # Extract volume ID from event source
    instance_name = "Unknown"
    private_ip = "N/A"
    public_ip = "N/A"
    
    try:
        # Describe the volume to find associated instance
        volume_info = ec2_client.describe_volumes(VolumeIds=[volume_id])
        attachments = volume_info['Volumes'][0].get('Attachments', [])
        
        if attachments:
            instance_id = attachments[0]['InstanceId']
            # Fetch instance details if attached
            instance_info = ec2_client.describe_instances(InstanceIds=[instance_id])
            instance = instance_info['Reservations'][0]['Instances'][0]
            
            # Extract instance name from tags
            instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unknown')
            private_ip = instance.get('PrivateIpAddress', 'N/A')
            public_ip = instance.get('PublicIpAddress', 'N/A')
        else:
            instance_id = "Not Attached"
    except Exception as e:
        print(f"Error fetching volume or instance details: {str(e)}")
        instance_id = "Error fetching instance details"

    # Format the notification message
    formatted_message = (
        f"EBS Snapshot Notification\n"
        f"Time: {event['time']}\n"
        f"Result: {detail.get('result', 'Unknown')}\n\n"
        f"Start Time: {detail.get('startTime', 'Unknown')}\n"
        f"End Time: {detail.get('endTime', 'Unknown')}\n"
        f"Snapshot ID: {detail.get('snapshot_id', 'Unknown')}\n"
        f"Source: {detail.get('source', 'Unknown')}\n\n"
        f"Associated EC2 Instance Details:\n"
        f"Instance ID: {instance_id}\n"
        f"Instance Name: {instance_name}\n"
        f"Private IP: {private_ip}\n"
        f"Public IP: {public_ip}\n"
    )

    # Send the formatted message to SNS
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=formatted_message,
        Subject="EBS Snapshot & Instance Details Alert"
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Notification Sent!')
    }
