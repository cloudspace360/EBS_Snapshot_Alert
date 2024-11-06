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
    instance_id = "Unknown"
    instance_name = "Unknown"
    private_ip = "N/A"
    public_ip = "N/A"
    volume_id = "N/A"
    snapshot_ids = []
    volume_ids = []
    
    try:
        # Filter snapshots based on the event time
        start_time = detail.get('startTime', event['time'])
        
        snapshots = ec2_client.describe_snapshots(
            Filters=[{'Name': 'start-time', 'Values': [start_time]}]
        )['Snapshots']
        
        # Collect snapshot IDs and retrieve volume IDs
        for snapshot in snapshots:
            snapshot_ids.append(snapshot['SnapshotId'])
            volume_ids.append(snapshot['VolumeId'])

        # Attempt to find the instance attached to each volume
        for vol_id in volume_ids:
            volume_info = ec2_client.describe_volumes(VolumeIds=[vol_id])
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
                break  # Stop once we find the instance info

    except Exception as e:
        print(f"Error fetching snapshot or instance details: {str(e)}")

    # Format the notification message
    formatted_message = (
        f"EC2 Instance Snapshot Notification\n"
        f"Time: {event['time']}\n"
        f"Result: {detail.get('result', 'Unknown')}\n"
        f"Start Time: {detail.get('startTime', 'Unknown')}\n"
        f"End Time: {detail.get('endTime', 'Unknown')}\n"
        f"Snapshot IDs: {', '.join(snapshot_ids) if snapshot_ids else 'Unknown'}\n"
        f"Source Volume IDs: {', '.join(volume_ids) if volume_ids else 'N/A'}\n\n"
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
